# src/services/booking_service_audit.py
from functools import wraps
from typing import Callable, Any, Optional
from datetime import datetime
import inspect

from ..domain.models import AuditLog, AuditActionType, Booking
from ..domain.exceptions import DomainError
from ..dto.audit_log_dto import AuditLogCreateDTO
from .booking_service import BookingService
from ..uow.unit_of_work import UnitOfWork


class AuditDecorator:
    """
    Декоратор для логирования действий с бронированиями.
    Использует паттерн Decorator для добавления функциональности аудита.
    """
    
    def __init__(self, service: BookingService):
        """
        Инициализация декоратора.
        
        Args:
            service: Базовый сервис бронирований
        """
        self._service = service
        self.uow = service.uow
    
    def set_context(self, user_id: Optional[int] = None, 
                   user_role: str = 'system',
                   ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None):
        """Установить контекст выполнения"""
        self._service.set_context(user_id, user_role, ip_address, user_agent)
    
    def __getattr__(self, name):
        """
        Проксирование всех методов к базовому сервису.
        Декорируем только нужные методы.
        """
        attr = getattr(self._service, name)
        if callable(attr) and name in ['create', 'cancel', 'confirm', 'update']:
            return self._decorate_method(name, attr)
        return attr
    
    def _decorate_method(self, method_name: str, method: Callable) -> Callable:
        """
        Декорирует метод для добавления аудита.
        """
        @wraps(method)
        def wrapper(*args, **kwargs):
            # Получаем контекст из сервиса
            context = self._service.get_context()
            user_id = context.get('user_id')
            user_role = context.get('user_role', 'system')
            ip_address = context.get('ip_address')
            user_agent = context.get('user_agent')
            
            # Определяем действие и получаем данные до выполнения
            action_type, booking_id, old_data = self._prepare_audit_data(
                method_name, args, kwargs
            )
            
            try:
                # Выполняем основной метод
                result = method(*args, **kwargs)
                
                # Получаем данные после выполнения
                new_data = self._get_booking_data(booking_id) if booking_id else None
                
                # Для создания бронирования - получаем ID из результата
                if action_type == AuditActionType.CREATE and result:
                    booking_id = result.id
                    new_data = self._get_booking_data(booking_id)
                
                # Создаем аудит-лог
                self._create_audit_log(
                    booking_id=booking_id if booking_id else 0,
                    action_type=action_type,
                    user_id=user_id,
                    user_role=user_role,
                    old_data=old_data,
                    new_data=new_data,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    description=f"{action_type.value} booking {booking_id if booking_id else 'new'}"
                )
                
                return result
                
            except DomainError as e:
                # Логируем ошибку в аудит
                self._create_audit_log(
                    booking_id=booking_id if booking_id else 0,
                    action_type=action_type,
                    user_id=user_id,
                    user_role=user_role,
                    old_data=old_data,
                    new_data=None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    description=f"ERROR: {str(e)}"
                )
                raise
        
        return wrapper
    
    def _prepare_audit_data(self, method_name: str, args: tuple, kwargs: dict) -> tuple:
        """
        Подготавливает данные для аудита.
        Возвращает (action_type, booking_id, old_data)
        """
        if method_name == 'create':
            return AuditActionType.CREATE, None, None
        
        elif method_name == 'cancel':
            booking_id = args[0] if args else kwargs.get('booking_id')
            old_data = self._get_booking_data(booking_id) if booking_id else None
            return AuditActionType.CANCEL, booking_id, old_data
        
        elif method_name == 'confirm':
            booking_id = args[0] if args else kwargs.get('booking_id')
            old_data = self._get_booking_data(booking_id) if booking_id else None
            return AuditActionType.CONFIRM, booking_id, old_data
        
        elif method_name == 'update':
            booking_id = args[0] if args else kwargs.get('booking_id')
            old_data = self._get_booking_data(booking_id) if booking_id else None
            return AuditActionType.UPDATE, booking_id, old_data
        
        return AuditActionType.UPDATE, None, None
    
    def _get_booking_data(self, booking_id: int) -> Optional[dict]:
        """Получает данные бронирования для аудита"""
        booking = self.uow.bookings.get_by_id(booking_id)
        if not booking:
            return None
        
        return {
            'id': booking.id,
            'room_id': booking.room_id,
            'guest_name': booking.guest_name,
            'guest_email': booking.guest_email,
            'check_in': booking.check_in.isoformat() if booking.check_in else None,
            'check_out': booking.check_out.isoformat() if booking.check_out else None,
            'total_price': booking.total_price,
            'status': booking.status.value if booking.status else None,
            'created_at': booking.created_at.isoformat() if booking.created_at else None,
        }
    
    def _get_changed_fields(self, old_data: Optional[dict], new_data: Optional[dict]) -> list:
        """Определяет измененные поля"""
        if not old_data or not new_data:
            return []
        
        changed = []
        for key in old_data.keys():
            if key in new_data and old_data[key] != new_data[key]:
                changed.append(key)
        return changed
    
    def _create_audit_log(
        self,
        booking_id: int,
        action_type: AuditActionType,
        user_id: Optional[int],
        user_role: str,
        old_data: Optional[dict],
        new_data: Optional[dict],
        ip_address: Optional[str],
        user_agent: Optional[str],
        description: str
    ):
        """
        Создает запись в аудит-логе.
        """
        # Определяем измененные поля
        changed_fields = self._get_changed_fields(old_data, new_data)
        
        # Создаем сущность AuditLog
        audit_log = AuditLog(
            id=None,
            booking_id=booking_id,
            action_type=action_type,
            user_id=user_id,
            user_role=user_role,
            old_data=old_data,
            new_data=new_data,
            changed_fields=changed_fields,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(),
            description=description
        )
        
        # Сохраняем аудит-лог
        self.uow.audit_logs.add(audit_log)
        self.uow.commit()