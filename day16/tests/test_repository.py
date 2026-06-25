import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import httpx

from app.models import OrderStatus, Order
from app.exceptions import EntityNotFoundException, DeliveryCalculationException, ValidationException


class TestOrderRepository:
    """Тесты для репозитория заказов"""
    
    @pytest.mark.parametrize("status", [
        OrderStatus.PENDING,
        OrderStatus.PAID,
        OrderStatus.SHIPPED,
        OrderStatus.CANCELLED
    ])
    def test_create_order(self, repository, sample_order_data, status):
        """Тест создания заказа с параметризацией по статусам"""
        # Arrange
        order_data = sample_order_data.copy()
        order_data["status"] = status
        
        # Act
        order = repository.create(order_data)
        
        # Assert
        assert order.id is not None
        assert order.customer_name == sample_order_data["customer_name"]
        assert order.delivery_address == sample_order_data["delivery_address"]
        assert order.status == status
        assert len(order.items) == len(sample_order_data["items"])
        
        # Проверяем, что позиции сохранились
        for i, item in enumerate(order.items):
            assert item.product_name == sample_order_data["items"][i]["product_name"]
            assert item.quantity == sample_order_data["items"][i]["quantity"]
            assert item.price == sample_order_data["items"][i]["price"]
        
        # Проверяем корректность total_amount
        expected_total = sum(item["quantity"] * item["price"] for item in sample_order_data["items"])
        assert order.total_amount == expected_total
    
    def test_create_order_with_invalid_items(self, repository, sample_order_data):
        """Тест создания заказа с некорректными позициями"""
        # Arrange
        order_data = sample_order_data.copy()
        order_data["items"] = [{"product_name": "Товар", "quantity": -5, "price": 100.0}]
        
        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            repository.create(order_data)
        
        assert "positive" in str(exc_info.value).lower()
        
        # Проверяем, что заказ не сохранился
        orders = repository.find_all_by_status(OrderStatus.PENDING)
        assert len(orders) == 0
    
    def test_find_by_id_existing_order(self, repository, sample_order):
        """Тест поиска существующего заказа по ID"""
        # Arrange
        order_id = sample_order.id
        
        # Act
        found_order = repository.find_by_id(order_id)
        
        # Assert
        assert found_order is not None
        assert found_order.id == order_id
        assert found_order.customer_name == sample_order.customer_name
    
    def test_find_by_id_not_existing_order(self, repository):
        """Тест поиска несуществующего заказа по ID"""
        # Act
        found_order = repository.find_by_id(99999)
        
        # Assert
        assert found_order is None
    
    @pytest.mark.parametrize("status", [
        OrderStatus.PENDING,
        OrderStatus.PAID,
        OrderStatus.SHIPPED,
        OrderStatus.CANCELLED
    ])
    def test_find_all_by_status(self, repository, sample_order_data, status):
        """Тест поиска заказов по статусу с параметризацией"""
        # Arrange
        # Создаём заказы с разными статусами
        for i in range(3):
            data = sample_order_data.copy()
            data["customer_name"] = f"Customer {i}"
            data["status"] = status
            repository.create(data)
        
        # Создаём заказ с другим статусом
        other_status = OrderStatus.PAID if status == OrderStatus.PENDING else OrderStatus.PENDING
        data = sample_order_data.copy()
        data["customer_name"] = "Other Customer"
        data["status"] = other_status
        repository.create(data)
        
        # Act
        orders = repository.find_all_by_status(status)
        
        # Assert
        assert len(orders) == 3
        for order in orders:
            assert order.status == status
    
    def test_update_status_success(self, repository, sample_order):
        """Тест успешного обновления статуса заказа"""
        # Arrange
        order_id = sample_order.id
        new_status = OrderStatus.PAID
        
        # Act
        updated_order = repository.update_status(order_id, new_status)
        
        # Assert
        assert updated_order.id == order_id
        assert updated_order.status == new_status
        
        # Проверяем, что статус изменился в БД
        found_order = repository.find_by_id(order_id)
        assert found_order.status == new_status
    
    def test_update_status_not_found(self, repository):
        """Тест обновления статуса несуществующего заказа"""
        # Act & Assert
        with pytest.raises(EntityNotFoundException) as exc_info:
            repository.update_status(99999, OrderStatus.PAID)
        
        assert "Order" in str(exc_info.value)
        assert "99999" in str(exc_info.value)
    
    def test_delete_order_success(self, repository, sample_order):
        """Тест успешного удаления заказа"""
        # Arrange
        order_id = sample_order.id
        
        # Act
        repository.delete(order_id)
        
        # Assert
        # Проверяем, что заказ удалён
        deleted_order = repository.find_by_id(order_id)
        assert deleted_order is None
        
        # Проверяем, что позиции удалены каскадно
        items = repository.session.query(Order).filter(Order.id == order_id).all()
        assert len(items) == 0
    
    def test_delete_order_not_found(self, repository):
        """Тест удаления несуществующего заказа"""
        # Act & Assert
        with pytest.raises(EntityNotFoundException) as exc_info:
            repository.delete(99999)
        
        assert "Order" in str(exc_info.value)
    
    def test_find_by_date_range(self, repository, sample_order_data):
        """Тест поиска заказов по диапазону дат"""
        # Arrange
        now = datetime.now()
        
        # Создаём заказы с разными датами
        orders_data = [
            {"customer_name": "Заказ 1", "days_offset": -5, "items": [{"product_name": "Товар 1", "quantity": 1, "price": 100}]},
            {"customer_name": "Заказ 2", "days_offset": 0, "items": [{"product_name": "Товар 2", "quantity": 2, "price": 200}]},
            {"customer_name": "Заказ 3", "days_offset": 5, "items": [{"product_name": "Товар 3", "quantity": 3, "price": 300}]},
        ]
        
        created_orders = []
        for data in orders_data:
            order_data = sample_order_data.copy()
            order_data["customer_name"] = data["customer_name"]
            order_data["items"] = data["items"]
            # Создаём заказ через репозиторий
            order = repository.create(order_data)
            # Вручную устанавливаем дату создания
            order.created_at = now + timedelta(days=data["days_offset"])
            repository.session.commit()
            created_orders.append(order)
        
        # Act
        start_date = now - timedelta(days=2)
        end_date = now + timedelta(days=2)
        orders = repository.find_by_date_range(start_date, end_date)
        
        # Assert
        # Должны найти только "Заказ 2" (в диапазоне от -2 до +2 дней)
        assert len(orders) == 1
        assert orders[0].customer_name == "Заказ 2"
    
    def test_get_total_amount_for_order(self, repository, sample_order_data, sample_order):
        """Тест подсчёта суммы заказа через SQL-агрегацию"""
        # Arrange
        order_id = sample_order.id
        expected_total = sum(item["quantity"] * item["price"] for item in sample_order_data["items"])
        
        # Act
        total = repository.get_total_amount_for_order(order_id)
        
        # Assert
        assert total == expected_total
    
    def test_get_total_amount_for_order_not_found(self, repository):
        """Тест подсчёта суммы для несуществующего заказа"""
        # Act & Assert
        with pytest.raises(EntityNotFoundException):
            repository.get_total_amount_for_order(99999)
    
    def test_transaction_rollback_on_error(self, repository, sample_order_data):
        """Тест транзакционности: при ошибке данные не сохраняются"""
        # Arrange
        order_data = sample_order_data.copy()
        order_data["items"] = [
            {"product_name": "Товар 1", "quantity": 1, "price": 100},
            {"product_name": "Товар 2", "quantity": -1, "price": 200}  # Некорректное количество
        ]
        
        # Act & Assert
        with pytest.raises(ValidationException):
            repository.create(order_data)
        
        # Проверяем, что данные не сохранились
        orders = repository.find_all_by_status(OrderStatus.PENDING)
        assert len(orders) == 0
        
        items = repository.session.query(Order).all()
        assert len(items) == 0
    
    def test_calculate_delivery_cost_success(self, repository, sample_order):
        """Тест успешного расчёта стоимости доставки через API"""
        # Arrange
        order_id = sample_order.id
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"cost": 150.0}
        
        # Вычисляем ожидаемый вес
        expected_weight = sum(item.quantity * 0.5 for item in sample_order.items)
        
        # Act
        with patch('httpx.Client.post') as mock_post:
            mock_post.return_value = mock_response
            cost = repository.calculate_delivery_cost(order_id)
        
        # Assert
        assert cost == 150.0
        # Проверяем, что запрос был отправлен с правильными данными
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert call_args["json"]["address"] == sample_order.delivery_address
        assert call_args["json"]["weight"] == expected_weight
    
    def test_calculate_delivery_cost_api_error(self, repository, sample_order):
        """Тест обработки ошибки API при расчёте доставки"""
        # Arrange
        order_id = sample_order.id
        mock_response = MagicMock()
        mock_response.status_code = 500
        
        # Act & Assert
        with patch('httpx.Client.post') as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(DeliveryCalculationException) as exc_info:
                repository.calculate_delivery_cost(order_id)
            
            assert "500" in str(exc_info.value)
    
    def test_calculate_delivery_cost_timeout(self, repository, sample_order):
        """Тест обработки таймаута API"""
        # Arrange
        order_id = sample_order.id
        
        # Act & Assert
        with patch('httpx.Client.post') as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")
            with pytest.raises(DeliveryCalculationException) as exc_info:
                repository.calculate_delivery_cost(order_id)
            
            assert "timeout" in str(exc_info.value).lower()
    
    def test_calculate_delivery_cost_not_found(self, repository):
        """Тест расчёта доставки для несуществующего заказа"""
        # Act & Assert
        with pytest.raises(EntityNotFoundException):
            repository.calculate_delivery_cost(99999)
             
             # Добавьте эти тесты в класс TestOrderRepository

    def test_repr_methods(self, repository, sample_order):
        """Тест методов __repr__ моделей"""
        # Проверяем __repr__ Order
        order_repr = repr(sample_order)
        assert "Order" in order_repr
        assert str(sample_order.id) in order_repr
        assert sample_order.status in order_repr
        
        # Проверяем __repr__ OrderItem
        if sample_order.items:
            item_repr = repr(sample_order.items[0])
            assert "OrderItem" in item_repr
            assert sample_order.items[0].product_name in item_repr
        
        # Проверяем свойство total
        for item in sample_order.items:
            assert item.total == item.quantity * item.price

    def test_create_order_duplicate_validation(self, repository, sample_order_data):
        """Тест валидации при создании заказа"""
        # Тест с пустым списком items
        invalid_data = sample_order_data.copy()
        invalid_data["items"] = []
        
        with pytest.raises(ValidationException) as exc_info:
            repository.create(invalid_data)
        assert "at least one item" in str(exc_info.value).lower()
        
        # Тест с отрицательной ценой
        invalid_data = sample_order_data.copy()
        invalid_data["items"] = [{"product_name": "Товар", "quantity": 1, "price": -100}]
        
        with pytest.raises(ValidationException) as exc_info:
            repository.create(invalid_data)
        assert "positive" in str(exc_info.value).lower()

    def test_calculate_delivery_cost_invalid_json(self, repository, sample_order):
        """Тест обработки невалидного JSON от API"""
        order_id = sample_order.id
        
        with patch('httpx.Client.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_post.return_value = mock_response
            
            with pytest.raises(DeliveryCalculationException) as exc_info:
                repository.calculate_delivery_cost(order_id)
            assert "json" in str(exc_info.value).lower()

    def test_calculate_delivery_cost_missing_cost_field(self, repository, sample_order):
        """Тест обработки ответа API без поля cost"""
        order_id = sample_order.id
        
        with patch('httpx.Client.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": "OK"}
            mock_post.return_value = mock_response
            
            with pytest.raises(DeliveryCalculationException) as exc_info:
                repository.calculate_delivery_cost(order_id)
            assert "cost" in str(exc_info.value).lower()

    def test_calculate_delivery_cost_request_error(self, repository, sample_order):
        """Тест обработки ошибки запроса к API"""
        order_id = sample_order.id
        
        with patch('httpx.Client.post') as mock_post:
            mock_post.side_effect = httpx.RequestError("Connection error")
            
            with pytest.raises(DeliveryCalculationException) as exc_info:
                repository.calculate_delivery_cost(order_id)
            assert "request error" in str(exc_info.value).lower()

    def test_calculate_delivery_cost_unexpected_error(self, repository, sample_order):
        """Тест обработки непредвиденной ошибки"""
        order_id = sample_order.id
        
        with patch('httpx.Client.post') as mock_post:
            mock_post.side_effect = Exception("Unexpected error")
            
            with pytest.raises(DeliveryCalculationException) as exc_info:
                repository.calculate_delivery_cost(order_id)
            assert "unexpected error" in str(exc_info.value).lower()


class TestContractTests:
    """Контрактные тесты для внешнего API"""
    
    def test_delivery_api_contract_success(self, repository, sample_order):
        """Контрактный тест: успешный ответ от API доставки"""
        # Arrange
        order_id = sample_order.id
        expected_cost = 250.0
        
        # Act
        with patch('httpx.Client.post') as mock_post:
            # Создаём мок ответа
            mock_response = httpx.Response(
                status_code=200,
                json={"cost": expected_cost},
                request=httpx.Request("POST", "https://api.delivery.com/calculate")
            )
            mock_post.return_value = mock_response
            
            cost = repository.calculate_delivery_cost(order_id)
        
        # Assert
        assert cost == expected_cost
        
        # Проверяем, что запрос соответствует контракту
        call_args = mock_post.call_args[1]
        assert "json" in call_args
        assert "address" in call_args["json"]
        assert "weight" in call_args["json"]
    
    def test_delivery_api_contract_error(self, repository, sample_order):
        """Контрактный тест: ошибка API доставки"""
        # Arrange
        order_id = sample_order.id
        
        # Act & Assert
        with patch('httpx.Client.post') as mock_post:
            # Создаём мок ответа с ошибкой
            mock_response = httpx.Response(
                status_code=500,
                json={"error": "Internal Server Error"},
                request=httpx.Request("POST", "https://api.delivery.com/calculate")
            )
            mock_post.return_value = mock_response
            
            with pytest.raises(DeliveryCalculationException) as exc_info:
                repository.calculate_delivery_cost(order_id)
            
            assert "500" in str(exc_info.value)