# src/repositories/audit_log_repo.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.domain.models import AuditLog
from src.repositories.base import BaseRepository

class AuditLogRepository(BaseRepository[AuditLog]):
    """Репозиторий для работы с аудит-логами (In-Memory)"""
    
    def __init__(self):
        self._storage: Dict[int, AuditLog] = {}
        self._next_id = 1
    
    def get_by_id(self, id: int) -> Optional[AuditLog]:
        return self._storage.get(id)
    
    def get_all(self, **filters) -> List[AuditLog]:
        result = list(self._storage.values())
        
        if 'booking_id' in filters:
            result = [log for log in result if log.booking_id == filters['booking_id']]
        
        if 'action_type' in filters:
            result = [log for log in result if log.action_type == filters['action_type']]
        
        if 'user_id' in filters:
            result = [log for log in result if log.user_id == filters['user_id']]
        
        if 'date_from' in filters:
            result = [log for log in result if log.created_at >= filters['date_from']]
        
        if 'date_to' in filters:
            result = [log for log in result if log.created_at <= filters['date_to']]
        
        # Сортировка по времени создания (новые сверху)
        result.sort(key=lambda x: x.created_at, reverse=True)
        
        return result
    
    def add(self, log: AuditLog) -> AuditLog:
        log.id = self._next_id
        self._storage[log.id] = log
        self._next_id += 1
        return log
    
    def update(self, log: AuditLog) -> AuditLog:
        if log.id not in self._storage:
            raise ValueError(f"AuditLog with id {log.id} not found")
        self._storage[log.id] = log
        return log
    
    def delete(self, id: int) -> bool:
        if id in self._storage:
            del self._storage[id]
            return True
        return False
    
    def get_by_booking(self, booking_id: int, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        """Получить все аудит-логи для конкретного бронирования"""
        logs = [log for log in self._storage.values() if log.booking_id == booking_id]
        logs.sort(key=lambda x: x.created_at, reverse=True)
        return logs[offset:offset + limit]