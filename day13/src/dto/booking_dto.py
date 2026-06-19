# src/dto/booking_dto.py
from pydantic import BaseModel, validator
from datetime import date, datetime
from typing import Optional


class BookingCreateDTO(BaseModel):
    room_id: int
    guest_name: str
    guest_email: str
    check_in: date
    check_out: date

    @validator('check_out')
    def validate_dates(cls, v, values):
        if 'check_in' in values and v <= values['check_in']:
            raise ValueError('Дата выезда должна быть позже даты заезда')
        if (v - values['check_in']).days > 30:
            raise ValueError('Бронирование не может превышать 30 дней')
        return v


class BookingResponseDTO(BaseModel):
    id: int
    room_id: int
    guest_name: str
    check_in: date
    check_out: date
    total_price: float
    status: str
    created_at: datetime


class BookingUpdateDTO(BaseModel):
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None