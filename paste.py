from pymongo import MongoClient
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

username = quote_plus(os.getenv("DB_USER", ""))
password = quote_plus(os.getenv("DB_PASSWORD", ""))
connection_string = f"mongodb+srv://{username}:{password}@cluster0.mongodb.net/?retryWrites=true&w=majority"


load_dotenv()

username = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
connection_string = f"mongodb+srv://{username}:{password}@cluster0.mongodb.net/?retryWrites=true&w=majority"

try:
    client = MongoClient(connection_string)
    db = client["budget_tracker"]
    users_collection = db["users"]

    # Test query
    username_to_test = "test_username"
    user = users_collection.find_one({"username": username_to_test})
    print("User found:", user)
except Exception as e:
    print(f"MongoDB error: {e}")
