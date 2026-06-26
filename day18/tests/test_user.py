"""
Тесты для модуля user.py - Управление пользователями
Вариант 5
"""
import pytest
from datetime import datetime
from src.user import (
    User, UserRole, UserValidator, UserService, UserRepository
)


# ============================================
# КЛАСС: Тесты для UserValidator
# ============================================

class TestUserValidator:
    """Тесты валидатора пользователей"""
    
    # --- Тесты для validate_email ---
    
    def test_validate_email_valid(self):
        """Проверка корректного email"""
        validator = UserValidator()
        assert validator.validate_email("user@example.com") is True
        assert validator.validate_email("john.doe@domain.ru") is True
        assert validator.validate_email("test123@mail.org") is True
        assert validator.validate_email("user.name@sub.domain.com") is True
        assert validator.validate_email("user+tag@example.com") is True
    
    def test_validate_email_invalid(self):
        """Проверка некорректного email"""
        validator = UserValidator()
        assert validator.validate_email("") is False
        assert validator.validate_email("user@") is False
        assert validator.validate_email("user.com") is False
        assert validator.validate_email("user@domain") is False
        assert validator.validate_email("user@domain.c") is False
        assert validator.validate_email("user@.com") is False
        assert validator.validate_email("user@domain.") is False
        assert validator.validate_email("user@domain..com") is False
        assert validator.validate_email(".user@domain.com") is False
        assert validator.validate_email("user name@domain.com") is False
    
    @pytest.mark.parametrize("email,expected", [
        ("user@example.com", True),
        ("john.doe@domain.ru", True),
        ("user+tag@example.com", True),
        ("user.name@sub.domain.com", True),
        ("user@example.co.uk", True),
        ("user@example.c", False),
        ("user@.com", False),
        ("user@domain.", False),
        ("user@domain..com", False),
        (".user@domain.com", False),
        ("user@domain.com.", False),
        ("user name@domain.com", False),
        ("", False),
    ])
    def test_validate_email_parametrized(self, email, expected):
        """Параметризованные тесты для email"""
        validator = UserValidator()
        assert validator.validate_email(email) == expected
    
    # --- Тесты для validate_password ---
    
    def test_validate_password_valid(self):
        """Проверка корректного пароля"""
        validator = UserValidator()
        assert validator.validate_password("Password123") is True
        assert validator.validate_password("SecurePass1") is True
        assert validator.validate_password("StrongP@ssw0rd") is True
    
    def test_validate_password_invalid(self):
        """Проверка некорректного пароля"""
        validator = UserValidator()
        assert validator.validate_password("") is False
        assert validator.validate_password("short") is False
        assert validator.validate_password("onlyletters") is False
        assert validator.validate_password("12345678") is False
        assert validator.validate_password("Pass123") is False  # Меньше 8 символов
    
    @pytest.mark.parametrize("password,expected", [
        ("Password123", True),
        ("SecurePass1", True),
        ("StrongP@ssw0rd", True),
        ("12345678", False),
        ("abcdefgh", False),
        ("Pass123", False),
        ("", False),
    ])
    def test_validate_password_parametrized(self, password, expected):
        """Параметризованные тесты для пароля"""
        validator = UserValidator()
        assert validator.validate_password(password) == expected
    
    # --- Тесты для validate_age ---
    
    def test_validate_age_valid(self):
        """Проверка корректного возраста"""
        validator = UserValidator()
        assert validator.validate_age(18) is True
        assert validator.validate_age(25) is True
        assert validator.validate_age(65) is True
        assert validator.validate_age(120) is True
    
    def test_validate_age_invalid(self):
        """Проверка некорректного возраста"""
        validator = UserValidator()
        assert validator.validate_age(17) is False
        assert validator.validate_age(121) is False
        assert validator.validate_age(0) is False
        assert validator.validate_age(-5) is False
    
    @pytest.mark.parametrize("age,expected", [
        (18, True),
        (25, True),
        (120, True),
        (17, False),
        (121, False),
        (0, False),
        (-5, False),
    ])
    def test_validate_age_parametrized(self, age, expected):
        """Параметризованные тесты для возраста"""
        validator = UserValidator()
        assert validator.validate_age(age) == expected
    
    # --- Тесты для validate_username ---
    
    @pytest.mark.parametrize("username,expected", [
        ("john_doe", True),
        ("John123", True),
        ("user", True),
        ("a", False),
        ("ab", False),
        ("john doe", False),
        ("john@doe", False),
        ("", False),
    ])
    def test_validate_username_parametrized(self, username, expected):
        """Тесты для валидации username"""
        validator = UserValidator()
        assert validator.validate_username(username) == expected


# ============================================
# КЛАСС: Тесты для UserService
# ============================================

class TestUserService:
    """Тесты сервиса пользователей"""
    
    # --- Тесты для create_user ---
    
    def test_create_user_success(self):
        """Успешное создание пользователя"""
        service = UserService()
        user = service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25,
            role=UserRole.GUEST
        )
        
        assert user.id is not None
        assert user.id == 1
        assert user.username == "john_doe"
        assert user.email == "john@example.com"
        assert user.age == 25
        assert user.role == UserRole.GUEST
        assert user.is_active is True
        assert user.created_at is not None
    
    def test_create_user_with_hotelier_role(self):
        """Создание пользователя с ролью HOTELIER"""
        service = UserService()
        user = service.create_user(
            username="hotelier1",
            email="hotel@example.com",
            password="Password123",
            age=30,
            role=UserRole.HOTELIER
        )
        
        assert user.role == UserRole.HOTELIER
    
    def test_create_user_invalid_username(self):
        """Создание пользователя с невалидным username"""
        service = UserService()
        with pytest.raises(ValueError, match="Invalid username"):
            service.create_user(
                username="",
                email="john@example.com",
                password="Password123",
                age=25
            )
    
    def test_create_user_invalid_email(self):
        """Создание пользователя с невалидным email"""
        service = UserService()
        with pytest.raises(ValueError, match="Invalid email"):
            service.create_user(
                username="john_doe",
                email="invalid-email",
                password="Password123",
                age=25
            )
    
    def test_create_user_invalid_password(self):
        """Создание пользователя со слабым паролем"""
        service = UserService()
        with pytest.raises(ValueError, match="Password is too weak"):
            service.create_user(
                username="john_doe",
                email="john@example.com",
                password="weak",
                age=25
            )
    
    def test_create_user_invalid_age(self):
        """Создание пользователя с невалидным возрастом"""
        service = UserService()
        with pytest.raises(ValueError, match="Invalid age"):
            service.create_user(
                username="john_doe",
                email="john@example.com",
                password="Password123",
                age=17
            )
    
    def test_create_user_duplicate_email(self):
        """Создание пользователя с дублирующимся email (допускается)"""
        service = UserService()
        service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        user2 = service.create_user(
            username="john_doe2",
            email="john@example.com",
            password="Password123",
            age=25
        )
        assert user2.id is not None
        assert user2.id == 2
    
    # --- Тесты для get_user ---
    
    def test_get_user_found(self):
        """Поиск существующего пользователя"""
        service = UserService()
        created = service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        found = service.get_user(created.id)
        assert found is not None
        assert found.id == created.id
        assert found.username == "john_doe"
        assert found.email == "john@example.com"
    
    def test_get_user_not_found(self):
        """Поиск несуществующего пользователя"""
        service = UserService()
        found = service.get_user(999)
        assert found is None
    
    # --- Тесты для update_user_email ---
    
    def test_update_user_email_success(self):
        """Успешное обновление email"""
        service = UserService()
        user = service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        updated = service.update_user_email(user.id, "new@example.com")
        assert updated.email == "new@example.com"
        
        # Проверяем, что email действительно изменился
        found = service.get_user(user.id)
        assert found.email == "new@example.com"
    
    def test_update_user_email_invalid(self):
        """Обновление email с невалидным значением"""
        service = UserService()
        user = service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        with pytest.raises(ValueError, match="Invalid email"):
            service.update_user_email(user.id, "invalid-email")
    
    def test_update_user_email_not_found(self):
        """Обновление email несуществующего пользователя"""
        service = UserService()
        with pytest.raises(ValueError, match="User not found"):
            service.update_user_email(999, "new@example.com")
    
    # --- Тесты для update_user_age ---
    
    def test_update_user_age_success(self):
        """Успешное обновление возраста"""
        service = UserService()
        user = service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        updated = service.update_user_age(user.id, 30)
        assert updated.age == 30
        
        found = service.get_user(user.id)
        assert found.age == 30
    
    def test_update_user_age_invalid(self):
        """Обновление возраста с невалидным значением"""
        service = UserService()
        user = service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        with pytest.raises(ValueError, match="Invalid age"):
            service.update_user_age(user.id, 17)
    
    def test_update_user_age_not_found(self):
        """Обновление возраста несуществующего пользователя"""
        service = UserService()
        with pytest.raises(ValueError, match="User not found"):
            service.update_user_age(999, 30)
    
    # --- Тесты для deactivate_user ---
    
    def test_deactivate_user_success(self):
        """Успешная деактивация пользователя"""
        service = UserService()
        user = service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        service.deactivate_user(user.id)
        assert service.get_user(user.id).is_active is False
    
    def test_deactivate_user_already_inactive(self):
        """Деактивация уже деактивированного пользователя"""
        service = UserService()
        user = service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        service.deactivate_user(user.id)
        
        with pytest.raises(ValueError, match="already deactivated"):
            service.deactivate_user(user.id)
    
    def test_deactivate_user_not_found(self):
        """Деактивация несуществующего пользователя"""
        service = UserService()
        with pytest.raises(ValueError, match="User not found"):
            service.deactivate_user(999)
    
    # --- Тесты для find_users_by_age_range ---
    
    def test_find_users_by_age_range_success(self):
        """Поиск пользователей по возрасту"""
        service = UserService()
        service.create_user("user1", "user1@example.com", "Password123", 20)
        service.create_user("user2", "user2@example.com", "Password123", 30)
        service.create_user("user3", "user3@example.com", "Password123", 40)
        service.create_user("user4", "user4@example.com", "Password123", 50)
        
        found = service.find_users_by_age_range(25, 45)
        assert len(found) == 2
        usernames = [u.username for u in found]
        assert "user2" in usernames
        assert "user3" in usernames
    
    def test_find_users_by_age_range_inclusive(self):
        """Поиск по возрасту с включением границ"""
        service = UserService()
        service.create_user("user1", "user1@example.com", "Password123", 20)
        service.create_user("user2", "user2@example.com", "Password123", 25)
        service.create_user("user3", "user3@example.com", "Password123", 30)
        
        found = service.find_users_by_age_range(25, 30)
        assert len(found) == 2
        usernames = [u.username for u in found]
        assert "user2" in usernames
        assert "user3" in usernames
    
    def test_find_users_by_age_range_empty(self):
        """Поиск по возрасту, когда нет подходящих пользователей"""
        service = UserService()
        service.create_user("user1", "user1@example.com", "Password123", 20)
        service.create_user("user2", "user2@example.com", "Password123", 30)
        
        found = service.find_users_by_age_range(40, 50)
        assert len(found) == 0
    
    def test_find_users_by_age_range_invalid(self):
        """Поиск по возрасту с некорректным диапазоном"""
        service = UserService()
        with pytest.raises(ValueError, match="Min age must be less than or equal to max age"):
            service.find_users_by_age_range(30, 20)
    
    # --- Тесты для authenticate ---
    
    def test_authenticate_success(self):
        """Успешная аутентификация"""
        service = UserService()
        service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        user = service.authenticate("john_doe", "Password123")
        assert user is not None
        assert user.username == "john_doe"
        assert user.email == "john@example.com"
    
    def test_authenticate_wrong_password(self):
        """Аутентификация с неправильным паролем"""
        service = UserService()
        service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        result = service.authenticate("john_doe", "WrongPassword")
        assert result is None
    
    def test_authenticate_inactive_user(self):
        """Аутентификация неактивного пользователя"""
        service = UserService()
        user = service.create_user(
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        service.deactivate_user(user.id)
        
        result = service.authenticate("john_doe", "Password123")
        assert result is None
    
    def test_authenticate_nonexistent_user(self):
        """Аутентификация несуществующего пользователя"""
        service = UserService()
        result = service.authenticate("nonexistent", "password")
        assert result is None
    
    def test_authenticate_case_sensitive_username(self):
        """Аутентификация с учётом регистра username"""
        service = UserService()
        service.create_user(
            username="John_Doe",
            email="john@example.com",
            password="Password123",
            age=25
        )
        
        # Разный регистр должен не совпадать
        result = service.authenticate("john_doe", "Password123")
        assert result is None


# ============================================
# КЛАСС: Тесты для UserRepository
# ============================================

class TestUserRepository:
    """Тесты репозитория пользователей"""
    
    def test_save_and_find_user(self):
        """Сохранение и поиск пользователя"""
        repo = UserRepository()
        user = User(
            id=1,
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25,
            role=UserRole.GUEST,
            is_active=True
        )
        
        repo.save(user)
        found = repo.find_by_email("john@example.com")
        
        assert found is not None
        assert found.id == 1
        assert found.username == "john_doe"
        assert found.email == "john@example.com"
        assert found.age == 25
        assert found.role == UserRole.GUEST
        assert found.is_active is True
    
    def test_save_existing_user(self):
        """Сохранение уже существующего пользователя (обновление)"""
        repo = UserRepository()
        user = User(
            id=1,
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25,
            role=UserRole.GUEST,
            is_active=True
        )
        
        repo.save(user)
        
        # Обновляем пользователя
        user.age = 30
        user.email = "new@example.com"
        repo.save(user)
        
        found = repo.find_by_email("new@example.com")
        assert found is not None
        assert found.age == 30
        assert found.email == "new@example.com"
    
    def test_find_by_email_not_found(self):
        """Поиск по email, которого нет в хранилище"""
        repo = UserRepository()
        found = repo.find_by_email("nonexistent@example.com")
        assert found is None
    
    def test_find_by_email_case_sensitive(self):
        """Поиск по email с учётом регистра"""
        repo = UserRepository()
        user = User(
            id=1,
            username="john_doe",
            email="John@Example.COM",
            password="Password123",
            age=25,
            role=UserRole.GUEST,
            is_active=True
        )
        
        repo.save(user)
        
        # Поиск должен быть чувствительным к регистру
        found = repo.find_by_email("john@example.com")
        assert found is None
        
        found = repo.find_by_email("John@Example.COM")
        assert found is not None
    
    def test_delete_user(self):
        """Удаление пользователя из репозитория"""
        repo = UserRepository()
        user = User(
            id=1,
            username="john_doe",
            email="john@example.com",
            password="Password123",
            age=25,
            role=UserRole.GUEST,
            is_active=True
        )
        
        repo.save(user)
        repo.delete(1)
        
        found = repo.find_by_email("john@example.com")
        assert found is None
    
    def test_delete_nonexistent_user(self):
        """Удаление несуществующего пользователя"""
        repo = UserRepository()
        # Не должно вызвать исключение
        repo.delete(999)
        assert True
    
    def test_save_user_with_admin_role(self):
        """Сохранение пользователя с ролью ADMIN"""
        repo = UserRepository()
        user = User(
            id=1,
            username="admin",
            email="admin@example.com",
            password="AdminPass123",
            age=30,
            role=UserRole.ADMIN,
            is_active=True
        )
        
        repo.save(user)
        found = repo.find_by_email("admin@example.com")
        
        assert found is not None
        assert found.role == UserRole.ADMIN
    
    def test_save_multiple_users(self):
        """Сохранение нескольких пользователей"""
        repo = UserRepository()
        
        user1 = User(
            id=1,
            username="user1",
            email="user1@example.com",
            password="Password123",
            age=20,
            role=UserRole.GUEST,
            is_active=True
        )
        
        user2 = User(
            id=2,
            username="user2",
            email="user2@example.com",
            password="Password123",
            age=30,
            role=UserRole.HOTELIER,
            is_active=True
        )
        
        repo.save(user1)
        repo.save(user2)
        
        found1 = repo.find_by_email("user1@example.com")
        found2 = repo.find_by_email("user2@example.com")
        
        assert found1 is not None
        assert found2 is not None
        assert found1.id != found2.id


# ============================================
# КЛАСС: Интеграционные тесты
# ============================================

class TestUserIntegration:
    """Интеграционные тесты для полного цикла работы с пользователем"""
    
    def test_full_user_lifecycle(self):
        """Полный жизненный цикл пользователя"""
        service = UserService()
        
        # 1. Создание пользователя
        user = service.create_user(
            username="test_user",
            email="test@example.com",
            password="TestPass123",
            age=25
        )
        assert user.id is not None
        
        # 2. Получение пользователя
        found = service.get_user(user.id)
        assert found is not None
        assert found.username == "test_user"
        
        # 3. Обновление email
        updated = service.update_user_email(user.id, "new_test@example.com")
        assert updated.email == "new_test@example.com"
        
        # 4. Обновление возраста
        updated = service.update_user_age(user.id, 30)
        assert updated.age == 30
        
        # 5. Поиск по возрасту
        results = service.find_users_by_age_range(25, 35)
        assert len(results) >= 1
        assert any(u.id == user.id for u in results)
        
        # 6. Аутентификация
        auth_user = service.authenticate("test_user", "TestPass123")
        assert auth_user is not None
        assert auth_user.id == user.id
        
        # 7. Деактивация
        service.deactivate_user(user.id)
        assert service.get_user(user.id).is_active is False
        
        # 8. Аутентификация после деактивации
        auth_user = service.authenticate("test_user", "TestPass123")
        assert auth_user is None
    
    def test_service_with_repository_integration(self):
        """Интеграция сервиса и репозитория"""
        service = UserService()
        repo = UserRepository()
        
        # Создаём пользователя через сервис
        user = service.create_user(
            username="integration_test",
            email="integration@example.com",
            password="TestPass123",
            age=25
        )
        
        # Сохраняем в репозиторий
        repo.save(user)
        
        # Находим через репозиторий
        found = repo.find_by_email("integration@example.com")
        assert found is not None
        assert found.username == "integration_test"
        
        # Проверяем, что данные соответствуют
        assert found.id == user.id
        assert found.age == user.age
        assert found.role == user.role