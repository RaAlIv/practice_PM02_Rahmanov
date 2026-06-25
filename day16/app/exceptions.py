class EntityNotFoundException(Exception):
    """Исключение, выбрасываемое при отсутствии сущности в БД"""
    def __init__(self, entity_type: str, entity_id: int):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id {entity_id} not found")


class DeliveryCalculationException(Exception):
    """Исключение при ошибке расчёта доставки во внешнем API"""
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(f"Delivery calculation failed: {message}")


class ValidationException(Exception):
    """Исключение при валидации данных"""
    pass