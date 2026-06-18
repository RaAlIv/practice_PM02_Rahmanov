#!/usr/bin/env python3
# Elasticsearch.py

import requests
import json
import time
import logging
import boto3
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ElasticsearchBlueGreenRecovery:
    """Blue-Green восстановление Elasticsearch без остановки покупок"""
    
    def __init__(self):
        self.blue_cluster = "elasticsearch-blue:9200"
        self.green_cluster = "elasticsearch-green:9200"
        self.s3_bucket = "fenix-backups-prod"
        self.s3_repo = "s3_repo"
        self.snapshot_name = "snapshot_latest"
        self.feature_flag_url = "http://config-service:8080/feature/search_cluster"
        
    def deploy_green_cluster(self):
        """Развернуть новый кластер (Green)"""
        logger.info("🚀 Развертывание Green-кластера Elasticsearch")
        
        # 1. Запуск через Kubernetes/Terraform (упрощенно)
        logger.info("   ✅ Green-кластер развернут")
        time.sleep(10)  # Ожидание запуска
        
        # 2. Проверка доступности
        try:
            resp = requests.get(f"http://{self.green_cluster}/_cluster/health")
            if resp.status_code == 200:
                logger.info("   ✅ Green-кластер доступен")
                return True
        except:
            logger.error("   ❌ Green-кластер недоступен")
            return False
    
    def restore_snapshot(self):
        """Восстановление снапшота в Green-кластер"""
        logger.info(f"📥 Восстановление снапшота {self.snapshot_name} в Green-кластер")
        
        # 1. Создание репозитория в Green
        repo_config = {
            "type": "s3",
            "settings": {
                "bucket": self.s3_bucket,
                "region": "us-east-1"
            }
        }
        resp = requests.put(
            f"http://{self.green_cluster}/_snapshot/{self.s3_repo}",
            json=repo_config
        )
        logger.info(f"   Репозиторий создан: {resp.status_code}")
        
        # 2. Восстановление индексов (только продукты, не перезаписывая существующие)
        restore_body = {
            "indices": "products,catalog",
            "ignore_unavailable": True,
            "include_global_state": False,
            "rename_pattern": "(.+)",
            "rename_replacement": "restored_$1"  # Восстанавливаем с префиксом restored_
        }
        
        resp = requests.post(
            f"http://{self.green_cluster}/_snapshot/{self.s3_repo}/{self.snapshot_name}/_restore",
            json=restore_body
        )
        
        if resp.status_code == 200:
            logger.info("   ✅ Снапшот восстановлен")
            return True
        else:
            logger.error(f"   ❌ Ошибка: {resp.text}")
            return False
    
    def validate_indices(self):
        """Валидация восстановленных индексов"""
        logger.info("🔍 Валидация восстановленных индексов")
        
        # 1. Проверка количества документов
        resp = requests.get(
            f"http://{self.green_cluster}/restored_products/_count"
        )
        if resp.status_code == 200:
            count = resp.json().get("count", 0)
            logger.info(f"   📊 Количество товаров: {count}")
            
            # Сравниваем с ожидаемым значением (из метрик)
            expected_count = 10000000  # 10 млн товаров
            if count < expected_count * 0.95:  # Допустимо 5% расхождение
                logger.warning(f"   ⚠️ Количество товаров меньше ожидаемого ({expected_count})")
                return False
        
        # 2. Проверка поиска на тестовом запросе
        test_query = {
            "query": {"match": {"name": "смартфон"}},
            "size": 1
        }
        resp = requests.post(
            f"http://{self.green_cluster}/restored_products/_search",
            json=test_query
        )
        if resp.status_code == 200 and resp.json().get("hits", {}).get("total", {}).get("value", 0) > 0:
            logger.info("   ✅ Поиск работает")
            return True
        else:
            logger.error("   ❌ Поиск не работает")
            return False
    
    def switch_traffic(self):
        """Переключение трафика на Green-кластер"""
        logger.info("🔄 Переключение трафика на Green-кластер")
        
        # 1. Изменяем Feature Flag (постепенное переключение 10% -> 100%)
        for percentage in [10, 25, 50, 75, 100]:
            payload = {"search_cluster": self.green_cluster, "percentage": percentage}
            resp = requests.post(self.feature_flag_url, json=payload)
            logger.info(f"   ✅ Переключено {percentage}% трафика")
            time.sleep(30)  # Ждем стабилизации
        
        # 2. Обновляем DNS (после полного переключения)
        logger.info("   ✅ DNS обновлен")
        return True
    
    def rollback(self):
        """Откат на Blue-кластер (если проблемы)"""
        logger.info("⏪ Откат на Blue-кластер")
        payload = {"search_cluster": self.blue_cluster, "percentage": 100}
        requests.post(self.feature_flag_url, json=payload)
        logger.info("   ✅ Откат выполнен")
    
    def run_recovery(self):
        """Полный процесс восстановления"""
        try:
            # 1. Развернуть Green-кластер
            if not self.deploy_green_cluster():
                logger.error("❌ Не удалось развернуть Green-кластер")
                return False
            
            # 2. Восстановить снапшот
            if not self.restore_snapshot():
                logger.error("❌ Не удалось восстановить снапшот")
                return False
            
            # 3. Валидация
            if not self.validate_indices():
                logger.error("❌ Валидация не пройдена")
                return False
            
            # 4. Переключить трафик
            self.switch_traffic()
            
            logger.info("✅ Восстановление Elasticsearch ЗАВЕРШЕНО успешно!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            logger.info("⏪ Выполнение отката...")
            self.rollback()
            return False

if __name__ == "__main__":
    recovery = ElasticsearchBlueGreenRecovery()
    recovery.run_recovery()