import sqlite3
import datetime
import dateutil.parser
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from helpers import apology, allowed_file


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

try:
    conn = sqlite3.connect('main.sqlite', check_same_thread=False)
    cursor = conn.cursor()
except FileNotFoundError:
    apology("Технічні проблеми. Вирішуємо..")


@app.route("/")
def index():
    cursor.execute("""SELECT name FROM main.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'users' AND name NOT LIKE 'phones' AND name NOT LIKE 'reviews'""")
    categories = list(map(lambda x: x[0], cursor.fetchall()))
    items = {}
    for category in categories:
        cursor.execute("SELECT * FROM {table}".format(table=category))   
        data = cursor.fetchall()
        data = [dict(zip(["id", "name", "path", "price"], element)) for element in data]
        data += ["None"] * (3 - len(data) % 3)
        items[category] = data
    return render_template("index.html", items=items, id="admin" if session.get("user_id") == 1 else session.get("user_id"))


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/registered", methods=["POST", "GET"])
def registered():
    if request.method == "GET":
        return redirect('/register')
    name, pswrd, conf = request.form.get("uname"), request.form.get("pswd"), request.form.get("confirm")
    if not name or not pswrd or not conf:
        return apology("Ви маєте ввести всі данні задля закінчення регістрації")
    if not name.isalpha():
        return apology("Ім'я має включати в себе лише букви")
    if len(pswrd) < 6:
        return apology("Пароль не може бути коротший, ніж 6 символів")
    if pswrd != conf:
        return apology("Паролі не збігаються")
    cursor.execute("""SELECT id FROM users WHERE name = :name""",
    {"name": name})
    uid = cursor.fetchall()
    if not uid == []:
        return apology("Таке ім'я вже зареєстровано")
    else:
        cursor.execute("""INSERT INTO users
        ('name', 'password')
        VALUES (:name, :password)""",
        {"name": name,"password": generate_password_hash(pswrd)})
        conn.commit()
        cursor.execute("""SELECT id FROM users WHERE name = :name""",
        {"name": name})
        user_id = cursor.fetchall()
        session["user_id"] = user_id
        return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/logined", methods=["POST", "GET"])
def logined():
    if request.method == "GET":
        return redirect('/login')
    name, pswrd = request.form.get("uname"), request.form.get("pswd")
    if not name or not pswrd:
        return apology("Ви маєте ввести всі данні для входу")
    cursor.execute("""SELECT id, password FROM users WHERE name = :name""",
    {"name": name})
    try:
       uid, user_password = (e for e in cursor.fetchone())
    except ValueError:
        return apology(f"Введеного імені користувача ({name}) не існує. Перевірте правильність наданих данних")
    except TypeError:
        return apology(f"Введеного імені користувача ({name}) не існує. Перевірте правильність наданих данних")
    if user_password == []:
        print(uid, user_password)
        return apology(f"Введеного імені користувача ({name}) не існує. Перевірте правильність наданих данних")
    if not check_password_hash(user_password, pswrd):
        return apology("Ви ввели некоректний пароль. Перевірте правильність наданих данних")
    session["user_id"] = uid
    if name == "admin":
        return redirect("/admin", code=307)
    return redirect("/")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "GET":
        return apology("Щось пішло не так. Поверніться на сторінку входу та повторіть спробу.")
    return redirect("/")


@app.route("/admin_panel", methods=["GET", "POST"])
def admin_panel():
    if request.method == "GET":
        return apology("Щось пішло не так")
    cursor.execute("""SELECT name FROM main.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'users' AND name NOT LIKE 'phones' AND name NOT LIKE 'reviews'""")
    categories = list(map(lambda x: x[0], cursor.fetchall()))
    items = {}
    for category in categories:
        cursor.execute("SELECT * FROM {table}".format(table=category))   
        data = cursor.fetchall()
        data = [dict(zip(["id", "name", "path", "price"], element)) for element in data]
        data += ["None"] * (3 - len(data) % 3)
        items[category] = data
    return render_template("admin.html", id="admin_panel", items=items)


@app.route('/add', methods=["POST", "GET"])
def upload_file():
    if request.method == 'GET':
        return redirect("/admin_panel", code=307)
    else:
        file, name, price, category = request.files["image"], request.form.get("name"), request.form.get("price"), request.form.get("category")
        if file and name and price and allowed_file(file.filename):
            cursor.execute("SELECT MAX(ID) FROM {category}".format(category=category))
            max_id = cursor.fetchone()[0]
            filename = file.filename
            try:
                filename = f"{category}_{max_id + 1}{filename[filename.index('.'):]}"
            except TypeError:
                filename = f"{category}_0{filename[filename.index('.'):]}"
            file.save(os.path.join("static/img", filename))
            cursor.execute('INSERT INTO {table} ("title", "path", "price") VALUES (:name, :path, :price)'.format(table=category), {
                "name": name, "path": filename, "price": price
            })
            conn.commit()
            return redirect("/admin_panel", code=307)
        else:
            return apology("Введіть всі данні")


@app.route("/delete", methods=["POST"])
def delete():
    fname, category = request.form.get("delete"), request.form.get("category")
    cursor.execute("DELETE FROM {table} WHERE path = :fname".format(table=category), {"fname": fname})
    conn.commit()
    os.remove(os.path.join("static/img", fname))
    return redirect("/admin_panel", code=307)


@app.route("/delete_category", methods=["POST"])
def delete_category():
    category = request.form.get("category")
    if not category:
        return apology("Что-то пошло не так")
    cursor.execute("SELECT path FROM {name}".format(name=category))
    for fname in cursor.fetchall():
        os.remove(os.path.join("static/img", fname[0]))
    cursor.execute("DROP TABLE {table}".format(table=category))
    conn.commit()
    cursor.execute("""DELETE FROM phones WHERE category = :category""", {"category": category})
    conn.commit()
    return redirect("/admin_panel", code=307)



@app.route("/add_category", methods=["POST"])
def add_category():
    name, phone = request.form.get("name"), request.form.get("phone")
    if not name:
        apology("Введіть назву категорії")
    cursor.execute("""SELECT name FROM main.sqlite_master WHERE type='table'""")
    if name in cursor.fetchall():
        return apology("Категорія з таким іменем вже існує на сайті")
    cursor.execute("CREATE TABLE {table} ('id' integer PRIMARY KEY AUTOINCREMENT NOT NULL, 'title' varchar(256) NOT NULL, 'path' varchar(500) NOT NULL, 'price' integer NOT NULL)".format(table=name))
    conn.commit()
    cursor.execute("""INSERT into phones ('category', 'phone') VALUES (:name, :phone)""", {"name": name, "phone": int(phone)})
    conn.commit()
    return redirect("/admin_panel", code=307)


@app.route("/rename", methods=["POST"])
def rename():
    name, category = request.form.get("name"), request.form.get("category")
    if not name or not category:
        apology("Введіть назву категорії")
    cursor.execute("ALTER TABLE {table} RENAME to {name}".format(table=category, name=name))
    conn.commit()
    cursor.execute("UPDATE phones SET category {name} WHERE category = {table}".format(table=category, name=name))
    conn.commit()
    return redirect("/admin_panel", code=307)



@app.route("/sell", methods=["POST"])
def sell():
    category, name = request.form.get("category"), request.form.get("name")
    if not category or not name:
        return apology("Что то пошло не так")
    cursor.execute("""SELECT phone FROM phones WHERE category = :category""", {"category": category})
    phone = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM {table} WHERE title = '{name}'".format(table=category, name=name))
    item = cursor.fetchall()[0]
    item = dict(zip(["id", "name", "path", "price"], item))
    return render_template("sell.html", item=item, phone=phone)



@app.route("/reviews", methods=["POST"])
def reviews():
    cursor.execute("""SELECT * FROM reviews""")
    reviews = cursor.fetchall()
    reviews = [dict(zip(["id", "text", "username", "date"], review)) for review in reviews]
    return render_template("reviews.html", reviews=reviews)

@app.route("/save_review", methods=["POST"])
def save_review():
    text = request.form.get("text")
    if not text:
        return apology(text)
    uid = session.get("user_id")
    if uid is None:
        return redirect("/login")
    cursor.execute("""SELECT name FROM users where id = :id""", {"id": uid})
    uname = cursor.fetchone()[0]
    cursor.execute("""INSERT INTO reviews ('text', 'username', 'date') VALUES (:text, :username, :date)""", {"text": text, "username": uname, "date": datetime.datetime.now().strftime("%d-%m-%Y")})
    conn.commit()
    return redirect("/reviews", code=307)


if __name__ == '__main__':
    app.run()
