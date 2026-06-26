"""
Конфигурация pytest для проекта
"""
import sys
from pathlib import Path

# Добавляем корневую папку проекта в PYTHONPATH
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))