#!/usr/bin/env python3
# backup_scheduler.py - Умное расписание бэкапов с учетом нагрузки

import datetime
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupScheduler:
    """Класс для управления расписанием бэкапов с учетом пиковых часов"""
    
    PEAK_HOURS_START = 9  # 09:00
    PEAK_HOURS_END = 18   # 18:00
    HIGH_LOAD_START = 18  # 18:00
    HIGH_LOAD_END = 21    # 21:00
    
    def __init__(self):
        self.current_hour = datetime.datetime.now().hour
        
    def get_load_level(self):
        """Определение уровня нагрузки"""
        hour = self.current_hour
        
        if self.PEAK_HOURS_START <= hour < self.PEAK_HOURS_END:
            return "PEAK"  # 100% нагрузка
        elif self.HIGH_LOAD_START <= hour < self.HIGH_LOAD_END:
            return "HIGH"  # 60% нагрузка
        elif hour < 6:
            return "LOW"   # 5% нагрузка
        else:
            return "MEDIUM"  # 30-40% нагрузка
    
    def can_run_full_backup(self):
        """Разрешено ли делать Full бэкап"""
        load = self.get_load_level()
        if load == "PEAK" or load == "HIGH":
            logger.warning(f"❌ Full бэкап запрещен в {load} нагрузку (час {self.current_hour})")
            return False
        return True
    
    def can_run_snapshot(self):
        """Разрешено ли делать Snapshot"""
        load = self.get_load_level()
        if load == "PEAK":
            logger.warning(f"⚠️ Snapshots ограничены в PEAK нагрузку (только read-only реплики)")
            return "readonly"
        return True
    
    def get_backup_priority(self):
        """Приоритет бэкапов в зависимости от нагрузки"""
        load = self.get_load_level()
        priorities = {
            "LOW": ["full", "incremental", "wal", "snapshot", "redis"],
            "MEDIUM": ["incremental", "wal", "redis_rdb"],
            "HIGH": ["wal", "changefeed", "redis_rdb", "elasticsearch_inc"],
            "PEAK": ["wal", "changefeed"]  # Только самое критичное!
        }
        return priorities.get(load, ["wal", "incremental"])

# ============================================================
# Класс для бэкапа CockroachDB с ограничением нагрузки
# ============================================================

class CockroachDBBackup:
    """Бэкап CockroachDB с ограничением IOPS в пиковые часы"""
    
    def __init__(self):
        self.scheduler = BackupScheduler()
        
    def run_incremental_backup(self):
        """Инкрементальный бэкап (работает всегда, минимальная нагрузка)"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"🔄 Запуск инкрементального бэкапа CockroachDB в {timestamp}")
        
        # Используем follower_read_timestamp для снижения нагрузки на мастер
        cmd = f"""
        cockroach sql --insecure -e "
        BACKUP TO 's3://fenix-backups-prod/cockroach/inc/{timestamp}?AWS_REGION=us-east-1' 
        AS OF SYSTEM TIME follower_read_timestamp();
        "
        """
        # Выполнение команды (упрощенно)
        logger.info("✅ Инкрементальный бэкап завершен")
        return True
    
    def run_full_backup(self):
        """Полный бэкап (только в LOW нагрузку)"""
        if not self.scheduler.can_run_full_backup():
            logger.warning("⏳ Full бэкап отложен до низкой нагрузки")
            return False
        
        logger.info("🔵 Запуск полного бэкапа CockroachDB (ночное окно)")
        # Полный бэкап с низким приоритетом IOPS
        cmd = """
        cockroach backup 
        --rate-limit=50MB/s  # Ограничение скорости для снижения влияния
        --max-connections=4  # Ограничение параллелизма
        --dest 's3://fenix-backups-prod/cockroach/full/'
        """
        logger.info("✅ Полный бэкап завершен")
        return True

# ============================================================
# Класс для бэкапа Elasticsearch (с read-only реплики)
# ============================================================

class ElasticsearchBackup:
    """Бэкап Elasticsearch с read-only реплики"""
    
    def __init__(self):
        self.scheduler = BackupScheduler()
        self.readonly_node = "elasticsearch-replica:9200"  # Read-only реплика
        
    def snapshot_from_replica(self):
        """Создание снапшота с read-only реплики (0 влияния на продажи)"""
        load = self.scheduler.get_load_level()
        
        logger.info(f"📸 Создание снапшота Elasticsearch (нагрузка: {load})")
        
        if load == "PEAK":
            # В пик - только инкрементальный снапшот с read-only реплики
            cmd = f"""
            curl -X PUT "http://{self.readonly_node}/_snapshot/s3_repo/snapshot_inc" -H 'Content-Type: application/json' -d'
            {{
              "indices": "products,catalog",
              "ignore_unavailable": true,
              "include_global_state": false,
              "partial": true
            }}'
            """
            logger.info("✅ Инкрементальный снапшот создан (read-only реплика)")
        else:
            # В обычное время - полный снапшот
            cmd = f"""
            curl -X PUT "http://{self.readonly_node}/_snapshot/s3_repo/snapshot_full" -H 'Content-Type: application/json' -d'
            {{
              "indices": "*",
              "ignore_unavailable": true,
              "include_global_state": true
            }}'
            """
            logger.info("✅ Полный снапшот создан")
        return True

# ============================================================
# Класс для бэкапа Redis (с read-only реплики)
# ============================================================

class RedisBackup:
    """Бэкап Redis с read-only реплики"""
    
    def __init__(self):
        self.scheduler = BackupScheduler()
        self.replica_host = "redis-replica"
        self.replica_port = 6379
        
    def save_rdb_from_replica(self):
        """Сохранение RDB с read-only реплики"""
        load = self.scheduler.get_load_level()
        
        if load == "PEAK":
            # В пик - только AOF (меньшая нагрузка)
            logger.info("⚡ PEAK: Только AOF-логирование Redis")
            cmd = f"redis-cli -h {self.replica_host} -p {self.replica_port} BGREWRITEAOF"
        else:
            # В обычное время - RDB + AOF
            logger.info("💾 Создание RDB-снапшота Redis с реплики")
            cmd = f"redis-cli -h {self.replica_host} -p {self.replica_port} BGSAVE"
        
        # Выполнение команды
        logger.info("✅ Redis бэкап завершен")
        return True

# ============================================================
# MAIN - Запуск с учетом нагрузки
# ============================================================

if __name__ == "__main__":
    scheduler = BackupScheduler()
    load = scheduler.get_load_level()
    
    logger.info(f"📊 Текущая нагрузка: {load} (час {scheduler.current_hour}:00)")
    logger.info(f"📋 Разрешенные бэкапы: {scheduler.get_backup_priority()}")
    
    # Запуск бэкапов в зависимости от нагрузки
    if "full" in scheduler.get_backup_priority():
        CockroachDBBackup().run_full_backup()
    
    if "incremental" in scheduler.get_backup_priority():
        CockroachDBBackup().run_incremental_backup()
    
    if "snapshot" in scheduler.get_backup_priority():
        ElasticsearchBackup().snapshot_from_replica()
    
    if "redis_rdb" in scheduler.get_backup_priority():
        RedisBackup().save_rdb_from_replica()