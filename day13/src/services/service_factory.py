# src/services/service_factory.py
from src.services.booking_service import BookingService
from src.services.booking_service_audit import AuditDecorator
from src.services.pricing_service import PricingService
from src.uow.unit_of_work import UnitOfWork

class ServiceFactory:
    """Фабрика для создания сервисов с или без аудита"""
    
    @staticmethod
    def create_booking_service(
        uow: UnitOfWork,
        pricing_service: PricingService,
        enable_audit: bool = True
    ) -> BookingService:
        """
        Создает сервис бронирований.
        
        Args:
            uow: Unit of Work
            pricing_service: Сервис ценообразования
            enable_audit: Включить ли аудит
        
        Returns:
            BookingService: Сервис бронирований (с аудитом или без)
        """
        base_service = BookingService(uow, pricing_service)
        
        if enable_audit:
            # Оборачиваем декоратором для добавления аудита
            return AuditDecorator(base_service)
        
        return base_service