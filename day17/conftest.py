# conftest.py
import sys
from pathlib import Path

# Добавляем src в путь импорта
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Явно указываем coverage, что нужно измерять модули из папки src
def pytest_configure(config):
    # Эта строка помогает coverage найти src
    pass