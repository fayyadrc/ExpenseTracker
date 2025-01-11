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
from dateutil import parser
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
CORS(app)
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")


class BudgetTracker:
    def __init__(self, user_id=None, username=None, database_name="budget_tracker", user_collection_name="users",
                 collection_name="expenses", deposits_collection_name="deposits",
                 withdrawals_collection_name="withdrawals", transactions_collection_name="transactions", categories_collection_name="categories"):

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

        #mongoDB connection
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
            self.categories_collection = self.db[categories_collection_name]
            self.load_user_data()
            self.init_categories()  
        except pymongo.errors.PyMongoError as e:
            print(f"Error connecting to MongoDB: {e}")

    def init_categories(self):
        """Initialize predefined categories in the database."""
        predefined_categories = [
            {"name": "Food", "created_by": "admin"},
            {"name": "Transportation", "created_by": "admin"},
            {"name": "Entertainment", "created_by": "admin"},
            {"name": "Shopping", "created_by": "admin"},
            {"name": "Gifts", "created_by": "admin"},
            {"name": "Utilities", "created_by": "admin"},
        ]

        for category in predefined_categories:
            self.categories_collection.update_one(
                {"name": category["name"], "created_by": "admin"},
                {"$setOnInsert": category},
                upsert=True
            )

    def add_category(self, category_name, user_id):
        """Add a new category for the specific user."""
        if not category_name:
            raise ValueError("Category name cannot be empty.")
        existing_category = self.categories_collection.find_one(
            {"name": category_name, "user_id": user_id}
        )
        if not existing_category:
            self.categories_collection.insert_one(
                {"name": category_name, "created_by": "user", "user_id": user_id}
            )
            return f"Category '{category_name}' added successfully."
        return f"Category '{category_name}' already exists."

    def get_categories(self, user_id):
        """Retrieve all categories for the specified user."""
        categories = self.categories_collection.find(
            {"$or": [{"created_by": "admin"}, {"user_id": user_id}]},
            {"_id": 0, "name": 1}
        )
        return [category["name"] for category in categories]

    def remove_category(self, category_name, user_id):
        """Remove a user-defined category from the database."""
        category = self.categories_collection.find_one(
            {"name": category_name, "created_by": user_id}
        )
        if category:
            self.categories_collection.delete_one(
                {"name": category_name, "created_by": user_id}
            )
            return f"Category '{category_name}' removed successfully."
        return f"Category '{category_name}' cannot be removed (predefined or does not exist)."


    def format_date(self, date_str):
        try:
            if isinstance(date_str, datetime):
                return date_str.strftime('%Y-%m-%d')

            date_obj = parser.parse(date_str)
            return date_obj.strftime('%Y-%m-%d')

        except Exception as e:
            print(f"Error formatting date: {e}")
            return None

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
            self.total_balance = self.__balance
            self.current_balance = self.__balance - \
                total_expenses

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
            expenses = list(self.expenses_collection.find({"user_id": self.user_id}))
            if not expenses:
                print("No expenses found in the database.")
                return {
                    "pie_chart": px.pie(title="No Expenses Recorded").to_html(full_html=False),
                    "line_chart": px.line(title="No Expenses Recorded").to_html(full_html=False),
                    "bar_chart": px.bar(title="No Expenses Recorded").to_html(full_html=False)
                }

            # Create DataFrame
            expenses_df = pd.DataFrame(expenses)
            expenses_df['Amount'] = pd.to_numeric(expenses_df['amount'], errors='coerce')
            expenses_df['Date'] = pd.to_datetime(expenses_df['date'], errors='coerce')

            # Drop invalid data
            expenses_df = expenses_df.dropna(subset=['Amount', 'Date'])
            if expenses_df.empty:
                print("No valid expenses data after cleaning.")
                return {
                    "pie_chart": px.pie(title="No Valid Data").to_html(full_html=False),
                    "line_chart": px.line(title="No Valid Data").to_html(full_html=False),
                    "bar_chart": px.bar(title="No Valid Data").to_html(full_html=False)
                }

            # Pie and bar charts
            category_counts = expenses_df.groupby("category")["Amount"].sum().reset_index()
            if category_counts.empty:
                print("No data available for category charts.")
                return {
                    "pie_chart": px.pie(title="No Data Available").to_html(full_html=False),
                    "line_chart": px.line(title="No Data Available").to_html(full_html=False),
                    "bar_chart": px.bar(title="No Data Available").to_html(full_html=False)
                }

            pie_chart = px.pie(category_counts, values='Amount', names='category', title="Expenses by Category")
            bar_chart = px.bar(category_counts, x='category', y='Amount', title="Expenses by Category", color="category")

            # Line chart for daily trends
            expenses_df['YearMonthDay'] = expenses_df['Date'].dt.strftime('%y%m%d')
            daily_trends = expenses_df.groupby("YearMonthDay")["Amount"].sum().reset_index()
            daily_trends = daily_trends.sort_values('YearMonthDay')

            if daily_trends.empty:
                print("No data available for daily trends.")
                return {
                    "pie_chart": pie_chart.to_html(full_html=False),
                    "line_chart": px.line(title="No Data Available").to_html(full_html=False),
                    "bar_chart": bar_chart.to_html(full_html=False)
                }

            line_chart = px.line(
                daily_trends,
                x="YearMonthDay",
                y="Amount",
                title="Daily Expense Trends (YYMMDD)",
                markers=True
            )

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
    if session.get("logged_in"):
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
    if "user_id" not in session:
        print("No user_id in session")
        if request.headers.get("Accept") == "application/json":
            return jsonify({"error": "Please login first"})
        return redirect(url_for("login"))

    tracker = BudgetTracker(
        user_id=session["user_id"],
        username=session.get("username")
    )
    user_id = session.get("user_id")
    print(user_id)
    try:
        if request.method == "POST":
            print("Received form data:", request.form)

            action_type = request.form.get("action_type")
            amount_str = request.form.get("amount", "").strip()
            date_str = request.form.get("date", "").strip()
            custom_category = request.form.get("custom_category", "").strip()

            if not all([action_type, amount_str, date_str]):
                error_msg = "All fields (action type, amount, and date) are required."
                if request.headers.get("Accept") == "application/json":
                    return jsonify({"error": error_msg})
                flash(error_msg)
                return redirect(url_for("index"))

            try:
                amount = float(amount_str)
            except ValueError:
                error_msg = "Please enter a valid number for amount."
                if request.headers.get("Accept") == "application/json":
                    return jsonify({"error": error_msg})
                flash(error_msg)
                return redirect(url_for("index"))

            try:
                if action_type == "transaction":
                    title = request.form.get("title", "").strip()
                    category = request.form.get("category", "").strip()

                    if category == "custom" and custom_category:
                        # Add custom category and use it
                        tracker.add_category(custom_category, user_id=user_id)  # Pass the actual user_id
                        category = custom_category


                    if not title or not category:
                        error_msg = "Title and category are required for transactions."
                        if request.headers.get("Accept") == "application/json":
                            return jsonify({"error": error_msg})
                        flash(error_msg)
                        return redirect(url_for("index"))

                    result = tracker.add_expense(amount, title, category, date_str)
                    print(f"Transaction result: {result}")

                elif action_type == "deposit":
                    result = tracker.deposit(amount, date_str)
                    print(f"Deposit result: {result}")

                elif action_type == "withdraw":
                    result = tracker.withdraw(amount, date_str)
                    print(f"Withdrawal result: {result}")

                else:
                    error_msg = "Invalid action type."
                    if request.headers.get("Accept") == "application/json":
                        return jsonify({"error": error_msg})
                    flash(error_msg)
                    return redirect(url_for("index"))

                if isinstance(result, str) and "Error" in result:
                    if request.headers.get("Accept") == "application/json":
                        return jsonify({"error": result})
                    flash(result)
                else:
                    success_msg = f"{action_type.capitalize()} of AED {amount:.2f} processed successfully!"
                    if request.headers.get("Accept") == "application/json":
                        return jsonify({"message": success_msg})
                    flash(success_msg)

                return redirect(url_for("index"))

            except Exception as e:
                error_msg = f"Error processing {action_type}: {str(e)}"
                print(f"Processing error: {error_msg}")
                if request.headers.get("Accept") == "application/json":
                    return jsonify({"error": error_msg})
                flash(error_msg)
                return redirect(url_for("index"))

        # Handle GET request
        try:
            expenses = list(tracker.expenses_collection.find(
                {"user_id": session["user_id"]}
            ).sort("date", -1))

            tracker.update_balances()
            charts = tracker.generate_charts()

            # Fetch categories
            categories = tracker.get_categories(user_id)

            template_data = {
                "balance": tracker.get_balance(),
                "total_balance": tracker.total_balance,
                "current_balance": tracker.current_balance,
                "total_expenses": tracker.total_expenses(),
                "username": session.get("username"),
                "expenses": expenses,
                "categories": categories,  # Pass categories to template
                "pie_chart": Markup(charts["pie_chart"]),
                "line_chart": Markup(charts["line_chart"]),
                "bar_chart": Markup(charts["bar_chart"]),
            }

            if request.headers.get("Accept") == "application/json":
                return jsonify(template_data)

            return render_template("index.html", **template_data)

        except Exception as e:
            error_msg = f"Error loading dashboard data: {str(e)}"
            print(f"Template error: {error_msg}")
            if request.headers.get("Accept") == "application/json":
                return jsonify({"error": error_msg})
            flash(error_msg)
            return redirect(url_for("login"))

    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        print(f"Unexpected error: {error_msg}")
        if request.headers.get("Accept") == "application/json":
            return jsonify({"error": error_msg})
        flash(error_msg)
        return redirect(url_for("index"))


@app.route("/expenses", methods=["GET"])
def show_expenses():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    tracker = BudgetTracker(user_id=user_id)

    try:
        selected_category = request.args.get("category", "").strip()
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()

        query = {"user_id": user_id}
        if selected_category:
            query["category"] = selected_category

        # Handle date filtering
        date_filter = {}
        date_format = "%d %B %Y"  # Your stored date format
        # In show_expenses route
        if start_date:
            date_filter["$gte"] = parser.parse(start_date).isoformat() + 'Z'
        if end_date:
            date_filter["$lte"] = parser.parse(end_date).isoformat() + 'Z'
        if date_filter:
            query["date"] = date_filter

        # Fetch filtered expenses
        expenses_cursor = tracker.expenses_collection.find(query)
        expenses = list(expenses_cursor)

        # Fetch unique categories for the dropdown
        unique_categories_cursor = tracker.expenses_collection.distinct(
            "category", {"user_id": user_id})
        unique_categories = list(unique_categories_cursor)

        return render_template(
            "expenses.html",
            expenses=expenses,
            unique_categories=unique_categories,
        )
    except Exception as e:
        return f"Error loading expenses: {e}", 500


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user_id = session.get("user_id")
    tracker = BudgetTracker(user_id=session.get("user_id"))
    if request.method == 'POST':
        action = request.form.get('action')
        category_name = request.form.get('newCategory') or request.form.get('category')

        if action == 'add_category':
            flash(tracker.add_category(category_name, user_id), "success")
        elif action == 'remove_category':
            flash(tracker.remove_category(category_name, user_id), "danger")

        return redirect(url_for('settings'))

    # Retrieve categories for the current user
    categories = tracker.get_categories(user_id)

    return render_template('settings.html', categories=categories)



#Pass username and expense list for right sidebar in all templates
@app.context_processor
def global_data():
    if not session.get("user_id"):
        return {"username": None, "expenses": []}
    
    try:
        tracker = BudgetTracker(
            user_id=session.get("user_id"),
            username=session.get("username")
        )
        username = session.get("username")
        expenses = list(tracker.expenses_collection.find(
                    {"user_id": session.get("user_id")}
                ).sort("date", -1))
        return {"username": username, "expenses": expenses}
    except Exception as e:
        print(f"Error in context processor: {e}")
        return {"username": None, "expenses": []}

@app.route('/reports', methods=["GET", "POST"])
def show_reports():
    user_id = session.get("user_id")
    tracker = BudgetTracker(user_id=session.get("user_id"))
    if not user_id:
        return redirect(url_for("login"))

    try:
        charts = tracker.generate_charts()

        return render_template(
            'reports.html',
            pie_chart=Markup(charts["pie_chart"]),
            line_chart=Markup(charts["line_chart"]),
            bar_chart=Markup(charts["bar_chart"])
        )
    except Exception as e:
        return f"Error generating reports: {e}", 500

@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
