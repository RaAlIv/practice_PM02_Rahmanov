#!/usr/bin/env python3
# backup_cockroach.py
# Маркетплейс "ВсёДляВсех" - Резервное копирование CockroachDB

import subprocess
import boto3
import os
import time
import json
import hashlib
import logging
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# ============================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ (сохранение в указанную папку)
# ============================================================
BACKUP_ROOT = r"Y:\24 ИСиП 2025\УП02\Группа 2\Рахманов А\day11\backup_log"

# Создаём вложенные папки для логов и бэкапов
LOG_DIR = os.path.join(BACKUP_ROOT, "logs")
BACKUP_DIR = os.path.join(BACKUP_ROOT, "backups")
REPORTS_DIR = os.path.join(BACKUP_ROOT, "reports")

for dir_path in [LOG_DIR, BACKUP_DIR, REPORTS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Настройка логгера
log_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_filepath = os.path.join(LOG_DIR, log_filename)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath, encoding='utf-8'),
        logging.StreamHandler()  # Вывод в консоль
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
S3_BUCKET = "fenix-backups-prod"
S3_PREFIX = "cockroach/inc/"
IMMUTABLE_DAYS = 7  # Защита от удаления в S3
CLUSTER_URL = "postgresql://root@localhost:26257/defaultdb"
LOCAL_RETENTION_DAYS = 2  # Храним локально 2 дня

# Папки для временного хранения
DUMP_TEMP = os.path.join(BACKUP_DIR, "temp")
os.makedirs(DUMP_TEMP, exist_ok=True)

# ============================================================
# ФУНКЦИИ
# ============================================================

def check_disk_space(path, required_gb=10):
    """
    Проверка свободного места на диске.
    """
    stat = os.statvfs(path)
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
    if free_gb < required_gb:
        raise Exception(f"Недостаточно места на диске! Свободно: {free_gb:.2f} ГБ, требуется: {required_gb} ГБ")
    logger.info(f"Свободно на диске: {free_gb:.2f} ГБ (OK)")
    return free_gb

def create_local_backup_file():
    """
    Создание локального файла бэкапа (дамп таблиц).
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_filename = f"cockroach_full_{timestamp}.sql"
    dump_filepath = os.path.join(DUMP_TEMP, dump_filename)
    
    logger.info(f"Начинаем создание локального дампа: {dump_filename}")
    
    # Команда для создания дампа CockroachDB
    # Используем pg_dump для совместимости (CockroachDB поддерживает PostgreSQL протокол)
    cmd = f"pg_dump -h localhost -U root -d defaultdb -F c -b -v -f \"{dump_filepath}\""
    
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"Локальный дамп создан: {dump_filepath} (размер: {os.path.getsize(dump_filepath) / (1024**2):.2f} МБ)")
        return dump_filepath
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка создания дампа: {e.stderr}")
        raise

def compress_file(filepath):
    """
    Сжатие файла с помощью gzip.
    """
    compressed_file = f"{filepath}.gz"
    logger.info(f"Сжатие файла: {filepath} -> {compressed_file}")
    
    cmd = f"gzip -c \"{filepath}\" > \"{compressed_file}\""
    subprocess.run(cmd, shell=True, check=True)
    
    # Удаляем оригинал после сжатия
    os.remove(filepath)
    logger.info(f"Сжатие завершено. Размер: {os.path.getsize(compressed_file) / (1024**2):.2f} МБ")
    return compressed_file

def calculate_checksum(filepath):
    """
    Вычисление MD5-хеша для проверки целостности.
    """
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    checksum = hash_md5.hexdigest()
    logger.info(f"MD5-хеш: {checksum}")
    return checksum

def upload_to_s3_with_lock(file_path, s3_key):
    """
    Загрузка в S3 с включением Object Lock (Immutable).
    """
    s3 = boto3.client('s3')
    try:
        with open(file_path, 'rb') as f:
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=f,
                ObjectLockMode='GOVERNANCE',
                ObjectLockRetainUntilDate=datetime.now() + timedelta(days=IMMUTABLE_DAYS)
            )
        logger.info(f"Загружено в S3: s3://{S3_BUCKET}/{s3_key} (защищено на {IMMUTABLE_DAYS} дней)")
        return True
    except ClientError as e:
        logger.error(f"Ошибка загрузки в S3: {e}")
        return False

def save_backup_report(filepath, checksum, duration, status):
    """
    Сохранение отчёта о бэкапе в JSON-файл.
    """
    report = {
        "job_name": "cockroach_full_backup",
        "status": status,
        "file_path": filepath,
        "file_size_bytes": os.path.getsize(filepath),
        "duration_seconds": duration,
        "timestamp": datetime.now().isoformat(),
        "checksum_md5": checksum,
        "immutable_days": IMMUTABLE_DAYS
    }
    
    report_filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_filepath = os.path.join(REPORTS_DIR, report_filename)
    
    with open(report_filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
    
    logger.info(f"Отчёт сохранён: {report_filepath}")
    return report_filepath

def cleanup_old_files(days=LOCAL_RETENTION_DAYS):
    """
    Удаление старых локальных бэкапов (старше указанного количества дней).
    """
    cutoff = datetime.now() - timedelta(days=days)
    deleted_count = 0
    
    for root, dirs, files in os.walk(BACKUP_DIR):
        for file in files:
            filepath = os.path.join(root, file)
            # Проверяем дату создания/модификации
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
                deleted_count += 1
                logger.debug(f"Удалён старый файл: {filepath}")
    
    # Также удаляем старые отчёты
    for root, dirs, files in os.walk(REPORTS_DIR):
        for file in files:
            filepath = os.path.join(root, file)
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
                deleted_count += 1
    
    logger.info(f"Очистка завершена. Удалено файлов: {deleted_count}")

def cleanup_logs(days=30):
    """
    Очистка старых логов (по умолчанию храним 30 дней).
    """
    cutoff = datetime.now() - timedelta(days=days)
    deleted_count = 0
    
    for root, dirs, files in os.walk(LOG_DIR):
        for file in files:
            filepath = os.path.join(root, file)
            if file.endswith('.log'):
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if mtime < cutoff:
                    os.remove(filepath)
                    deleted_count += 1
    
    if deleted_count > 0:
        logger.info(f"Удалено старых логов: {deleted_count}")

# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

def run_backup():
    """
    Основная функция запуска резервного копирования.
    """
    start_time = time.time()
    status = "failed"
    dump_file = None
    compressed_file = None
    checksum = None
    
    try:
        logger.info("=" * 60)
        logger.info("ЗАПУСК РЕЗЕРВНОГО КОПИРОВАНИЯ (CockroachDB)")
        logger.info("=" * 60)
        logger.info(f"Папка бэкапов: {BACKUP_DIR}")
        logger.info(f"Папка логов: {LOG_DIR}")
        logger.info(f"Папка отчётов: {REPORTS_DIR}")
        
        # 1. Проверка дискового пространства
        check_disk_space(BACKUP_DIR, required_gb=10)
        
        # 2. Создание локального дампа
        dump_file = create_local_backup_file()
        
        # 3. Сжатие файла
        compressed_file = compress_file(dump_file)
        
        # 4. Вычисление контрольной суммы
        checksum = calculate_checksum(compressed_file)
        
        # 5. Загрузка в S3 (с защитой от удаления)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{S3_PREFIX}{timestamp}/cockroach_full_{timestamp}.sql.gz"
        s3_upload_success = upload_to_s3_with_lock(compressed_file, s3_key)
        
        if not s3_upload_success:
            logger.warning("Загрузка в S3 не удалась, но локальный файл сохранён")
            status = "partial"
        else:
            status = "success"
        
        # 6. Сохранение отчёта
        duration = time.time() - start_time
        save_backup_report(compressed_file, checksum, duration, status)
        
        # 7. Очистка старых файлов
        cleanup_old_files()
        cleanup_logs()
        
        logger.info(f"Резервное копирование ЗАВЕРШЕНО со статусом: {status}")
        logger.info(f"Общее время выполнения: {duration:.2f} секунд")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        status = "failed"
        
        # Сохраняем отчёт об ошибке
        duration = time.time() - start_time
        error_report = {
            "job_name": "cockroach_full_backup",
            "status": "failed",
            "error_message": str(e),
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat()
        }
        error_file = os.path.join(REPORTS_DIR, f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_report, f, indent=4, ensure_ascii=False)
        
        raise

# ============================================================
# ТОЧКА ВХОДА
# ============================================================

if __name__ == "__main__":
    try:
        run_backup()
    except Exception as e:
        logger.error(f"Программа завершена с ошибкой: {e}")
        exit(1)