# repositories/in_memory.py
from typing import List, Optional, Dict
from datetime import datetime
from .interfaces import (
    BoardRepository, ColumnRepository, 
    TaskRepository, AuditLogRepository
)


class InMemoryBoardRepository(BoardRepository):
    """In-Memory реализация репозитория досок"""
    
    def __init__(self):
        self._boards: Dict[int, Dict] = {}
        self._next_id = 1
    
    def get_by_id(self, board_id: int) -> Optional[Dict]:
        return self._boards.get(board_id)
    
    def get_all(self) -> List[Dict]:
        return list(self._boards.values())
    
    def save(self, board: Dict) -> Dict:
        if 'id' not in board or board['id'] is None:
            board['id'] = self._next_id
            self._next_id += 1
        board['created_at'] = board.get('created_at', datetime.now().isoformat())
        board['updated_at'] = datetime.now().isoformat()
        self._boards[board['id']] = board
        return board
    
    def delete(self, board_id: int) -> bool:
        if board_id in self._boards:
            del self._boards[board_id]
            return True
        return False
    
    def find_by_name(self, name: str) -> Optional[Dict]:
        for board in self._boards.values():
            if board.get('name') == name:
                return board
        return None


class InMemoryColumnRepository(ColumnRepository):
    """In-Memory реализация репозитория колонок"""
    
    def __init__(self):
        self._columns: Dict[int, Dict] = {}
        self._next_id = 1
    
    def get_by_id(self, column_id: int) -> Optional[Dict]:
        return self._columns.get(column_id)
    
    def get_by_board_id(self, board_id: int) -> List[Dict]:
        return [col for col in self._columns.values() 
                if col.get('board_id') == board_id]
    
    def save(self, column: Dict) -> Dict:
        if 'id' not in column or column['id'] is None:
            column['id'] = self._next_id
            self._next_id += 1
        column['created_at'] = column.get('created_at', datetime.now().isoformat())
        column['updated_at'] = datetime.now().isoformat()
        self._columns[column['id']] = column
        return column
    
    def delete(self, column_id: int) -> bool:
        if column_id in self._columns:
            # Проверяем, есть ли задачи в колонке
            if self.has_tasks(column_id):
                return False
            del self._columns[column_id]
            return True
        return False
    
    def has_tasks(self, column_id: int) -> bool:
        # Этот метод будет проверять через TaskRepository
        # В реальной реализации здесь может быть связь с TaskRepository
        return False
    
    def update_order(self, column_id: int, new_order: int):
        if column_id in self._columns:
            self._columns[column_id]['order'] = new_order
            self._columns[column_id]['updated_at'] = datetime.now().isoformat()


class InMemoryTaskRepository(TaskRepository):
    """In-Memory реализация репозитория задач"""
    
    def __init__(self):
        self._tasks: Dict[int, Dict] = {}
        self._next_id = 1
    
    def get_by_id(self, task_id: int) -> Optional[Dict]:
        return self._tasks.get(task_id)
    
    def get_by_column_id(self, column_id: int) -> List[Dict]:
        return [task for task in self._tasks.values() 
                if task.get('column_id') == column_id]
    
    def get_by_assignee_id(self, assignee_id: int) -> List[Dict]:
        return [task for task in self._tasks.values() 
                if task.get('assignee_id') == assignee_id]
    
    def get_by_tags(self, tag_ids: List[int]) -> List[Dict]:
        return [task for task in self._tasks.values() 
                if any(tag in task.get('tags', []) for tag in tag_ids)]
    
    def save(self, task: Dict) -> Dict:
        if 'id' not in task or task['id'] is None:
            task['id'] = self._next_id
            self._next_id += 1
        task['created_at'] = task.get('created_at', datetime.now().isoformat())
        task['updated_at'] = datetime.now().isoformat()
        self._tasks[task['id']] = task
        return task
    
    def delete(self, task_id: int) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False
    
    def update_status(self, task_id: int, new_column_id: int) -> Dict:
        if task_id in self._tasks:
            self._tasks[task_id]['column_id'] = new_column_id
            self._tasks[task_id]['updated_at'] = datetime.now().isoformat()
            return self._tasks[task_id]
        return None
    
    def update_assignee(self, task_id: int, assignee_id: Optional[int]) -> Dict:
        if task_id in self._tasks:
            self._tasks[task_id]['assignee_id'] = assignee_id
            self._tasks[task_id]['updated_at'] = datetime.now().isoformat()
            return self._tasks[task_id]
        return None


class InMemoryAuditLogRepository(AuditLogRepository):
    """In-Memory реализация репозитория аудита"""
    
    def __init__(self):
        self._logs: List[Dict] = []
        self._next_id = 1
    
    def save(self, log_entry: Dict) -> Dict:
        log_entry['id'] = self._next_id
        self._next_id += 1
        log_entry['timestamp'] = log_entry.get('timestamp', datetime.now().isoformat())
        self._logs.append(log_entry)
        return log_entry
    
    def get_by_task_id(self, task_id: int) -> List[Dict]:
        return [log for log in self._logs 
                if log.get('task_id') == task_id]
    
    def get_by_user_id(self, user_id: int) -> List[Dict]:
        return [log for log in self._logs 
                if log.get('user_id') == user_id]