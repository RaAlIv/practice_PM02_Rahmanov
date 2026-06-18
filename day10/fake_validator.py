import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ValidationError

# ---------- Pydantic модели ----------
class OrderItem(BaseModel):
    name: str
    quantity: int
    price: float
    category: Optional[str] = None

class Order(BaseModel):
    order_id: str
    user_id: str
    created_at: datetime
    items: List[OrderItem]
    total_amount: float
    user_created_at: datetime
    age_verified: bool
    email_last_changed: Optional[datetime] = None
    delivery_country: str
    wallet_country: str


# ---------- FakeValidator ----------
class FakeValidator:
    def __init__(self, chaos_mode: bool = False):
        self.chaos_mode = chaos_mode

    def _chaos(self) -> bool:
        return self.chaos_mode and random.random() < 0.05

    def validate_order(self, order_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Chaos mode: случайный сбой
        if self._chaos():
            return {
                "valid": random.choice([True, False]),
                "reasons": ["chaos"] if random.random() > 0.5 else [],
                "risk_score": random.random()
            }

        try:
            order = Order(**order_dict)
        except ValidationError as e:
            return {"valid": False, "reasons": [f"Invalid input structure: {str(e)}"], "risk_score": 0.0}

        reasons = []
        risk_score = 0.0
        now = order.created_at

        # Rule 1: 0 < sum < 1_000_000
        if not (0 < order.total_amount < 1_000_000):
            reasons.append("total_amount out of range (0, 1_000_000)")

        # Rule 2: New user limit
        # Новый пользователь = created_at < 7 дней назад (т.е. зарегистрирован менее 7 дней назад)
        days_diff = (now - order.user_created_at).days
        is_new_user = days_diff < 7  # Исправлено: < 7, а не > 7
        
        if is_new_user and order.total_amount > 15_000:
            reasons.append("new user total_amount > 15_000")

        # Rule 3: Items count
        if len(order.items) > 50:
            reasons.append("items count > 50")

        # Rule 4: Alcohol rules (время 08:00-23:00 включительно)
        has_alcohol = any(item.category == "Alcohol" for item in order.items)
        if has_alcohol:
            if not order.age_verified:
                reasons.append("Alcohol requires age_verified=True")
            # Проверяем полное время (час + минуты)
            order_time = order.created_at.time()
            start_time = datetime.strptime("08:00:00", "%H:%M:%S").time()
            end_time = datetime.strptime("23:00:00", "%H:%M:%S").time()
            if not (start_time <= order_time <= end_time):
                reasons.append("Alcohol order outside 08:00-23:00")

        is_valid = len(reasons) == 0

        # Risk calculations (only if order is valid)
        if is_valid:
            # Risk 5: Amount risk (строго > 100_000)
            if order.total_amount > 100_000:
                risk_score = 0.9

            # Risk 6: Email risk (строго < 1 часа)
            if order.email_last_changed:
                diff = now - order.email_last_changed
                if diff < timedelta(hours=1):
                    risk_score = min(1.0, risk_score + 0.2)

            # Risk 7: Country mismatch
            if order.delivery_country != order.wallet_country:
                risk_score = min(1.0, risk_score + 0.3)

        return {
            "valid": is_valid,
            "reasons": reasons,
            "risk_score": risk_score
        }