# services/task_service.py
import logging
from typing import List, Optional, Dict
from datetime import datetime

from repositories.interfaces import (
    BoardRepository, ColumnRepository,
    TaskRepository, AuditLogRepository
)
from exceptions import (
    BoardNotFoundError, ColumnNotFoundError, TaskNotFoundError,
    ColumnNotEmptyError, ValidationError, BusinessRuleViolation
)
from schemas import BoardCreate, ColumnCreate, TaskCreate, TaskUpdate


class TaskManagementService:
    """
    Сервис управления задачами (Trello-like)
    """

    def __init__(
        self,
        board_repo: BoardRepository,
        column_repo: ColumnRepository,
        task_repo: TaskRepository,
        audit_log_repo: AuditLogRepository
    ):
        self.board_repo = board_repo
        self.column_repo = column_repo
        self.task_repo = task_repo
        self.audit_log_repo = audit_log_repo
        self.logger = logging.getLogger(__name__)

        # Устанавливаем связь для проверки задач в колонках
        if hasattr(self.column_repo, 'set_task_repo'):
            self.column_repo.set_task_repo(task_repo)

    # === Управление досками ===

    def create_board(self, board_data: BoardCreate) -> Dict:
        """Создание новой доски"""
        try:
            self.logger.info(f"Создание доски: {board_data.name}")

            # Проверка на дубликат
            existing = self.board_repo.find_by_name(board_data.name)
            if existing:
                raise ValidationError(f"Доска с именем '{board_data.name}' уже существует")

            board = board_data.model_dump()  # Исправлено: dict() -> model_dump()
            result = self.board_repo.save(board)

            self.logger.info(f"Доска создана: ID={result['id']}")
            return result

        except Exception as e:
            self.logger.error(f"Ошибка создания доски: {e}")
            raise

    def get_board(self, board_id: int) -> Dict:
        """Получение доски по ID"""
        board = self.board_repo.get_by_id(board_id)
        if not board:
            raise BoardNotFoundError(f"Доска с ID {board_id} не найдена")
        return board

    def get_all_boards(self) -> List[Dict]:
        """Получение всех досок"""
        return self.board_repo.get_all()

    def delete_board(self, board_id: int) -> bool:
        """Удаление доски"""
        board = self.get_board(board_id)

        # Проверяем, есть ли колонки в доске
        columns = self.column_repo.get_by_board_id(board_id)
        if columns:
            for column in columns:
                if self.column_repo.has_tasks(column['id']):
                    raise ColumnNotEmptyError(
                        f"Нельзя удалить доску с задачами. Колонка '{column['name']}' содержит задачи"
                    )

        # Удаляем все колонки
        for column in columns:
            self.column_repo.delete(column['id'])

        result = self.board_repo.delete(board_id)
        self.logger.info(f"Доска удалена: ID={board_id}")
        return result

    # === Управление колонками ===

    def create_column(self, column_data: ColumnCreate) -> Dict:
        """Создание новой колонки"""
        # Проверяем существование доски
        board = self.board_repo.get_by_id(column_data.board_id)
        if not board:
            raise BoardNotFoundError(f"Доска с ID {column_data.board_id} не найдена")

        column = column_data.model_dump()  # Исправлено: dict() -> model_dump()
        result = self.column_repo.save(column)

        # Логируем создание колонки
        self.audit_log_repo.save({
            'action': 'column_created',
            'board_id': column_data.board_id,
            'column_id': result['id'],
            'column_name': column_data.name
        })

        self.logger.info(f"Колонка создана: ID={result['id']} в доске {board['name']}")
        return result

    def delete_column(self, column_id: int) -> bool:
        """Удаление колонки"""
        column = self.column_repo.get_by_id(column_id)
        if not column:
            raise ColumnNotFoundError(f"Колонка с ID {column_id} не найдена")

        # Проверяем, есть ли задачи в колонке
        if self.column_repo.has_tasks(column_id):
            tasks = self.task_repo.get_by_column_id(column_id)
            if tasks:
                raise ColumnNotEmptyError(
                    f"Нельзя удалить колонку '{column['name']}' - содержит {len(tasks)} задач(и)"
                )

        result = self.column_repo.delete(column_id)
        self.logger.info(f"Колонка удалена: ID={column_id}")
        return result

    def move_column(self, column_id: int, new_order: int) -> Dict:
        """Перемещение колонки"""
        column = self.column_repo.get_by_id(column_id)
        if not column:
            raise ColumnNotFoundError(f"Колонка с ID {column_id} не найдена")

        self.column_repo.update_order(column_id, new_order)
        updated = self.column_repo.get_by_id(column_id)
        self.logger.info(f"Колонка перемещена: ID={column_id}, новый порядок={new_order}")
        return updated

    # === Управление задачами ===

    def create_task(self, task_data: TaskCreate) -> Dict:
        """Создание новой задачи"""
        # Проверяем существование колонки
        column = self.column_repo.get_by_id(task_data.column_id)
        if not column:
            raise ColumnNotFoundError(f"Колонка с ID {task_data.column_id} не найдена")

        task = task_data.model_dump()  # Исправлено: dict() -> model_dump()
        result = self.task_repo.save(task)

        # Логируем создание задачи
        self.audit_log_repo.save({
            'action': 'task_created',
            'task_id': result['id'],
            'task_title': task_data.title,
            'column_id': task_data.column_id
        })

        self.logger.info(f"Задача создана: ID={result['id']}, '{task_data.title}'")
        return result

    def get_task(self, task_id: int) -> Dict:
        """Получение задачи по ID"""
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Задача с ID {task_id} не найдена")
        return task

    def update_task(self, task_id: int, task_update: TaskUpdate) -> Dict:
        """Обновление задачи"""
        task = self.get_task(task_id)

        update_data = task_update.model_dump(exclude_unset=True)  # Исправлено: dict() -> model_dump()
        if not update_data:
            raise ValidationError("Нет данных для обновления")

        # Обновляем поля
        for key, value in update_data.items():
            if value is not None:
                task[key] = value

        result = self.task_repo.save(task)

        # Логируем обновление
        self.audit_log_repo.save({
            'action': 'task_updated',
            'task_id': task_id,
            'updated_fields': list(update_data.keys())
        })

        self.logger.info(f"Задача обновлена: ID={task_id}")
        return result

    def delete_task(self, task_id: int) -> bool:
        """Удаление задачи"""
        task = self.get_task(task_id)

        result = self.task_repo.delete(task_id)

        # Логируем удаление
        self.audit_log_repo.save({
            'action': 'task_deleted',
            'task_id': task_id,
            'task_title': task.get('title')
        })

        self.logger.info(f"Задача удалена: ID={task_id}")
        return result

    def move_task(self, task_id: int, new_column_id: int) -> Dict:
        """Перемещение задачи в другую колонку"""
        task = self.get_task(task_id)

        # Проверяем существование новой колонки
        new_column = self.column_repo.get_by_id(new_column_id)
        if not new_column:
            raise ColumnNotFoundError(f"Колонка с ID {new_column_id} не найдена")

        old_column_id = task['column_id']
        result = self.task_repo.update_status(task_id, new_column_id)

        # Логируем перемещение
        self.audit_log_repo.save({
            'action': 'task_moved',
            'task_id': task_id,
            'from_column': old_column_id,
            'to_column': new_column_id
        })

        self.logger.info(f"Задача перемещена: ID={task_id}, из колонки {old_column_id} в {new_column_id}")
        return result

    def assign_task(self, task_id: int, assignee_id: int) -> Dict:
        """Назначение задачи исполнителю"""
        task = self.get_task(task_id)

        if task.get('assignee_id') == assignee_id:
            raise BusinessRuleViolation("Задача уже назначена этому исполнителю")

        result = self.task_repo.update_assignee(task_id, assignee_id)

        # Логируем назначение
        self.audit_log_repo.save({
            'action': 'task_assigned',
            'task_id': task_id,
            'assignee_id': assignee_id
        })

        self.logger.info(f"Задача назначена: ID={task_id}, исполнитель={assignee_id}")
        return result

    def unassign_task(self, task_id: int) -> Dict:
        """Снять назначение с задачи"""
        task = self.get_task(task_id)

        if task.get('assignee_id') is None:
            raise BusinessRuleViolation("Задача не назначена исполнителю")

        result = self.task_repo.update_assignee(task_id, None)

        self.audit_log_repo.save({
            'action': 'task_unassigned',
            'task_id': task_id
        })

        self.logger.info(f"Назначение снято с задачи: ID={task_id}")
        return result

    # === Поиск и фильтрация ===

    def get_tasks_by_column(self, column_id: int) -> List[Dict]:
        """Получение всех задач в колонке"""
        column = self.column_repo.get_by_id(column_id)
        if not column:
            raise ColumnNotFoundError(f"Колонка с ID {column_id} не найдена")
        return self.task_repo.get_by_column_id(column_id)

    def get_tasks_by_assignee(self, assignee_id: int) -> List[Dict]:
        """Получение задач по исполнителю"""
        return self.task_repo.get_by_assignee_id(assignee_id)

    def get_tasks_by_tags(self, tags: List[str]) -> List[Dict]:
        """Получение задач по тегам"""
        all_tasks = []
        for tag in tags:
            tasks = self.task_repo.get_by_tags([tag])
            all_tasks.extend(tasks)
        return all_tasks

    def get_board_tasks(self, board_id: int) -> List[Dict]:
        """Получение всех задач в доске"""
        board = self.board_repo.get_by_id(board_id)
        if not board:
            raise BoardNotFoundError(f"Доска с ID {board_id} не найдена")

        columns = self.column_repo.get_by_board_id(board_id)
        tasks = []
        for column in columns:
            tasks.extend(self.task_repo.get_by_column_id(column['id']))
        return tasks

    # === Аудит ===

    def get_task_history(self, task_id: int) -> List[Dict]:
        """Получение истории изменений задачи"""
        self.get_task(task_id)  # Проверяем существование задачи
        return self.audit_log_repo.get_by_task_id(task_id)

    def get_user_activity(self, user_id: int) -> List[Dict]:
        """Получение активности пользователя"""
        return self.audit_log_repo.get_by_user_id(user_id)