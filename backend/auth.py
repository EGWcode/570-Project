'''
 auth.py

     FLOW - Enterprise Restaurant Management System
     CSC 570 Sp 26'
     Created by Day Ekoi - March 23 - April 10, 2026

 This file:
  - handles all authentication logic for the FLOW system.
  - responsible for registering new users, logging in existing users
  - verifies credentials against the user_account table in the database.
  - manages the current user session in memory so the frontend can
  - checks who is logged in at any point.

 Functions:
  - register_user()    : creates a new person, links to a role, hashes password
  - login_user()       : verifies username and password, returns role on success
  - logout_user()      : clears the current user session
  - is_authenticated() : returns True if a user is currently logged in
  - get_current_user() : returns the currently logged in user's data
  - set_current_user() : sets the session after a successful login
  - hash_password()    : hashes a plain text password using bcrypt
  - verify_password()  : checks a plain text password against a stored hash
'''


import bcrypt
from config.db_config import get_connection, close_connection

# Session state which tracks the currently logged in user in memory
_current_user = None


def hash_password(plain_password):
    """Hashes a plain text password using bcrypt."""
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())

def verify_password(plain_password, hashed_password):
    """Checks a plain text password against a stored bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def set_current_user(user):
    """Sets the current user session after a successful login."""
    global _current_user
    _current_user = user

def logout_user():
    """Clears the current user session."""
    global _current_user
    _current_user = None

def is_authenticated():
    """Returns True if a user is currently logged in."""
    return _current_user is not None

def get_current_user():
    """Returns the currently logged in user's data."""
    return _current_user

def register_user(first_name, last_name, email, phone, username, password, role, dob=None, address=None, dietary_restrictions=None, branch_id=None, job_title=None, hire_date=None, salary=None, hourly_rate=None, staff_role=None):
    """
    Registers a new user in the system.
    Creates a person record, a role specific record (customer, staff, manager),
    and a user_account record with a hashed password.
    Returns True on success, False on failure.
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        # Step 1 - Insert into person table
        cursor.execute("""
            INSERT INTO person (first_name, last_name, dob, phone, address, email)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (first_name, last_name, dob, phone, address, email))
        person_id = cursor.lastrowid

        # Step 2 - Insert into role specific table
        if role == 'CUSTOMER':
            cursor.execute("""
                INSERT INTO customer (person_id, dietary_restrictions)
                VALUES (%s, %s)
            """, (person_id, dietary_restrictions))

        elif role == 'STAFF':
            cursor.execute("""
                INSERT INTO employee (person_id, branch_id, job_title, hire_date)
                VALUES (%s, %s, %s, %s)
            """, (person_id, branch_id, job_title, hire_date))
            cursor.execute("""
                INSERT INTO staff (person_id, hourly_rate, role)
                VALUES (%s, %s, %s)
            """, (person_id, hourly_rate, staff_role))

        elif role == 'MANAGER':
            cursor.execute("""
                INSERT INTO employee (person_id, branch_id, job_title, hire_date)
                VALUES (%s, %s, %s, %s)
            """, (person_id, branch_id, job_title, hire_date))
            cursor.execute("""
                INSERT INTO manager (person_id, salary)
                VALUES (%s, %s)
            """, (person_id, salary))

        elif role == 'ADMIN':
            cursor.execute("""
                INSERT INTO employee (person_id, branch_id, job_title, hire_date)
                VALUES (%s, %s, %s, %s)
            """, (person_id, branch_id, job_title, hire_date))

        # Step 3 - Hash password and insert into user_account
        hashed = hash_password(password)
        cursor.execute("""
            INSERT INTO user_account (person_id, username, password_hash, role)
            VALUES (%s, %s, %s, %s)
        """, (person_id, username, hashed.decode('utf-8'), role))

        conn.commit()
        return True, "Registration successful."

    except Exception as e:
        conn.rollback()
        return False, f"Registration failed: {e}"

    finally:
        close_connection(conn, cursor)

def login_user(username, password):
    """
    Verifies a username and password against the user_account table.
    Returns the user's role and person_id on success, None on failure.
    """
    conn = get_connection()
    if not conn:
        return None, "Database connection failed."

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT ua.account_id, ua.person_id, ua.username, ua.password_hash, ua.role,
                   p.first_name, p.last_name
            FROM user_account ua
            JOIN person p ON ua.person_id = p.person_id
            WHERE ua.username = %s
        """, (username,))

        user = cursor.fetchone()

        if not user:
            return None, "Username not found."

        if not verify_password(password, user['password_hash']):
            return None, "Incorrect password."

        set_current_user(user)
        return user, "Login successful."

    except Exception as e:
        return None, f"Login failed: {e}"

    finally:
        close_connection(conn, cursor)