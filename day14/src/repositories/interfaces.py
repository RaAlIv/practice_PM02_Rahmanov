# repositories/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime


class Repository(ABC):
    """Базовый интерфейс репозитория"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int):
        pass
    
    @abstractmethod
    def save(self, entity):
        pass
    
    @abstractmethod
    def delete(self, entity_id: int):
        pass


class BoardRepository(ABC):
    """Репозиторий для досок"""
    
    @abstractmethod
    def get_by_id(self, board_id: int) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def get_all(self) -> List[Dict]:
        pass
    
    @abstractmethod
    def save(self, board: Dict) -> Dict:
        pass
    
    @abstractmethod
    def delete(self, board_id: int) -> bool:
        pass
    
    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Dict]:
        pass


class ColumnRepository(ABC):
    """Репозиторий для колонок"""
    
    @abstractmethod
    def get_by_id(self, column_id: int) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def get_by_board_id(self, board_id: int) -> List[Dict]:
        pass
    
    @abstractmethod
    def save(self, column: Dict) -> Dict:
        pass
    
    @abstractmethod
    def delete(self, column_id: int) -> bool:
        pass
    
    @abstractmethod
    def has_tasks(self, column_id: int) -> bool:
        pass
    
    @abstractmethod
    def update_order(self, column_id: int, new_order: int):
        pass


class TaskRepository(ABC):
    """Репозиторий для задач"""
    
    @abstractmethod
    def get_by_id(self, task_id: int) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def get_by_column_id(self, column_id: int) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_by_assignee_id(self, assignee_id: int) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_by_tags(self, tag_ids: List[int]) -> List[Dict]:
        pass
    
    @abstractmethod
    def save(self, task: Dict) -> Dict:
        pass
    
    @abstractmethod
    def delete(self, task_id: int) -> bool:
        pass
    
    @abstractmethod
    def update_status(self, task_id: int, new_column_id: int) -> Dict:
        pass
    
    @abstractmethod
    def update_assignee(self, task_id: int, assignee_id: Optional[int]) -> Dict:
        pass


class AuditLogRepository(ABC):
    """Репозиторий для аудита"""
    
    @abstractmethod
    def save(self, log_entry: Dict) -> Dict:
        pass
    
    @abstractmethod
    def get_by_task_id(self, task_id: int) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_by_user_id(self, user_id: int) -> List[Dict]:
        pass