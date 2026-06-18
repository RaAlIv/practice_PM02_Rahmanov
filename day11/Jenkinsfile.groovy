// Jenkinsfile - Ночное тестирование восстановления (02:00 каждый день)

pipeline {
    agent any
    
    triggers {
        // Запуск каждый день в 02:00
        cron('0 2 * * *')
    }
    
    parameters {
        string(name: 'ENVIRONMENT', defaultValue: 'staging', description: 'Окружение для теста')
        string(name: 'BACKUP_DATE', defaultValue: '', description: 'Дата бэкапа (пусто - последний)')
        choice(name: 'TEST_TYPE', choices: ['full', 'quick', 'chaos'], description: 'Тип теста')
    }
    
    environment {
        AWS_REGION = 'us-east-1'
        S3_BUCKET = 'fenix-backups-prod'
        SLACK_WEBHOOK = credentials('slack-webhook-url')
    }
    
    stages {
        stage('Подготовка') {
            steps {
                script {
                    echo '🚀 Начало ночного тестирования восстановления'
                    echo "📅 Дата: ${new Date()}"
                    echo "🌍 Окружение: ${params.ENVIRONMENT}"
                }
            }
        }
        
        stage('Развертывание тестового кластера') {
            steps {
                script {
                    echo '🔄 Развертывание изолированного кластера в Staging'
                    sh '''
                        cd terraform/staging
                        terraform init
                        terraform apply -auto-approve \
                            -var="environment=nightly-test" \
                            -var="instance_count=3" \
                            -var="db_size=small"
                    '''
                    echo '✅ Кластер развернут'
                }
            }
        }
        
        stage('Восстановление CockroachDB') {
            steps {
                script {
                    echo '🔄 Восстановление CockroachDB из последнего бэкапа'
                    sh '''
                        # Скачивание Full бэкапа
                        aws s3 cp s3://${S3_BUCKET}/cockroach/full/latest.dump.gz /tmp/latest.dump.gz
                        gunzip /tmp/latest.dump.gz
                        
                        # Восстановление
                        cockroach sql --insecure -e "RESTORE FROM '/tmp/latest.dump';"
                        
                        # Применение WAL (если есть)
                        if [ -d "/tmp/wal" ]; then
                            cockroach sql --insecure -e "RESTORE FROM '/tmp/wal' AS OF SYSTEM TIME follower_read_timestamp();"
                        fi
                    '''
                    echo '✅ CockroachDB восстановлен'
                }
            }
        }
        
        stage('Восстановление Elasticsearch') {
            steps {
                script {
                    echo '🔄 Восстановление Elasticsearch из снапшота'
                    sh '''
                        curl -X PUT "http://elasticsearch-test:9200/_snapshot/s3_repo" -H 'Content-Type: application/json' -d'
                        {
                            "type": "s3",
                            "settings": { "bucket": "'${S3_BUCKET}'", "region": "'${AWS_REGION}'" }
                        }'
                        
                        curl -X POST "http://elasticsearch-test:9200/_snapshot/s3_repo/snapshot_latest/_restore" -H 'Content-Type: application/json' -d'
                        {
                            "indices": "products,catalog",
                            "ignore_unavailable": true
                        }'
                    '''
                    echo '✅ Elasticsearch восстановлен'
                }
            }
        }
        
        stage('Валидация данных') {
            steps {
                script {
                    echo '🔍 Валидация восстановленных данных'
                    sh '''
                        # Проверка количества заказов
                        ORDER_COUNT=$(cockroach sql --insecure -e "SELECT COUNT(*) FROM orders;" | tail -n1)
                        echo "📊 Количество заказов: $ORDER_COUNT"
                        
                        # Проверка количества товаров в Elasticsearch
                        PRODUCT_COUNT=$(curl -s "http://elasticsearch-test:9200/products/_count" | jq '.count')
                        echo "📊 Количество товаров: $PRODUCT_COUNT"
                        
                        # Проверка Redis (цены)
                        REDIS_PRICE=$(redis-cli -h redis-test GET "price:test_sku_1")
                        echo "📊 Цена тестового товара: $REDIS_PRICE"
                        
                        # Сохранение результатов в файл
                        echo "order_count=$ORDER_COUNT" > /tmp/validation_results.txt
                        echo "product_count=$PRODUCT_COUNT" >> /tmp/validation_results.txt
                        echo "redis_price=$REDIS_PRICE" >> /tmp/validation_results.txt
                    '''
                }
            }
        }
        
        stage('Chaos-тестирование (если выбрано)') {
            when {
                expression { params.TEST_TYPE == 'chaos' }
            }
            steps {
                script {
                    echo '💀 Запуск Chaos-инжектора'
                    sh '''
                        # Удаление таблицы
                        cockroach sql --insecure -e "DROP TABLE orders CASCADE;"
                        echo "⚠️ Таблица orders удалена"
                        
                        # Повреждение файлов в S3 (имитация)
                        aws s3 cp s3://${S3_BUCKET}/test/clean.txt s3://${S3_BUCKET}/test/clean.txt.backup
                        aws s3 cp s3://${S3_BUCKET}/test/clean.txt s3://${S3_BUCKET}/test/clean.txt.corrupted
                        echo "⚠️ Файлы повреждены"
                    '''
                    echo '💀 Chaos-инжектор завершен'
                }
            }
            
            post {
                always {
                    script {
                        echo '🔄 Повторное восстановление после Chaos'
                        sh '''
                            # Восстановление удаленной таблицы
                            cockroach sql --insecure -e "RESTORE TABLE orders FROM 's3://${S3_BUCKET}/cockroach/inc/latest';"
                            echo "✅ Таблица orders восстановлена"
                        '''
                    }
                }
            }
        }
        
        stage('Генерация отчета') {
            steps {
                script {
                    echo '📝 Генерация отчета о тестировании'
                    
                    // Сбор метрик
                    def startTime = currentBuild.startTimeInMillis
                    def duration = (System.currentTimeMillis() - startTime) / 60000
                    
                    // Формирование JSON-отчета
                    sh """
                        cat > /tmp/test_report.json << EOF
                        {
                            "test_date": "$(date -Iseconds)",
                            "environment": "${params.ENVIRONMENT}",
                            "test_type": "${params.TEST_TYPE}",
                            "duration_minutes": ${duration},
                            "status": "SUCCESS",
                            "results": $(cat /tmp/validation_results.txt | jq -R -s -c 'split("\n") | map(select(. != "")) | map(split("=") | {(.): .}) | add')
                        }
                        EOF
                    """
                    
                    // Сохранение отчета в S3
                    sh """
                        aws s3 cp /tmp/test_report.json s3://${S3_BUCKET}/test-reports/test_$(date +%Y%m%d_%H%M%S).json
                    """
                    
                    echo '✅ Отчет сгенерирован и сохранен'
                }
            }
        }
        
        stage('Отправка уведомления в Slack') {
            steps {
                script {
                    def status = currentBuild.result ?: 'SUCCESS'
                    def emoji = status == 'SUCCESS' ? '✅' : '❌'
                    
                    sh """
                        curl -X POST -H 'Content-Type: application/json' -d '
                        {
                            "text": "${emoji} Ночное тестирование восстановления ${status}\n",
                            "attachments": [{
                                "color": "${status == 'SUCCESS' ? 'good' : 'danger'}",
                                "fields": [
                                    {"title": "Окружение", "value": "${params.ENVIRONMENT}", "short": true},
                                    {"title": "Тип теста", "value": "${params.TEST_TYPE}", "short": true},
                                    {"title": "Время выполнения", "value": "${duration} мин", "short": true},
                                    {"title": "Ссылка на отчет", "value": "s3://${S3_BUCKET}/test-reports/", "short": false}
                                ]
                            }]
                        }' ${SLACK_WEBHOOK}
                    """
                }
            }
        }
    }
    
    post {
        always {
            stage('Очистка') {
                steps {
                    script {
                        echo '🧹 Удаление тестового кластера'
                        sh '''
                            cd terraform/staging
                            terraform destroy -auto-approve \
                                -var="environment=nightly-test"
                        '''
                        echo '✅ Кластер удален'
                    }
                }
            }
        }
        
        failure {
            script {
                echo '❌ Тест завершился неудачей! Срочно проверьте план восстановления.'
                // Отправка критического оповещения
                sh """
                    curl -X POST -H 'Content-Type: application/json' -d '
                    {
                        "text": "🚨 КРИТИЧЕСКАЯ ОШИБКА: Ночной тест восстановления ПРОВАЛИЛСЯ!",
                        "attachments": [{"color": "danger"}]
                    }' ${SLACK_WEBHOOK}
                """
            }
        }
    }
}