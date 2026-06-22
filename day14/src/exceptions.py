# src/exceptions.py
class DomainError(Exception):
    """Базовое исключение для доменных ошибок"""
    pass


class ValidationError(DomainError):
    """Ошибка валидации данных"""
    pass


class NotFoundError(DomainError):
    """Сущность не найдена"""
    pass


class BusinessRuleViolation(DomainError):
    """Нарушение бизнес-правила"""
    pass


class BoardNotFoundError(NotFoundError):
    """Доска не найдена"""
    pass


class ColumnNotFoundError(NotFoundError):
    """Колонка не найдена"""
    pass


class TaskNotFoundError(NotFoundError):
    """Задача не найдена"""
    pass


class ColumnNotEmptyError(BusinessRuleViolation):
    """Колонка не пуста (содержит задачи)"""
    pass


class TaskAlreadyAssignedError(BusinessRuleViolation):
    """Задача уже назначена исполнителю"""
    pass