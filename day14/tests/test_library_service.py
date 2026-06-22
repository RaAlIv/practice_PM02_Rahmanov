# tests/test_library_service.py
import pytest
from unittest.mock import Mock, MagicMock
from datetime import date, timedelta

from services.library_service import LibraryService
from exceptions import (
    BookNotFoundError, ReaderNotFoundError, NoAvailableCopiesError,
    ReaderHasDebtError, DuplicateBookError, ValidationError
)
from schemas import BookCreate, ReaderCreate, LoanCreate

class TestLibraryService:
    """Тесты для LibraryService с моками"""
    
    @pytest.fixture
    def mock_repositories(self):
        """Фикстура с моками репозиториев"""
        return {
            'book_repo': Mock(),
            'reader_repo': Mock(),
            'loan_repo': Mock()
        }
    
    @pytest.fixture
    def service(self, mock_repositories):
        """Фикстура сервиса с моками"""
        return LibraryService(
            book_repo=mock_repositories['book_repo'],
            reader_repo=mock_repositories['reader_repo'],
            loan_repo=mock_repositories['loan_repo']
        )
    
    # ======== Тесты для книг ========
    
    def test_add_book_success(self, service, mock_repositories):
        """Успешное добавление книги"""
        book_data = BookCreate(
            title="Война и мир",
            author="Толстой",
            isbn="978-5-17-123456-7",
            year=1869,
            genre="Роман",
            copies=3
        )
        
        mock_repositories['book_repo'].get_by_isbn.return_value = None
        mock_repositories['book_repo'].save.return_value = {
            'id': 1,
            'title': 'Война и мир',
            'author': 'Толстой'
        }
        
        result = service.add_book(book_data)
        
        assert result['id'] == 1
        assert result['title'] == 'Война и мир'
        mock_repositories['book_repo'].save.assert_called_once()
    
    def test_add_book_duplicate_isbn(self, service, mock_repositories):
        """Добавление книги с дублирующимся ISBN"""
        book_data = BookCreate(
            title="Книга 1",
            author="Автор",
            isbn="1234567890",
            year=2000,
            copies=1
        )
        
        mock_repositories['book_repo'].get_by_isbn.return_value = {'id': 1}
        
        with pytest.raises(DuplicateBookError):
            service.add_book(book_data)
    
    def test_add_book_invalid_copies(self, service, mock_repositories):
        """Добавление книги с отрицательным количеством"""
        with pytest.raises(ValidationError):
            BookCreate(
                title="Книга",
                author="Автор",
                isbn="1234567890",
                year=2000,
                copies=-5
            )
    
    # ======== Тесты для выдачи ========
    
    def test_lend_book_success(self, service, mock_repositories):
        """Успешная выдача книги"""
        loan_data = LoanCreate(book_id=1, reader_id=1)
        
        mock_repositories['book_repo'].get_by_id.return_value = {
            'id': 1,
            'title': 'Тестовая книга',
            'copies': 3
        }
        mock_repositories['reader_repo'].get_by_id.return_value = {
            'id': 1,
            'name': 'Читатель'
        }
        mock_repositories['loan_repo'].get_active_loans_by_reader.return_value = []
        mock_repositories['loan_repo'].get_overdue_loans.return_value = []
        mock_repositories['book_repo'].update_copies.return_value = {
            'id': 1,
            'copies': 2
        }
        mock_repositories['loan_repo'].create.return_value = {
            'id': 1,
            'book_id': 1,
            'reader_id': 1
        }
        
        result = service.lend_book(loan_data)
        
        assert result['id'] == 1
        mock_repositories['book_repo'].update_copies.assert_called_with(1, -1)
        mock_repositories['loan_repo'].create.assert_called_once()
    
    def test_lend_book_no_copies(self, service, mock_repositories):
        """Попытка выдать книгу без экземпляров"""
        loan_data = LoanCreate(book_id=1, reader_id=1)
        
        mock_repositories['book_repo'].get_by_id.return_value = {
            'id': 1,
            'title': 'Тестовая книга',
            'copies': 0
        }
        
        with pytest.raises(NoAvailableCopiesError):
            service.lend_book(loan_data)
    
    def test_lend_book_reader_not_found(self, service, mock_repositories):
        """Попытка выдать книгу несуществующему читателю"""
        loan_data = LoanCreate(book_id=1, reader_id=999)
        
        mock_repositories['book_repo'].get_by_id.return_value = {
            'id': 1,
            'copies': 3
        }
        mock_repositories['reader_repo'].get_by_id.return_value = None
        
        with pytest.raises(ReaderNotFoundError):
            service.lend_book(loan_data)
    
    def test_lend_book_reader_has_debt(self, service, mock_repositories):
        """Попытка выдать книгу читателю с долгами"""
        loan_data = LoanCreate(book_id=1, reader_id=1)
        
        mock_repositories['book_repo'].get_by_id.return_value = {
            'id': 1,
            'copies': 3
        }
        mock_repositories['reader_repo'].get_by_id.return_value = {
            'id': 1,
            'name': 'Читатель'
        }
        mock_repositories['loan_repo'].get_active_loans_by_reader.return_value = [
            {'id': 1},
            {'id': 2},
            {'id': 3},
            {'id': 4},
            {'id': 5}  # 5 активных выдач - достигнут лимит
        ]
        
        with pytest.raises(ReaderHasDebtError):
            service.lend_book(loan_data)
    
    # ======== Тесты для возврата ========
    
    def test_return_book_success(self, service, mock_repositories):
        """Успешный возврат книги"""
        loan_date = date.today() - timedelta(days=5)
        
        mock_repositories['loan_repo'].get_active_loan.return_value = {
            'id': 1,
            'book_id': 1,
            'reader_id': 1,
            'loan_date': loan_date
        }
        mock_repositories['book_repo'].get_by_id.return_value = {
            'id': 1,
            'copies': 2
        }
        mock_repositories['book_repo'].update_copies.return_value = {
            'id': 1,
            'copies': 3
        }
        mock_repositories['loan_repo'].close_loan.return_value = {
            'id': 1,
            'return_date': date.today()
        }
        
        result = service.return_book(1, 1)
        
        assert result['id'] == 1
        assert result['fine'] == 0
        mock_repositories['book_repo'].update_copies.assert_called_with(1, 1)
    
    def test_return_book_overdue(self, service, mock_repositories):
        """Возврат книги с просрочкой (штраф)"""
        loan_date = date.today() - timedelta(days=20)  # 20 дней назад
        
        mock_repositories['loan_repo'].get_active_loan.return_value = {
            'id': 1,
            'book_id': 1,
            'reader_id': 1,
            'loan_date': loan_date
        }
        mock_repositories['book_repo'].get_by_id.return_value = {
            'id': 1,
            'copies': 2
        }
        mock_repositories['book_repo'].update_copies.return_value = {
            'id': 1,
            'copies': 3
        }
        mock_repositories['loan_repo'].close_loan.return_value = {
            'id': 1,
            'return_date': date.today()
        }
        
        result = service.return_book(1, 1)
        
        # 20 дней - 14 дней срока = 6 дней просрочки * 10 руб = 60 руб
        assert result['fine'] == 60
        assert result['days_overdue'] == 6
    
    def test_return_book_not_found(self, service, mock_repositories):
        """Возврат книги, которая не была выдана"""
        mock_repositories['loan_repo'].get_active_loan.return_value = None
        
        with pytest.raises(LoanNotFoundError):
            service.return_book(1, 1)
    
    # ======== Тесты для поиска ========
    
    def test_search_books(self, service, mock_repositories):
        """Поиск книг по запросу"""
        expected_result = [
            {'id': 1, 'title': 'Война и мир', 'author': 'Толстой'},
            {'id': 2, 'title': 'Мир и война', 'author': 'Толстой'}
        ]
        mock_repositories['book_repo'].search.return_value = expected_result
        
        result = service.search_books("Толстой")
        
        assert len(result) == 2
        assert result == expected_result
        mock_repositories['book_re