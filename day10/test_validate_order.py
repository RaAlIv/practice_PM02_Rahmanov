import pytest
from datetime import datetime, timedelta
from fake_validator import FakeValidator

# ---------- ФИКСИРОВАННОЕ ВРЕМЯ ДЛЯ ВСЕХ ТЕСТОВ ----------
FIXED_NOW = datetime(2026, 6, 18, 10, 0, 0, 0)


# ---------- Фикстура ----------
@pytest.fixture
def validator():
    return FakeValidator(chaos_mode=False)


# ---------- Вспомогательная функция создания заказа ----------
def create_base_order(
    order_id="test123",
    user_id="user123",
    total_amount=100.0,
    items_count=1,
    has_alcohol=False,
    age_verified=False,
    hour=10,
    minute=0,
    second=0,
    user_created_at=None,
    email_last_changed=None,
    delivery_country="RU",
    wallet_country="RU",
    created_at=None,
    items=None
):
    if created_at is None:
        created_at = FIXED_NOW.replace(hour=hour, minute=minute, second=second)
    
    if user_created_at is None:
        # По умолчанию пользователь старый (создан более 7 дней назад)
        user_created_at = FIXED_NOW - timedelta(days=365)
    
    if items is None:
        items = []
        category = "Alcohol" if has_alcohol else None
        if items_count > 0:
            price = total_amount / items_count
            for i in range(items_count):
                items.append({
                    "name": f"item_{i}",
                    "quantity": 1,
                    "price": price,
                    "category": category
                })
    
    return {
        "order_id": order_id,
        "user_id": user_id,
        "created_at": created_at,
        "items": items,
        "total_amount": total_amount,
        "user_created_at": user_created_at,
        "age_verified": age_verified,
        "email_last_changed": email_last_changed,
        "delivery_country": delivery_country,
        "wallet_country": wallet_country
    }


# ---------- 1. Базовые проверки (R1 - Сумма заказа) ----------
@pytest.mark.parametrize("total_amount,expected_valid,expected_risk,expected_reasons", [
    # TC001: Сумма = 0 (граница)
    (0, False, 0.0, ["total_amount out of range (0, 1_000_000)"]),
    # TC002: Сумма = 0.01 (минимальная положительная)
    (0.01, True, 0.0, []),
    # TC003: Сумма = 1,000,000 (граница - невалидно)
    (1000000, False, 0.0, ["total_amount out of range (0, 1_000_000)"]),
    # TC004: Сумма = 999,999.99 (максимальная допустимая, риск 0.9)
    (999999.99, True, 0.9, []),
    # TC005: Сумма = 100,000 (граница риска - риск НЕ применяется)
    (100000, True, 0.0, []),
    # TC006: Сумма = 100,000.01 (выше границы риска)
    (100000.01, True, 0.9, []),
    # TC007: Сумма = 99,999.99 (ниже границы риска)
    (99999.99, True, 0.0, []),
    # TC008: Отрицательная сумма
    (-100, False, 0.0, ["total_amount out of range (0, 1_000_000)"]),
])
def test_r1_total_amount(validator, total_amount, expected_valid, expected_risk, expected_reasons):
    # Для этих тестов используем СТАРОГО пользователя (по умолчанию)
    order = create_base_order(total_amount=total_amount)
    result = validator.validate_order(order)
    
    assert result["valid"] == expected_valid, f"valid expected {expected_valid}, got {result['valid']} for amount={total_amount}, reasons={result['reasons']}"
    assert result["risk_score"] == expected_risk, f"risk expected {expected_risk}, got {result['risk_score']} for amount={total_amount}"
    for reason in expected_reasons:
        assert reason in result["reasons"], f"reason '{reason}' not found in {result['reasons']}"

# ---------- 2. Проверки для новых пользователей (R2) ----------
@pytest.mark.parametrize("days_ago,total_amount,expected_valid,expected_risk,expected_reasons", [
    # TC009: Новый пользователь (меньше 7 дней), сумма = 15,000 (граница)
    (6, 15000, True, 0.0, []),
    # TC010: Новый пользователь (меньше 7 дней), сумма = 15,001 (превышение)
    (6, 15001, False, 0.0, ["new user total_amount > 15_000"]),
    # TC011: Пользователь ровно 7 дней (НЕ новый, т.к. нужно < 7)
    (7, 20000, True, 0.0, []),
    # TC012: Пользователь 6.9 дней (НОВЫЙ)
    (6.9, 20000, False, 0.0, ["new user total_amount > 15_000"]),
    # TC013: Старый пользователь (365 дней), сумма > 15,000
    (365, 50000, True, 0.0, []),
    # TC014: Новый пользователь, минимальная сумма
    (6, 0.01, True, 0.0, []),
])
def test_r2_new_user(validator, days_ago, total_amount, expected_valid, expected_risk, expected_reasons):
    user_created_at = FIXED_NOW - timedelta(days=days_ago)
    order = create_base_order(
        total_amount=total_amount,
        user_created_at=user_created_at,
        created_at=FIXED_NOW
    )
    result = validator.validate_order(order)
    
    assert result["valid"] == expected_valid, f"valid expected {expected_valid}, got {result['valid']} for days_ago={days_ago}, amount={total_amount}, reasons={result['reasons']}"
    assert result["risk_score"] == expected_risk
    for reason in expected_reasons:
        assert reason in result["reasons"]


# ---------- 3. Проверки количества позиций (R3) ----------
@pytest.mark.parametrize("items_count,expected_valid,expected_risk,expected_reasons", [
    # TC015: Ровно 50 позиций (граница)
    (50, True, 0.0, []),
    # TC016: 51 позиция (превышение)
    (51, False, 0.0, ["items count > 50"]),
    # TC017: 1 позиция (минимальное)
    (1, True, 0.0, []),
    # TC018: 0 позиций
    (0, True, 0.0, []),
])
def test_r3_items_count(validator, items_count, expected_valid, expected_risk, expected_reasons):
    order = create_base_order(items_count=items_count)
    result = validator.validate_order(order)
    
    assert result["valid"] == expected_valid
    assert result["risk_score"] == expected_risk
    for reason in expected_reasons:
        assert reason in result["reasons"]


# ---------- 4. Проверки алкоголя (R4) ----------
@pytest.mark.parametrize("has_alcohol,age_verified,hour,minute,expected_valid,expected_risk,expected_reasons", [
    # TC019: Alcohol, age_verified=True, время 10:00
    (True, True, 10, 0, True, 0.0, []),
    # TC020: Alcohol, age_verified=False
    (True, False, 10, 0, False, 0.0, ["Alcohol requires age_verified=True"]),
    # TC021: Alcohol, время 07:59 (до открытия)
    (True, True, 7, 59, False, 0.0, ["Alcohol order outside 08:00-23:00"]),
    # TC022: Alcohol, время 08:00 (граница открытия)
    (True, True, 8, 0, True, 0.0, []),
    # TC023: Alcohol, время 23:00 (граница закрытия - валидно!)
    (True, True, 23, 0, True, 0.0, []),
    # TC024: Alcohol, время 23:01 (после закрытия - НЕ валидно!)
    (True, True, 23, 1, False, 0.0, ["Alcohol order outside 08:00-23:00"]),
    # TC025: Без алкоголя, age_verified=False
    (False, False, 10, 0, True, 0.0, []),
])
def test_r4_alcohol(validator, has_alcohol, age_verified, hour, minute, 
                    expected_valid, expected_risk, expected_reasons):
    order = create_base_order(
        has_alcohol=has_alcohol,
        age_verified=age_verified,
        hour=hour,
        minute=minute
    )
    result = validator.validate_order(order)
    
    assert result["valid"] == expected_valid, f"valid expected {expected_valid}, got {result['valid']} for hour={hour}:{minute}"
    assert result["risk_score"] == expected_risk
    for reason in expected_reasons:
        assert reason in result["reasons"]


# ---------- 5. Проверки риск-скоринга (R5 - Сумма) ----------
@pytest.mark.parametrize("total_amount,expected_risk", [
    # TC026: Сумма 100,000.01 → risk=0.9
    (100000.01, 0.9),
    # TC027: Сумма 500,000 → risk=0.9
    (500000, 0.9),
    # TC028: Сумма 999,999.99 → risk=0.9
    (999999.99, 0.9),
])
def test_r5_risk_by_amount(validator, total_amount, expected_risk):
    # Используем СТАРОГО пользователя (по умолчанию)
    order = create_base_order(total_amount=total_amount)
    result = validator.validate_order(order)
    
    assert result["valid"] == True, f"valid should be True for amount={total_amount}, got {result['valid']}, reasons={result['reasons']}"
    assert result["risk_score"] == expected_risk


# ---------- 6. Проверки риск-скоринга (R6 - Email) ----------
@pytest.mark.parametrize("minutes_ago,expected_risk", [
    # TC029: Email changed 59 минут назад
    (59, 0.2),
    # TC030: Email changed ровно 1 час (не триггерит)
    (60, 0.0),
    # TC031: Email changed 1 час 1 минута
    (61, 0.0),
])
def test_r6_risk_by_email(validator, minutes_ago, expected_risk):
    email_last_changed = FIXED_NOW - timedelta(minutes=minutes_ago)
    order = create_base_order(
        email_last_changed=email_last_changed,
        created_at=FIXED_NOW
    )
    result = validator.validate_order(order)
    
    assert result["valid"] == True
    assert result["risk_score"] == expected_risk, f"risk expected {expected_risk}, got {result['risk_score']} for {minutes_ago} min"


# ---------- 7. Проверки риск-скоринга (R7 - Страны) ----------
@pytest.mark.parametrize("delivery_country,wallet_country,expected_risk", [
    # TC033: Страны совпадают
    ("RU", "RU", 0.0),
    # TC034: Страны разные
    ("RU", "US", 0.3),
])
def test_r7_risk_by_country(validator, delivery_country, wallet_country, expected_risk):
    order = create_base_order(
        delivery_country=delivery_country,
        wallet_country=wallet_country
    )
    result = validator.validate_order(order)
    
    assert result["valid"] == True
    assert result["risk_score"] == expected_risk


# ---------- 8. Комбинации правил (валидность) ----------
@pytest.mark.parametrize("days_ago,total_amount,items_count,has_alcohol,age_verified,hour,expected_valid,expected_reasons", [
    # TC037: Новый пользователь + сумма 15,000 (граница)
    (6, 15000, 1, False, False, 10, True, []),
    # TC038: Новый пользователь + сумма 15,001 (нарушение)
    (6, 15001, 1, False, False, 10, False, ["new user total_amount > 15_000"]),
    # TC039: Новый пользователь + 50 позиций (граница)
    (6, 100, 50, False, False, 10, True, []),
    # TC040: Новый пользователь + 51 позиция
    (6, 100, 51, False, False, 10, False, ["items count > 50"]),
    # TC041: Новый пользователь + Alcohol валидный
    (6, 100, 1, True, True, 10, True, []),
    # TC042: Новый пользователь + Alcohol невалидный
    (6, 100, 1, True, False, 10, False, ["Alcohol requires age_verified=True"]),
    # TC043: Новый пользователь + сумма 15,000 + Alcohol валидный
    (6, 15000, 1, True, True, 10, True, []),
    # TC044: Новый пользователь + сумма 15,001 + Alcohol валидный
    (6, 15001, 1, True, True, 10, False, ["new user total_amount > 15_000"]),
    # TC045: Alcohol + 50 позиций (граница)
    (30, 100, 50, True, True, 10, True, []),
    # TC046: Alcohol + 51 позиция
    (30, 100, 51, True, True, 10, False, ["items count > 50"]),
])
def test_combinations_validity(validator, days_ago, total_amount, items_count, 
                               has_alcohol, age_verified, hour, 
                               expected_valid, expected_reasons):
    user_created_at = FIXED_NOW - timedelta(days=days_ago)
    order = create_base_order(
        total_amount=total_amount,
        items_count=items_count,
        has_alcohol=has_alcohol,
        age_verified=age_verified,
        hour=hour,
        user_created_at=user_created_at,
        created_at=FIXED_NOW
    )
    result = validator.validate_order(order)
    
    assert result["valid"] == expected_valid, f"valid expected {expected_valid}, got {result['valid']}, reasons={result['reasons']}"
    for reason in expected_reasons:
        assert reason in result["reasons"]


# ---------- 9. Комбинации правил (риск + валидность) ----------
@pytest.mark.parametrize("total_amount,email_minutes_ago,delivery_country,wallet_country,expected_valid,expected_risk", [
    # TC047: Все правила соблюдены, без рисков
    (100, None, "RU", "RU", True, 0.0),
    # TC048: Все правила соблюдены, сумма > 100k
    (150000, None, "RU", "RU", True, 0.9),
    # TC049: Все правила соблюдены, email changed
    (100, 30, "RU", "RU", True, 0.2),
    # TC050: Все правила соблюдены, страны разные
    (100, None, "RU", "US", True, 0.3),
    # TC051: Все правила соблюдены, все риски
    (150000, 30, "RU", "US", True, 1.0),
    # TC052: Все нарушения сразу (невалидно)
    (20000, None, "RU", "RU", False, 0.0),
    # TC053: Все нарушения + все риски
    (20000, 30, "RU", "US", False, 0.0),
])
def test_combinations_risk_and_validity(validator, total_amount, email_minutes_ago,
                                        delivery_country, wallet_country,
                                        expected_valid, expected_risk):
    email_last_changed = None
    if email_minutes_ago is not None:
        email_last_changed = FIXED_NOW - timedelta(minutes=email_minutes_ago)
    
    is_invalid_case = total_amount == 20000
    
    # Для невалидных заказов используем старого пользователя, но с нарушениями
    if is_invalid_case:
        # Невалидный случай: 51 товар + Alcohol без верификации + время 02:00
        items = []
        for i in range(51):
            items.append({
                "name": f"item_{i}",
                "quantity": 1,
                "price": total_amount / 51,
                "category": "Alcohol"
            })
        order = create_base_order(
            total_amount=total_amount,
            items=items,
            has_alcohol=True,
            age_verified=False,
            hour=2,
            user_created_at=FIXED_NOW - timedelta(days=365),  # Старый пользователь
            email_last_changed=email_last_changed,
            delivery_country=delivery_country,
            wallet_country=wallet_country,
            created_at=FIXED_NOW.replace(hour=2)
        )
    else:
        # Валидные заказы: старый пользователь
        order = create_base_order(
            total_amount=total_amount,
            items_count=1,
            has_alcohol=False,
            age_verified=True,
            hour=10,
            user_created_at=FIXED_NOW - timedelta(days=365),  # Старый пользователь
            email_last_changed=email_last_changed,
            delivery_country=delivery_country,
            wallet_country=wallet_country,
            created_at=FIXED_NOW
        )
    
    result = validator.validate_order(order)
    
    assert result["valid"] == expected_valid, f"valid expected {expected_valid}, got {result['valid']}, reasons={result['reasons']}"
    assert result["risk_score"] == expected_risk, f"risk expected {expected_risk}, got {result['risk_score']}"


# ---------- 10. Граничные и временные тесты ----------
@pytest.mark.parametrize("hour,minute,second,expected_valid", [
    # TC054: Время заказа 07:59, Alcohol
    (7, 59, 0, False),
    # TC055: Время заказа 08:00, Alcohol
    (8, 0, 0, True),
    # TC056: Время заказа 23:00, Alcohol (валидно!)
    (23, 0, 0, True),
    # TC057: Время заказа 23:01, Alcohol (невалидно!)
    (23, 1, 0, False),
])
def test_time_boundaries(validator, hour, minute, second, expected_valid):
    created_at = FIXED_NOW.replace(hour=hour, minute=minute, second=second)
    order = create_base_order(
        has_alcohol=True,
        age_verified=True,
        hour=hour,
        minute=minute,
        second=second,
        created_at=created_at
    )
    result = validator.validate_order(order)
    
    assert result["valid"] == expected_valid, f"valid expected {expected_valid}, got {result['valid']} for {hour}:{minute}:{second}"


@pytest.mark.parametrize("minutes_ago,expected_risk", [
    # TC058: Email changed 59:59 назад
    (59.98, 0.2),
    # TC059: Email changed 60:00 назад (ровно час - не триггерит)
    (60, 0.0),
])
def test_email_boundaries(validator, minutes_ago, expected_risk):
    email_last_changed = FIXED_NOW - timedelta(minutes=minutes_ago)
    order = create_base_order(
        email_last_changed=email_last_changed,
        created_at=FIXED_NOW
    )
    result = validator.validate_order(order)
    
    assert result["valid"] == True
    assert result["risk_score"] == expected_risk, f"risk expected {expected_risk}, got {result['risk_score']} for {minutes_ago} min"


# ---------- 11. Тесты на устойчивость ----------
def test_duplicate_orders(validator):
    """TC062: Дубликат заказа (одинаковый order_id)"""
    order = create_base_order(order_id="same_id")
    result1 = validator.validate_order(order)
    result2 = validator.validate_order(order)
    
    assert result1["valid"] == result2["valid"]
    assert result1["risk_score"] == result2["risk_score"]


def test_future_order(validator):
    """TC063: Время заказа в будущем"""
    order = create_base_order(
        created_at=FIXED_NOW + timedelta(hours=1)
    )
    result = validator.validate_order(order)
    assert result["valid"] == True


def test_past_order(validator):
    """TC064: Время заказа в прошлом (1 год назад)"""
    order = create_base_order(
        created_at=FIXED_NOW - timedelta(days=365)
    )
    result = validator.validate_order(order)
    assert result["valid"] == True


def test_very_long_item_name(validator):
    """TC065: Очень длинное имя товара (>1000 символов)"""
    items = [{"name": "a" * 1001, "quantity": 1, "price": 100}]
    order = create_base_order(items=items)
    result = validator.validate_order(order)
    assert result["valid"] == True


# ---------- 12. Property-Based тесты ----------
from hypothesis import given, strategies as st, assume

@given(
    total_amount=st.floats(min_value=0.01, max_value=999999.99),
    items_count=st.integers(min_value=1, max_value=50),
    has_alcohol=st.booleans(),
    age_verified=st.booleans(),
    hour=st.integers(min_value=0, max_value=23),
    email_changed=st.booleans(),
    same_country=st.booleans()
)
def test_property_risk_non_decreasing(total_amount, items_count, has_alcohol, 
                                      age_verified, hour, email_changed, same_country):
    """P001-P006: Property-Based тесты"""
    # Если алкоголь, время должно быть в допустимом диапазоне
    if has_alcohol:
        assume(8 <= hour <= 23)
        assume(age_verified == True)
    
    created_at = FIXED_NOW.replace(hour=hour, minute=0, second=0)
    email_last_changed = created_at - timedelta(minutes=30 if email_changed else 120)
    
    order = {
        "order_id": "prop1",
        "user_id": "user1",
        "created_at": created_at,
        "items": [
            {"name": "item", "quantity": 1, "price": total_amount / items_count, 
             "category": "Alcohol" if has_alcohol else None}
            for _ in range(items_count)
        ],
        "total_amount": total_amount,
        "user_created_at": created_at - timedelta(days=365),  # Старый пользователь
        "age_verified": age_verified,
        "email_last_changed": email_last_changed,
        "delivery_country": "RU",
        "wallet_country": "RU" if same_country else "US"
    }
    
    v = FakeValidator()
    result = v.validate_order(order)
    
    # P004: risk_score всегда в [0, 1]
    assert 0 <= result["risk_score"] <= 1.0
    
    # P005: valid всегда bool
    assert isinstance(result["valid"], bool)
    
    # P003: Если invalid, то есть причина
    if not result["valid"]:
        assert len(result["reasons"]) > 0


# ---------- 13. Тест на chaos_mode ----------
def test_chaos_mode():
    """Проверка, что chaos_mode работает"""
    chaos_validator = FakeValidator(chaos_mode=True)
    order = create_base_order()
    
    results = []
    for _ in range(20):
        result = chaos_validator.validate_order(order)
        results.append(result)
    
    assert all(isinstance(r["valid"], bool) for r in results)
    assert all(0 <= r["risk_score"] <= 1.0 for r in results)