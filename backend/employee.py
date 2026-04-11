'''
employee.py

    FLOW - Enterprise Restaurant Management System
    CSC 570 Sp 26'
    Created by Day Ekoi - March 23 - April 10, 2026

 This file handles all employee related database queries for the FLOW system.
 It provides functions for retrieving employee profiles, managing employee
 records, and looking up staff and manager information. It is used primarily
 by the manager interface for workforce management and by the employee
 interface for profile and schedule access.

Functions:
   - get_employee_profile()       : retrieves full profile for an employee
   - get_all_employees()          : retrieves all employees for a branch
   - get_employee_by_id()         : retrieves a single employee by person_id
   - update_employee_status()     : updates the employment status of an employee
   - get_all_staff()              : retrieves all staff members for a branch
   - get_all_managers()           : retrieves all managers for a branch
   - add_employee()               : adds a new employee record
   - update_employee_branch()     : transfers an employee to a different branch

   !!!! Important Notes to self: refer to auth.py notes !!!!!
   '''

from config.db_config import get_connection, close_connection


def get_employee_profile(person_id):
    """
    Retrieves the full profile for an employee including
    person info, employment details, and role specific data.
    """
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT p.person_id, p.first_name, p.last_name, p.dob,
                   p.phone, p.address, p.email,
                   e.branch_id, e.job_title, e.hire_date, e.employment_status,
                   b.branch_name,
                   s.hourly_rate, s.role as staff_role,
                   m.salary
            FROM person p
            JOIN employee e ON p.person_id = e.person_id
            JOIN branch b ON e.branch_id = b.branch_id
            LEFT JOIN staff s ON p.person_id = s.person_id
            LEFT JOIN manager m ON p.person_id = m.person_id
            WHERE p.person_id = %s
        """, (person_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving employee profile: {e}")
        return None

    finally:
        close_connection(conn, cursor)


def get_all_employees(branch_id):
    """Retrieves all employees for a specific branch."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT p.person_id, p.first_name, p.last_name,
                   p.phone, p.email,
                   e.job_title, e.hire_date, e.employment_status,
                   s.role as staff_role, s.hourly_rate,
                   m.salary
            FROM person p
            JOIN employee e ON p.person_id = e.person_id
            LEFT JOIN staff s ON p.person_id = s.person_id
            LEFT JOIN manager m ON p.person_id = m.person_id
            WHERE e.branch_id = %s
            ORDER BY p.last_name ASC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving employees: {e}")
        return []

    finally:
        close_connection(conn, cursor)


def get_employee_by_id(person_id):
    """Retrieves a single employee record by person_id."""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT p.person_id, p.first_name, p.last_name,
                   p.phone, p.email,
                   e.branch_id, e.job_title, e.hire_date, e.employment_status,
                   b.branch_name
            FROM person p
            JOIN employee e ON p.person_id = e.person_id
            JOIN branch b ON e.branch_id = b.branch_id
            WHERE p.person_id = %s
        """, (person_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving employee: {e}")
        return None

    finally:
        close_connection(conn, cursor)


def update_employee_status(person_id, status):
    """Updates the employment status of an employee."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE employee
            SET employment_status = %s
            WHERE person_id = %s
        """, (status, person_id))

        if cursor.rowcount == 0:
            return False, "Employee not found."

        conn.commit()
        return True, f"Employment status updated to {status}."

    except Exception as e:
        conn.rollback()
        return False, f"Status update failed: {e}"

    finally:
        close_connection(conn, cursor)


def get_all_staff(branch_id):
    """Retrieves all staff members for a specific branch."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT p.person_id, p.first_name, p.last_name,
                   p.phone, p.email,
                   e.job_title, e.hire_date, e.employment_status,
                   s.hourly_rate, s.role as staff_role
            FROM person p
            JOIN employee e ON p.person_id = e.person_id
            JOIN staff s ON p.person_id = s.person_id
            WHERE e.branch_id = %s
            AND e.employment_status = 'ACTIVE'
            ORDER BY p.last_name ASC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving staff: {e}")
        return []

    finally:
        close_connection(conn, cursor)


def get_all_managers(branch_id):
    """Retrieves all managers for a specific branch."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT p.person_id, p.first_name, p.last_name,
                   p.phone, p.email,
                   e.job_title, e.hire_date, e.employment_status,
                   m.salary
            FROM person p
            JOIN employee e ON p.person_id = e.person_id
            JOIN manager m ON p.person_id = m.person_id
            WHERE e.branch_id = %s
            AND e.employment_status = 'ACTIVE'
            ORDER BY p.last_name ASC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving managers: {e}")
        return []

    finally:
        close_connection(conn, cursor)


def add_employee(person_id, branch_id, job_title, hire_date, hourly_rate=None, staff_role=None, salary=None):
    """
    Adds a new employee record linked to an existing person.
    Also creates the appropriate staff or manager subtype record
    depending on whether salary or hourly rate is provided.
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        # Insert into employee table
        cursor.execute("""
            INSERT INTO employee (person_id, branch_id, job_title, hire_date)
            VALUES (%s, %s, %s, %s)
        """, (person_id, branch_id, job_title, hire_date))

        # Insert into staff or manager subtype
        if salary is not None:
            cursor.execute("""
                INSERT INTO manager (person_id, salary)
                VALUES (%s, %s)
            """, (person_id, salary))
        elif hourly_rate is not None:
            cursor.execute("""
                INSERT INTO staff (person_id, hourly_rate, role)
                VALUES (%s, %s, %s)
            """, (person_id, hourly_rate, staff_role))

        conn.commit()
        return True, "Employee added successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Failed to add employee: {e}"

    finally:
        close_connection(conn, cursor)


def update_employee_branch(person_id, new_branch_id):
    """Transfers an employee to a different branch."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE employee
            SET branch_id = %s
            WHERE person_id = %s
        """, (new_branch_id, person_id))

        if cursor.rowcount == 0:
            return False, "Employee not found."

        conn.commit()
        return True, "Employee transferred successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Transfer failed: {e}"

    finally:
        close_connection(conn, cursor)