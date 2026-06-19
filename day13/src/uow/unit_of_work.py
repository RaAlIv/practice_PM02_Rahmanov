# src/uow/unit_of_work.py
from contextlib import contextmanager
from typing import Type
from src.repositories.booking_repo import BookingRepository
from src.repositories.hotel_repo import HotelRepository
from src.repositories.room_repo import RoomRepository
from src.repositories.audit_log_repo import AuditLogRepository

class UnitOfWork:
    def __init__(self):
        self._hotel_repo = HotelRepository()
        self._room_repo = RoomRepository()
        self._booking_repo = BookingRepository()
        self._audit_log_repo = AuditLogRepository()
        self._committed = False
    
    @property
    def hotels(self) -> HotelRepository:
        return self._hotel_repo
    
    @property
    def rooms(self) -> RoomRepository:
        return self._room_repo
    
    @property
    def bookings(self) -> BookingRepository:
        return self._booking_repo
    
    @property
    def audit_logs(self) -> AuditLogRepository:
        return self._audit_log_repo
    
    def commit(self) -> None:
        """Фиксация транзакции"""
        self._committed = True
    
    def rollback(self) -> None:
        """Откат транзакции"""
        self._committed = False
    
    @contextmanager
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        elif not self._committed:
            self.commit()