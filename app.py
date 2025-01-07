import pymongo
import os
import urllib
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, session
from markupsafe import Markup
import datetime
import pandas as pd
import plotly.express as px
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
'''
create vars for total balance, current balance etc for each user
show the vars in frontend



'''

app = Flask(__name__)
CORS(app)
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")


class BudgetTracker:
    def __init__(self, user_id=None, username=None, database_name="budget_tracker", user_collection_name="users",
                 collection_name="expenses", deposits_collection_name="deposits",
                 withdrawals_collection_name="withdrawals", transactions_collection_name="transactions"):
        
        self.__balance = 0
        self.expenses = []
        self.user_id = user_id
        self.username = username
        self.users_collection = None
        self.expenses_collection = None
        self.deposits_collection = None
        self.withdrawals_collection = None
        self.transactions_collection = None

        # MongoDB Connection
        username = urllib.parse.quote_plus(os.getenv("DB_USER"))
        password = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
        connection_string = f"mongodb+srv://{username}:{
            password}@cluster0.6w52j.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"

        try:
            self.client = pymongo.MongoClient(
                connection_string, serverSelectionTimeoutMS=5000)
            self.db = self.client[database_name]
            self.users_collection = self.db[user_collection_name]
            self.expenses_collection = self.db[collection_name]
            self.deposits_collection = self.db[deposits_collection_name]
            self.withdrawals_collection = self.db[withdrawals_collection_name]
            self.transactions_collection = self.db[transactions_collection_name]
            self.load_user_data()
        except pymongo.errors.PyMongoError as e:
            print(f"Error connecting to MongoDB: {e}")

    def format_date(self, date):
        try:
            if isinstance(date, str):
                # Parse assuming the input is in the format "%Y-%m-%d"
                date = datetime.strptime(date, "%Y-%m-%d")
            elif isinstance(date, datetime):
                # Already a datetime object, no need to parse
                pass
            else:
                raise ValueError("Unsupported date format")
            # Return date in the format "02 January 2025"
            return date.strftime("%d %B %Y")
        except (ValueError, AttributeError) as e:
            print(f"Error formatting date: {e}")
            return "Invalid date"



    def load_user_data(self):
        try:
            user_data = None
            if self.user_id:
                user_data = self.users_collection.find_one(
                    {"user_id": self.user_id})
            elif self.username:
                user_data = self.users_collection.find_one(
                    {"username": self.username})

            if user_data:
                self.user_id = user_data.get("user_id")
                self.username = user_data.get("username")
                self.__balance = user_data.get("balance", 0)
        except Exception as e:
            print(f"Error loading user data: {e}")

    def create_user(self, user_data):
        try:
            if not user_data.get("user_id"):
                user_data["user_id"] = str(uuid.uuid4())

            result = self.users_collection.insert_one(user_data)
            if result.inserted_id:
                self.user_id = user_data["user_id"]
                self.username = user_data.get("username")
                self.__balance = user_data.get("balance", 0)
                return True
            return False
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

    def get_balance(self):
        try:
            user_data = self.users_collection.find_one(
                {"user_id": self.user_id})
            if user_data:
                self.__balance = user_data.get("balance", 0)
        except Exception as e:
            print(f"Error fetching balance: {e}")
        return self.__balance

    def update_balance(self):
        try:
            self.users_collection.update_one(
                {"user_id": self.user_id},
                {"$set": {"balance": self.__balance}},
                upsert=True
            )
        except pymongo.errors.PyMongoError as e:
            print(f"Error updating balance: {e}")
            raise RuntimeError("Failed to update balance in the database.")

    def deposit(self, amount, date):
        if amount > 0:
            self.__balance += amount
            transaction = {
                "user_id": self.user_id,
                "amount": amount,
                "date": self.format_date(date),
                "action": "deposit"
            }
            self.transactions_collection.insert_one(transaction)
            self.update_balance()
            return f"Deposited: {amount}, New Balance: {self.__balance}"
        return "Invalid deposit amount. Please enter a positive value."

    def withdraw(self, amount, date):
        if amount <= self.__balance:
            self.__balance -= amount
            transaction = {
                "user_id": self.user_id,
                "amount": amount,
                "date": self.format_date(date),
                "action": "withdraw"
            }
            self.transactions_collection.insert_one(transaction)
            self.update_balance()
            return f"Withdrawn: {amount}, New Balance: {self.__balance}"
        return "Insufficient funds."

    def add_expense(self, amount, title, category, date):
        if amount > 0 and amount <= self.__balance:
            self.__balance -= amount
            expense = {
                "user_id": self.user_id,
                "amount": amount,
                "title": title,
                "category": category,
                "date": self.format_date(date)
            }
            self.expenses_collection.insert_one(expense)
            # Update total expenses in users_collection
            total_expenses = self.total_expenses() + amount
            self.users_collection.update_one(
                {"user_id": self.user_id},
                {"$set": {"total_expenses": total_expenses}}
            )
            self.update_balance()
            return f"Expense added: {expense}"
        return "Invalid amount or insufficient balance."

        if amount > 0 and amount <= self.__balance:
            self.__balance -= amount
            expense = {
                "user_id": self.user_id,
                "amount": amount,
                "title": title,
                "category": category,
                "date": self.format_date(date)
            }
            self.expenses_collection.insert_one(expense)
            self.update_balance()
            return f"Expense added: {expense}"
        return "Invalid amount or insufficient balance."

    def total_expenses(self):
        total = 0
        try:
            expenses = self.expenses_collection.find({"user_id": self.user_id})
            total = sum(expense.get("amount", 0) for expense in expenses)
        except Exception as e:
            print(f"Error calculating total expenses: {e}")
        return total

    def generate_charts(self):
        try:
            expenses = list(self.expenses_collection.find(
                {"user_id": self.user_id}))
            if not expenses:
                return {
                    "pie_chart": px.pie(title="No Expenses Recorded").to_html(full_html=False),
                    "line_chart": px.line(title="No Expenses Recorded").to_html(full_html=False),
                    "bar_chart": px.bar(title="No Expenses Recorded").to_html(full_html=False)
                }

            expenses_df = pd.DataFrame(expenses)
            expenses_df['Amount'] = pd.to_numeric(
                expenses_df['amount'], errors='coerce')
            expenses_df['Date'] = pd.to_datetime(expenses_df['date'], format="%Y-%m-%d", errors='coerce')
            expenses_df['Formatted Date'] = expenses_df['Date'].dt.strftime("%d %B %Y")


            category_counts = expenses_df.groupby(
                "category")["Amount"].sum().reset_index()
            pie_chart = px.pie(category_counts, values='Amount',
                               names='category', title="Expenses by Category")

            expenses_df['YearMonth'] = expenses_df['Date'].dt.to_period(
                'M').astype(str)
            monthly_trends = expenses_df.groupby(
                "YearMonth")["Amount"].sum().reset_index()
            line_chart = px.line(monthly_trends, x="YearMonth",
                                 y="Amount", title="Monthly Expense Trends", markers=True)

            bar_chart = px.bar(category_counts, x='category', y='Amount',
                               title="Expenses by Category", color="category")

            return {
                "pie_chart": pie_chart.to_html(full_html=False),
                "line_chart": line_chart.to_html(full_html=False),
                "bar_chart": bar_chart.to_html(full_html=False)
            }
        except Exception as e:
            print(f"Error generating charts: {e}")
            return {
                "pie_chart": px.pie(title="Error Generating Charts").to_html(full_html=False),
                "line_chart": px.line(title="Error Generating Charts").to_html(full_html=False),
                "bar_chart": px.bar(title="Error Generating Charts").to_html(full_html=False)
            }

# Flask Routes

@app.route("/", methods=["GET"])
def default():
    print(f"Session during default route: {session}")  # Add this line for debugging
    if session.get("logged_in"):  # Check directly for 'logged_in' in session
        print("Logged in, redirecting to index.")
        return redirect(url_for("index"))
    print("Not logged in, redirecting to login.")
    return redirect(url_for("login"))



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        firstname = request.form.get("firstname", "").strip()
        lastname = request.form.get("lastname", "").strip()

        if not username or not password or not firstname or not lastname:
            flash("All fields are required.")
            return redirect(url_for("register"))

        if len(username) < 3 or len(password) < 6:
            flash(
                "Username must be at least 3 characters and password at least 6 characters.")
            return redirect(url_for("register"))

        try:
            tracker = BudgetTracker(username=username)

            if tracker.users_collection.find_one({"username": username}):
                flash("Username already exists.")
                return redirect(url_for("register"))

            user_id = str(uuid.uuid4())
            hashed_password = generate_password_hash(
                password, method='pbkdf2:sha256', salt_length=16)

            user_data = {
                "user_id": user_id,
                "firstName": firstname,
                "lastName": lastname,
                "username": username,
                "hashed_password": hashed_password,
                "balance": 0,
                "created_at": datetime.datetime.now()
            }

            result = tracker.users_collection.insert_one(user_data)

            if result.inserted_id:
                session.clear()
                session["logged_in"] = True
                session["username"] = username
                session["user_id"] = user_id
                flash("Account created successfully!")
                return redirect(url_for("index"))

        except Exception as e:
            print(f"Registration error: {e}")
            flash("An error occurred during registration.")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Check for empty fields
        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("login"))

        try:
            # Initialize BudgetTracker with the provided username
            tracker = BudgetTracker(username=username)

            # Fetch the user from the database
            user = tracker.users_collection.find_one({"username": username})

            # If user is found, validate the password
            if user and check_password_hash(user.get("hashed_password", ""), password):
                print("Login successful, setting session variables.")
                session["logged_in"] = True
                session["username"] = username
                session["user_id"] = user["user_id"]
                flash("Login successful!", "success")
                print(f"Session after login: {session}")  # Debug session after login
                return redirect(url_for("index"))

            flash("Invalid username or password.", "error")


        except pymongo.errors.PyMongoError as db_error:
            print(f"Database error during login: {db_error}")
            flash(
                "An error occurred while connecting to the database. Please try again later.", "error")
        except Exception as e:
            print(f"Unexpected error during login: {e}")
            flash("An unexpected error occurred. Please try again later.", "error")

    return render_template("login.html")

@app.route("/index", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    tracker = BudgetTracker(
        user_id=session["user_id"], 
        username=session.get("username")
    )

    try:
        if request.method == "POST":
            action_type = request.form.get("action_type")
            amount_str = request.form.get("amount", "").strip()
            date_str = request.form.get("date", "").strip()

            if not action_type or not amount_str or not date_str:
                flash("All fields (action type, amount, and date) are required.")
                return redirect(url_for("index"))

            try:
                amount = float(amount_str)
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%d %B %Y")
            except ValueError:
                flash("Invalid date format. Use YYYY-MM-DD.")
                return redirect(url_for("index"))

            if action_type == "transaction":
                title = request.form.get("title", "").strip()
                category = request.form.get("category", "").strip()
                if not title or not category:
                    flash("Title and category are required for transactions.")
                    return redirect(url_for("index"))
                tracker.add_expense(amount, title, category, formatted_date)
                flash(f"Transaction '{title}' added successfully.")
            elif action_type == "deposit":
                tracker.deposit(amount, formatted_date)
                flash(f"Deposit of {amount:.2f} added successfully.")
            elif action_type == "withdraw":
                tracker.withdraw(amount, formatted_date)
                flash(f"Withdrawal of {amount:.2f} processed successfully.")
            else:
                flash("Invalid action type. Please try again.")
                return redirect(url_for("index"))

            return redirect(url_for("index"))

        expenses = list(tracker.expenses_collection.find(
            {"user_id": session["user_id"]}
        ).sort("date", -1))
        for expense in expenses:
            try:
                date_obj = datetime.strptime(expense["date"], "%d %B %Y")
                expense["date"] = date_obj.strftime("%d %B %Y")
            except ValueError as e:
                app.logger.error(f"Error parsing date: {str(e)}")

        charts = tracker.generate_charts()

        return render_template(
            "index.html",
            balance=tracker.get_balance(),
            total_expenses=tracker.total_expenses(),
            username=session.get("username"),
            expenses=expenses,
            pie_chart=Markup(charts["pie_chart"]),
            line_chart=Markup(charts["line_chart"]),
            bar_chart=Markup(charts["bar_chart"]),
        )

    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for("index"))


@app.route("/expenses", methods=["GET", "POST"])
def show_expenses():
    user_id = session.get("user_id")
    tracker = BudgetTracker(user_id=session.get("user_id"))

    if not user_id:
        return redirect(url_for("login"))  # Redirect to login if user is not logged in

    try:
        # Assuming `tracker.expenses` is a MongoDB collection or query
        expenses = tracker.expenses.find({"user_id": user_id})
        return render_template("expenses.html", expenses=expenses)
    except Exception as e:
        return f"Error loading expenses: {e}", 500

@app.route('/reports', methods=["GET", "POST"])
def show_reports():
    user_id = session.get("user_id")
    tracker = BudgetTracker(user_id=session.get("user_id"))
    if not user_id:
        return redirect(url_for("login"))  

    try:
        charts = tracker.generate_charts(user_id=user_id)

        return render_template(
            'reports.html',
            pie_chart=Markup(charts["pie_chart"]),
            line_chart=Markup(charts["line_chart"]),
            bar_chart=Markup(charts["bar_chart"])
        )
    except Exception as e:
        return f"Error generating reports: {e}", 500


@app.route('/settings', methods=['GET'])
def settings():
    return render_template('index.html')


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))



if __name__ == "__main__":
    app.run(debug=True, port=5000)
