
import datetime

class LibraryService:
    # Жёсткая связанность: сервис сам создаёт структуры данных
    def __init__(self):
        self.books = []  # список словарей (нарушение инкапсуляции)
        self.readers = []
        self.loans = []

    def add_book(self, title, author, isbn, year, genre, copies):
        # Нет валидации: copies может быть отрицательным
        # Нет проверки на отрицательное количество
        # Нет проверки на пустые строки
        # Нет проверки на дубликат ISBN
        self.books.append({
            "id": len(self.books) + 1,
            "title": title,
            "author": author,
            "isbn": isbn,
            "year": year,
            "genre": genre,
            "copies": copies
        })

    def register_reader(self, name, email, phone):
        self.readers.append({
            "id": len(self.readers) + 1,
            "name": name,
            "email": email,
            "phone": phone
        })

    def lend_book(self, book_id, reader_id):
        # Эти две операции должны быть в одной транзакции
        # Нет проверки на долги читателя
        # Нет проверки на уже выданную книгу
        # Нет проверки существования книги и читателя
        book = next((b for b in self.books if b["id"] == book_id), None)
        if not book:
            return "Книга не найдена"
        if book["copies"] <= 0:
            return "Нет экземпляров"
        reader = next((r for r in self.readers if r["id"] == reader_id), None)
        if not reader:
            return "Читатель не найден"
        # Уменьшаем количество
        book["copies"] -= 1
        # Запись о выдаче (без проверки долгов)
        self.loans.append({
            # Если между ними произойдёт ошибка - данные несогласованы
            "book_id": book_id,
            "reader_id": reader_id,
            "loan_date": datetime.date.today(),
            "return_date": None
        })
        return "Книга выдана"

    def return_book(self, book_id, reader_id):
        loan = next((l for l in self.loans if l["book_id"] == book_id and 
                    l["reader_id"] == reader_id and l["return_date"] is None), None)
        if not loan:
            return "Выдача не найдена"
        loan["return_date"] = datetime.date.today()
        book = next((b for b in self.books if b["id"] == book_id), None)
        if book:
            book["copies"] += 1
        # Штраф не считается
        return "Книга возвращена"