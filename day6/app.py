"""
День 6. GUI приложение для управления таблицей user
Группа 2, Рахманов А
"""

import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error

# ========== ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ ==========

def connect_db():
    """Подключение к базе данных MySQL"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='1111',
            database='mydb'
        )
        return connection
    except Error as e:
        messagebox.showerror("Ошибка БД", f"Не удалось подключиться: {e}")
        return None


# ========== ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ ==========

class DatabaseApp:
    def __init__(self, root, table_name, columns):
        """
        table_name: имя таблицы (например, 'user')
        columns: список словарей [{'name':'login', 'label':'Логин', 'pk':True}, ...]
        """
        self.root = root
        self.table_name = table_name
        self.columns = columns
        self.root.title(f"Управление таблицей: {table_name}")
        self.root.geometry("1000x600")
        self.root.configure(bg='#f0f0f0')
        
        # Создаём интерфейс
        self.create_widgets()
        
        # Загружаем данные
        self.refresh_table()
    
    def create_widgets(self):
        """Создание всех элементов интерфейса"""
        
        # ===== Заголовок =====
        title_label = tk.Label(self.root, text=f"Управление таблицей '{self.table_name}'",
                                font=('Arial', 16, 'bold'), bg='#f0f0f0', fg='#333')
        title_label.pack(pady=10)
        
        # ===== Рамка для полей ввода =====
        input_frame = tk.LabelFrame(self.root, text="Данные записи", 
                                     font=('Arial', 10, 'bold'),
                                     bg='#f0f0f0', padx=10, pady=10)
        input_frame.pack(pady=10, padx=10, fill='x')
        
        self.entries = {}
        entry_frame = tk.Frame(input_frame, bg='#f0f0f0')
        entry_frame.pack()
        
        # Создаём поля для каждого столбца
        row = 0
        col = 0
        for i, column in enumerate(self.columns):
            # Метка
            label = tk.Label(entry_frame, text=f"{column['label']}:", 
                            font=('Arial', 10), bg='#f0f0f0')
            label.grid(row=row, column=col*2, padx=5, pady=5, sticky='e')
            
            # Поле ввода
            if column['name'] == 'password_hash':
                # Для пароля используем специальное поле
                entry = tk.Entry(entry_frame, width=40, font=('Arial', 10), show='*')
            else:
                entry = tk.Entry(entry_frame, width=25, font=('Arial', 10))
            
            entry.grid(row=row, column=col*2+1, padx=5, pady=5)
            self.entries[column['name']] = entry
            
            col += 1
            if col >= 2:  # 2 поля в строке
                col = 0
                row += 1
        
        # ===== Рамка для кнопок =====
        button_frame = tk.Frame(self.root, bg='#f0f0f0')
        button_frame.pack(pady=10)
        
        btn_style = {'width': 12, 'height': 1, 'font': ('Arial', 10)}
        
        tk.Button(button_frame, text="➕ Добавить", command=self.add_record,
                 bg='#4CAF50', fg='white', **btn_style).grid(row=0, column=0, padx=5)
        
        tk.Button(button_frame, text="✏️ Обновить", command=self.update_record,
                 bg='#FF9800', fg='white', **btn_style).grid(row=0, column=1, padx=5)
        
        tk.Button(button_frame, text="🗑️ Удалить", command=self.delete_record,
                 bg='#f44336', fg='white', **btn_style).grid(row=0, column=2, padx=5)
        
        tk.Button(button_frame, text="🧹 Очистить", command=self.clear_entries,
                 bg='#9E9E9E', fg='white', **btn_style).grid(row=0, column=3, padx=5)
        
        tk.Button(button_frame, text="🔄 Обновить", command=self.refresh_table,
                 bg='#2196F3', fg='white', **btn_style).grid(row=0, column=4, padx=5)
        
        # ===== Рамка для поиска =====
        search_frame = tk.Frame(self.root, bg='#f0f0f0')
        search_frame.pack(pady=5)
        
        tk.Label(search_frame, text="🔍 Поиск:", font=('Arial', 10), bg='#f0f0f0').pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame, width=30, font=('Arial', 10))
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<KeyRelease>', lambda event: self.search())
        tk.Button(search_frame, text="Найти", command=self.search,
                 bg='#673AB7', fg='white', width=10).pack(side=tk.LEFT, padx=5)
        
        # ===== Рамка для таблицы =====
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Создаём скроллы
        scroll_y = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scroll_x = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Определяем колонки для Treeview
        columns_display = [col['name'] for col in self.columns]
        
        self.tree = ttk.Treeview(tree_frame, columns=columns_display, show="headings",
                                 yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)
        
        # Настраиваем заголовки
        for col in self.columns:
            self.tree.heading(col['name'], text=col['label'])
            if col['name'] == 'password_hash':
                width = 400
            elif col['name'] == 'login':
                width = 120
            elif col['name'] == 'email':
                width = 150
            else:
                width = 100
            self.tree.column(col['name'], width=width, anchor="center")
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Привязываем событие выбора строки
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # ===== Статус бар =====
        self.status_bar = tk.Label(self.root, text="Готов", bd=1, relief=tk.SUNKEN, 
                                   anchor=tk.W, font=('Arial', 9), bg='#f0f0f0')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def refresh_table(self):
        """Обновить данные в таблице Treeview"""
        # Очищаем текущие данные
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        # Получаем данные из БД
        conn = connect_db()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # Формируем запрос SELECT
        columns_names = [col['name'] for col in self.columns]
        query = f"SELECT {', '.join(columns_names)} FROM {self.table_name}"
        
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                # Скрываем полный хеш пароля для отображения
                display_row = list(row)
                for i, col in enumerate(self.columns):
                    if col['name'] == 'password_hash' and display_row[i]:
                        display_row[i] = display_row[i][:40] + "..."
                self.tree.insert("", tk.END, values=display_row)
            
            self.status_bar.config(text=f"Загружено записей: {len(rows)}")
            
        except Error as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def on_select(self, event):
        """При выборе строки в таблице - заполняем поля ввода"""
        selected = self.tree.selection()
        if not selected:
            return
        
        values = self.tree.item(selected[0])['values']
        
        # Заполняем поля ввода
        for i, col in enumerate(self.columns):
            col_name = col['name']
            if col_name in self.entries:
                self.entries[col_name].delete(0, tk.END)
                if values[i] != "...":
                    self.entries[col_name].insert(0, str(values[i]) if values[i] is not None else "")
    
    def get_pk_name(self):
        """Вернуть имя первичного ключа"""
        for col in self.columns:
            if col.get('pk'):
                return col['name']
        return None
    
    def get_pk_value_from_selected(self):
        """Получить значение PK из выбранной строки"""
        selected = self.tree.selection()
        if not selected:
            return None
        
        values = self.tree.item(selected[0])['values']
        pk_name = self.get_pk_name()
        pk_index = [col['name'] for col in self.columns].index(pk_name)
        return values[pk_index]
    
    def add_record(self):
        """Добавить новую запись"""
        # Собираем значения из полей ввода
        values = {}
        for col_name, entry in self.entries.items():
            values[col_name] = entry.get().strip()
        
        # Проверяем обязательные поля
        for col in self.columns:
            col_name = col['name']
            if col.get('required') and col_name in self.entries and not values[col_name]:
                messagebox.showwarning("Ошибка", f"Поле '{col['label']}' обязательно для заполнения")
                return
        
        conn = connect_db()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # Формируем INSERT-запрос (исключаем PK если он автоинкремент)
        columns_names = []
        values_list = []
        for col_name, value in values.items():
            # Проверяем, не является ли поле PK с автоинкрементом
            is_auto_pk = False
            for col in self.columns:
                if col['name'] == col_name and col.get('pk') and col.get('auto_increment'):
                    is_auto_pk = True
                    break
            if not is_auto_pk:
                columns_names.append(col_name)
                values_list.append(value)
        
        placeholders = ", ".join(["%s"] * len(columns_names))
        query = f"INSERT INTO {self.table_name} ({', '.join(columns_names)}) VALUES ({placeholders})"
        
        try:
            cursor.execute(query, values_list)
            conn.commit()
            messagebox.showinfo("Успех", "Запись добавлена")
            self.clear_entries()
            self.refresh_table()
        except Error as e:
            messagebox.showerror("Ошибка БД", str(e))
        finally:
            cursor.close()
            conn.close()
    
    def update_record(self):
        """Обновить выбранную запись"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите запись для обновления")
            return
        
        pk_name = self.get_pk_name()
        if not pk_name:
            messagebox.showwarning("Предупреждение", "Не найден первичный ключ")
            return
        
        # Получаем ID выбранной записи
        values_current = self.tree.item(selected[0])['values']
        pk_index = [col['name'] for col in self.columns].index(pk_name)
        pk_value = values_current[pk_index]
        
        # Собираем новые значения из полей
        new_values = {}
        for col_name, entry in self.entries.items():
            new_values[col_name] = entry.get().strip()
        
        conn = connect_db()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # Формируем UPDATE-запрос
        set_clause = ", ".join([f"{col} = %s" for col in new_values.keys()])
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE {pk_name} = %s"
        
        try:
            params = list(new_values.values()) + [pk_value]
            cursor.execute(query, params)
            conn.commit()
            messagebox.showinfo("Успех", "Запись обновлена")
            self.refresh_table()
        except Error as e:
            messagebox.showerror("Ошибка БД", str(e))
        finally:
            cursor.close()
            conn.close()
    
    def delete_record(self):
        """Удалить выбранную запись"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите запись для удаления")
            return
        
        # Подтверждение удаления
        if not messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить запись?"):
            return
        
        pk_name = self.get_pk_name()
        if not pk_name:
            return
        
        pk_value = self.get_pk_value_from_selected()
        
        conn = connect_db()
        if not conn:
            return
        
        cursor = conn.cursor()
        query = f"DELETE FROM {self.table_name} WHERE {pk_name} = %s"
        
        try:
            cursor.execute(query, (pk_value,))
            conn.commit()
            messagebox.showinfo("Успех", "Запись удалена")
            self.clear_entries()
            self.refresh_table()
        except Error as e:
            messagebox.showerror("Ошибка БД", str(e))
        finally:
            cursor.close()
            conn.close()
    
    def clear_entries(self):
        """Очистить все поля ввода"""
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        
        # Очищаем выделение в таблице
        selection = self.tree.selection()
        if selection:
            self.tree.selection_remove(selection[0])
    
    def search(self):
        """Поиск по таблице"""
        keyword = self.search_entry.get().strip()
        
        if not keyword:
            self.refresh_table()
            return
        
        # Очищаем таблицу
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        conn = connect_db()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # Ищем по текстовым полям
        text_columns = [col['name'] for col in self.columns 
                       if col['name'] not in ['password_hash']]
        
        if not text_columns:
            self.refresh_table()
            return
        
        conditions = " OR ".join([f"{col} LIKE %s" for col in text_columns])
        query = f"SELECT * FROM {self.table_name} WHERE {conditions}"
        
        try:
            params = tuple([f"%{keyword}%"] * len(text_columns))
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            for row in rows:
                display_row = list(row)
                for i, col in enumerate(self.columns):
                    if col['name'] == 'password_hash' and display_row[i]:
                        display_row[i] = display_row[i][:40] + "..."
                self.tree.insert("", tk.END, values=display_row)
            
            self.status_bar.config(text=f"Найдено записей: {len(rows)}")
            
        except Error as e:
            messagebox.showerror("Ошибка", str(e))
        finally:
            cursor.close()
            conn.close()


# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========

def main():
    root = tk.Tk()
    
    # КОНФИГУРАЦИЯ ДЛЯ ТАБЛИЦЫ user (БЕЗ user_id)
    # Сначала выполните DESCRIBE user; чтобы узнать точные имена полей
    columns = [
        {"name": "login", "label": "Логин", "pk": True, "required": True},
        {"name": "password_hash", "label": "Хеш пароля", "required": True},
        {"name": "role", "label": "Роль", "required": True},
        {"name": "email", "label": "Email", "required": False}
    ]
    
    app = DatabaseApp(root, table_name="user", columns=columns)
    root.mainloop()


if __name__ == "__main__":
    main()