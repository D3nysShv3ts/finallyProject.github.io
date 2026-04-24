# Online Restaurant — Setup Guide

## Вимоги
- Python 3.10+
- PostgreSQL (запущений локально або на сервері)

## Встановлення

### 1. Встановити залежності
```bash
pip install -r requirements.txt
```

### 2. Налаштувати .env
Файл `.env` вже налаштований. За потреби змініть параметри підключення до БД:
```
DATABASE_URL=postgresql+psycopg2://postgres:228337Wrt@localhost:5432/online_restaurant
SECRET_KEY=cv)3v7w$*s3fk;5c!@y0?:?3"9)#
ADMIN_NICKNAME=ADMIN
ADMIN_EMAIL=admin@restaurant.com
ADMIN_PASSWORD=ADMIN_123
```

### 3. Створити БД у PostgreSQL (якщо не існує)
```sql
CREATE DATABASE online_restaurant;
```

### 4. Запустити додаток
```bash
python app.py
```

При першому запуску автоматично:
- Створяться всі таблиці (users, menu, orders, reservations)
- Заповниться меню (20 страв)
- Створяться 3 demo-користувачі з тестовими замовленнями і бронюваннями
- Створюється адмін-акаунт

## Вхід до адмін-панелі

| Поле      | Значення   |
|-----------|------------|
| Nickname  | `ADMIN`    |
| Пароль    | `ADMIN_123`|

Адмін-панель: http://localhost:5000/admin

## Структура проєкту
```
online_restaurant_1/
├── app.py                   # Точка входу
├── online_restaurant.py     # Flask routes
├── online_restaurant_db.py  # SQLAlchemy моделі та seed
├── .env                     # Конфіг (DB URL, admin credentials)
├── requirements.txt
├── static/
│   ├── css/styles.css
│   ├── js/
│   └── menu/                # Зображення страв
└── templates/
    ├── base.html
    ├── home.html
    ├── menu.html
    ├── orders.html
    ├── reservation.html
    ├── login.html
    ├── register.html
    └── admin/
        ├── dashboard.html
        ├── menu_list.html
        ├── menu_form.html
        ├── orders.html
        ├── reservations.html
        ├── users.html
        ├── 403.html
        └── 404.html
```

## Функціонал
- ✅ Реєстрація / вхід / вихід
- ✅ Перегляд меню з фільтрами і сортуванням
- ✅ Замовлення страв
- ✅ Бронювання столиків
- ✅ Адмін-панель (меню, замовлення, бронювання, користувачі)
- ✅ Автоматичне заповнення БД при першому запуску
- ✅ PostgreSQL підключення
