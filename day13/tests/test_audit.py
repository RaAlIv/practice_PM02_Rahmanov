# day13/test_audit.py
import sys
import os

# Добавляем текущую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.domain.models import Hotel, Room
from src.services.booking_service import BookingService
from src.services.booking_service_audit import AuditDecorator
from src.services.pricing_service import PricingService
from src.uow.unit_of_work import UnitOfWork
from src.dto.booking_dto import BookingCreateDTO
from datetime import date


def test_audit():
    print("=" * 50)
    print("Тестирование аудит-логов")
    print("=" * 50)
    
    # Создаем UoW
    uow = UnitOfWork()
    
    # Создаем тестовый отель и номер
    print("\n1. Создание тестовых данных...")
    hotel = Hotel(id=None, name="Test Hotel", address="Test Address", phone="+123456789")
    saved_hotel = uow.hotels.add(hotel)
    print(f"   ✅ Создан отель ID: {saved_hotel.id}")
    
    room = Room(id=None, hotel_id=saved_hotel.id, number="101", capacity=2, price_per_night=100.0)
    saved_room = uow.rooms.add(room)
    print(f"   ✅ Создан номер ID: {saved_room.id}")
    
    # Создаем сервис с аудитом
    pricing_service = PricingService()
    booking_service = BookingService(uow, pricing_service)
    audit_service = AuditDecorator(booking_service)
    
    # Устанавливаем контекст выполнения
    audit_service.set_context(
        user_id=1,
        user_role="admin",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0"
    )
    
    # Создаем бронирование
    dto = BookingCreateDTO(
        room_id=saved_room.id,
        guest_name="John Doe",
        guest_email="john@example.com",
        check_in=date(2026, 6, 15),
        check_out=date(2026, 6, 20)
    )
    
    print("\n2. Создание бронирования...")
    try:
        result = audit_service.create(dto)
        print(f"   ✅ Создано бронирование ID: {result.id}")
        print(f"   💰 Стоимость: {result.total_price} руб.")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return
    
    print("\n3. Проверка аудит-логов...")
    logs = uow.audit_logs.get_all()
    print(f"   📝 Всего аудит-логов: {len(logs)}")
    
    for log in logs:
        print(f"   - {log.action_type.value}: бронирование {log.booking_id}")
        print(f"     Пользователь: {log.user_role} (ID: {log.user_id})")
    
    print("\n4. Отмена бронирования...")
    try:
        audit_service.cancel(result.id)
        print(f"   ✅ Бронирование {result.id} отменено")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("\n5. Проверка аудит-логов после отмены...")
    logs = uow.audit_logs.get_all()
    print(f"   📝 Всего аудит-логов: {len(logs)}")
    
    for log in logs:
        print(f"   - {log.action_type.value}: бронирование {log.booking_id}")
        if log.old_data:
            old_status = log.old_data.get('status', 'N/A')
            print(f"     Старый статус: {old_status}")
        if log.new_data:
            new_status = log.new_data.get('status', 'N/A')
            print(f"     Новый статус: {new_status}")
        if log.changed_fields:
            print(f"     Измененные поля: {', '.join(log.changed_fields)}")
    
    print("\n6. Получение аудит-логов по бронированию...")
    booking_logs = uow.audit_logs.get_by_booking(result.id)
    print(f"   📝 Найдено {len(booking_logs)} логов для бронирования {result.id}")
    
    print("\n7. Детальная информация об аудит-логах:")
    for log in booking_logs:
        print(f"   📋 Лог #{log.id}:")
        print(f"      Действие: {log.action_type.value}")
        print(f"      Время: {log.created_at}")
        print(f"      Описание: {log.description}")
        if log.old_data:
            print(f"      Было: {log.old_data.get('status', 'N/A')}")
        if log.new_data:
            print(f"      Стало: {log.new_data.get('status', 'N/A')}")
    
    print("\n" + "=" * 50)
    print("✅ Тест завершен успешно!")


if __name__ == "__main__":
    test_audit()