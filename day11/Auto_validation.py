#!/usr/bin/env python3
# Auto_validation.py - Автоматическая валидация восстановленных данных

import psycopg2
import requests
import redis
import json
import logging
import boto3
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NightlyValidation:
    """Класс для ночной валидации восстановления"""
    
    def __init__(self):
        # Подключения к тестовому окружению
        self.db_conn = psycopg2.connect(
            host="cockroach-test",
            port=26257,
            user="root",
            database="defaultdb"
        )
        self.redis_conn = redis.Redis(host="redis-test", port=6379, db=0)
        self.es_host = "elasticsearch-test:9200"
        self.s3 = boto3.client('s3')
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "status": "PASSED"
        }
    
    def validate_db(self) -> Dict[str, Any]:
        """Валидация CockroachDB"""
        logger.info("🔍 Проверка CockroachDB...")
        checks = {}
        
        try:
            cur = self.db_conn.cursor()
            
            # 1. Проверка количества таблиц
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
            table_count = cur.fetchone()[0]
            checks["table_count"] = {"value": table_count, "expected": 15, "status": "PASSED" if table_count > 10 else "FAILED"}
            
            # 2. Проверка количества заказов
            cur.execute("SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '1 DAY';")
            order_count = cur.fetchone()[0]
            checks["orders_24h"] = {"value": order_count, "expected": 5000, "status": "PASSED" if order_count > 1000 else "FAILED"}
            
            # 3. Проверка консистентности (сумма заказов)
            cur.execute("SELECT SUM(total_amount) FROM orders WHERE status='completed';")
            total_revenue = cur.fetchone()[0] or 0
            checks["total_revenue"] = {"value": total_revenue, "expected": 1000000, "status": "PASSED" if total_revenue > 100000 else "WARNING"}
            
            cur.close()
            logger.info("   ✅ CockroachDB проверена")
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка проверки CockroachDB: {e}")
            checks["error"] = {"value": str(e), "status": "FAILED"}
        
        return checks
    
    def validate_elasticsearch(self) -> Dict[str, Any]:
        """Валидация Elasticsearch"""
        logger.info("🔍 Проверка Elasticsearch...")
        checks = {}
        
        try:
            # 1. Проверка доступности
            resp = requests.get(f"http://{self.es_host}/_cluster/health")
            health = resp.json()
            checks["cluster_health"] = {
                "value": health.get("status", "unknown"),
                "expected": "green",
                "status": "PASSED" if health.get("status") in ["green", "yellow"] else "FAILED"
            }
            
            # 2. Проверка количества документов
            resp = requests.get(f"http://{self.es_host}/products/_count")
            product_count = resp.json().get("count", 0)
            checks["product_count"] = {
                "value": product_count,
                "expected": 10000000,
                "status": "PASSED" if product_count > 9000000 else "FAILED"
            }
            
            # 3. Тестовый поиск
            test_query = {"query": {"match": {"name": "телефон"}}, "size": 1}
            resp = requests.post(f"http://{self.es_host}/products/_search", json=test_query)
            hits = resp.json().get("hits", {}).get("total", {}).get("value", 0)
            checks["search_test"] = {
                "value": hits,
                "expected": 1,
                "status": "PASSED" if hits > 0 else "FAILED"
            }
            
            logger.info("   ✅ Elasticsearch проверен")
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка проверки Elasticsearch: {e}")
            checks["error"] = {"value": str(e), "status": "FAILED"}
        
        return checks
    
    def validate_redis(self) -> Dict[str, Any]:
        """Валидация Redis"""
        logger.info("🔍 Проверка Redis...")
        checks = {}
        
        try:
            # 1. Проверка кэша цен
            test_key = self.redis_conn.get("price:test_sku_1")
            checks["price_cache"] = {
                "value": test_key.decode() if test_key else None,
                "expected": "50000",
                "status": "PASSED" if test_key else "FAILED"
            }
            
            # 2. Проверка сессий
            session_count = self.redis_conn.dbsize()
            checks["session_count"] = {
                "value": session_count,
                "expected": 100000,
                "status": "PASSED" if session_count > 1000 else "WARNING"
            }
            
            # 3. Проверка остатков
            stock = self.redis_conn.get("stock:sku_100500")
            checks["stock_cache"] = {
                "value": stock.decode() if stock else None,
                "expected": 100,
                "status": "PASSED" if stock else "FAILED"
            }
            
            logger.info("   ✅ Redis проверен")
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка проверки Redis: {e}")
            checks["error"] = {"value": str(e), "status": "FAILED"}
        
        return checks
    
    def validate_s3(self) -> Dict[str, Any]:
        """Валидация S3 объектов"""
        logger.info("🔍 Проверка S3...")
        checks = {}
        
        try:
            # 1. Проверка наличия бэкапов
            response = self.s3.list_objects_v2(
                Bucket="fenix-backups-prod",
                Prefix="cockroach/full/",
                MaxKeys=5
            )
            backups = response.get("Contents", [])
            checks["backup_count"] = {
                "value": len(backups),
                "expected": 1,
                "status": "PASSED" if len(backups) > 0 else "FAILED"
            }
            
            # 2. Проверка CRR (кросс-региональная репликация)
            # Проверяем, что объекты есть в us-west-2
            s3_dr = boto3.client('s3', region_name='us-west-2')
            dr_response = s3_dr.list_objects_v2(
                Bucket="fenix-backups-prod",
                Prefix="cockroach/full/",
                MaxKeys=1
            )
            dr_backups = dr_response.get("Contents", [])
            checks["crr_status"] = {
                "value": len(dr_backups),
                "expected": 1,
                "status": "PASSED" if len(dr_backups) > 0 else "FAILED"
            }
            
            logger.info("   ✅ S3 проверен")
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка проверки S3: {e}")
            checks["error"] = {"value": str(e), "status": "FAILED"}
        
        return checks
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Запуск всех проверок"""
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК НОЧНОЙ ВАЛИДАЦИИ ВОССТАНОВЛЕНИЯ")
        logger.info("=" * 60)
        
        # Проверка всех компонентов
        self.results["checks"]["cockroachdb"] = self.validate_db()
        self.results["checks"]["elasticsearch"] = self.validate_elasticsearch()
        self.results["checks"]["redis"] = self.validate_redis()
        self.results["checks"]["s3"] = self.validate_s3()
        
        # Подсчет статуса
        failed_checks = 0
        for component, checks in self.results["checks"].items():
            if isinstance(checks, dict):
                for check_name, check_data in checks.items():
                    if isinstance(check_data, dict) and check_data.get("status") == "FAILED":
                        failed_checks += 1
        
        self.results["status"] = "PASSED" if failed_checks == 0 else "FAILED"
        self.results["failed_checks_count"] = failed_checks
        
        # Сохранение отчета
        report_file = f"/tmp/nightly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=4)
        
        logger.info("=" * 60)
        logger.info(f"📊 Результат: {self.results['status']}")
        logger.info(f"❌ Проваленных проверок: {failed_checks}")
        logger.info(f"📄 Отчет сохранен: {report_file}")
        logger.info("=" * 60)
        
        return self.results

if __name__ == "__main__":
    validator = NightlyValidation()
    results = validator.run_all_validations()
    
    # Отправка результатов в Slack (если есть ошибки)
    if results["status"] == "FAILED":
        logger.error("🚨 ВАЛИДАЦИЯ ПРОВАЛЕНА! Требуется вмешательство!")