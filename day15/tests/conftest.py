"""
Глобальные фикстуры и настройки для всех тестов.
"""
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
from app.schemas import OrderCreateDTO


@pytest.fixture
def valid_order_data():
    """Фикстура с валидными данными для заказа."""
    return {
        "phone": "+79991234567",
        "email": "test@example.com"
    }


@pytest.fixture
def valid_dto(valid_order_data):
    """Фикстура с созданным валидным DTO."""
    return OrderCreateDTO(**valid_order_data)


@pytest.fixture
def sample_phones():
    """Фикстура с примерами телефонов для тестирования."""
    return {
        "valid": [
            "+79991234567",
            "89991234567",
            "+7-999-123-45-67",
            "+7 999 123 45 67",
            "+7(999)123-45-67"
        ],
        "invalid": [
            "123",
            "abc",
            "+7999123456",
            "+799912345678",
            "+1-999-123-45-67"
        ]
    }


@pytest.fixture
def sample_emails():
    """Фикстура с примерами email для тестирования."""
    return {
        "valid": [
            "user@example.com",
            "admin@company.ru",
            "test+filter@gmail.com"
        ],
        "invalid": [
            "not-an-email",
            "missing@domain",
            "@example.com",
            "user@.com"
        ]
    }