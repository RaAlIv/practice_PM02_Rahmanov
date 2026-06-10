import bcrypt
import MySQLdb

# Подключение к БД
conn = MySQLdb.connect(
    host='localhost',
    user='root',
    passwd='1111',
    db='mydb'
)
cursor = conn.cursor()

# Очищаем таблицу
cursor.execute("DELETE FROM user")
print("🗑️ Таблица очищена")

# Создаём пользователей
users = [
    ('admin', 'admin123', 'admin'),
    ('worker', 'worker123', 'worker'),
    ('user1', '1111', 'worker')
]

for login, password, role in users:
    # Генерируем хеш
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hashed_str = hashed.decode('utf-8')
    
    # Вставляем
    cursor.execute(
        "INSERT INTO user (login, password_hash, role) VALUES (%s, %s, %s)",
        (login, hashed_str, role)
    )
    print(f"✅ {login} | пароль: {password}")
    print(f"   Хеш: {hashed_str[:50]}...")
    print(f"   Длина хеша: {len(hashed_str)}")
    print(f"   Начинается с $2b$: {hashed_str.startswith('$2b$')}")
    print()

conn.commit()
print("✅ Все пользователи сохранены в БД!")

# Проверяем результат
cursor.execute("SELECT login, password_hash, LENGTH(password_hash) as len FROM user")
print("\n📋 Проверка в базе данных:")
for row in cursor.fetchall():
    print(f"   Логин: {row[0]}")
    print(f"   Хеш: {row[1][:50]}...")
    print(f"   Длина: {row[2]}")
    print(f"   Начинается с $2b$: {row[1].startswith('$2b$') if row[1] else False}")
    print()

cursor.close()
conn.close()