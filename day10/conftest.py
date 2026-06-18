import pytest
from fake_validator import FakeValidator

@pytest.fixture
def validator():
    """Фикстура для тестов"""
    return FakeValidator(chaos_mode=False)