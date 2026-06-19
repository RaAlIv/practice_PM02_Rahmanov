# src/dto/audit_log_dto.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from src.domain.models import AuditActionType  # Относительный импорт


class AuditLogCreateDTO(BaseModel):
    """DTO для создания аудит-лога"""
    booking_id: int
    action_type: AuditActionType
    user_id: Optional[int] = None
    user_role: Optional[str] = None
    old_data: Optional[dict] = None
    new_data: Optional[dict] = None
    changed_fields: Optional[List[str]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    description: Optional[str] = None


class AuditLogResponseDTO(BaseModel):
    """DTO для ответа с аудит-логом"""
    id: int
    booking_id: int
    action_type: str
    user_id: Optional[int]
    user_role: Optional[str]
    old_data: Optional[dict]
    new_data: Optional[dict]
    changed_fields: Optional[List[str]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    description: Optional[str]


class AuditLogFilterDTO(BaseModel):
    """DTO для фильтрации аудит-логов"""
    booking_id: Optional[int] = None
    action_type: Optional[AuditActionType] = None
    user_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 100
    offset: int = 0