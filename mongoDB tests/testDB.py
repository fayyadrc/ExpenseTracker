import pymongo
import os
import urllib
from pymongo import MongoClient
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, session
from markupsafe import Markup
import datetime
import pandas as pd
import plotly.express as px
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash


#test connection
username_env = urllib.parse.quote_plus(os.getenv("DB_USER", "default_user"))
password_env = urllib.parse.quote_plus(os.getenv("DB_PASSWORD", "default_password"))
connection_string = f"mongodb+srv://{username_env}:{password_env}@cluster0.mongodb.net/?retryWrites=true&w=majority"

try:
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    db = client["budget_tracker"]
    print("Connected to MongoDB successfully.")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")

#update collections and add to db
