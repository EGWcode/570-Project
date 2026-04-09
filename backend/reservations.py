'''
 reservations.py

     FLOW - Enterprise Restaurant Management System
     CSC 570 Sp 26'
     Created by Day Ekoi - March 23 - April 10, 2026

 This file handles all reservation related database queries for the FLOW system.
 It provides functions for creating, updating, and managing reservations
 across all branches. It is used by both the customer interface for making
 reservations and the manager/staff interface for managing them.

 Functions:
   - get_all_reservations()        : retrieves all reservations for a branch
   - get_reservation_by_id()       : retrieves a single reservation by id
   - get_reservations_by_date()    : retrieves all reservations for a branch on a date
   - create_reservation()          : creates a new reservation
   - update_reservation_status()   : updates the status of a reservation
   - cancel_reservation()          : cancels a reservation
   - check_in_party()              : checks in a party and creates a party record
   - check_out_party()             : checks out a party and closes the party record
   - get_active_parties()          : retrieves all currently seated parties for a branch
   - get_available_tables()        : retrieves tables not currently occupied at a branch
'''

from config.db_config import get_connection, close_connection


def get_all_reservations(branch_id):
    """Retrieves all reservations for a branch ordered by datetime."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT r.reservation_id, r.reservation_datetime, r.party_size,
                   r.status, p.first_name, p.last_name, p.phone, p.email
            FROM reservation r
            JOIN person p ON r.person_id = p.person_id
            WHERE r.branch_id = %s
            ORDER BY r.reservation_datetime ASC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving reservations: {e}")
        return []

    finally:
        close_connection(conn, cursor)


def get_reservation_by_id(reservation_id):
    """Retrieves a single reservation by reservation_id."""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT r.reservation_id, r.reservation_datetime, r.party_size,
                   r.status, r.branch_id, r.person_id,
                   p.first_name, p.last_name, p.phone, p.email,
                   b.branch_name
            FROM reservation r
            JOIN person p ON r.person_id = p.person_id
            JOIN branch b ON r.branch_id = b.branch_id
            WHERE r.reservation_id = %s
        """, (reservation_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving reservation: {e}")
        return None

    finally:
        close_connection(conn, cursor)


def get_reservations_by_date(branch_id, date):
    """Retrieves all reservations for a branch on a specific date."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT r.reservation_id, r.reservation_datetime, r.party_size,
                   r.status, p.first_name, p.last_name, p.phone
            FROM reservation r
            JOIN person p ON r.person_id = p.person_id
            WHERE r.branch_id = %s AND DATE(r.reservation_datetime) = %s
            ORDER BY r.reservation_datetime ASC
        """, (branch_id, date))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving reservations by date: {e}")
        return []

    finally:
        close_connection(conn, cursor)


def create_reservation(person_id, branch_id, reservation_datetime, party_size):
    """Creates a new reservation with PENDING status."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO reservation (person_id, branch_id, reservation_datetime, party_size, status)
            VALUES (%s, %s, %s, %s, 'PENDING')
        """, (person_id, branch_id, reservation_datetime, party_size))

        conn.commit()
        return True, "Reservation created successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Reservation creation failed: {e}"

    finally:
        close_connection(conn, cursor)


def update_reservation_status(reservation_id, status):
    """Updates the status of a reservation."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE reservation
            SET status = %s
            WHERE reservation_id = %s
        """, (status, reservation_id))

        if cursor.rowcount == 0:
            return False, "Reservation not found."

        conn.commit()
        return True, f"Reservation status updated to {status}."

    except Exception as e:
        conn.rollback()
        return False, f"Status update failed: {e}"

    finally:
        close_connection(conn, cursor)


def cancel_reservation(reservation_id):
    """Cancels a reservation if it is still pending or confirmed."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE reservation
            SET status = 'CANCELLED'
            WHERE reservation_id = %s
            AND status IN ('PENDING', 'CONFIRMED')
        """, (reservation_id,))

        if cursor.rowcount == 0:
            return False, "Reservation not found or cannot be cancelled."

        conn.commit()
        return True, "Reservation cancelled successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Cancellation failed: {e}"

    finally:
        close_connection(conn, cursor)


def check_in_party(reservation_id, branch_id, table_number, party_size):
    """
    Checks in a party by creating a party record and updating
    the reservation status to SEATED.
    Returns the new party_id on success.
    """
    conn = get_connection()
    if not conn:
        return None, "Database connection failed."

    cursor = conn.cursor()

    try:
        # Create the party record
        cursor.execute("""
            INSERT INTO party (reservation_id, branch_id, table_number, party_size, check_in_datetime)
            VALUES (%s, %s, %s, %s, NOW())
        """, (reservation_id, branch_id, table_number, party_size))

        party_id = cursor.lastrowid

        # Update reservation status to SEATED
        cursor.execute("""
            UPDATE reservation
            SET status = 'SEATED'
            WHERE reservation_id = %s
        """, (reservation_id,))

        conn.commit()
        return party_id, "Party checked in successfully."

    except Exception as e:
        conn.rollback()
        return None, f"Check in failed: {e}"

    finally:
        close_connection(conn, cursor)


def check_out_party(party_id):
    """
    Checks out a party by setting the check_out_datetime
    and updating the reservation status to COMPLETED.
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        # Set check out time
        cursor.execute("""
            UPDATE party
            SET check_out_datetime = NOW()
            WHERE party_id = %s
        """, (party_id,))

        # Update linked reservation to COMPLETED
        cursor.execute("""
            UPDATE reservation r
            JOIN party pa ON r.reservation_id = pa.reservation_id
            SET r.status = 'COMPLETED'
            WHERE pa.party_id = %s
        """, (party_id,))

        conn.commit()
        return True, "Party checked out successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Check out failed: {e}"

    finally:
        close_connection(conn, cursor)


def get_active_parties(branch_id):
    """Retrieves all currently seated parties for a branch."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT pa.party_id, pa.table_number, pa.party_size,
                   pa.check_in_datetime, pa.reservation_id,
                   p.first_name, p.last_name
            FROM party pa
            LEFT JOIN reservation r ON pa.reservation_id = r.reservation_id
            LEFT JOIN person p ON r.person_id = p.person_id
            WHERE pa.branch_id = %s AND pa.check_out_datetime IS NULL
            ORDER BY pa.check_in_datetime ASC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving active parties: {e}")
        return []

    finally:
        close_connection(conn, cursor)


def get_available_tables(branch_id, total_tables=20):
    """
    Returns a list of table numbers not currently occupied at a branch.
    Assumes tables are numbered 1 through total_tables.
    """
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT table_number
            FROM party
            WHERE branch_id = %s AND check_out_datetime IS NULL
        """, (branch_id,))

        occupied = {row[0] for row in cursor.fetchall()}
        available = [t for t in range(1, total_tables + 1) if t not in occupied]
        return available

    except Exception as e:
        print(f"Error retrieving available tables: {e}")
        return []

    finally:
        close_connection(conn, cursor)