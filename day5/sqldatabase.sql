-- =====================================================
-- 1. Создать БД, таблицы
-- =====================================================
DROP DATABASE IF EXISTS HotelDB;
CREATE DATABASE HotelDB;
USE HotelDB;

-- 2. Таблица Rooms
CREATE TABLE Rooms (
    room_id INT PRIMARY KEY AUTO_INCREMENT,
    room_number VARCHAR(10) NOT NULL UNIQUE,
    room_type VARCHAR(50) NOT NULL,
    price_per_night DECIMAL(10,2) NOT NULL,
    capacity INT NOT NULL
);

-- 3. Таблица Guests
CREATE TABLE Guests (
    guest_id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(100) NOT NULL,
    passport VARCHAR(20) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL
);

-- 4. Таблица Bookings
CREATE TABLE Bookings (
    booking_id INT PRIMARY KEY AUTO_INCREMENT,
    guest_id INT NOT NULL,
    room_id INT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    status ENUM('active', 'cancelled', 'completed') DEFAULT 'active',
    FOREIGN KEY (guest_id) REFERENCES Guests(guest_id),
    FOREIGN KEY (room_id) REFERENCES Rooms(room_id),
    CHECK (check_out > check_in)
);

-- 5. Таблица Services
CREATE TABLE Services (
    service_id INT PRIMARY KEY AUTO_INCREMENT,
    service_name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

-- 6. Таблица BookingServices
CREATE TABLE BookingServices (
    booking_service_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    service_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id),
    FOREIGN KEY (service_id) REFERENCES Services(service_id)
);

-- =====================================================
-- 7. Вставить 5 номеров
-- =====================================================
INSERT INTO Rooms (room_number, room_type, price_per_night, capacity) VALUES
('101', 'Люкс', 5000.00, 2),
('102', 'Полулюкс', 3500.00, 2),
('103', 'Стандарт', 2500.00, 2),
('104', 'Эконом', 1500.00, 1),
('105', 'Семейный', 4000.00, 4);

-- =====================================================
-- 8. Вставить 4 гостей
-- =====================================================
INSERT INTO Guests (full_name, passport, phone) VALUES
('Иванов Иван Иванович', '4510 123456', '+7(912)345-67-89'),
('Петрова Анна Сергеевна', '4510 654321', '+7(913)987-65-43'),
('Сидоров Алексей Владимирович', '4511 111222', '+7(914)555-12-34'),
('Козлова Екатерина Дмитриевна', '4511 333444', '+7(915)777-88-99');

-- =====================================================
-- 9. Вставить 3 услуги
-- =====================================================
INSERT INTO Services (service_name, price) VALUES
('Завтрак', 500.00),
('Уборка номера', 700.00),
('Трансфер', 1500.00);

-- =====================================================
-- 10. Создать 4 бронирования (разные даты)
-- =====================================================
INSERT INTO Bookings (guest_id, room_id, check_in, check_out, status) VALUES
(1, 1, '2026-06-10', '2026-06-15', 'active'),   -- текущая дата '2026-06-15' (сегодня) - заезд был раньше, выезд сегодня
(2, 3, '2026-06-20', '2026-06-25', 'active'),
(3, 5, '2025-12-01', '2025-12-10', 'completed'), -- прошлое бронирование
(4, 2, '2026-07-01', '2026-07-05', 'active');

-- Добавим ещё одно отменённое бронирование для задания 22
INSERT INTO Bookings (guest_id, room_id, check_in, check_out, status) VALUES
(1, 4, '2026-05-01', '2026-05-03', 'cancelled');

-- =====================================================
-- 11. Привязать услуги к бронированиям
-- =====================================================
-- Завтрак к бронированию 1 на 2 дня (quantity = 2)
INSERT INTO BookingServices (booking_id, service_id, quantity) VALUES (1, 1, 2);
-- Уборка к бронированию 1 на 1 день
INSERT INTO BookingServices (booking_id, service_id, quantity) VALUES (1, 2, 1);
-- Трансфер к бронированию 2
INSERT INTO BookingServices (booking_id, service_id, quantity) VALUES (2, 3, 1);
-- Завтрак к бронированию 3 на 5 дней
INSERT INTO BookingServices (booking_id, service_id, quantity) VALUES (3, 1, 5);

