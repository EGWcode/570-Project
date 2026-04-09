'''
 shifts.py

     FLOW - Enterprise Restaurant Management System
     CSC 570 Sp 26'
     Created by Day Ekoi - March 23 - April 10, 2026

 This file handles all shift and schedule related database queries for the
 FLOW system. It provides functions for creating, retrieving, and managing
 employee shift schedules across all branches. It is used by both the
 employee interface for viewing personal schedules and the manager interface
 for creating and managing shifts.

 Functions:
   - get_shifts_by_employee()   : retrieves all shifts for a specific employee
   - get_shifts_by_branch()     : retrieves all shifts for a branch on a date
   - get_shifts_by_date()       : retrieves all shifts scheduled for a specific date
   - create_shift()             : creates a new shift for an employee
   - update_shift()             : updates an existing shift record
   - delete_shift()             : removes a shift from the schedule
   - get_shift_by_id()          : retrieves a single shift by shift_id
   - get_upcoming_shifts()      : retrieves upcoming shifts for an employee
'''

from config.db_config import get_connection, close_connection

def get_shifts_by_employee(person_id):
    """Retrieves all shifts for a specific employee ordered by date."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT s.shift_id, s.shift_date, s.start_time,
                   s.end_time, s.role_assigned, b.branch_name
            FROM shift_schedule s
            JOIN branch b ON s.branch_id = b.branch_id
            WHERE s.person_id = %s
            ORDER BY s.shift_date ASC, s.start_time ASC
        """, (person_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving shifts by employee: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_shifts_by_branch(branch_id):
    """Retrieves all shifts for a branch ordered by date and start time."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT s.shift_id, s.shift_date, s.start_time,
                   s.end_time, s.role_assigned,
                   p.first_name, p.last_name, p.person_id
            FROM shift_schedule s
            JOIN person p ON s.person_id = p.person_id
            WHERE s.branch_id = %s
            ORDER BY s.shift_date ASC, s.start_time ASC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving shifts by branch: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_shifts_by_date(branch_id, date):
    """Retrieves all shifts for a branch on a specific date."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT s.shift_id, s.shift_date, s.start_time,
                   s.end_time, s.role_assigned,
                   p.first_name, p.last_name, p.person_id
            FROM shift_schedule s
            JOIN person p ON s.person_id = p.person_id
            WHERE s.branch_id = %s AND s.shift_date = %s
            ORDER BY s.start_time ASC
        """, (branch_id, date))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving shifts by date: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def create_shift(person_id, branch_id, shift_date, start_time, end_time, role_assigned):
    """Creates a new shift for an employee."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO shift_schedule (person_id, branch_id, shift_date,
                                        start_time, end_time, role_assigned)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (person_id, branch_id, shift_date, start_time, end_time, role_assigned))

        conn.commit()
        return True, "Shift created successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Shift creation failed: {e}"

    finally:
        close_connection(conn, cursor)

def update_shift(shift_id, shift_date=None, start_time=None, end_time=None, role_assigned=None):
    """Updates an existing shift record with any provided fields."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE shift_schedule
            SET shift_date = COALESCE(%s, shift_date),
                start_time = COALESCE(%s, start_time),
                end_time = COALESCE(%s, end_time),
                role_assigned = COALESCE(%s, role_assigned)
            WHERE shift_id = %s
        """, (shift_date, start_time, end_time, role_assigned, shift_id))

        if cursor.rowcount == 0:
            return False, "Shift not found."

        conn.commit()
        return True, "Shift updated successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Shift update failed: {e}"

    finally:
        close_connection(conn, cursor)

def delete_shift(shift_id):
    """Removes a shift from the schedule."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM shift_schedule
            WHERE shift_id = %s
        """, (shift_id,))

        if cursor.rowcount == 0:
            return False, "Shift not found."

        conn.commit()
        return True, "Shift deleted successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Shift deletion failed: {e}"

    finally:
        close_connection(conn, cursor)

def get_shift_by_id(shift_id):
    """Retrieves a single shift record by shift_id."""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT s.shift_id, s.shift_date, s.start_time,
                   s.end_time, s.role_assigned,
                   p.first_name, p.last_name, p.person_id,
                   b.branch_name, b.branch_id
            FROM shift_schedule s
            JOIN person p ON s.person_id = p.person_id
            JOIN branch b ON s.branch_id = b.branch_id
            WHERE s.shift_id = %s
        """, (shift_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving shift: {e}")
        return None

    finally:
        close_connection(conn, cursor)

def get_upcoming_shifts(person_id):
    """Retrieves all upcoming shifts for an employee from today onwards."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT s.shift_id, s.shift_date, s.start_time,
                   s.end_time, s.role_assigned, b.branch_name
            FROM shift_schedule s
            JOIN branch b ON s.branch_id = b.branch_id
            WHERE s.person_id = %s AND s.shift_date >= CURDATE()
            ORDER BY s.shift_date ASC, s.start_time ASC
        """, (person_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving upcoming shifts: {e}")
        return []

    finally:
        close_connection(conn, cursor)