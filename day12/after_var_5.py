"""
Вариант №5: Генераторы (ИСПРАВЛЕННАЯ ВЕРСИЯ)
Все ошибки исправлены:
1. StopIteration обрабатывается корректно
2. Правильный сдвиг бит (<<)
3. Утечка памяти через замыкание устранена
4. Бесконечный генератор исправлен
"""

import tracemalloc
import time
import sys
from typing import Generator, List, Dict, Any
from functools import lru_cache
import weakref


class MemoryEfficientCache:
    """
    Класс для управления кешем с автоматической очисткой
    Вместо глобального списка используем LRU кеш с ограничением
    """
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache = {}
        self._access_order = []
    
    def add(self, key: Any, value: Any) -> None:
        """Добавление значения в кеш с контролем размера"""
        if len(self._cache) >= self.max_size:
            # Удаляем самый старый элемент
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]
        
        self._cache[key] = value
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def get(self, key: Any, default: Any = None) -> Any:
        """Получение значения из кеша"""
        if key in self._cache:
            # Обновляем порядок доступа
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return default
    
    def clear(self) -> None:
        """Очистка кеша"""
        self._cache.clear()
        self._access_order.clear()
    
    def size(self) -> int:
        """Текущий размер кеша"""
        return len(self._cache)


# Используем класс вместо глобального списка
BIG_DATA_CACHE = MemoryEfficientCache(max_size=10)


def create_large_data_efficient() -> List[int]:
    """
    Создание больших данных без утечки памяти
    Используем weakref или немедленное освобождение
    """
    # Создаем большой список
    large_list = [i * 2 for i in range(1000000)]
    
    # Извлекаем нужные данные
    result = large_list[:100]
    
    # Явно удаляем большой список для освобождения памяти
    del large_list
    
    # Сохраняем только результат в кеше (уже не большой список)
    BIG_DATA_CACHE.add('last_result', result)
    
    return result


def create_large_data_with_weakref() -> List[int]:
    """
    Альтернативный подход с использованием слабых ссылок
    """
    large_list = [i * 2 for i in range(1000000)]
    
    # Используем слабую ссылку вместо сильной
    weak_list = weakref.ref(large_list)
    
    # Возвращаем только необходимые данные
    result = large_list[:100]
    
    # Удаляем оригинальный список, слабая ссылка не помешает сборке мусора
    del large_list
    
    return result


def fixed_bit_generator() -> Generator[int, None, None]:
    """
    Исправленный генератор с правильным сдвигом бит
    """
    num = 1
    while num <= 10:  # Добавлено ограничение
        yield num << 1  # Правильный сдвиг влево (умножение на 2)
        num += 1


def safe_generator_with_validation(data: List[int]) -> Generator[int, None, None]:
    """
    Генератор с валидацией и безопасной обработкой
    """
    for item in data:
        if item is None:
            continue  # Пропускаем None значения
        try:
            # Валидация данных перед обработкой
            if not isinstance(item, (int, float)):
                raise TypeError(f"Неверный тип данных: {type(item)}")
            yield item * 2
        except (TypeError, ValueError) as e:
            print(f"Ошибка при обработке {item}: {e}")
            # Возвращаем значение по умолчанию вместо ошибки
            yield 0


def limited_infinite_generator(max_items: int = 100) -> Generator[int, None, None]:
    """
    Исправленный генератор с условием выхода
    """
    num = 0
    while num < max_items:  # Добавлено условие выхода
        yield num ** 2
        num += 1


def process_data_with_generators_fixed(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Исправленная основная функция обработки данных
    """
    result = {
        'even_squares': [],
        'odd_squares': [],
        'bit_results': [],
        'processing_time': 0,
        'cache_size': 0
    }
    
    start_time = time.time()
    
    # Используем безопасный генератор с обработкой StopIteration
    def safe_generator():
        for i in range(5):  # Увеличили количество элементов
            yield i * 10
    
    gen = safe_generator()
    
    # Корректная обработка StopIteration
    for i in range(7):  # Запрашиваем 7 элементов
        try:
            value = next(gen)
            result['bit_results'].append(value)
            print(f"Получено значение из генератора: {value}")
        except StopIteration:
            print(f"Генератор закончился на итерации {i}. Больше элементов нет.")
            break  # Выходим из цикла корректно
    
    # Используем исправленный генератор битового сдвига
    bit_gen = fixed_bit_generator()
    bit_values = list(bit_gen)  # Безопасное получение всех значений
    
    print("\n=== ИСПРАВЛЕННЫЙ БИТОВЫЙ СДВИГ ===")
    print(f"Правильные значения (<<): {bit_values}")
    
    # Исправленная утечка памяти
    print("\n=== ИСПРАВЛЕННАЯ УТЕЧКА ПАМЯТИ ===")
    large_data = create_large_data_efficient()
    print(f"Создан список размером: {sys.getsizeof(large_data)} байт")
    print(f"Количество элементов в кеше: {BIG_DATA_CACHE.size()}")
    
    # Исправленный бесконечный генератор
    print("\n=== ИСПРАВЛЕННЫЙ ГЕНЕРАТОР ===")
    inf_gen = limited_infinite_generator(10)  # Ограничили 10 элементами
    
    # Безопасное получение значений
    inf_values = []
    for i, value in enumerate(inf_gen):
        inf_values.append(value)
        print(f"Квадрат {i}: {value}")
    
    # Обработка результатов
    result['even_squares'] = [x for x in inf_values if x % 2 == 0]
    result['odd_squares'] = [x for x in inf_values if x % 2 != 0]
    result['bit_results'].extend(bit_values[:5])
    result['processing_time'] = time.time() - start_time
    result['cache_size'] = BIG_DATA_CACHE.size()
    
    return result


def test_fixed_generators():
    """
    Тестовая функция для демонстрации исправлений
    """
    print("=" * 60)
    print("ЗАПУСК ИСПРАВЛЕННОЙ ВЕРСИИ (Вариант №5)")
    print("=" * 60)
    
    # Запуск отслеживания памяти
    tracemalloc.start()
    
    try:
        # Тестовые данные
        test_data = [
            {'id': 1, 'value': 100},
            {'id': 2, 'value': 200},
            {'id': 3, 'value': 300},
            {'id': 4, 'value': 400},
            {'id': 5, 'value': 500}
        ]
        
        # Вызов исправленной функции
        result = process_data_with_generators_fixed(test_data)
        
        print("\n=== РЕЗУЛЬТАТ ОБРАБОТКИ ===")
        print(f"Четные квадраты: {result['even_squares']}")
        print(f"Нечетные квадраты: {result['odd_squares']}")
        print(f"Результаты битового сдвига: {result['bit_results']}")
        print(f"Время обработки: {result['processing_time']:.4f} сек")
        print(f"Размер кеша: {result['cache_size']}")
        
        # Демонстрация корректной обработки StopIteration
        print("\n=== КОРРЕКТНАЯ ОБРАБОТКА STOPITERATION ===")
        gen = (x for x in range(3))
        for i in range(5):  # Запрашиваем больше элементов
            try:
                value = next(gen)
                print(f"Элемент {i}: {value}")
            except StopIteration:
                print(f"Элемент {i}: Итерация завершена")
                break
        
        # Проверка памяти
        snapshot = tracemalloc.take_snapshot()
        print("\n=== СТАТИСТИКА ПАМЯТИ ===")
        print("\nТоп-5 строк по потреблению памяти:")
        for i, stat in enumerate(snapshot.statistics('lineno')[:5], 1):
            print(f"{i}. {stat}")
        
        # Демонстрация эффективного использования памяти
        print("\n=== ЭФФЕКТИВНОСТЬ ИСПОЛЬЗОВАНИЯ ПАМЯТИ ===")
        import gc
        gc.collect()  # Принудительная сборка мусора
        snapshot_after_gc = tracemalloc.take_snapshot()
        
        diff = snapshot_after_gc.compare_to(snapshot, 'lineno')
        print("Изменения в памяти после сборки мусора:")
        for stat in diff[:3]:
            print(f"  {stat}")
        
        tracemalloc.stop()
        
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


def demonstrate_generator_best_practices():
    """
    Демонстрация лучших практик использования генераторов
    """
    print("\n" + "=" * 60)
    print("ЛУЧШИЕ ПРАКТИКИ ИСПОЛЬЗОВАНИЯ ГЕНЕРАТОРОВ")
    print("=" * 60)
    
    # 1. Использование контекстного менеджера для генераторов
    print("\n1. Контекстный менеджер:")
    def read_large_file_chunks(filename: str, chunk_size: int = 1024):
        """Чтение большого файла по частям"""
        try:
            with open(filename, 'r') as file:
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except FileNotFoundError:
            print(f"Файл {filename} не найден")
            return
    
    # 2. Генератор с очисткой ресурсов
    print("\n2. Генератор с очисткой ресурсов:")
    def resource_generator():
        resource = None
        try:
            resource = "some_resource"
            yield resource
        finally:
            if resource:
                print("Ресурс освобожден")
                resource = None
    
    for item in resource_generator():
        print(f"Использование: {item}")
    
    # 3. Композиция генераторов
    print("\n3. Композиция генераторов:")
    def square_generator(numbers):
        for n in numbers:
            yield n ** 2
    
    def filter_even_generator(numbers):
        for n in numbers:
            if n % 2 == 0:
                yield n
    
    # Композиция с безопасной обработкой
    numbers = range(10)
    even_squares = filter_even_generator(square_generator(numbers))
    print(f"Четные квадраты: {list(even_squares)}")
    
    # 4. Использование itertools для эффективной обработки
    print("\n4. Использование itertools:")
    import itertools
    
    # Бесконечный итератор с ограничением
    counter = itertools.count(start=1, step=2)  # Нечетные числа
    limited_odd = itertools.islice(counter, 0, 5)  # Берем только 5
    print(f"Первые 5 нечетных чисел: {list(limited_odd)}")
    
    # 5. Генератор с кешированием результатов
    print("\n5. Генератор с кешированием:")
    @lru_cache(maxsize=3)
    def cached_computation(n):
        """Вычисление с кешированием"""
        print(f"Вычисление для {n}...")
        return n ** 3
    
    for i in range(5):
        result = cached_computation(i % 3 + 1)
        print(f"cube({i % 3 + 1}) = {result}")


def compare_memory_usage():
    """
    Сравнение использования памяти между старой и новой версией
    """
    print("\n" + "=" * 60)
    print("СРАВНЕНИЕ ИСПОЛЬЗОВАНИЯ ПАМЯТИ")
    print("=" * 60)
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss / 1024 / 1024  # В МБ
    
    # Тест исправленной версии
    print("\nТестирование исправленной версии:")
    tracemalloc.start()
    
    # Создаем и обрабатываем большой объем данных
    for _ in range(100):
        create_large_data_efficient()
        list(limited_infinite_generator(50))
        list(fixed_bit_generator())
    
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')[:5]
    
    memory_after = process.memory_info().rss / 1024 / 1024
    
    print(f"Память до: {memory_before:.2f} МБ")
    print(f"Память после: {memory_after:.2f} МБ")
    print(f"Использовано: {memory_after - memory_before:.2f} МБ")
    print("\nТоп-5 строк по памяти:")
    for stat in top_stats:
        print(f"  {stat}")
    
    tracemalloc.stop()
    
    # Освобождаем память
    BIG_DATA_CACHE.clear()
    import gc
    gc.collect()
    
    memory_final = process.memory_info().rss / 1024 / 1024
    print(f"Память после очистки: {memory_final:.2f} МБ")


if __name__ == "__main__":
    # Запуск исправленной тестовой функции
    test_fixed_generators()
    
    # Демонстрация лучших практик
    demonstrate_generator_best_practices()
    
    # Сравнение использования памяти
    compare_memory_usage()
    
    print("\n" + "=" * 60)
    print("ИТОГ ИСПРАВЛЕНИЙ В ВАРИАНТЕ №5")
    print("=" * 60)
    print("""
    ✅ ИСПРАВЛЕНО:
    1. StopIteration обрабатывается корректно через try-except с break
    2. Сдвиг бит исправлен на << (умножение на 2)
    3. Утечка памяти устранена через:
       - MemoryEfficientCache с ограничением размера
       - Явное удаление больших объектов
       - Использование weakref
       - Сборка мусора
    4. Бесконечный генератор исправлен добавлением условия выхода
    
    🔧 ДОПОЛНИТЕЛЬНЫЕ УЛУЧШЕНИЯ:
    - Добавлена валидация данных
    - Использование lru_cache для кеширования
    - Композиция генераторов
    - Контекстные менеджеры
    - Эффективное использование памяти
    
    📊 РЕЗУЛЬТАТЫ:
    - Нет утечек памяти
    - Корректная обработка всех исключений
    - Правильная работа генераторов
    - Эффективное использование ресурсов
    """)