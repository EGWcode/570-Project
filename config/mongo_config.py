# mongo_config.py
#
#     FLOW - Enterprise Restaurant Management System
#     CSC 570 Sp 26'
#     Created by Day Ekoi - April 24, 2026
#
# Manages the MongoDB connection for the FLOW system.
# Collections:
#   - table_availability : real-time table occupancy status per branch
#   - order_events       : order lifecycle event log for analytics
#   - reviews            : mirrored review documents for full-text search
#
# Functions:
#   - get_mongo_db()        : returns the shared MongoDB database object
#   - set_table_status()    : upserts a table's occupancy status
#   - get_table_statuses()  : returns all table statuses for a branch
#   - log_order_event()     : appends an order lifecycle event
#   - get_order_events()    : retrieves all events for a specific order
#   - log_review()          : mirrors a review document for analytics

import os
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI     = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "flow_db")

_client = None


def get_mongo_db():
    """Returns the shared MongoDB database object, creating the client on first call."""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    return _client[MONGO_DB_NAME]


def set_table_status(branch_id, table_number, status):
    """Upserts a table availability document for the given branch and table."""
    try:
        get_mongo_db().table_availability.update_one(
            {"branch_id": branch_id, "table_number": table_number},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}},
            upsert=True
        )
        return True
    except Exception:
        return False


def get_table_statuses(branch_id):
    """Returns all table status documents for a branch."""
    try:
        return list(get_mongo_db().table_availability.find(
            {"branch_id": branch_id}, {"_id": 0}
        ))
    except Exception:
        return []


def log_order_event(order_id, branch_id, event_type, data=None):
    """Appends an order lifecycle event to the order_events collection."""
    try:
        get_mongo_db().order_events.insert_one({
            "order_id": order_id,
            "branch_id": branch_id,
            "event_type": event_type,
            "data": data or {},
            "timestamp": datetime.utcnow()
        })
        return True
    except Exception:
        return False


def get_order_events(order_id):
    """Returns all logged events for a specific order in chronological order."""
    try:
        return list(get_mongo_db().order_events.find(
            {"order_id": order_id}, {"_id": 0}
        ).sort("timestamp", 1))
    except Exception:
        return []


def log_review(person_id, branch_id, rating, comments):
    """Mirrors a customer review to MongoDB for full-text search and analytics."""
    try:
        get_mongo_db().reviews.insert_one({
            "person_id": person_id,
            "branch_id": branch_id,
            "rating": rating,
            "comments": comments,
            "created_at": datetime.utcnow()
        })
        return True
    except Exception:
        return False
