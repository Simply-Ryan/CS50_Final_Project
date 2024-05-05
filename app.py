import sqlite3
import locale
from datetime import datetime, timedelta
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

# Global Variables
bank_user_id = 1
db_name = "bank.db"
home_route = "/home"
signin_route = "/signin"
signout_route = "/signout"
register_route = "/register"
error_route = "/error"
settings_route = "/settings"
edit_profile_route = "/settings/edit"
transfers_route = "/transfers"
send_route = "/send"
request_route = "/request"
accept_route = "/accept"
reject_route = "/reject"
loans_route = "/loans"
edit_route = "/edit"
history_route = "/history"
delete_account_route = "/delete_account"

# Setup
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
connection = sqlite3.connect(db_name)
db = connection.cursor()
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8') # USD

# Table creation
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, first_name TEXT NOT NULL, last_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL)")
connection.commit()
db.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, balance REAL DEFAULT 0, FOREIGN KEY (user_id) REFERENCES users(id))")
connection.commit()
db.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, sender_id INTEGER, receiver_id INTEGER, amount REAL NOT NULL, reason TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (sender_id) REFERENCES users(id), FOREIGN KEY (receiver_id) REFERENCES users(id))")
connection.commit()
db.execute("CREATE TABLE IF NOT EXISTS loans (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL NOT NULL, interest_rate REAL NOT NULL, duration INTEGER NOT NULL, reason TEXT, start_date DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(id))")
connection.commit()
db.execute("CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, amount REAL NOT NULL, reason TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (sender_id) REFERENCES users(id), FOREIGN KEY (receiver_id) REFERENCES users(id))")
connection.commit()

# Login required
def signed_in():
    if session.get("user_id") is None:
        return False
    return True
# Login required

def check_form(elements):
    for element in elements:
        if element == "":
            return False
    return True


# Always check before accessing website
@app.before_request
def before_request_tasks():
    if not signed_in():
        return

    connection = sqlite3.connect(db_name)
    db = connection.cursor()

    # Check user loans
    db.execute("SELECT start_date, duration, amount, reason, id FROM loans WHERE user_id = ?", [session["user_id"]])
    loans = db.fetchall()

    for loan in loans:
        timestamp = datetime.strptime(loan[0], "%Y-%m-%d %H:%M:%S")
        if datetime.now() - timestamp > timedelta(days=int(loan[1])):
            # Repay loan automatically
            sent = send_money("Loan repayed", session["user_id"], bank_user_id, loan[2], loan[3])
            if not sent is None:
                return error(sent, 403)

            # Delete loan
            db.execute("DELETE FROM loans WHERE id = ?", [loan[4]])
            connection.commit()

    return

# Executes regardless of route
@app.context_processor
def get_username():
    username = None
    if "user_id" in session:
        connection = sqlite3.connect(db_name)
        db = connection.cursor()

        db.execute("SELECT username FROM users WHERE id = ?", [session["user_id"]])
        username = db.fetchone()[0]
        connection.close()

    return dict(username=username)

# Transfer money
def send_money(type, sender_id, receiver_id, amount, reason):
    connection = sqlite3.connect(db_name)
    db = connection.cursor()

    # Check funds sufficiency
    db.execute("SELECT balance FROM accounts WHERE user_id = ?", [sender_id])
    user_balance = db.fetchone()[0]
    if amount < 0 or amount > user_balance:
        return "Insufficient funds amount"
    
    # Check receiver existance
    if not receiver_id:
        return "Receiver not found"
    
    # Remove money from sender
    db.execute("SELECT balance FROM accounts WHERE user_id = ?", [sender_id])
    sender_balance = int(db.fetchone()[0])
    db.execute("UPDATE accounts SET balance = ? WHERE user_id = ?", (sender_balance - amount, session["user_id"]))
    
    # Add money to receiver
    db.execute("SELECT balance FROM accounts WHERE user_id = ?", [receiver_id])
    receiver_balance = int(db.fetchone()[0])
    db.execute("UPDATE accounts SET balance = ? WHERE user_id = ?", (receiver_balance + amount, receiver_id))

    # Log transaction
    db.execute("INSERT INTO transactions (type, sender_id, receiver_id, amount, reason) VALUES (?, ?, ?, ?, ?)", (type, sender_id, receiver_id, amount, reason))
    connection.commit()

    return

def error(msg, code):
    return render_template("error.html", message=msg, code=code)

def usd(value):
    # Format values as USD
    return f"${value:,.2f}"

# Redirect to home
@app.route("/")
def index():
    return redirect(home_route)

# Home
@app.route(home_route)
def home():
    if not signed_in():
        return redirect(signin_route)
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()

    # Get user balance
    db.execute("SELECT balance FROM accounts WHERE user_id = ?", [session["user_id"]])
    user_balance = db.fetchone()[0]
    balance = locale.currency(user_balance, grouping=True)

    db.execute("SELECT sender_id, amount, reason, timestamp FROM requests WHERE receiver_id = ?", [session["user_id"]])
    requests = db.fetchall()

    # Get usernames
    requests_with_username = []
    for sender_id, amount, reason, timestamp in requests:
        db.execute("SELECT username FROM users WHERE id = ?", [sender_id])
        sender_username = db.fetchone()[0]
        amount = locale.currency(amount, grouping=True)
        requests_with_username.append((sender_username, amount, reason, timestamp))

    # Most recent first
    requests_with_username.reverse()

    return render_template("home.html", balance=balance, requests=requests_with_username)

# Render error
@app.route(error_route)
def error(message, code):
    return render_template("error.html", message=message, code=code)

# Registry
@app.route(register_route, methods=["GET", "POST"])
def register():
    if signed_in():
        return redirect(home_route)
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()
    if request.method == "GET":
        return render_template("register.html")
    
    # CHECK IF EMAIL IS VALID ---------------------------------------------------- 

    # Check all fields
    username = request.form.get("username")
    password = request.form.get("password")

    if not check_form((username, password, request.form.get("first_name"), request.form.get("last_name"), request.form.get("email"))):
        return error("All fields must be filled.", 403)
    
    # Check passwords match
    if not request.form.get("password") == request.form.get("pwConfirm"):
        return error("Passwords do not match.", 403)
    
    # Check email is already in use
    db.execute("SELECT * FROM users WHERE email = ?", [request.form.get("email")])
    if db.fetchone():
        return error("Email address is already in use.", 403)
    
    # Check if username is already in use
    db.execute("SELECT * FROM users WHERE username = ?", [username])
    if db.fetchone():
        return error("Username already exists.", 403)

    # Create new user and store in session (cookies)
    hashedPassword = generate_password_hash(password)
    db.execute("INSERT INTO users (first_name, last_name, username, email, password) VALUES(?, ?, ?, ?, ?)", (request.form.get("first_name"), request.form.get("last_name"), request.form.get("username"), request.form.get("email"), hashedPassword))
    connection.commit()
    db.execute("SELECT id FROM users WHERE username = ?", [request.form.get("username")])
    user_id = db.fetchone()[0]
    db.execute("INSERT INTO accounts (user_id) VALUES (?)", [user_id])
    connection.commit()
    session["user_id"] = user_id
    
    return redirect(home_route)

# Sign in
@app.route(signin_route, methods=["GET", "POST"])
def signin():
    if signed_in():
        return redirect(home_route)
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()

    # User is entering website
    if request.method == "GET":
        return render_template("signin.html")
    
    # Check validity
    if not check_form((request.form.get("username"), request.form.get("password"))):
        return error("All fields must be filled.", 403)

    # Check username and password
    db.execute("SELECT id, password FROM users WHERE username = ?", [request.form.get("username")])
    user = db.fetchone()
    if user is None or not check_password_hash(user[1], request.form.get("password")):
        return error("Incorrect username or password.", 403)
    
    # Sign user in
    user_id = user[0]
    session["user_id"] = user_id
    return redirect(home_route)

# Sign out
@app.route(signout_route)
def signout():
    # Clear session (cookies)
    session.clear()
    return redirect(signin_route)

@app.route(settings_route)
def settings():
    if not signed_in():
        return redirect(signin_route)
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()

    db.execute("SELECT first_name, last_name, username, email FROM users WHERE id = ?", [session["user_id"]])
    user = db.fetchone()

    return render_template("settings.html", user=user)

# Edit profile
@app.route(edit_profile_route, methods=["GET", "POST"])
def edit_profile():
    if not signed_in():
        return redirect(signin_route)
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()
    
    if request.method == "GET":
        # Get user data
        db.execute("SELECT first_name, last_name, username, email FROM users WHERE id = ?", [session["user_id"]])
        data = db.fetchone()

        return render_template("edit_profile.html", data=data)
    
    # Check fields validity
    if not check_form((request.form.get("first_name"), request.form.get("last_name"), request.form.get("username"), request.form.get("email"))):
        return error("All fields must be filled.", 403)
    
    # Check username validity
    db.execute("SELECT id, username, email FROM users WHERE username = ? OR email = ?", (request.form.get("username"), request.form.get("email")))
    exists = db.fetchone()

    if exists and int(exists[0]) != session["user_id"]:
        return error("Username and/or email already exist(s).", 403)
    
    db.execute("UPDATE users SET first_name = ?, last_name = ?, username = ?, email = ? WHERE id = ?", (request.form.get("first_name"), request.form.get("last_name"), request.form.get("username"), request.form.get("email"), session["user_id"]))
    connection.commit()

    return redirect(settings_route)

# Transfer
@app.route(transfers_route)
def transfer():
    if not signed_in():
        return redirect(signin_route)
    
    return render_template("transfers.html")

@app.route(send_route, methods=["GET", "POST"])
def send():
    if not signed_in():
        return redirect(signin_route)
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()

    # Display send page if user is posting
    if request.method == "GET":
        return render_template("send.html")
    
    # Check password validity
    db.execute("SELECT password FROM users WHERE id = ?", [session["user_id"]])
    password = db.fetchone()[0]
    if not check_password_hash(password, request.form.get("password")):
        return error("Incorrect password.", 403)
    
    # Check form validity
    db.execute("SELECT id FROM users WHERE username = ?", [request.form.get("username")])
    receiver_id = db.fetchone()[0]
    if not receiver_id:
        return error("Recipient not found.", 403)
    
    # Check amount validity
    try:
        amount = int(request.form.get("amount"))
    except ValueError:
        return error("Invalid funds amount.", 403)

    sent = send_money("Transaction", session["user_id"], receiver_id, amount, request.form.get("reason"))
    if not sent is None:
        return error(sent, 403)

    return redirect(home_route)

@app.route(edit_route, methods=["GET", "POST"])
def edit():
    if not signed_in():
        return redirect(signin_route)

    if request.method == "GET":
        return render_template("edit.html")
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()

    # Make sure amount inputted is a valid integer (negative is allowed)
    try:
        amount = int(request.form.get("amount"))
    except ValueError:
        return error("Invalid amount.", 403)

    # Add money to user balance
    db.execute("SELECT balance FROM accounts WHERE user_id = ?", [session["user_id"]])
    user_balance = int(db.fetchone()[0])
    db.execute("UPDATE accounts SET balance = ? WHERE user_id = ?", (str(user_balance + amount), session["user_id"]))
    connection.commit()

    # Log transaction
    db.execute("INSERT INTO transactions (type, sender_id, receiver_id, amount) VALUES (?, ?, ?, ?)", ("Balance edit", session["user_id"], session["user_id"], amount))
    connection.commit()

    return redirect(home_route)

@app.route(request_route, methods=["GET", "POST"])
def requests():
    if not signed_in():
        return redirect(signin_route)
    
    if request.method == "GET":
        return render_template("request.html")
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()
    
    # Check password validity
    db.execute("SELECT password FROM users WHERE id = ?", [session["user_id"]])
    password = db.fetchone()[0]
    if not check_password_hash(password, request.form.get("password")):
        return error("Incorrect password.", 403)

    # Check amount validity
    try:
        amount = int(request.form.get("amount"))
    except ValueError:
        return error("Invalid funds amount.", 403)

    if amount < 0:
        return error("Invalid funds amount.", 403)
    
    # Check recipient validity
    db.execute("SELECT id FROM users WHERE username = ?", [request.form.get("username")])
    receiver_id = db.fetchone()[0]
    if not receiver_id:
        return error("Recipient not found.", 403)
    
    # Send request to recipient
    db.execute("INSERT INTO requests (sender_id, receiver_id, reason, amount) VALUES (?, ?, ?, ?)", (session["user_id"], receiver_id, request.form.get("reason"), amount))
    connection.commit()

    # Log request
    db.execute("INSERT INTO transactions (type, sender_id, receiver_id, reason, amount) VALUES (?, ?, ?, ?, ?)", ("Request sent", session["user_id"], receiver_id, request.form.get("reason"), amount))
    connection.commit()

    return redirect(home_route)

@app.route(accept_route, methods=["GET", "POST"])
def accept():
    if not signed_in():
        return redirect(signin_route)
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()
    
    # Check receiver validity
    db.execute("SELECT id FROM users WHERE username = ?", [request.form.get("receiver")])
    receiver_id = db.fetchone()[0]
    if not receiver_id:
        return error("Receiver does not exist.", 403)
    
    # Necessary data for transaction and verification
    amount = locale.atof(request.form.get("amount").strip('$').replace(',', ''))
    reason = request.form.get("reason")
    
    # Check request validity
    db.execute("SELECT id FROM requests WHERE sender_id = ? AND amount = ? AND reason = ?", (receiver_id, amount, reason))
    request_id = db.fetchone()[0]
    if not request_id:
        return error("Request does not exist.", 403)
    
    # Send money
    sent = send_money("Request accepted", session["user_id"], receiver_id, amount, reason)
    if not sent is None:
        return error(sent, 403)

    # Delete request
    db.execute("DELETE FROM requests WHERE sender_id = ? AND receiver_id = ? AND amount = ? AND reason = ?", (receiver_id, session["user_id"], amount, reason))
    connection.commit()

    return redirect(home_route)

@app.route(reject_route, methods=["GET", "POST"])
def reject():
    if not signed_in():
        return redirect(signin_route)
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()

    # Check receiver validity
    db.execute("SELECT id FROM users WHERE username = ?", [request.form.get("receiver")])
    receiver_id = db.fetchone()[0]
    if not receiver_id:
        return error("Receiver does not exist.", 403)
    
    # Necessary data for transaction and verification
    amount = locale.atof(request.form.get("amount").strip('$').replace(',', ''))
    reason = request.form.get("reason")
    timestamp = request.form.get("timestamp")
    
    # Check request validity
    db.execute("SELECT id FROM requests WHERE sender_id = ? AND amount = ? AND reason = ? AND timestamp = ?", (receiver_id, amount, reason, timestamp))
    request_id = db.fetchone()[0]
    if not request_id:
        return error("Request does not exist.", 403)
    
    # Log request rejection
    db.execute("INSERT INTO transactions (type, sender_id, receiver_id, amount, reason) VALUES (?, ?, ?, ?, ?)", ("Request refusal", session["user_id"], receiver_id, 0, reason))

    # Delete request
    db.execute("DELETE FROM requests WHERE sender_id = ? AND receiver_id = ? AND amount = ? AND reason = ? AND timestamp = ?", (receiver_id, session["user_id"], amount, reason, timestamp))
    connection.commit()

    return redirect(home_route)

@app.route(loans_route, methods=["GET", "POST"])
def loans():
    if not signed_in():
        return redirect(signin_route)
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()

    if request.method == "GET":
        # Get current loans
        db.execute("SELECT amount, interest_rate, duration, reason, start_date FROM loans WHERE user_id = ?", [session["user_id"]])
        loans = db.fetchall()
        
        loan_table = []
        for amount, interest, duration, reason, start_date in loans:
            amount = locale.currency(amount, grouping=True)
            interest = f"{interest}%"
            loan_table.append((amount, interest, duration, reason, start_date))

        # Most recent first
        loan_table.reverse()

        return render_template("loans.html", loan_table=loan_table)
    
    # Check amount validity
    try:
        amount = int(request.form.get("amount"))
        duration = int(request.form.get("duration"))
    except ValueError:
        return error("Invalid loan amount or duration.", 403)
    
    if amount < 0 or duration < 0:
        return error("Invalid loan amount or duration.", 403)
    
    # Check password validity
    db.execute("SELECT password FROM users WHERE id = ?", [session["user_id"]])
    password = db.fetchone()[0]
    if not check_password_hash(password, request.form.get("password")):
        return error("Incorrect password.", 403)
    
    # Loan money
    sent = send_money("Loan", bank_user_id, session["user_id"], amount, request.form.get("reason"))
    if not sent is None:
        return error(sent, 403)
    
    # Log loan
    db.execute("INSERT INTO loans (user_id, amount, interest_rate, duration, reason) VALUES (?, ?, ?, ?, ?)", (session["user_id"], amount, "10", duration, request.form.get("reason")))
    connection.commit()
    
    return redirect(loans_route)

    """elif form_id == "2": # User is repaying a loan
        # Check loan validity
        amount = int(request.form.get("amount"))
        interest = int(request.form.get("interest"))
        duration = int(request.form.get("duration"))
        reason = request.form.get("reason")
        start_date = request.form.get("start_date")

        db.execute("SELECT id FROM loans WHERE user_id = ? AND amount = ? AND interest = ? AND duration = ? AND reason = ? AND start_date = ?", (session["user_id"], amount, interest, duration, reason, start_date))
        loan_id = db.fetchone()

        if not loan_id:
            return error("Loan does not exist.", 403)
        
        # Calculate interest
        amount_with_interest = amount + amount * (interest / 100)

        # Pay loan
        sent = send_money("Loan repayed", session["user_id"], bank_user_id, amount_with_interest, reason)
        if not sent is None:
            return error(sent, 403)

        # Delete loan
        db.execute("DELETE FROM loans WHERE id = ?", [loan_id[0]])
        connection.commit()

        return redirect(home_route)

    # Invalid form
    return error("Invalid loan form.", 403)"""

@app.route(history_route)
def history():
    if not signed_in():
        return redirect(signin_route)
    
    connection = sqlite3.connect(db_name)
    db = connection.cursor()

    db.execute("SELECT type, sender_id, receiver_id, amount, reason, timestamp FROM transactions WHERE sender_id = ? OR receiver_id = ?", (session["user_id"], session["user_id"]))
    transactions = db.fetchall()

    transactions_with_usernames = []
    for type, sender_id, receiver_id, amount, reason, timestamp in transactions:
        db.execute("SELECT username FROM users WHERE id = ?", [sender_id])
        sender_username = db.fetchone()[0]
        db.execute("SELECT username FROM users WHERE id = ?", ([receiver_id]))
        receiver_username = db.fetchone()[0]
        amount = locale.currency(amount, grouping=True)
        transactions_with_usernames.append((type, sender_username, receiver_username, amount, reason, timestamp))

    # Most recent first
    transactions_with_usernames.reverse()

    return render_template("history.html", transactions=transactions_with_usernames)

@app.route(delete_account_route)
def delete_account():
    if not signed_in():
        redirect(signin_route)

    connection = sqlite3.connect(db_name)
    db = connection.cursor()
    db.execute("DELETE FROM users WHERE id = ?", [session["user_id"]])
    db.execute("DELETE FROM accounts WHERE user_id = ?", [session["user_id"]])
    db.execute("DELETE FROM transactions WHERE sender_id = ? OR receiver_id = ?", (session["user_id"], session["user_id"]))
    db.execute("DELETE FROM loans WHERE user_id = ?", [session["user_id"]])
    db.execute("DELETE FROM requests WHERE user_id = ?", [session["user_id"]])
    connection.commit()
    session.clear()
    
    return redirect(signin_route)

# Disconnect from database
connection.close()