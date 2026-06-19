# src/services/booking_service.py
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from ..domain.models import Booking, BookingStatus
from ..domain.exceptions import (
    RoomNotFoundError, RoomNotAvailableError,
    BookingConflictError, BookingNotFoundError, InvalidDatesError, DomainError
)
from ..dto.booking_dto import BookingCreateDTO, BookingResponseDTO, BookingUpdateDTO
from ..uow.unit_of_work import UnitOfWork
from .pricing_service import PricingService


class BookingService:
    """Базовый сервис для управления бронированиями (без аудита)"""
    
    def __init__(self, uow: UnitOfWork, pricing_service: PricingService):
        self.uow = uow
        self.pricing_service = pricing_service
        self.booking_repo = uow.bookings
        self.room_repo = uow.rooms
        # Контекст выполнения для аудита
        self._context = {
            'user_id': None,
            'user_role': 'system',
            'ip_address': None,
            'user_agent': None
        }
    
    def set_context(self, user_id: Optional[int] = None, 
                   user_role: str = 'system',
                   ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None):
        """Установить контекст выполнения"""
        self._context.update({
            'user_id': user_id,
            'user_role': user_role,
            'ip_address': ip_address,
            'user_agent': user_agent
        })
    
    def get_context(self) -> dict:
        """Получить контекст выполнения"""
        return self._context.copy()
    
    def create(self, dto: BookingCreateDTO) -> BookingResponseDTO:
        """Создать новое бронирование"""
        # Проверяем существование номера
        room = self.room_repo.get_by_id(dto.room_id)
        if not room:
            raise RoomNotFoundError(f"Номер {dto.room_id} не найден")
        if not room.is_active:
            raise RoomNotFoundError(f"Номер {dto.room_id} не активен")
        
        # Проверяем пересечения бронирований
        existing = self.booking_repo.get_by_room_and_dates(
            dto.room_id, dto.check_in, dto.check_out
        )
        if existing:
            raise BookingConflictError(
                f"Номер {dto.room_id} уже забронирован на эти даты",
                details={"conflicting_bookings": [b.id for b in existing]}
            )
        
        # Рассчитываем стоимость
        total_price = self.pricing_service.calculate_price(
            room, dto.check_in, dto.check_out
        )
        
        # Создаем бронирование
        booking = Booking(
            id=None,
            room_id=dto.room_id,
            guest_name=dto.guest_name,
            guest_email=dto.guest_email,
            check_in=dto.check_in,
            check_out=dto.check_out,
            total_price=total_price,
            status=BookingStatus.PENDING
        )
        
        # Сохраняем
        saved = self.booking_repo.add(booking)
        self.uow.commit()
        
        return BookingResponseDTO(
            id=saved.id,
            room_id=saved.room_id,
            guest_name=saved.guest_name,
            check_in=saved.check_in,
            check_out=saved.check_out,
            total_price=saved.total_price,
            status=saved.status.value,
            created_at=saved.created_at
        )
    
    def cancel(self, booking_id: int) -> bool:
        """Отменить бронирование"""
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise BookingNotFoundError(f"Бронирование {booking_id} не найдено")
        
        if booking.status in (BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT):
            raise DomainError(
                f"Нельзя отменить бронирование в статусе {booking.status.value}"
            )
        
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now()
        booking.updated_at = datetime.now()
        
        self.booking_repo.update(booking)
        self.uow.commit()
        
        return True
    
    def confirm(self, booking_id: int) -> None:
        """Подтвердить бронирование"""
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise BookingNotFoundError(f"Бронирование {booking_id} не найдено")
        
        if booking.status != BookingStatus.PENDING:
            raise DomainError(
                f"Бронирование в статусе {booking.status.value} нельзя подтвердить"
            )
        
        booking.status = BookingStatus.CONFIRMED
        booking.updated_at = datetime.now()
        
        self.booking_repo.update(booking)
        self.uow.commit()
    
    def update(self, booking_id: int, dto: BookingUpdateDTO) -> BookingResponseDTO:
        """Обновить данные бронирования"""
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise BookingNotFoundError(f"Бронирование {booking_id} не найдено")
        
        if booking.status in (BookingStatus.CANCELLED, BookingStatus.CHECKED_OUT):
            raise DomainError(f"Нельзя изменить бронирование в статусе {booking.status.value}")
        
        # Обновляем поля
        if dto.guest_name is not None:
            booking.guest_name = dto.guest_name
        if dto.guest_email is not None:
            booking.guest_email = dto.guest_email
        booking.updated_at = datetime.now()
        
        self.booking_repo.update(booking)
        self.uow.commit()
        
        return BookingResponseDTO(
            id=booking.id,
            room_id=booking.room_id,
            guest_name=booking.guest_name,
            check_in=booking.check_in,
            check_out=booking.check_out,
            total_price=booking.total_price,
            status=booking.status.value,
            created_at=booking.created_at
        )
    
    def get_available_rooms(
        self,
        hotel_id: int,
        check_in: date,
        check_out: date,
        capacity: Optional[int] = None
    ) -> List[dict]:
        """Получить доступные номера в отеле на указанные даты"""
        # 1. Получаем все номера отеля
        rooms = self.room_repo.get_by_hotel(hotel_id, active_only=True)
        
        # 2. Фильтруем по вместимости
        if capacity:
            rooms = [r for r in rooms if r.capacity >= capacity]
        
        # 3. Для каждого номера проверяем доступность
        available = []
        for room in rooms:
            existing = self.booking_repo.get_by_room_and_dates(
                room.id, check_in, check_out
            )
            if not existing:
                available.append({
                    'room_id': room.id,
                    'number': room.number,
                    'capacity': room.capacity,
                    'price_per_night': room.price_per_night
                })
        
        return available
    
    def get_by_id(self, booking_id: int) -> Optional[Booking]:
        """Получить бронирование по ID"""
        return self.booking_repo.get_by_id(booking_id)
    
    def get_all(self, **filters) -> List[Booking]:
        """Получить все бронирования с фильтрами"""
        return self.booking_repo.get_all(**filters)