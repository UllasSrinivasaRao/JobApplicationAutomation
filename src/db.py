# db.py
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv() 

def get_db():
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI not found in environment")

    client = MongoClient(uri)
    return client["applications_data"]
