from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class OrderStatus(str, enum.Enum):
    """Статусы заказа"""
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"


class Order(Base):
    """Модель заказа"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), nullable=False, default=OrderStatus.PENDING)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    customer_name = Column(String(200), nullable=False)
    delivery_address = Column(String(500), nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)

    # Отношение "один ко многим" с позициями заказа
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self):
        return f"<Order(id={self.id}, status='{self.status}', customer='{self.customer_name}')>"


class OrderItem(Base):
    """Модель позиции заказа"""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    # Отношение к заказу
    order: Mapped["Order"] = relationship("Order", back_populates="items")

    @property
    def total(self) -> float:
        """Общая стоимость позиции"""
        return self.quantity * self.price

    def __repr__(self):
        return f"<OrderItem(id={self.id}, product='{self.product_name}', qty={self.quantity})>"