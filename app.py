import pymongo
import ssl
import os
import urllib
from bson.objectid import ObjectId
from flask import Flask, render_template, request, redirect, url_for
from markupsafe import Markup
import datetime
import pandas as pd
import plotly.express as px
from flask_cors import CORS


''' 
BUGS
1. dark mode not working
2. deposit and withdraw action result to 404 DONE
3. total expense in index.html not being updated
'''


app = Flask(__name__)
CORS(app)


class BudgetTracker:
    def __init__(self, balance=1000, database_name="budget_tracker", collection_name="expenses", deposits_collection_name="deposits", withdrawals_collection_name="withdrawals"):
        self.__balance = balance
        self.expenses = []

        # MongoDB Connection
        username = urllib.parse.quote_plus(os.getenv("DB_USER", "fayyadrc"))
        password = urllib.parse.quote_plus(
            os.getenv("DB_PASSWORD", "fayyad@123"))
        connection_string = f"mongodb+srv://{username}:{
            password}@cluster0.6w52j.mongodb.net/?retryWrites=true&w=majority"

        try:
            self.client = pymongo.MongoClient(
                connection_string, serverSelectionTimeoutMS=5000, tlsAllowInvalidCertificates=True)
            self.db = self.client[database_name]
            self.expenses_collection = self.db[collection_name]
            self.deposits_collection = self.db[deposits_collection_name]
            self.withdrawals_collection = self.db[withdrawals_collection_name]
            self.load_data_mongodb()
        except pymongo.errors.PyMongoError as e:
            print(f"Error connecting to MongoDB: {e}")

    def get_balance(self):
        try:
            balance_data = self.db["balance"].find_one()
            if balance_data:
                self.__balance = balance_data.get("balance", self.__balance)
        except Exception as e:
            print(f"Error fetching balance from MongoDB: {e}")
        return self.__balance

    def deposit(self, amount, date):
        if amount > 0:
            self.__balance += amount
            data = {
                'Amount': amount,
                'Date': date.strftime("%d:%B:%Y"),
                'Action': 'deposit'
            }
            self.deposits_collection.insert_one(data)
            self.save_data_mongodb()
            return f"Deposited amount: {amount}, New Available Balance: {self.__balance}"
        else:
            return "Invalid deposit amount, please enter a positive number."

    def withdraw(self, amount, date):
        if self.__balance >= amount:
            self.__balance -= amount
            data = {
                'Amount': amount,
                'Date': date.strftime("%d:%B:%Y"),
                'Action': 'withdraw'
            }
            self.withdrawals_collection.insert_one(data)
            self.save_data_mongodb()
            return f"Withdrawn amount: {amount}, New Available Balance: {self.__balance}"
        else:
            return 'Insufficient funds'

    def add_expense(self, amount, title, category, date, action_type):
        if action_type == "transaction":
            if amount <= self.__balance:
                self.__balance -= amount
                formatted_date = date.strftime("%d:%B:%Y")
                expense = {
                    'Amount': amount,
                    'Title': title,
                    'Category': category,
                    'Date': formatted_date,
                    'Action': action_type
                }
                self.expenses_collection.insert_one(expense)
                self.save_data_mongodb()
                return f"Expense added: {expense}"
            else:
                return "Insufficient Balance"

    def save_data_mongodb(self):
        try:
            self.db["balance"].update_one(
                {}, {"$set": {"balance": self.__balance}}, upsert=True)
        except Exception as e:
            print(f"Error saving balance to MongoDB: {e}")

    def load_data_mongodb(self):
        try:
            balance_data = self.db["balance"].find_one()
            if balance_data:
                self.__balance = balance_data.get("balance", self.__balance)
            else:
                self.db["balance"].insert_one({"balance": self.__balance})
            self.expenses = list(self.expenses_collection.find())
            self.deposits = list(self.deposits_collection.find())
            self.withdrawals = list(self.withdrawals_collection.find())
        except Exception as e:
            print(f"Error loading data from MongoDB: {e}")

    def total_expenses(self):
        total = 0
        try:
            # Sum expenses from transactions
            expenses_cursor = self.expenses_collection.find()
            for expense in expenses_cursor:
                try:
                    total += float(expense.get("Amount", 0))
                except (ValueError, TypeError):
                    print(f"Invalid expense amount: {expense}")
            
            # Add withdrawals
            withdrawals_cursor = self.withdrawals_collection.find()
            for withdrawal in withdrawals_cursor:
                try:
                    total += float(withdrawal.get("Amount", 0))
                except (ValueError, TypeError):
                    print(f"Invalid withdrawal amount: {withdrawal}")
                    
        except Exception as e:
            print(f"Error calculating total expenses: {e}")
        
        return total

    def cash_inflow(self):
        total_inflow = 0
        try:
            for deposit in self.deposits:
                try:
                    total_inflow += float(deposit["Amount"])
                except (ValueError, KeyError, TypeError):
                    print(f"Skipping invalid deposit record: {deposit}")
        except Exception as e:
            print(f"Error calculating cash inflows: {e}")
        return total_inflow

    def cash_outflow(self):
        total_outflow = 0
        try:
            for withdrawal in self.withdrawals:
                try:
                    total_outflow += float(withdrawal["Amount"])
                except (ValueError, KeyError, TypeError):
                    print(f"Skipping invalid withdrawal record: {withdrawal}")
            total_outflow += self.total_expenses()  # Add total expenses to outflow
        except Exception as e:
            print(f"Error calculating cash outflows: {e}")
        return total_outflow

    def generate_charts(self):
        if not self.expenses:
            return {
                "pie_chart": px.pie(title="No Expenses Recorded").to_html(full_html=False),
                "line_chart": px.line(title="No Expenses Recorded").to_html(full_html=False),
                "bar_chart": px.bar(title="No Expenses Recorded").to_html(full_html=False),
            }

        expenses_df = pd.DataFrame(self.expenses)
        expenses_df['Amount'] = pd.to_numeric(
            expenses_df['Amount'], errors='coerce')
        expenses_df['Date'] = pd.to_datetime(
            expenses_df['Date'], format="%d:%B:%Y", errors='coerce')

        # Pie Chart
        category_counts = expenses_df.groupby(
            "Category")["Amount"].sum().reset_index()
        pie_chart = px.pie(category_counts, values='Amount',
                           names='Category', title="Expenses by Category")

        # Line Chart
        expenses_df['YearMonth'] = expenses_df['Date'].dt.to_period(
            'M').astype(str)
        monthly_trends = expenses_df.groupby(
            "YearMonth")["Amount"].sum().reset_index()
        line_chart = px.line(monthly_trends, x="YearMonth",
                             y="Amount", title="Monthly Expense Trends", markers=True)

        # Bar Chart
        bar_chart = px.bar(category_counts, x='Category', y='Amount',
                           title="Expenses by Category", color="Category")

        return {
            "pie_chart": pie_chart.to_html(full_html=False),
            "line_chart": line_chart.to_html(full_html=False),
            "bar_chart": bar_chart.to_html(full_html=False),
        }


tracker = BudgetTracker()


@app.route("/", methods=["GET", "POST"])
def index():
    try:
        if request.method == "POST":
            action_type = request.form["action_type"]
            amount = float(request.form["amount"])
            date_str = request.form["date"]
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")

            if action_type == "transaction":
                title = request.form.get("title")
                category = request.form.get("category")
                if not title or not category or amount <= 0:
                    return "Invalid input for transaction."
                tracker.add_expense(amount, title, category,
                                    date_obj, action_type)
            elif action_type == "deposit":
                tracker.deposit(amount, date_obj)
            elif action_type == "withdraw":
                tracker.withdraw(amount, date_obj)

            return redirect(url_for("index"))

        charts = tracker.generate_charts()
        return render_template(
            "index.html",
            balance=tracker.get_balance(),
            total_expenses=tracker.total_expenses(),
            expenses=tracker.expenses,
            pie_chart=Markup(charts["pie_chart"]),
            line_chart=Markup(charts["line_chart"]),
            bar_chart=Markup(charts["bar_chart"]),
        )
    except Exception as e:
        return f"An error occurred: {e}", 500


@app.route("/expenses", methods=["GET", "POST"])
def show_expenses():
    try:
        return render_template("expenses.html", expenses=tracker.expenses)
    except TemplateNotFound:
        return "Expenses template not found", 404


@app.route('/reports', methods=["GET", "POST"])
def show_reports():
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


@app.route('/logout', methods=['GET'])
def logout():
    return redirect(url_for('index'))


@app.route('/settings', methods=['GET'])
def settings():
    # Replace with your settings page logic
    return render_template('settings.html')


if __name__ == "__main__":
    app.run(debug=True)
