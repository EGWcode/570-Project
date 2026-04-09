# db_config.py
#
#     FLOW - Enterprise Restaurant Management System
#     CSC 570 Sp 26'
#     Created by Day Ekoi
#     4/9/2026
#
# This file handles the database connection configuration for the FLOW system.
# It loads environment variables from the .env file to keep credentials secure
# and out of the codebase.
#
# This file provides:
#   - DB_CONFIG: a dictionary of connection parameters pulled from .env
#   - get_connection(): establishes and returns a MySQL database connection
#   - close_connection():  closes the cursor and connection when done
#
# All backend modules import get_connection() from this file to interact
# with the flow_db MySQL database.


import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "flow_db")
}

def get_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def close_connection(connection, cursor=None):
    if cursor:
        cursor.close()
    if connection and connection.is_connected():
        connection.close()