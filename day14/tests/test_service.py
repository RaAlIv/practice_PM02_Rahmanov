# tests/test_service.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from unittest.mock import Mock
from datetime import datetime

from services.task_service import TaskManagementService
from exceptions import BoardNotFoundError, TaskNotFoundError
from schemas import BoardCreate, TaskCreate


class TestTaskManagement:
    """Тесты для TaskManagementService"""
    
    def test_create_board_success(self):
        """Тест успешного создания доски"""
        # Создаем моки
        board_repo = Mock()
        column_repo = Mock()
        task_repo = Mock()
        audit_repo = Mock()
        
        # Настраиваем моки
        board_repo.find_by_name.return_value = None
        board_repo.save.return_value = {'id': 1, 'name': 'Test Board'}
        
        # Создаем сервис
        service = TaskManagementService(board_repo, column_repo, task_repo, audit_repo)
        
        # Выполняем тест
        result = service.create_board(BoardCreate(name="Test Board"))
        
        assert result['id'] == 1
        assert result['name'] == 'Test Board'
        board_repo.save.assert_called_once()
    
    def test_create_task_success(self):
        """Тест успешного создания задачи"""
        board_repo = Mock()
        column_repo = Mock()
        task_repo = Mock()
        audit_repo = Mock()
        
        column_repo.get_by_id.return_value = {'id': 1, 'name': 'To Do'}
        task_repo.save.return_value = {'id': 1, 'title': 'Test Task', 'column_id': 1}
        
        service = TaskManagementService(board_repo, column_repo, task_repo, audit_repo)
        
        result = service.create_task(TaskCreate(title="Test Task", column_id=1))
        
        assert result['id'] == 1
        assert result['title'] == 'Test Task'
        audit_repo.save.assert_called_once()
    
    def test_get_task_not_found(self):
        """Тест получения несуществующей задачи"""
        board_repo = Mock()
        column_repo = Mock()
        task_repo = Mock()
        audit_repo = Mock()
        
        task_repo.get_by_id.return_value = None
        
        service = TaskManagementService(board_repo, column_repo, task_repo, audit_repo)
        
        with pytest.raises(TaskNotFoundError):
            service.get_task(999)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])