"""
Вариант №5: Генераторы
Ошибки:
1. StopIteration без обработки
2. Неверный сдвиг бит (>> вместо <<)
3. Замыкание с большими данными (утечка памяти)
4. Бесконечный генератор
"""

import tracemalloc
import time
import sys
from typing import Generator, List, Dict, Any

# Глобальный кеш для хранения больших данных (утечка памяти)
BIG_DATA_CACHE = []


def create_large_data() -> List[int]:
    """Создает большой список данных (замыкание)"""
    # Потенциальная утечка: большие данные сохраняются в замыкании
    large_list = [i * 2 for i in range(1000000)]
    
    def inner_function() -> List[int]:
        # Замыкание захватывает large_list, препятствуя сборке мусора
        return large_list[:100]  # Возвращаем только часть, но весь список в памяти
    
    # Утечка: сохраняем замыкание в глобальном кеше
    BIG_DATA_CACHE.append(inner_function)
    return large_list


def bit_generator_wrong() -> Generator[int, None, None]:
    """
    Генератор с логической ошибкой: неверный сдвиг бит
    Ошибка: используется >> (сдвиг вправо) вместо << (сдвиг влево)
    """
    num = 1
    while True:
        # Ошибка: должен быть num << 1, а не num >> 1
        yield num >> 1  # Неверный сдвиг!
        num += 1
        
        # Условный выход, чтобы не был бесконечным
        if num > 10:
            break


def infinite_generator() -> Generator[int, None, None]:
    """
    Бесконечный генератор без условия выхода
    Ошибка: отсутствует условие остановки
    """
    num = 0
    while True:
        # Нет условия выхода - бесконечный цикл
        yield num ** 2
        num += 1


def process_data_with_generators(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Основная функция обработки данных с использованием генераторов
    """
    result = {
        'even_squares': [],
        'odd_squares': [],
        'bit_results': [],
        'processing_time': 0
    }
    
    start_time = time.time()
    
    # Ошибка 1: StopIteration без обработки
    # Создаем генератор, который закончится быстрее, чем мы ожидаем
    def limited_generator():
        for i in range(3):  # Всего 3 элемента
            yield i * 10
    
    gen = limited_generator()
    
    # Пытаемся получить больше элементов, чем есть в генераторе
    # Это вызовет StopIteration
    try:
        for i in range(5):  # Запрашиваем 5 элементов, а есть только 3
            value = next(gen)
            result['bit_results'].append(value)
            print(f"Получено значение из генератора: {value}")
    except StopIteration as e:
        # Ошибка: мы не обрабатываем StopIteration корректно
        # Просто выводим сообщение, но не обрабатываем ситуацию
        print(f"Ошибка StopIteration: генератор закончился раньше времени")
        # Утечка: продолжаем выполнение с некорректными данными
        result['bit_results'].append(-1)  # Заполняем мусорными данными
    
    # Ошибка 2: Неверный сдвиг бит
    bit_gen = bit_generator_wrong()
    bit_values = []
    try:
        for _ in range(10):
            bit_values.append(next(bit_gen))
    except StopIteration:
        pass
    
    # Сравнение правильного и неправильного результата
    print("\n=== Ошибка в битовом сдвиге ===")
    print(f"Неправильные значения (>>): {bit_values[:10]}")
    correct_values = [1 << 1, 2 << 1, 3 << 1, 4 << 1, 5 << 1, 6 << 1, 7 << 1, 8 << 1, 9 << 1, 10 << 1]
    print(f"Правильные значения (<<): {correct_values}")
    
    # Ошибка 3: Утечка памяти через замыкание
    print("\n=== Утечка памяти через замыкание ===")
    large_data = create_large_data()
    print(f"Создан большой список размером: {sys.getsizeof(large_data)} байт")
    print(f"Количество замыканий в кеше: {len(BIG_DATA_CACHE)}")
    
    # Ошибка 4: Бесконечный генератор
    print("\n=== Бесконечный генератор ===")
    inf_gen = infinite_generator()
    
    # Попытка получить значения из бесконечного генератора
    # Ограничиваем количество итераций, чтобы не зависнуть
    inf_values = []
    try:
        for i in range(10):
            inf_values.append(next(inf_gen))
            if i == 9:
                # Имитация ошибки: забыли добавить условие выхода
                print("Бесконечный генератор продолжает работать...")
                # В реальном коде здесь бы был бесконечный цикл
                break
    except Exception as e:
        print(f"Ошибка в бесконечном генераторе: {e}")
    
    result['even_squares'] = [x for x in inf_values if x % 2 == 0]
    result['odd_squares'] = [x for x in inf_values if x % 2 != 0]
    result['bit_results'].extend(bit_values[:5])
    
    result['processing_time'] = time.time() - start_time
    
    return result


def test_generator_errors():
    """
    Тестовая функция для демонстрации всех ошибок
    """
    print("=" * 60)
    print("ЗАПУСК ТЕСТА ГЕНЕРАТОРОВ (Вариант №5)")
    print("=" * 60)
    
    # Запуск отслеживания памяти
    tracemalloc.start()
    
    # Тестовые данные
    test_data = [
        {'id': 1, 'value': 100},
        {'id': 2, 'value': 200},
        {'id': 3, 'value': 300},
        # Добавляем данные, которые могут вызвать проблемы
        {'id': 4, 'value': 400},
        {'id': 5, 'value': 500}
    ]
    
    try:
        # Вызов основной функции
        result = process_data_with_generators(test_data)
        
        print("\n=== РЕЗУЛЬТАТ ОБРАБОТКИ ===")
        print(f"Четные квадраты: {result['even_squares']}")
        print(f"Нечетные квадраты: {result['odd_squares']}")
        print(f"Результаты битового сдвига: {result['bit_results']}")
        print(f"Время обработки: {result['processing_time']:.4f} сек")
        
        # Демонстрация StopIteration
        print("\n=== ДЕМОНСТРАЦИЯ STOPITERATION ===")
        gen = (x for x in range(2))
        print(f"Элемент 1: {next(gen)}")
        print(f"Элемент 2: {next(gen)}")
        # Следующий вызов вызовет StopIteration
        try:
            print(f"Элемент 3: {next(gen)}")
        except StopIteration:
            print("Перехвачено StopIteration (как и ожидалось)")
        
    except Exception as e:
        print(f"\n!!! КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Снимок памяти
        print("\n=== СТАТИСТИКА ПАМЯТИ ===")
        snapshot = tracemalloc.take_snapshot()
        
        print("\nТоп-10 строк по потреблению памяти:")
        for i, stat in enumerate(snapshot.statistics('lineno')[:10], 1):
            print(f"{i}. {stat}")
        
        # Информация о размере данных в кеше
        total_cache_size = sum(sys.getsizeof(cache) for cache in BIG_DATA_CACHE)
        print(f"\nРазмер глобального кеша: {total_cache_size} байт")
        print(f"Количество объектов в кеше: {len(BIG_DATA_CACHE)}")
        
        tracemalloc.stop()


def debug_with_pdb():
    """
    Функция для демонстрации отладки с pdb
    """
    print("\n=== ДЕМОНСТРАЦИЯ ОТЛАДКИ С PDB ===")
    print("Для использования pdb раскомментируйте строку с breakpoint()")
    
    # Раскомментируйте для отладки:
    # breakpoint()  # Точка останова
    
    # Пример проблемного генератора
    def problematic_generator():
        data = [1, 2, 3, 4, 5]
        for item in data:
            # Здесь происходит ошибка: выход за границы
            try:
                # Попытка получить следующий элемент (вызовет StopIteration)
                next_item = data[data.index(item) + 1]
                yield item * next_item
            except IndexError:
                # Ошибка: неправильная обработка IndexError
                # Вместо корректного завершения, просто игнорируем
                print(f"Ошибка индекса для элемента {item}")
                yield -1
    
    gen = problematic_generator()
    print("Результаты проблемного генератора:")
    for _ in range(10):  # Запрашиваем больше элементов, чем есть
        try:
            value = next(gen)
            print(f"  {value}")
        except StopIteration:
            print("  Генератор завершен")
            break


if __name__ == "__main__":
    # Запуск основной тестовой функции
    test_generator_errors()
    
    # Демонстрация отладки
    debug_with_pdb()
    
    print("\n" + "=" * 60)
    print("АНАЛИЗ ОШИБОК В ВАРИАНТЕ №5")
    print("=" * 60)
    print("""
    1. StopIteration без обработки:
       - Генератор limited_generator() создает только 3 элемента
       - Цикл пытается получить 5 элементов
       - StopIteration перехватывается, но не обрабатывается корректно
       
    2. Неверный сдвиг бит:
       - Используется >> (сдвиг вправо) вместо << (сдвиг влево)
       - Результат: num/2 вместо num*2
       
    3. Утечка памяти через замыкание:
       - Функция create_large_data() создает большой список
       - Внутренняя функция inner_function() захватывает список
       - Список сохраняется в глобальном кеше BIG_DATA_CACHE
       - Память не освобождается после использования
       
    4. Бесконечный генератор:
       - infinite_generator() не имеет условия выхода
       - while True без break или return
       - Может привести к зависанию программы
    """)