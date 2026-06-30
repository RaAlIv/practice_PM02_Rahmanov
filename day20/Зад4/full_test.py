import sys
import os
import pytest
import requests
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.user_defect import (
    validate_email,
    validate_password,
    validate_age,
    create_user,
    update_user_age
)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Файл config.json не найден. Telegram уведомления отключены.")
        return {}
    except json.JSONDecodeError:
        print("Ошибка в формате config.json. Telegram уведомления отключены.")
        return {}

config = load_config()
TELEGRAM_BOT_TOKEN = config.get('telegram_bot_token', '')
TELEGRAM_CHAT_ID = config.get('telegram_chat_id', '')

def send_telegram_notification(test_name, error_message, test_file="full_test.py"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram не настроен. Пропускаем уведомление.")
        return
    
    if len(error_message) > 500:
        error_message = error_message[:500] + "..."
    
    message = f"""ОШИБКА ТЕСТА

Файл: {test_file}
Тест: {test_name}
Ошибка: 
{error_message}
Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        print("Уведомление в Telegram отправлено")
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

@pytest.fixture(autouse=True)
def notify_on_failure(request):
    yield
    if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
        test_name = request.node.name
        error_message = str(request.node.rep_call.longrepr)
        send_telegram_notification(test_name, error_message)

def test_validate_email_valid():
    assert validate_email("user@example.com") is True
    assert validate_email("test@mail.ru") is True

def test_validate_email_no_at():
    assert validate_email("userexample.com") is False

def test_validate_email_empty():
    assert validate_email("") is False

@pytest.mark.parametrize("email, expected", [
    ("user+tag@example.com", True),
    ("user.name@example.com", True),
    ("user_name@example.com", True),
    ("user@sub.domain.com", True),
    ("user@example.co.uk", True),
    ("user@example", False),
    ("user@.com", False),
    ("user@example.c", False),
    ("user@exa_mple.com", False),
])
def test_validate_email_parametrized(email, expected):
    assert validate_email(email) == expected

def test_validate_password_valid():
    assert validate_password("Passw0rd!") is True
    assert validate_password("P@ssw0rd") is True

def test_validate_password_too_short():
    assert validate_password("Pass1!") is False

def test_validate_password_no_digit():
    assert validate_password("Password!") is False

def test_validate_password_no_special():
    assert validate_password("Password1") is False

@pytest.mark.parametrize("password, expected", [
    ("Passw0rd!", True),
    ("Pass123!", True),
    ("Passw0rd", False),
    ("P@ssw0rd", True),
    ("Passwo1!", True),
    ("12345678!", False),
    ("Passw0rd@", True),
    ("Abc123!!", True),
    ("short1!", False),
    ("NoSpecial1", False),
    ("NoDigit!", False),
])
def test_validate_password_parametrized(password, expected):
    assert validate_password(password) == expected

def test_validate_age_valid():
    assert validate_age(25) is True
    assert validate_age(18) is True
    assert validate_age(120) is True

def test_validate_age_too_young():
    assert validate_age(17) is False

def test_validate_age_too_old():
    assert validate_age(121) is False
    assert validate_age(150) is False

def test_validate_age_negative():
    assert validate_age(-5) is False

@pytest.mark.parametrize("age, expected", [
    (18, True),
    (120, True),
    (25, True),
    (17, False),
    (121, False),
    (0, False),
    (-5, False),
    (150, False),
])
def test_validate_age_parametrized(age, expected):
    assert validate_age(age) == expected

def test_validate_age_non_integer():
    assert validate_age(25.5) is False
    assert validate_age("25") is False
    assert validate_age(None) is False

def test_create_user_valid():
    user = create_user("test@example.com", "Passw0rd!", 25)
    assert user["email"] == "test@example.com"
    assert user["age"] == 25
    assert user["active"] is True

def test_create_user_invalid_email():
    with pytest.raises(ValueError, match="Invalid email"):
        create_user("invalid", "Passw0rd!", 25)

def test_create_user_invalid_password():
    with pytest.raises(ValueError, match="Invalid password"):
        create_user("test@example.com", "password", 25)

def test_create_user_invalid_age():
    with pytest.raises(ValueError, match="Invalid age"):
        create_user("test@example.com", "Passw0rd!", 15)

def test_create_user_age_121():
    with pytest.raises(ValueError, match="Invalid age"):
        create_user("test@example.com", "Passw0rd!", 121)

def test_create_user_invalid_age_type():
    with pytest.raises(ValueError, match="Age must be integer"):
        create_user("test@example.com", "Passw0rd!", 25.5)

def test_update_user_age_valid():
    user = create_user("test@example.com", "Passw0rd!", 25)
    updated = update_user_age(user, 30)
    assert updated["age"] == 30

def test_update_user_age_invalid():
    user = create_user("test@example.com", "Passw0rd!", 25)
    with pytest.raises(ValueError, match="Invalid age"):
        update_user_age(user, 15)

def test_update_user_age_empty_user():
    with pytest.raises(ValueError, match="User not found"):
        update_user_age(None, 30)