# Imports
from helpers import error, usd
import sqlite3
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

# Setup
app = Flask(__name__)
app.jinja_env.filters["usd"] = usd
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
connection = sqlite3.connect("dealership.db")
db = connection.cursor()

db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER AUTO_INCREMENT PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL, username TEXT NOT NULL UNIQUE, password TEXT NOT NULL)")
connection.commit()

# Home
@app.route("/")
def index():
    if "user_id" in session:
        return redirect("/login")
    
    return render_template("index.html")

# Registry
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    
    # Check all fields and redirect to index
    if not request.form.get("password") == request.form.get("pwConfirm"):
        return error("Passwords do not match.", 403)

    # Check username availability
    username = request.form.get("username")
    if db.execute("SELECT * FROM users WHERE username = ?", username):
        return error("Username already exists.", 403)

    # Create new user and store in session (cookies)
    hashedPassword = generate_password_hash(request.form.get("password"))
    db.execute("INSERT INTO users (first_name, last_name, username, password) VALUES(?, ?, ?, ?)", request.form.get("firstname"), request.form.get("lastname"), username , hashedPassword)
    connection.commit()
    session["user_id"] = db.execute("SELECT id FROM users WHERE username = ?", username)
    return redirect("/")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    # User is entering website
    if request.method == "GET":
        return render_template("login.html")
    
    # Check validity
    if check_password_hash(db.execute("SELECT password FROM users WHERE username = ?", request.form.get("username")), request.form.get("password")):
        return error("Incorrect username or password.", 403)
    
    session["user_id"] = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))
    return redirect("/")

# Disconnect database
connection.close()

# Debug mode
if __name__ == "__main__":
    app.run(debug=True)