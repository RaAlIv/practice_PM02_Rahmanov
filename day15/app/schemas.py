from pydantic import BaseModel, Field, EmailStr, field_validator
import re


class OrderCreateDTO(BaseModel):
    phone: str = Field(..., description="Номер телефона в формате +7XXX...")
    email: EmailStr = Field(..., description="Email адрес")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, value: str) -> str:
        """Валидация телефонного номера."""
        # Убираем все нецифровые символы, кроме +
        cleaned = re.sub(r'[^\d+]', '', value)
        
        # Проверяем, что номер начинается с +7 или 8 и содержит 11 цифр
        pattern = r'^(\+7|8)\d{10}$'
        if not re.match(pattern, cleaned):
            raise ValueError(f'Некорректный номер телефона: {value}')
        
        # Нормализуем: приводим к формату +7XXXXXXXXXX
        if cleaned.startswith('8'):
            cleaned = '+7' + cleaned[1:]
        
        return cleaned