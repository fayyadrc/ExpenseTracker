from pymongo import MongoClient
import os
import urllib
from dotenv import load_dotenv

load_dotenv()

username = urllib.parse.quote_plus(os.getenv("DB_USER"))
password = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
connection_string = f"mongodb+srv://{username}:{password}@cluster0.6w52j.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"


client = MongoClient(connection_string)
db = client["budget_tracker"]

# Drop all collections to delete existing data
collections = ["expenses", "deposits", "withdrawals", "balance", "users"]
for collection in collections:
    db[collection].drop()

print("All data cleared.")
