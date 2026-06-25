# src/user.py
"""
Модуль для управления пользователями в системе бронирования
"""
import re
from typing import Optional

def validate_email(email: str) -> bool:
    """Проверить корректность email"""
    # ОШИБКА: слишком простая валидация, пропускает невалидные email
    if '@' not in email:
        return False
    # ОШИБКА: не проверяет наличие домена после точки
    return True

def validate_password(password: str) -> bool:
    """Проверить надежность пароля"""
    # Требования: минимум 8 символов, есть цифра и спецсимвол
    if len(password) < 8:
        return False
    # ОШИБКА: проверяет только наличие цифры, но не спецсимволов
    if not any(c.isdigit() for c in password):
        return False
    # ОШИБКА: всегда возвращает True, даже если нет спецсимволов
    return True

def validate_age(age: int) -> bool:
    """Проверить возраст (должен быть 18-120)"""
    # ОШИБКА: пропускает отрицательные значения
    if age < 18:
        return False
    # ОШИБКА: не проверяет верхнюю границу
    return True

def create_user(email: str, password: str, age: int) -> dict:
    """Создать пользователя с валидацией"""
    # ОШИБКА: не проверяет age на тип (может быть None)
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
    """Обновить возраст пользователя"""
    # ОШИБКА: не проверяет, что пользователь существует
    # ОШИБКА: не проверяет валидность нового возраста
    user["age"] = new_age
    return user