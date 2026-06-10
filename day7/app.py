from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import bcrypt
from functools import wraps
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = '1111'

# Настройки MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1111'
app.config['MYSQL_DB'] = 'mydb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


# ========== ДЕКОРАТОРЫ ==========

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'login' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'login' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Доступ запрещён. Требуется роль администратора.', 'danger')
            return redirect(url_for('worker_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ========== ГЛАВНЫЕ СТРАНИЦЫ ==========

@app.route('/')
def index():
    if 'login' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('worker_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        captcha_user = request.form['captcha']
        
        # Проверка капчи
        if int(captcha_user) != session.get('captcha_result'):
            flash('Неверно введена капча', 'danger')
            return redirect(url_for('login'))
        
        # Поиск пользователя
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM user WHERE login = %s", (login,))
        user = cur.fetchone()
        cur.close()
        
        if user:
            stored_hash = user['password_hash']
            
            try:
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                    session['login'] = user['login']
                    session['role'] = user['role']
                    session['user_id'] = user.get('user_id')
                    
                    flash(f'Добро пожаловать, {user["login"]}!', 'success')
                    
                    if user['role'] == 'admin':
                        return redirect(url_for('admin_dashboard'))
                    else:
                        return redirect(url_for('worker_dashboard'))
                else:
                    flash('Неверный логин или пароль', 'danger')
            except Exception as e:
                flash('Ошибка проверки пароля', 'danger')
        else:
            flash('Неверный логин или пароль', 'danger')
        
        return redirect(url_for('login'))
    
    # Генерация капчи
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    session['captcha_result'] = num1 + num2
    
    return render_template('login.html', num1=num1, num2=num2)


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

#admin_reservations
@app.route('/worker/dashboard')
@login_required
def worker_dashboard():
    return render_template('worker/dashboard.html')


# ========== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ==========

@app.route('/admin/users')
@admin_required
def admin_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT login, role, email FROM user")
    users = cur.fetchall()
    cur.close()
    return render_template('admin/users.html', users=users)


@app.route('/admin/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        role = request.form['role']
        email = request.form.get('email', '')
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO user (login, password_hash, role, email) VALUES (%s, %s, %s, %s)",
                (login, hashed.decode('utf-8'), role, email)
            )
            mysql.connection.commit()
            flash(f'Пользователь {login} успешно создан', 'success')
        except Exception as e:
            flash(f'Ошибка: пользователь с таким логином уже существует', 'danger')
        finally:
            cur.close()
        
        return redirect(url_for('admin_users'))
    
    return render_template('admin/add_user.html')


@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT login FROM user WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    
    if user and user['login'] == session.get('login'):
        flash('Нельзя удалить самого себя', 'danger')
        return redirect(url_for('admin_users'))
    
    cur.execute("DELETE FROM user WHERE user_id = %s", (user_id,))
    mysql.connection.commit()
    cur.close()
    
    flash('Пользователь удалён', 'success')
    return redirect(url_for('admin_users'))


# ========== УПРАВЛЕНИЕ БРОНЯМИ ==========

@app.route('/admin/reservations')
@admin_required
def admin_reservations():
    """Управление бронями"""
    try:
        cur = mysql.connection.cursor()
        
        # Проверяем, существует ли таблица
        cur.execute("SHOW TABLES LIKE 'reservations'")
        table_exists = cur.fetchone()
        
        if not table_exists:
            flash('Таблица reservations не найдена в базе данных!', 'danger')
            return render_template('admin/reservations.html', 
                                 reservations=[], 
                                 active_count=0, 
                                 total_sum=0)
        
        # Получаем параметры фильтрации
        status = request.args.get('status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Базовый запрос
        query = "SELECT * FROM reservations WHERE 1=1"
        params = []
        
        if status:
            query += " AND Status = %s"
            params.append(status)
        if date_from:
            query += " AND Arrival_date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND Departure_date <= %s"
            params.append(date_to)
        
        query += " ORDER BY Arrival_date DESC"
        
        print(f"DEBUG: Выполняется запрос: {query}")
        print(f"DEBUG: Параметры: {params}")
        
        cur.execute(query, params)
        reservations = cur.fetchall()
        
        print(f"DEBUG: Найдено броней: {len(reservations)}")
        
        # Подсчет активных броней
        cur.execute("SELECT COUNT(*) as count FROM reservations WHERE Status = 'Active'")
        active_result = cur.fetchone()
        active_count = active_result['count'] if active_result else 0
        
        # Подсчет общей суммы
        cur.execute("SELECT SUM(Price) as total_sum FROM reservations")
        sum_result = cur.fetchone()
        total_sum = sum_result['total_sum'] if sum_result and sum_result['total_sum'] else 0
        
        cur.close()
        
        return render_template('admin/reservations.html', 
                             reservations=reservations, 
                             active_count=active_count,
                             total_sum=total_sum)
    
    except Exception as e:
        print(f"ОШИБКА: {e}")
        flash(f'Ошибка при загрузке броней: {str(e)}', 'danger')
        return render_template('admin/reservations.html', 
                             reservations=[], 
                             active_count=0, 
                             total_sum=0)


@app.route('/admin/add_reservation', methods=['GET', 'POST'])
@admin_required
def add_reservation():
    """Добавление новой брони"""
    if request.method == 'POST':
        guest_id = request.form['guest_id']
        room_id = request.form['room_id']
        arrival_date = request.form['arrival_date']
        departure_date = request.form['departure_date']
        status = request.form['status']
        price = request.form['price']
        
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO reservations (Guest_id, Room_id, Arrival_date, Departure_date, Status, Price) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (guest_id, room_id, arrival_date, departure_date, status, price))
            mysql.connection.commit()
            flash('Бронь успешно добавлена', 'success')
        except Exception as e:
            flash(f'Ошибка при добавлении: {e}', 'danger')
        finally:
            cur.close()
        
        return redirect(url_for('admin_reservations'))
    
    return render_template('admin/add_reservation.html')


@app.route('/admin/edit_reservation/<int:reservation_id>', methods=['GET', 'POST'])
@admin_required
def edit_reservation(reservation_id):
    """Редактирование брони"""
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        guest_id = request.form['guest_id']
        room_id = request.form['room_id']
        arrival_date = request.form['arrival_date']
        departure_date = request.form['departure_date']
        status = request.form['status']
        price = request.form['price']
        
        try:
            cur.execute("""
                UPDATE reservations 
                SET Guest_id=%s, Room_id=%s, Arrival_date=%s, Departure_date=%s, Status=%s, Price=%s 
                WHERE Reservation_id=%s
            """, (guest_id, room_id, arrival_date, departure_date, status, price, reservation_id))
            mysql.connection.commit()
            flash('Бронь обновлена', 'success')
        except Exception as e:
            flash(f'Ошибка при обновлении: {e}', 'danger')
        finally:
            cur.close()
        
        return redirect(url_for('admin_reservations'))
    
    cur.execute("SELECT * FROM reservations WHERE Reservation_id = %s", (reservation_id,))
    reservation = cur.fetchone()
    cur.close()
    
    return render_template('admin/edit_reservation.html', reservation=reservation)


@app.route('/admin/delete_reservation/<int:reservation_id>')
@admin_required
def delete_reservation(reservation_id):
    """Удаление брони"""
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM reservations WHERE Reservation_id = %s", (reservation_id,))
    mysql.connection.commit()
    cur.close()
    
    flash('Бронь удалена', 'success')
    return redirect(url_for('admin_reservations'))


# ========== СОЗДАНИЕ ТЕСТОВЫХ ПОЛЬЗОВАТЕЛЕЙ ==========

def create_test_users():
    try:
        cur = mysql.connection.cursor()
        
        # Проверяем, есть ли пользователи
        cur.execute("SELECT COUNT(*) as count FROM user")
        result = cur.fetchone()
        
        if result['count'] == 0:
            print("📝 Создание тестовых пользователей...")
            
            users = [
                ('admin', 'admin123', 'admin', 'admin@test.com'),
                ('worker', 'worker123', 'worker', 'worker@test.com'),
                ('user1', '1111', 'worker', 'user1@test.com')
            ]
            
            for login, password, role, email in users:
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                cur.execute(
                    "INSERT INTO user (login, password_hash, role, email) VALUES (%s, %s, %s, %s)",
                    (login, hashed.decode('utf-8'), role, email)
                )
                print(f"  ✅ Создан: {login} (пароль: {password}, роль: {role})")
            
            mysql.connection.commit()
            print("✅ Тестовые пользователи созданы!")
        
        cur.close()
    except Exception as e:
        print(f"⚠️ Ошибка при создании пользователей: {e}")


if __name__ == '__main__':
    with app.app_context():
        create_test_users()
    app.run(debug=True)