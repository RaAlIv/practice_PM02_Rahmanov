import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

from app.models import Base, Order, OrderItem
from app.repositories import OrderRepository


@pytest.fixture(scope="function")
def db_session():
    """
    Фикстура для создания in-memory SQLite базы данных.
    Создаёт все таблицы, возвращает сессию и очищает всё после теста.
    """
    # Создаём in-memory базу
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Создаём все таблицы
    Base.metadata.create_all(engine)
    
    # Создаём фабрику сессий
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    
    # Создаём сессию
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Удаляем все таблицы после теста
        Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def repository(db_session):
    """Фикстура для создания репозитория с тестовой сессией"""
    return OrderRepository(db_session)


@pytest.fixture(scope="function")
def sample_order_data():
    """Пример данных для создания заказа"""
    return {
        "customer_name": "Иван Петров",
        "delivery_address": "ул. Ленина, д. 10, г. Москва",
        "items": [
            {"product_name": "Ноутбук", "quantity": 1, "price": 50000.0},
            {"product_name": "Мышь", "quantity": 2, "price": 1000.0},
            {"product_name": "Клавиатура", "quantity": 1, "price": 3000.0}
        ]
    }


@pytest.fixture(scope="function")
def sample_order(repository, sample_order_data):
    """Создаёт тестовый заказ в базе данных"""
    return repository.create(sample_order_data)