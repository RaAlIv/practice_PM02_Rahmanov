# Спецификация сервиса validate_order

## Назначение
Сервис принимает заказ и возвращает:
- `valid` — прошёл ли заказ валидацию,
- `reasons` — список нарушений (если есть),
- `risk_score` — оценка риска (0..1).

## Входной формат (Pydantic)
```python
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

class OrderItem(BaseModel):
    name: str
    quantity: int = Field(ge=1)
    price: float = Field(ge=0)
    category: Optional[str] = None

class Order(BaseModel):
    order_id: str
    user_id: str
    created_at: datetime          # момент создания заказа
    items: List[OrderItem]
    total_amount: float
    user_created_at: datetime     # дата регистрации пользователя
    age_verified: bool
    email_last_changed: Optional[datetime] = None
    delivery_country: str
    wallet_country: str