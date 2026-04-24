from __future__ import annotations

from datetime import datetime, timedelta
import json
import os

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///online_restaurant.db")

# PostgreSQL needs no check_same_thread; SQLite does
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nickname: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    orders: Mapped[list["Orders"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class Menu(Base):
    __tablename__ = "menu"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="Основні страви")
    weight: Mapped[str] = mapped_column(String(50), default="")
    ingredients: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), default="placeholder.svg")


class Orders(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_list_text: Mapped[str] = mapped_column(Text, default="{}")
    total_price: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="Нове")
    order_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    user: Mapped["Users"] = relationship(back_populates="orders")

    @property
    def order_list(self):
        try:
            return json.loads(self.order_list_text or "{}")
        except Exception:
            return {}

    @order_list.setter
    def order_list(self, value):
        self.order_list_text = json.dumps(value, ensure_ascii=False)


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    type_table: Mapped[str] = mapped_column(String(100), nullable=False)
    guests: Mapped[int] = mapped_column(Integer, default=2)
    comment: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    user: Mapped["Users"] = relationship(back_populates="reservations")


def create_tables() -> None:
    Base.metadata.create_all(engine)


def seed_menu() -> None:
    dishes = [
        {"name": "Піца 4 сири", "category": "Піца", "weight": "520 г", "ingredients": "Моцарела, дорблю, пармезан, чедер, тісто, соус", "description": "Ніжна сирна піца з насиченим вершковим смаком.", "price": 289, "is_featured": True, "file_name": "4cheese.jpg"},
        {"name": "Бургер BBQ", "category": "Бургери", "weight": "340 г", "ingredients": "Яловичина, бекон, сир, BBQ соус, булочка", "description": "Соковитий бургер з димним BBQ соусом.", "price": 219, "is_featured": True, "file_name": "burger_bbq.jpg"},
        {"name": "Бургер Класичний", "category": "Бургери", "weight": "320 г", "ingredients": "Яловичина, сир, салат, помідор, булочка", "description": "Класичний бургер з яловичою котлетою та сиром.", "price": 185, "is_featured": True, "file_name": "burger_classic.jpg"},
        {"name": "Салат Цезар", "category": "Салати", "weight": "250 г", "ingredients": "Курка, романо, сухарики, пармезан, соус Цезар", "description": "Легендарний салат з куркою та пармезаном.", "price": 169, "is_featured": True, "file_name": "caesar.jpg"},
        {"name": "Рол Каліфорнія", "category": "Суші", "weight": "230 г", "ingredients": "Рис, крабовий мікс, авокадо, огірок, ікра масаго", "description": "Популярний рол з ніжною текстурою та свіжим смаком.", "price": 199, "is_featured": False, "file_name": "california.jpg"},
        {"name": "Чізкейк", "category": "Десерти", "weight": "150 г", "ingredients": "Сирний крем, вершки, печиво", "description": "Ніжний вершково-сирний десерт.", "price": 129, "is_featured": False, "file_name": "cheesecake.jpg"},
        {"name": "Курячий суп", "category": "Супи", "weight": "350 г", "ingredients": "Курка, локшина, бульйон, овочі", "description": "Домашній курячий суп для ситного обіду.", "price": 115, "is_featured": False, "file_name": "chicken_soup.jpg"},
        {"name": "Картопля фрі", "category": "Закуски", "weight": "140 г", "ingredients": "Картопля, сіль, соус", "description": "Хрустка картопля фрі — класика до будь-якої страви.", "price": 89, "is_featured": False, "file_name": "fries.jpg"},
        {"name": "Грецький салат", "category": "Салати", "weight": "260 г", "ingredients": "Овочі, фета, оливки, оливкова олія", "description": "Свіжий овочевий салат із сиром фета.", "price": 159, "is_featured": False, "file_name": "greek_salad.jpg"},
        {"name": "Лимонад", "category": "Напої", "weight": "400 мл", "ingredients": "Лимон, вода, цукор, м'ята", "description": "Освіжаючий домашній лимонад.", "price": 79, "is_featured": False, "file_name": "lemonade.jpg"},
        {"name": "Стейк Нью-Йорк", "category": "Стейки", "weight": "300 г", "ingredients": "Яловичина, спеції, соус", "description": "Класичний стейк із насиченим м'ясним смаком.", "price": 429, "is_featured": True, "file_name": "newyork_steak.jpg"},
        {"name": "Нагетси", "category": "Закуски", "weight": "180 г", "ingredients": "Куряче філе, панірування, соус", "description": "Хрусткі курячі нагетси з ніжним м'ясом усередині.", "price": 119, "is_featured": False, "file_name": "nuggets.jpg"},
        {"name": "Паста Болоньєзе", "category": "Паста", "weight": "340 г", "ingredients": "Спагеті, томатний соус, фарш, пармезан", "description": "Італійська паста з м'ясним соусом болоньєзе.", "price": 219, "is_featured": False, "file_name": "pasta_bolognese.jpg"},
        {"name": "Паста Карбонара", "category": "Паста", "weight": "320 г", "ingredients": "Спагеті, бекон, вершки, пармезан", "description": "Кремова паста з беконом і сиром.", "price": 229, "is_featured": False, "file_name": "pasta_carbonara.jpg"},
        {"name": "Піца Пепероні", "category": "Піца", "weight": "530 г", "ingredients": "Пепероні, сир, томатний соус, тісто", "description": "Піца з пікантною ковбаскою пепероні.", "price": 279, "is_featured": True, "file_name": "pepperoni.jpg"},
        {"name": "Рол Філадельфія", "category": "Суші", "weight": "240 г", "ingredients": "Лосось, крем-сир, рис, норі, огірок", "description": "Ніжний рол з лососем і крем-сиром.", "price": 249, "is_featured": True, "file_name": "philadelphia.jpg"},
        {"name": "Піца Класична", "category": "Піца", "weight": "510 г", "ingredients": "Сир, томатний соус, тісто, базилік", "description": "Універсальна піца на щодень.", "price": 239, "is_featured": False, "file_name": "pizza.jpg"},
        {"name": "Стейк Рібай", "category": "Стейки", "weight": "320 г", "ingredients": "Мармурова яловичина, спеції, соус", "description": "Соковитий рібай для справжніх поціновувачів м'яса.", "price": 459, "is_featured": True, "file_name": "ribeye.jpg"},
        {"name": "Тірамісу", "category": "Десерти", "weight": "160 г", "ingredients": "Савоярді, крем маскарпоне, кава, какао", "description": "Класичний італійський десерт з кавовими нотами.", "price": 139, "is_featured": False, "file_name": "tiramisu.jpg"},
        {"name": "Томатний суп", "category": "Супи", "weight": "320 г", "ingredients": "Томати, вершки, базилік, спеції", "description": "Ароматний томатний крем-суп.", "price": 119, "is_featured": False, "file_name": "tomato_soup.jpg"},
    ]

    with SessionLocal() as db:
        if db.query(Menu).count() == 0:
            for item in dishes:
                db.add(Menu(active=True, **item))
            db.commit()


def create_default_admin() -> None:
    admin_nickname = os.getenv("ADMIN_NICKNAME", "ADMIN")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@restaurant.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "ADMIN_123")

    with SessionLocal() as db:
        existing = db.query(Users).filter(
            (Users.nickname == admin_nickname) | (Users.email == admin_email)
        ).first()

        if existing:
            # Ensure admin rights and correct password
            existing.is_admin = True
            existing.nickname = admin_nickname
            existing.email = admin_email
            existing.set_password(admin_password)
            db.commit()
            return

        user = Users(nickname=admin_nickname, email=admin_email, is_admin=True)
        user.set_password(admin_password)
        db.add(user)
        db.commit()


def seed_demo_users_and_data() -> None:
    """Seed demo users with orders and reservations if tables are empty."""
    with SessionLocal() as db:
        # Only seed if there's only the admin user
        user_count = db.query(Users).count()
        if user_count > 1:
            return

        # Create demo users
        demo_users_data = [
            {"nickname": "ivan_user", "email": "ivan@example.com", "password": "demo1234"},
            {"nickname": "olena_k", "email": "olena@example.com", "password": "demo1234"},
            {"nickname": "mykola88", "email": "mykola@example.com", "password": "demo1234"},
        ]
        demo_users = []
        for u in demo_users_data:
            user = Users(nickname=u["nickname"], email=u["email"], is_admin=False)
            user.set_password(u["password"])
            db.add(user)
            demo_users.append(user)
        db.flush()

        # Get menu items for orders
        menu_items = db.query(Menu).filter_by(active=True).all()
        if not menu_items:
            db.commit()
            return

        # Seed demo orders
        orders_data = [
            {"dish": menu_items[0], "qty": 2, "status": "Завершено", "delta_hours": -48, "user_idx": 0},
            {"dish": menu_items[1], "qty": 1, "status": "В дорозі",  "delta_hours": -2,  "user_idx": 1},
            {"dish": menu_items[3], "qty": 1, "status": "Готується", "delta_hours": -1,  "user_idx": 2},
            {"dish": menu_items[6], "qty": 3, "status": "Нове",      "delta_hours":  0,  "user_idx": 0},
            {"dish": menu_items[10], "qty": 1, "status": "Підтверджено", "delta_hours": -5, "user_idx": 1},
            {"dish": menu_items[14], "qty": 2, "status": "Завершено", "delta_hours": -72, "user_idx": 2},
            {"dish": menu_items[17], "qty": 1, "status": "Скасовано", "delta_hours": -24, "user_idx": 0},
        ]
        for od in orders_data:
            dish = od["dish"]
            qty = od["qty"]
            order = Orders(
                order_list_text=json.dumps({
                    "name": dish.name,
                    "category": dish.category,
                    "price": dish.price,
                    "quantity": qty,
                    "file_name": dish.file_name,
                }, ensure_ascii=False),
                total_price=dish.price * qty,
                status=od["status"],
                order_time=datetime.utcnow() + timedelta(hours=od["delta_hours"]),
                user_id=demo_users[od["user_idx"]].id,
            )
            db.add(order)

        # Seed demo reservations
        table_options = ["2 місця", "4 місця", "6 місць", "VIP"]
        reservations_data = [
            {"table": table_options[0], "guests": 2, "delta_days": 1,  "comment": "Романтична вечеря", "user_idx": 0},
            {"table": table_options[1], "guests": 4, "delta_days": 2,  "comment": "День народження", "user_idx": 1},
            {"table": table_options[3], "guests": 6, "delta_days": 3,  "comment": "Корпоратив", "user_idx": 2},
            {"table": table_options[2], "guests": 5, "delta_days": -1, "comment": "Сімейний обід", "user_idx": 0},
        ]
        for rd in reservations_data:
            res = Reservation(
                time_start=datetime.utcnow() + timedelta(days=rd["delta_days"]),
                type_table=rd["table"],
                guests=rd["guests"],
                comment=rd["comment"],
                user_id=demo_users[rd["user_idx"]].id,
            )
            db.add(res)

        db.commit()


def init_database() -> None:
    create_tables()
    seed_menu()
    create_default_admin()
    seed_demo_users_and_data()
