"""
Module for user management in the booking system
Variant 5
"""
import re
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum


class UserRole(Enum):
    """User roles"""
    GUEST = "guest"
    HOTELIER = "hotelier"
    ADMIN = "admin"


@dataclass
class User:
    """User model"""
    id: Optional[int]
    username: str
    email: str
    password: str
    age: int
    role: UserRole
    created_at: Optional[datetime] = None
    is_active: bool = True


class UserValidator:
    """User data validator"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address.
        Valid formats: user@domain.com, user.name@domain.ru
        """
        if not email:
            return False
        
        # Проверка на пробелы
        if ' ' in email:
            return False
        
        if '@' not in email or '.' not in email.split('@')[1]:
            return False
        
        local_part, domain = email.split('@')
        
        if not local_part or local_part.startswith('.'):
            return False
        
        if '..' in domain:
            return False
        
        if domain.startswith('.') or domain.endswith('.'):
            return False
        
        parts = domain.split('.')
        if len(parts) < 2:
            return False
        
        tld = parts[-1]
        if not tld.isalpha() or len(tld) < 2:
            return False
        
        return True
    
    @staticmethod
    def validate_password(password: str) -> bool:
        """
        Validate password strength.
        Requirements: minimum 8 characters, letters and numbers.
        """
        if not password:
            return False
        
        if len(password) < 8:
            return False
        
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        return has_letter and has_digit
    
    @staticmethod
    def validate_age(age: int) -> bool:
        """
        Validate user age.
        Valid age: from 18 to 120 years.
        """
        return 18 <= age <= 120
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """
        Validate username.
        Allowed characters: letters, numbers, underscore.
        Minimum length: 3 characters.
        """
        if not username or len(username) < 3:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))


class UserService:
    """User service"""
    
    def __init__(self):
        self._users: Dict[int, User] = {}
        self._next_id = 1
        self.validator = UserValidator()
    
    def create_user(self, username: str, email: str, password: str, age: int, role: UserRole = UserRole.GUEST) -> User:
        """
        Create a new user.
        """
        if not self.validator.validate_username(username):
            raise ValueError("Invalid username format")
        
        if not self.validator.validate_email(email):
            raise ValueError("Invalid email format")
        
        if not self.validator.validate_password(password):
            raise ValueError("Password is too weak")
        
        if not self.validator.validate_age(age):
            raise ValueError("Invalid age")
        
        user = User(
            id=self._next_id,
            username=username,
            email=email,
            password=password,
            age=age,
            role=role,
            created_at=datetime.now()
        )
        self._users[user.id] = user
        self._next_id += 1
        return user
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)
    
    def update_user_email(self, user_id: int, new_email: str) -> User:
        """Update user email"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        if not self.validator.validate_email(new_email):
            raise ValueError("Invalid email format")
        
        user.email = new_email
        return user
    
    def update_user_age(self, user_id: int, new_age: int) -> User:
        """Update user age"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        if not self.validator.validate_age(new_age):
            raise ValueError("Invalid age")
        
        user.age = new_age
        return user
    
    def deactivate_user(self, user_id: int) -> None:
        """Deactivate user"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        if not user.is_active:
            raise ValueError("User is already deactivated")
        
        user.is_active = False
    
    def find_users_by_age_range(self, min_age: int, max_age: int) -> List[User]:
        """Find users by age range"""
        if min_age > max_age:
            raise ValueError("Min age must be less than or equal to max age")
        
        result = []
        for user in self._users.values():
            if min_age <= user.age <= max_age:
                result.append(user)
        return result
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user"""
        for user in self._users.values():
            if user.username == username and user.password == password and user.is_active:
                return user
        return None


class UserRepository:
    """User repository for database operations"""
    
    def __init__(self):
        self._storage: Dict[int, Dict] = {}
    
    def save(self, user: User) -> None:
        """Save user to storage"""
        self._storage[user.id] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'password': user.password,
            'age': user.age,
            'role': user.role.value,
            'is_active': user.is_active
        }
    
    def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email"""
        for data in self._storage.values():
            if data['email'] == email:
                return User(
                    id=data['id'],
                    username=data['username'],
                    email=data['email'],
                    password=data['password'],
                    age=data['age'],
                    role=UserRole(data['role']),
                    is_active=data['is_active']
                )
        return None
    
    def delete(self, user_id: int) -> None:
        """Delete user by ID"""
        if user_id in self._storage:
            del self._storage[user_id]