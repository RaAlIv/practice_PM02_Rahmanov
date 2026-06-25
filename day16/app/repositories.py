from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, select
from sqlalchemy.exc import SQLAlchemyError
import httpx
import json

from app.models import Order, OrderItem, OrderStatus
from app.exceptions import EntityNotFoundException, DeliveryCalculationException, ValidationException


class OrderRepository:
    """Репозиторий для работы с заказами"""
    
    def __init__(self, session: Session):
        self.session = session
        self.delivery_api_url = "https://api.delivery.com/calculate"
    
    def create(self, order_data: Dict[str, Any]) -> Order:
        """
        Создаёт заказ и связанные позиции из словаря order_data.
        
        Args:
            order_data: словарь с полями заказа и списком items
            
        Returns:
            Order: созданный объект заказа
            
        Raises:
            ValidationException: при некорректных данных
        """
        try:
            # Валидация данных
            if 'items' not in order_data or not order_data['items']:
                raise ValidationException("Order must have at least one item")
            
            for item in order_data['items']:
                if item.get('quantity', 0) <= 0:
                    raise ValidationException("Item quantity must be positive")
                if item.get('price', 0) <= 0:
                    raise ValidationException("Item price must be positive")
            
            # Создаём заказ
            order = Order(
                customer_name=order_data['customer_name'],
                delivery_address=order_data['delivery_address'],
                status=order_data.get('status', OrderStatus.PENDING),
                total_amount=order_data.get('total_amount', 0.0)
            )
            
            # Добавляем позиции
            for item_data in order_data['items']:
                item = OrderItem(
                    product_name=item_data['product_name'],
                    quantity=item_data['quantity'],
                    price=item_data['price']
                )
                order.items.append(item)
            
            # Вычисляем общую сумму
            order.total_amount = sum(item.quantity * item.price for item in order.items)
            
            self.session.add(order)
            self.session.commit()
            self.session.refresh(order)
            
            return order
            
        except (ValidationException, SQLAlchemyError) as e:
            self.session.rollback()
            raise e
        except Exception as e:
            self.session.rollback()
            raise RuntimeError(f"Failed to create order: {str(e)}")
    
    def find_by_id(self, order_id: int) -> Optional[Order]:
        """
        Возвращает заказ по ID или None, если не найден.
        
        Args:
            order_id: ID заказа
            
        Returns:
            Optional[Order]: найденный заказ или None
        """
        return self.session.query(Order).filter(Order.id == order_id).first()
    
    def find_all_by_status(self, status: str) -> List[Order]:
        """
        Возвращает список заказов с указанным статусом.
        
        Args:
            status: статус заказа
            
        Returns:
            List[Order]: список заказов
        """
        return self.session.query(Order).filter(Order.status == status).all()
    
    def update_status(self, order_id: int, new_status: str) -> Order:
        """
        Обновляет статус заказа.
        
        Args:
            order_id: ID заказа
            new_status: новый статус
            
        Returns:
            Order: обновлённый заказ
            
        Raises:
            EntityNotFoundException: если заказ не найден
        """
        order = self.find_by_id(order_id)
        if not order:
            raise EntityNotFoundException("Order", order_id)
        
        order.status = new_status
        self.session.commit()
        self.session.refresh(order)
        return order
    
    def delete(self, order_id: int) -> None:
        """
        Жёстко удаляет заказ и все его позиции из БД.
        
        Args:
            order_id: ID заказа
            
        Raises:
            EntityNotFoundException: если заказ не найден
        """
        order = self.find_by_id(order_id)
        if not order:
            raise EntityNotFoundException("Order", order_id)
        
        self.session.delete(order)
        self.session.commit()
    
    def find_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Order]:
        """
        Возвращает заказы, созданные в указанном временном интервале.
        
        Args:
            start_date: начальная дата (включительно)
            end_date: конечная дата (включительно)
            
        Returns:
            List[Order]: список заказов
        """
        return self.session.query(Order).filter(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        ).all()
    
    def get_total_amount_for_order(self, order_id: int) -> float:
        """
        Вычисляет сумму всех позиций заказа, используя SQL-агрегацию.
        
        Args:
            order_id: ID заказа
            
        Returns:
            float: общая сумма заказа
            
        Raises:
            EntityNotFoundException: если заказ не найден
        """
        order = self.find_by_id(order_id)
        if not order:
            raise EntityNotFoundException("Order", order_id)
        
        result = self.session.query(
            func.sum(OrderItem.quantity * OrderItem.price)
        ).filter(OrderItem.order_id == order_id).scalar()
        
        return float(result) if result else 0.0
    
    def calculate_delivery_cost(self, order_id: int) -> float:
        """
        Рассчитывает стоимость доставки через внешний API.
        
        Args:
            order_id: ID заказа
            
        Returns:
            float: стоимость доставки
            
        Raises:
            EntityNotFoundException: если заказ не найден
            DeliveryCalculationException: при ошибке API
        """
        order = self.find_by_id(order_id)
        if not order:
            raise EntityNotFoundException("Order", order_id)
        
        # Вычисляем вес (каждый товар весит 0.5 кг)
        total_weight = 0.0
        for item in order.items:
            total_weight += item.quantity * 0.5
        
        # Формируем запрос к API доставки
        payload = {
            "address": order.delivery_address,
            "weight": total_weight
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    self.delivery_api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code >= 400:
                    raise DeliveryCalculationException(
                        f"API returned status {response.status_code}",
                        status_code=response.status_code
                    )
                
                data = response.json()
                cost = data.get("cost")
                if cost is None:
                    raise DeliveryCalculationException("Missing 'cost' field in response")
                
                return float(cost)
                
        except httpx.TimeoutException:
            raise DeliveryCalculationException("API request timeout")
        except httpx.RequestError as e:
            raise DeliveryCalculationException(f"Request error: {str(e)}")
        except json.JSONDecodeError:
            raise DeliveryCalculationException("Invalid JSON response")
        except DeliveryCalculationException:
            raise
        except Exception as e:
            raise DeliveryCalculationException(f"Unexpected error: {str(e)}")