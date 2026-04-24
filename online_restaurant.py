from __future__ import annotations

from datetime import datetime
from functools import wraps
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload

from online_restaurant_db import (
    SessionLocal,
    Menu,
    Orders,
    Reservation,
    Users,
    init_database,
)


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super_secret_key_change_me_123!")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["WTF_CSRF_ENABLED"] = True

csrf = CSRFProtect(app)
app.jinja_env.globals["csrf_token"] = generate_csrf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_PATH = os.path.join(BASE_DIR, "static", "menu")
os.makedirs(FILES_PATH, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ORDER_STATUSES = ["Нове", "Підтверджено", "Готується", "В дорозі", "Завершено", "Скасовано"]
TABLE_OPTIONS = ["2 місця", "4 місця", "6 місць", "VIP"]


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Спочатку увійдіть у систему"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    with SessionLocal() as db:
        return db.get(Users, int(user_id))


@app.context_processor
def inject_globals():
    return {
        "current_year": datetime.now().year,
        "order_statuses": ORDER_STATUSES,
    }


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return func(*args, **kwargs)
    return wrapper


def save_uploaded_image(uploaded_file) -> str:
    safe_name = secure_filename(uploaded_file.filename)
    ext = safe_name.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}_{safe_name.rsplit('.', 1)[0]}.{ext}"
    return filename


# ─── Public Routes ────────────────────────────────────────────────────────────

@app.route("/")
@app.route("/home")
def home():
    with SessionLocal() as db:
        featured_items = db.query(Menu).filter_by(active=True, is_featured=True).limit(4).all()
        menu_count = db.query(Menu).filter_by(active=True).count()
        orders_count = db.query(Orders).count()
        reservations_count = db.query(Reservation).count()

    return render_template(
        "home.html",
        featured_items=featured_items,
        menu_count=menu_count,
        orders_count=orders_count,
        reservations_count=reservations_count,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not nickname or not email or not password:
            flash("Заповніть усі поля", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Пароль має містити щонайменше 6 символів", "danger")
            return render_template("register.html")

        with SessionLocal() as db:
            user_exist = db.query(Users).filter(
                (Users.email == email) | (Users.nickname == nickname)
            ).first()
            if user_exist:
                flash("Користувач з таким email або nickname вже існує", "danger")
                return render_template("register.html")

            new_user = Users(nickname=nickname, email=email, is_admin=False)
            new_user.set_password(password)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            login_user(new_user)
            flash("Реєстрація успішна! Ласкаво просимо!", "success")
            return redirect(url_for("home"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        password = request.form.get("password", "").strip()

        if not nickname or not password:
            flash("Введіть nickname і пароль", "danger")
            return render_template("login.html")

        with SessionLocal() as db:
            user = db.query(Users).filter_by(nickname=nickname).first()
            if user and user.check_password(password):
                login_user(user)
                next_page = request.args.get("next")
                flash("Ви успішно увійшли", "success")
                return redirect(next_page or url_for("home"))

        flash("Неправильний nickname або пароль", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Ви вийшли з акаунту", "info")
    return redirect(url_for("home"))


@app.route("/menu")
def menu():
    category = request.args.get("category", "all")
    sort = request.args.get("sort", "popular")

    with SessionLocal() as db:
        query = db.query(Menu).filter_by(active=True)
        if category != "all":
            query = query.filter(Menu.category == category)

        if sort == "price_asc":
            query = query.order_by(Menu.price.asc())
        elif sort == "price_desc":
            query = query.order_by(Menu.price.desc())
        else:
            query = query.order_by(Menu.is_featured.desc(), Menu.id.desc())

        dishes = query.all()
        categories = [
            item[0]
            for item in db.query(Menu.category).filter_by(active=True).distinct().order_by(Menu.category.asc()).all()
            if item[0]
        ]

    return render_template(
        "menu.html",
        dishes=dishes,
        categories=categories,
        active_category=category,
        active_sort=sort,
    )


@app.route("/reservation", methods=["GET", "POST"])
@login_required
def reservation():
    if request.method == "POST":
        time_start = request.form.get("time_start")
        type_table = request.form.get("type_table")
        guests = request.form.get("guests", "2")
        comment = request.form.get("comment", "").strip()

        if not time_start or not type_table:
            flash("Заповніть усі обов'язкові поля", "danger")
            return render_template("reservation.html", table_options=TABLE_OPTIONS)

        try:
            reservation_time = datetime.fromisoformat(time_start)
            guests_value = max(1, int(guests))
        except ValueError:
            flash("Неправильний формат дати, часу або кількості гостей", "danger")
            return render_template("reservation.html", table_options=TABLE_OPTIONS)

        with SessionLocal() as db:
            new_reservation = Reservation(
                time_start=reservation_time,
                type_table=type_table,
                guests=guests_value,
                comment=comment,
                user_id=current_user.id,
            )
            db.add(new_reservation)
            db.commit()

        flash("Бронювання успішно створено!", "success")
        return redirect(url_for("home"))

    return render_template("reservation.html", table_options=TABLE_OPTIONS)


@app.route("/orders")
@login_required
def orders():
    with SessionLocal() as db:
        user_orders = (
            db.query(Orders)
            .filter_by(user_id=current_user.id)
            .order_by(Orders.order_time.desc())
            .all()
        )
    return render_template("orders.html", orders=user_orders)


@app.route("/add_order", methods=["POST"])
@login_required
def add_order():
    dish_id = request.form.get("dish_id")
    quantity = request.form.get("quantity", "1")

    if not dish_id:
        flash("Страву не вибрано", "danger")
        return redirect(url_for("menu"))

    try:
        quantity = max(1, int(quantity))
    except ValueError:
        quantity = 1

    with SessionLocal() as db:
        dish = db.get(Menu, int(dish_id))
        if not dish:
            flash("Страву не знайдено", "danger")
            return redirect(url_for("menu"))

        # Зберігаємо потрібні дані ДО закриття сесії
        dish_name = dish.name
        dish_category = dish.category
        dish_price = dish.price
        dish_file = dish.file_name

        import json
        total_price = dish_price * quantity
        new_order = Orders(
            order_list_text=json.dumps({
                "name": dish_name,
                "category": dish_category,
                "price": dish_price,
                "quantity": quantity,
                "file_name": dish_file,
            }, ensure_ascii=False),
            total_price=total_price,
            status="Нове",
            order_time=datetime.utcnow(),
            user_id=current_user.id,
        )
        db.add(new_order)
        db.commit()

    flash(f"«{dish_name}» додано до замовлень!", "success")
    return redirect(url_for("orders"))


# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    with SessionLocal() as db:
        users_count = db.query(Users).count()
        menu_count = db.query(Menu).count()
        orders_count = db.query(Orders).count()
        reservations_count = db.query(Reservation).count()
        latest_orders = db.query(Orders).options(joinedload(Orders.user)).order_by(Orders.order_time.desc()).limit(5).all()
        latest_reservations = db.query(Reservation).options(joinedload(Reservation.user)).order_by(Reservation.time_start.desc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        users_count=users_count,
        menu_count=menu_count,
        orders_count=orders_count,
        reservations_count=reservations_count,
        latest_orders=latest_orders,
        latest_reservations=latest_reservations,
    )


@app.route("/admin/menu")
@login_required
@admin_required
def admin_menu():
    with SessionLocal() as db:
        dishes = db.query(Menu).order_by(Menu.id.desc()).all()
    return render_template("admin/menu_list.html", dishes=dishes)


@app.route("/admin/menu/create", methods=["GET", "POST"])
@login_required
@admin_required
def admin_menu_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "Основні страви").strip()
        weight = request.form.get("weight", "").strip()
        ingredients = request.form.get("ingredients", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "").strip()
        active = request.form.get("active") == "on"
        is_featured = request.form.get("is_featured") == "on"

        if not name or not price_raw:
            flash("Назва і ціна обов'язкові", "danger")
            return render_template("admin/menu_form.html", dish=None)

        try:
            price = int(price_raw)
        except ValueError:
            flash("Ціна повинна бути числом", "danger")
            return render_template("admin/menu_form.html", dish=None)

        uploaded_file = request.files.get("image")
        file_name = "placeholder.svg"

        if uploaded_file and uploaded_file.filename:
            if allowed_file(uploaded_file.filename):
                file_name = save_uploaded_image(uploaded_file)
                uploaded_file.save(os.path.join(FILES_PATH, file_name))
            else:
                flash("Дозволені тільки png, jpg, jpeg, webp", "danger")
                return render_template("admin/menu_form.html", dish=None)

        with SessionLocal() as db:
            dish = Menu(
                name=name,
                category=category,
                weight=weight,
                ingredients=ingredients,
                description=description,
                price=price,
                active=active,
                is_featured=is_featured,
                file_name=file_name,
            )
            db.add(dish)
            db.commit()

        flash(f"Страву «{name}» додано", "success")
        return redirect(url_for("admin_menu"))

    return render_template("admin/menu_form.html", dish=None)


@app.route("/admin/menu/edit/<int:dish_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_menu_edit(dish_id):
    with SessionLocal() as db:
        dish = db.get(Menu, dish_id)
        if not dish:
            abort(404)

        if request.method == "POST":
            dish.name = request.form.get("name", "").strip()
            dish.category = request.form.get("category", "Основні страви").strip()
            dish.weight = request.form.get("weight", "").strip()
            dish.ingredients = request.form.get("ingredients", "").strip()
            dish.description = request.form.get("description", "").strip()
            price_raw = request.form.get("price", "0").strip()
            dish.active = request.form.get("active") == "on"
            dish.is_featured = request.form.get("is_featured") == "on"

            try:
                dish.price = int(price_raw)
            except ValueError:
                flash("Ціна повинна бути числом", "danger")
                return render_template("admin/menu_form.html", dish=dish)

            uploaded_file = request.files.get("image")
            if uploaded_file and uploaded_file.filename:
                if allowed_file(uploaded_file.filename):
                    file_name = save_uploaded_image(uploaded_file)
                    uploaded_file.save(os.path.join(FILES_PATH, file_name))
                    dish.file_name = file_name
                else:
                    flash("Дозволені тільки png, jpg, jpeg, webp", "danger")
                    return render_template("admin/menu_form.html", dish=dish)

            db.commit()
            flash(f"Страву «{dish.name}» оновлено", "success")
            return redirect(url_for("admin_menu"))

    return render_template("admin/menu_form.html", dish=dish)


@app.route("/admin/menu/delete/<int:dish_id>", methods=["POST"])
@login_required
@admin_required
def admin_menu_delete(dish_id):
    with SessionLocal() as db:
        dish = db.get(Menu, dish_id)
        if not dish:
            abort(404)
        name = dish.name
        db.delete(dish)
        db.commit()

    flash(f"Страву «{name}» видалено", "info")
    return redirect(url_for("admin_menu"))


@app.route("/admin/orders")
@login_required
@admin_required
def admin_orders():
    with SessionLocal() as db:
        all_orders = db.query(Orders).options(joinedload(Orders.user)).order_by(Orders.order_time.desc()).all()
    return render_template("admin/orders.html", orders=all_orders)


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@login_required
@admin_required
def admin_order_status(order_id):
    new_status = request.form.get("status", "Нове")
    if new_status not in ORDER_STATUSES:
        flash("Невірний статус", "danger")
        return redirect(url_for("admin_orders"))

    with SessionLocal() as db:
        order = db.get(Orders, order_id)
        if not order:
            abort(404)
        order.status = new_status
        db.commit()

    flash("Статус замовлення оновлено", "success")
    return redirect(url_for("admin_orders"))


@app.route("/admin/reservations")
@login_required
@admin_required
def admin_reservations():
    with SessionLocal() as db:
        reservations = db.query(Reservation).options(joinedload(Reservation.user)).order_by(Reservation.time_start.desc()).all()
    return render_template("admin/reservations.html", reservations=reservations)


@app.route("/admin/reservations/<int:reservation_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_reservation_delete(reservation_id):
    with SessionLocal() as db:
        item = db.get(Reservation, reservation_id)
        if not item:
            abort(404)
        db.delete(item)
        db.commit()

    flash("Бронювання видалено", "info")
    return redirect(url_for("admin_reservations"))


@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    with SessionLocal() as db:
        users = db.query(Users).order_by(Users.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@app.route("/admin/users/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
@admin_required
def admin_toggle_user(user_id):
    if current_user.id == user_id:
        flash("Не можна забрати права адміністратора у самого себе", "warning")
        return redirect(url_for("admin_users"))

    with SessionLocal() as db:
        user = db.get(Users, user_id)
        if not user:
            abort(404)
        user.is_admin = not user.is_admin
        db.commit()

    flash("Роль користувача оновлено", "success")
    return redirect(url_for("admin_users"))


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(400)
def bad_request(error):
    return render_template("admin/404.html"), 400


@app.errorhandler(403)
def forbidden(error):
    return render_template("admin/403.html"), 403


@app.errorhandler(404)
def not_found(error):
    return render_template("admin/404.html"), 404


@app.errorhandler(413)
def too_large(error):
    flash("Файл занадто великий. Максимум 16 МБ.", "danger")
    return redirect(request.referrer or url_for("home")), 413


# ─── Init ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_database()
    app.run(debug=True, host="0.0.0.0", port=5000)