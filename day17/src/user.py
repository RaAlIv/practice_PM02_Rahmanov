# src/user.py
"""
Модуль для управления пользователями в системе бронирования
"""
import re
from typing import Optional


def validate_email(email: str) -> bool:
    """Проверить корректность email"""
    if not email:
        return False
    # Полная проверка email с помощью regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> bool:
    """Проверить надежность пароля"""
    # Требования: минимум 8 символов, есть буква, цифра и спецсимвол
    if len(password) < 8:
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c.isalpha() for c in password):  # ← ДОБАВИТЬ ПРОВЕРКУ БУКВ
        return False
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/"
    if not any(c in special_chars for c in password):
        return False
    return True

def validate_age(age: int) -> bool:
    """Проверить возраст (должен быть 18-120)"""
    # Проверка типа
    if not isinstance(age, int):
        return False
    # Проверка границ
    if age < 18 or age > 120:
        return False
    return True


def create_user(email: str, password: str, age: int) -> dict:
    """Создать пользователя с валидацией"""
    # Проверка типа age
    if not isinstance(age, int):
        raise ValueError("Age must be integer")
    
    if not validate_email(email):
        raise ValueError("Invalid email")
    if not validate_password(password):
        raise ValueError("Invalid password")
    if not validate_age(age):
        raise ValueError("Invalid age")
    
    return {
        "email": email,
        "password": "***",  # хэш в реальной системе
        "age": age,
        "active": True
    }


def update_user_age(user: dict, new_age: int) -> dict:
    """Обновить возраст пользователя с валидацией"""
    if not user:
        raise ValueError("User not found")
    if not validate_age(new_age):
        raise ValueError("Invalid age")
    user["age"] = new_age
    return user