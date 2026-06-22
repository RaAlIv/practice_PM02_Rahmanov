# services/library_service.py
import logging
from typing import List, Optional, Dict
from datetime import date, timedelta

from repositories.interfaces import (
    BookRepository, ReaderRepository, LoanRepository
)
from exceptions import (
    BookNotFoundError, ReaderNotFoundError, NoAvailableCopiesError,
    ReaderHasDebtError, DuplicateBookError, ValidationError, LoanNotFoundError
)
from schemas import BookCreate, ReaderCreate, LoanCreate

class LibraryService:
    """
    Сервис управления библиотекой
    Реализует бизнес-логику с использованием Dependency Injection
    """
    
    # Константы
    MAX_LOANS_PER_READER = 5
    LOAN_DAYS = 14
    FINE_PER_DAY = 10  # рублей за день просрочки
    
    def __init__(
        self,
        book_repo: BookRepository,
        reader_repo: ReaderRepository,
        loan_repo: LoanRepository
    ):
        self.book_repo = book_repo
        self.reader_repo = reader_repo
        self.loan_repo = loan_repo
        self.logger = logging.getLogger(__name__)
        
        # Внедряем loan_repo в reader_repo для проверки долгов
        if hasattr(self.reader_repo, 'set_loan_repo'):
            self.reader_repo.set_loan_repo(loan_repo)
    
    # ============ Управление книгами ============
    
    def add_book(self, book_data: BookCreate) -> Dict:
        """Добавление новой книги с валидацией"""
        try:
            self.logger.info(f"Добавление книги: {book_data.title}")
            
            # Проверка на дубликат ISBN
            existing = self.book_repo.get_by_isbn(book_data.isbn)
            if existing:
                raise DuplicateBookError(
                    f"Книга с ISBN '{book_data.isbn}' уже существует"
                )
            
            # Валидация выполняется Pydantic автоматически
            
            book = book_data.dict()
            result = self.book_repo.save(book)
            
            self.logger.info(f"Книга добавлена: ID={result['id']}, '{result['title']}'")
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления книги: {e}")
            raise
    
    def search_books(self, query: str) -> List[Dict]:
        """Поиск книг по автору, названию, жанру"""
        self.logger.info(f"Поиск книг: {query}")
        return self.book_repo.search(query)
    
    def get_book(self, book_id: int) -> Dict:
        """Получение книги по ID"""
        book = self.book_repo.get_by_id(book_id)
        if not book:
            raise BookNotFoundError(f"Книга с ID {book_id} не найдена")
        return book
    
    # ============ Управление читателями ============
    
    def register_reader(self, reader_data: ReaderCreate) -> Dict:
        """Регистрация нового читателя"""
        try:
            self.logger.info(f"Регистрация читателя: {reader_data.name}")
            
            # Проверка на дубликат email
            existing = self.reader_repo.get_by_email(reader_data.email)
            if existing:
                raise ValidationError(
                    f"Читатель с email '{reader_data.email}' уже зарегистрирован"
                )
            
            reader = reader_data.dict()
            result = self.reader_repo.save(reader)
            
            self.logger.info(f"Читатель зарегистрирован: ID={result['id']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка регистрации читателя: {e}")
            raise
    
    def get_reader(self, reader_id: int) -> Dict:
        """Получение читателя по ID"""
        reader = self.reader_repo.get_by_id(reader_id)
        if not reader:
            raise ReaderNotFoundError(f"Читатель с ID {reader_id} не найден")
        return reader
    
    # ============ Выдача и возврат книг ============
    
    def lend_book(self, loan_data: LoanCreate) -> Dict:
        """
        Выдача книги читателю (с проверками и транзакцией)
        """
        try:
            book_id = loan_data.book_id
            reader_id = loan_data.reader_id
            
            self.logger.info(f"Выдача книги: book_id={book_id}, reader_id={reader_id}")
            
            # 1. Проверяем существование книги
            book = self.book_repo.get_by_id(book_id)
            if not book:
                raise BookNotFoundError(f"Книга с ID {book_id} не найдена")
            
            # 2. Проверяем наличие экземпляров
            if book['copies'] <= 0:
                raise NoAvailableCopiesError(
                    f"Нет доступных экземпляров книги '{book['title']}'"
                )
            
            # 3. Проверяем существование читателя
            reader = self.reader_repo.get_by_id(reader_id)
            if not reader:
                raise ReaderNotFoundError(f"Читатель с ID {reader_id} не найден")
            
            # 4. Проверяем количество активных выдач
            active_loans = self.loan_repo.get_active_loans_by_reader(reader_id)
            if len(active_loans) >= self.MAX_LOANS_PER_READER:
                raise ReaderHasDebtError(
                    f"Читатель уже имеет {len(active_loans)} книг (максимум {self.MAX_LOANS_PER_READER})"
                )
            
            # 5. Проверяем просрочки
            overdue = self.loan_repo.get_overdue_loans(reader_id)
            if overdue:
                raise ReaderHasDebtError(
                    f"Читатель имеет {len(overdue)} просроченных книг"
                )
            
            # 6. ТРАНЗАКЦИЯ: Обновление копий и создание выдачи
            try:
                # Шаг 1: Уменьшаем количество экземпляров
                updated_book = self.book_repo.update_copies(book_id, -1)
                if not updated_book:
                    raise BookNotFoundError(f"Книга с ID {book_id} не найдена")
                
                # Шаг 2: Создаём запись о выдаче
                loan = self.loan_repo.create(loan_data.dict())
                
                self.logger.info(f"Книга выдана: loan_id={loan['id']}")
                return loan
                
            except Exception as e:
                # Если произошла ошибка, данные откатываются автоматически
                # (в In-Memory версии нужно восстановить состояние)
                self.logger.error(f"Ошибка в транзакции выдачи: {e}")
                # Восстанавливаем количество экземпляров
                self.book_repo.update_copies(book_id, 1)
                raise
            
        except Exception as e:
            self.logger.error(f"Ошибка выдачи книги: {e}")
            raise
    
    def return_book(self, book_id: int, reader_id: int) -> Dict:
        """
        Возврат книги (с расчётом штрафа)
        """
        try:
            self.logger.info(f"Возврат книги: book_id={book_id}, reader_id={reader_id}")
            
            # 1. Находим активную выдачу
            loan = self.loan_repo.get_active_loan(book_id, reader_id)
            if not loan:
                raise LoanNotFoundError(
                    f"Активная выдача книги ID={book_id} читателю ID={reader_id} не найдена"
                )
            
            # 2. Проверяем существование книги
            book = self.book_repo.get_by_id(book_id)
            if not book:
                raise BookNotFoundError(f"Книга с ID {book_id} не найдена")
            
            # 3. ТРАНЗАКЦИЯ: Возврат книги и закрытие выдачи
            try:
                # Шаг 1: Увеличиваем количество экземпляров
                updated_book = self.book_repo.update_copies(book_id, 1)
                
                # Шаг 2: Закрываем выдачу
                return_date = date.today()
                closed_loan = self.loan_repo.close_loan(loan['id'], return_date)
                
                # 3. Расчёт штрафа за просрочку
                loan_date = loan['loan_date']
                days_overdue = (return_date - loan_date).days - self.LOAN_DAYS
                
                if days_overdue > 0:
                    fine = days_overdue * self.FINE_PER_DAY
                    self.logger.warning(
                        f"Просрочка {days_overdue} дней, штраф: {fine} руб."
                    )
                    closed_loan['fine'] = fine
                    closed_loan['days_overdue'] = days_overdue
                else:
                    closed_loan['fine'] = 0
                    closed_loan['days_overdue'] = 0
                
                self.logger.info(f"Книга возвращена: loan_id={loan['id']}")
                return closed_loan
                
            except Exception as e:
                self.logger.error(f"Ошибка в транзакции возврата: {e}")
                # Восстанавливаем количество экземпляров
                self.book_repo.update_copies(book_id, -1)
                raise
            
        except Exception as e:
            self.logger.error(f"Ошибка возврата книги: {e}")
            raise
    
    # ============ Дополнительные методы ============
    
    def get_reader_loans(self, reader_id: int) -> List[Dict]:
        """Получение всех выдач читателя"""
        self.get_reader(reader_id)  # Проверяем существование
        return self.loan_repo.get_active_loans_by_reader(reader_id)
    
    def get_overdue_loans(self) -> List[Dict]:
        """Получение всех просроченных выдач"""
        # В реальной реализации нужно перебирать всех читателей
        # Для упрощения возвращаем просроченные по всем читателям
        all_loans = []
        # Здесь нужна более сложная логика
        return all_loans
    
    def get_book_availability(self, book_id: int) -> Dict:
        """Получение информации о доступности книги"""
        book = self.get_book(book_id)
        active_loans = self.loan_repo.get_active_loans_by_book(book_id)
        return {
            'book_id': book_id,
            'title': book['title'],
            'total_copies': book['copies'] + len(active_loans),
            'available_copies': book['copies'],
            'loaned_copies': len(active_loans)
        }