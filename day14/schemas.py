# schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class BoardCreate(BaseModel):
    """Схема создания доски"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Название доски не может быть пустым')
        return v.strip()


class ColumnCreate(BaseModel):
    """Схема создания колонки"""
    name: str = Field(..., min_length=1, max_length=50)
    board_id: int
    order: Optional[int] = 0

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Название колонки не может быть пустым')
        return v.strip()


class TaskCreate(BaseModel):
    """Схема создания задачи"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    column_id: int
    assignee_id: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    due_date: Optional[datetime] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Название задачи не может быть пустым')
        return v.strip()

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v < datetime.now():
            raise ValueError('Дедлайн не может быть в прошлом')
        return v


class TaskUpdate(BaseModel):
    """Схема обновления задачи"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    assignee_id: Optional[int] = None
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError('Название задачи не может быть пустым')
        return v