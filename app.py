import pymongo
import os
import urllib
import uuid
import jsonify
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from markupsafe import Markup
import datetime
import pandas as pd
import plotly.express as px
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
CORS(app)
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")


class BudgetTracker:
    def __init__(self, user_id=None, username=None, database_name="budget_tracker", user_collection_name="users",
                 collection_name="expenses", deposits_collection_name="deposits",
                 withdrawals_collection_name="withdrawals", transactions_collection_name="transactions"):

        self.__balance = 0
        self.total_balance = 0
        self.current_balance = 0
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

    def format_date(self, date_str):
        """
        Format date to "2 January 2025" format
        """
        try:
            # If it's already a datetime object, just format it
            if isinstance(date_str, datetime):
                return date_str.strftime("%d %B %Y")

            # Try parsing with multiple formats
            formats_to_try = [
                "%d %B %Y",      # "1 January 2025"
                "%Y-%m-%d",      # "2025-01-01"
                "%B %d, %Y",     # "January 1, 2025"
                "%d-%m-%Y",      # "01-01-2025"
                "%m/%d/%Y"       # "01/01/2025"
            ]

            for date_format in formats_to_try:
                try:
                    date_obj = datetime.strptime(date_str, date_format)
                    return date_obj.strftime("%d %B %Y")
                except ValueError:
                    continue

            # If none of the explicit formats work, try dateutil parser as fallback
            from dateutil import parser
            date_obj = parser.parse(date_str)
            return date_obj.strftime("%d %B %Y")

        except Exception as e:
            print(f"Error formatting date: {e}")
            return None

            """
            Enhanced date formatting to handle multiple input formats including '1 January 2025'
            """
            try:
                formats_to_try = [
                    "%d %B %Y",      # "1 January 2025"
                    "%Y-%m-%d",      # "2025-01-01"
                    "%B %d, %Y",     # "January 1, 2025"
                    "%d-%m-%Y",      # "01-01-2025"
                    "%m/%d/%Y"       # "01/01/2025"
                ]

                # If it's already a datetime object, just format it
                if isinstance(date_str, datetime):
                    return date_str.strftime("%d %B %Y")

                # Try each format until one works
                for date_format in formats_to_try:
                    try:
                        date_obj = datetime.strptime(date_str, date_format)
                        return date_obj.strftime("%d %B %Y")
                    except ValueError:
                        continue

                # If none of the explicit formats work, try dateutil parser
                from dateutil import parser
                date_obj = parser.parse(date_str)
                return date_obj.strftime("%d %B %Y")

            except Exception as e:
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
                self.total_balance = user_data.get("total_balance", 0)
                self.current_balance = self.__balance
        except Exception as e:
            print(f"Error loading user data: {e}")

    def create_user(self, user_data):
        try:
            if not user_data.get("user_id"):
                user_data["user_id"] = str(uuid.uuid4())

            # Initialize all balance fields
            user_data.setdefault("balance", 0)
            user_data.setdefault("total_balance", 0)
            user_data.setdefault("current_balance", 0)
            user_data.setdefault("total_expenses", 0)

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

    def update_balances(self):
        try:
            total_expenses = self.total_expenses()
            self.total_balance = self.__balance  # This is the running total
            self.current_balance = self.__balance - \
                total_expenses  # This is balance minus expenses

            # Update the user document with new balances
            self.users_collection.update_one(
                {"user_id": self.user_id},
                {
                    "$set": {
                        "balance": self.__balance,
                        "total_balance": self.total_balance,
                        "current_balance": self.current_balance,
                        "total_expenses": total_expenses
                    }
                }
            )
        except Exception as e:
            print(f"Error updating balances: {e}")

    def deposit(self, amount, date):
        try:
            if amount <= 0:
                return "Invalid deposit amount. Please enter a positive value."

            formatted_date = self.format_date(date)
            if formatted_date == "Invalid date":
                return "Invalid date format"

            self.__balance += amount
            transaction = {
                "user_id": self.user_id,
                "amount": amount,
                "date": formatted_date,
                "action": "deposit"
            }
            self.transactions_collection.insert_one(transaction)
            self.update_balances()
            return f"Deposited: {amount}, New Balance: {self.__balance}"

        except Exception as e:
            print(f"Error processing deposit: {e}")
            return "Error processing deposit"

    def withdraw(self, amount, date):
        try:
            if amount <= 0:
                return "Invalid withdrawal amount. Please enter a positive value."
            if amount > self.__balance:
                return "Insufficient funds."

            formatted_date = self.format_date(date)
            if formatted_date == "Invalid date":
                return "Invalid date format"

            self.__balance -= amount
            transaction = {
                "user_id": self.user_id,
                "amount": amount,
                "date": formatted_date,
                "action": "withdraw"
            }
            self.transactions_collection.insert_one(transaction)
            self.update_balances()
            return f"Withdrawn: {amount}, New Balance: {self.__balance}"

        except Exception as e:
            print(f"Error processing withdrawal: {e}")
            return "Error processing withdrawal"

    def add_expense(self, amount, title, category, date):
        """
        Add an expense transaction with enhanced validation and error handling
        """
        try:
            if amount <= 0:
                return "Invalid expense amount. Please enter a positive value."

            if amount > self.__balance:
                return "Insufficient funds for this expense."

            formatted_date = self.format_date(date)
            if formatted_date == "Invalid date":
                return "Invalid date format"

            expense = {
                "user_id": self.user_id,
                "amount": amount,
                "title": title,
                "category": category,
                "date": formatted_date,
                "type": "expense"
            }

            self.expenses_collection.insert_one(expense)
            self.__balance -= amount

            # Update the users collection with the new balance
            self.users_collection.update_one(
                {"user_id": self.user_id},
                {"$inc": {"balance": -amount}}
            )

            self.update_balances()
            return True

        except Exception as e:
            print(f"Error adding expense: {e}")
            return f"Error adding expense: {str(e)}"

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
            expenses_df['Date'] = pd.to_datetime(
                expenses_df['date'], format="%d %B %Y", errors='coerce')
            expenses_df['Formatted Date'] = expenses_df['Date'].dt.strftime(
                "%d %B %Y")

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
    # Add this line for debugging
    print(f"Session during default route: {session}")
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
                "total_balance": 0,
                "current_balance": 0,
                "total_expenses": 0
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

        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("login"))

        try:

            tracker = BudgetTracker(username=username)

            user = tracker.users_collection.find_one({"username": username})

            if user and check_password_hash(user.get("hashed_password", ""), password):
                print("Login successful, setting session variables.")
                session["logged_in"] = True
                session["username"] = username
                session["user_id"] = user["user_id"]
                flash("Login successful!", "success")
                print(f"Session after login: {session}")
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
    # Check authentication
    if "user_id" not in session:
        print("No user_id in session")
        if request.headers.get('Accept') == 'application/json':
            return jsonify({"error": "Please login first"})
        return redirect(url_for("login"))

    # Initialize budget tracker
    tracker = BudgetTracker(
        user_id=session["user_id"],
        username=session.get("username")
    )

    try:
        if request.method == "POST":
            print("Received form data:", request.form)

            # Get basic form data
            action_type = request.form.get("action_type")
            amount_str = request.form.get("amount", "").strip()
            date_str = request.form.get("date", "").strip()

            # Validate required fields
            if not all([action_type, amount_str, date_str]):
                error_msg = "All fields (action type, amount, and date) are required."
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({"error": error_msg})
                flash(error_msg)
                return redirect(url_for("index"))

            # Parse amount and date
            try:
                amount = float(amount_str)
                # Date will be handled by the tracker's format_date method
            except ValueError as e:
                error_msg = "Please enter a valid number for amount"
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({"error": error_msg})
                flash(error_msg)
                return redirect(url_for("index"))

            # Process different action types
            try:
                if action_type == "transaction":
                    title = request.form.get("title", "").strip()
                    category = request.form.get("category", "").strip()

                    if not title or not category:
                        error_msg = "Title and category are required for transactions."
                        if request.headers.get('Accept') == 'application/json':
                            return jsonify({"error": error_msg})
                        flash(error_msg)
                        return redirect(url_for("index"))

                    result = tracker.add_expense(
                        amount, title, category, date_str)
                    print(f"Transaction result: {result}")
                elif action_type == "deposit":
                    result = tracker.deposit(amount, date_str)
                    print(f"Deposit result: {result}")
                elif action_type == "withdraw":
                    result = tracker.withdraw(amount, date_str)
                    print(f"Withdrawal result: {result}")
                else:
                    error_msg = "Invalid action type"
                    if request.headers.get('Accept') == 'application/json':
                        return jsonify({"error": error_msg})
                    flash(error_msg)
                    return redirect(url_for("index"))

                # Handle operation result
                if isinstance(result, str) and any(x in result for x in ["Error", "Invalid", "Insufficient"]):
                    if request.headers.get('Accept') == 'application/json':
                        return jsonify({"error": result})
                    flash(result)
                else:
                    success_msg = (f"Expense of ${amount:.2f} added successfully!"
                                   if action_type == "transaction"
                                   else f"{action_type.capitalize()} of ${amount:.2f} processed successfully!")
                    if request.headers.get('Accept') == 'application/json':
                        return jsonify({"message": success_msg})
                    flash(success_msg)

                return redirect(url_for("index"))

            except Exception as e:
                error_msg = f"Error processing {action_type}: {str(e)}"
                print(f"Processing error: {error_msg}")
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({"error": error_msg})
                flash(error_msg)
                return redirect(url_for("index"))

        # Handle GET request
        try:
            # Fetch expenses sorted by date
            expenses = list(tracker.expenses_collection.find(
                {"user_id": session["user_id"]}
            ).sort("date", -1))

            # Update balances and generate charts
            tracker.update_balances()
            charts = tracker.generate_charts()

            # Prepare template data
            template_data = {
                "balance": tracker.get_balance(),
                "total_balance": tracker.total_balance,
                "current_balance": tracker.current_balance,
                "total_expenses": tracker.total_expenses(),
                "username": session.get("username"),
                "expenses": expenses,
                "pie_chart": Markup(charts["pie_chart"]),
                "line_chart": Markup(charts["line_chart"]),
                "bar_chart": Markup(charts["bar_chart"]),
            }

            # Return JSON if requested
            if request.headers.get('Accept') == 'application/json':
                return jsonify(template_data)

            return render_template("index.html", **template_data)

        except Exception as e:
            error_msg = "Error loading dashboard data"
            print(f"Template error: {str(e)}")
            if request.headers.get('Accept') == 'application/json':
                return jsonify({"error": error_msg})
            flash(error_msg)
            return redirect(url_for("login"))

    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        print(f"Unexpected error: {error_msg}")
        if request.headers.get('Accept') == 'application/json':
            return jsonify({"error": error_msg})
        flash(error_msg)
        return redirect(url_for("index"))


@app.route("/expenses", methods=["GET", "POST"])
def show_expenses():
    user_id = session.get("user_id")
    tracker = BudgetTracker(user_id=session.get("user_id"))

    if not user_id:
        return redirect(url_for("login"))
    try:
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
