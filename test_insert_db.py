# test_insert.py
from src.db import get_db
from uuid import uuid4
from datetime import datetime

db = get_db()
applications = db["applications"]

doc = {
    "_id": str(uuid4()),
    "job_title": "Test JavaScript Developer",
    "job_description": "This is a test job description",
    "company_name":"adventure gmbh",
    "resume": {},
    "cover_letter": {},
    "created_at": datetime.utcnow()
}

applications.insert_one(doc)
print("Inserted!")
