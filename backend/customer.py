'''
customer.py

    FLOW - Enterprise Restaurant Management System
    CSC 570 Sp 26'
    Created by Day Ekoi - March 23 - April 10, 2026

 This file handles all customer related database queries for the FLOW system.
 It provides functions for retrieving customer profiles, viewing the menu,
 placing orders, making reservations, and submitting reviews.

Functions:
   - get_customer_profile()       : retrieves a customer's profile by person_id
   - update_customer_profile()    : updates a customer's contact and dietary info
   - get_active_menu()            : retrieves all active menu items
   - get_menu_by_category()       : retrieves menu items filtered by category
   - get_customer_reservations()  : retrieves all reservations for a customer
   - make_reservation()           : creates a new reservation record
   - cancel_reservation()         : cancels an existing reservation
   - get_customer_orders()        : retrieves all orders associated with a customer
   - submit_review()              : submits a customer review for a branch
'''

from config.db_config import get_connection, close_connection

def get_customer_profile(person_id):
    """Retrieves a customer's full profile including person and dietary info."""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT p.person_id, p.first_name, p.last_name, p.dob,
                   p.phone, p.address, p.email, c.dietary_restrictions
            FROM person p
            JOIN customer c ON p.person_id = c.person_id
            WHERE p.person_id = %s
        """, (person_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving customer profile: {e}")
        return None

    finally:
        close_connection(conn, cursor)

def update_customer_profile(person_id, phone=None, address=None, email=None, dietary_restrictions=None):
    """Updates a customer's contact information and dietary restrictions."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE person
            SET phone = COALESCE(%s, phone),
                address = COALESCE(%s, address),
                email = COALESCE(%s, email)
            WHERE person_id = %s
        """, (phone, address, email, person_id))

        cursor.execute("""
            UPDATE customer
            SET dietary_restrictions = COALESCE(%s, dietary_restrictions)
            WHERE person_id = %s
        """, (dietary_restrictions, person_id))

        conn.commit()
        return True, "Profile updated successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Profile update failed: {e}"

    finally:
        close_connection(conn, cursor)

def get_active_menu():
    """Retrieves all active menu items."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT menu_item_id, item_name, category, description, price
            FROM menu_item
            WHERE active_status = TRUE
            ORDER BY category, item_name
        """)
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving menu: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_menu_by_category(category):
    """Retrieves all active menu items filtered by category."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT menu_item_id, item_name, category, description, price
            FROM menu_item
            WHERE active_status = TRUE AND category = %s
            ORDER BY item_name
        """, (category,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving menu by category: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_customer_reservations(person_id):
    """Retrieves all reservations for a customer."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT r.reservation_id, r.reservation_datetime, r.party_size,
                   r.status, b.branch_name, b.address
            FROM reservation r
            JOIN branch b ON r.branch_id = b.branch_id
            WHERE r.person_id = %s
            ORDER BY r.reservation_datetime DESC
        """, (person_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving reservations: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def make_reservation(person_id, branch_id, reservation_datetime, party_size):
    """Creates a new reservation for a customer."""
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
        return False, f"Reservation failed: {e}"

    finally:
        close_connection(conn, cursor)

def cancel_reservation(reservation_id, person_id):
    """Cancels an existing reservation for a customer."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE reservation
            SET status = 'CANCELLED'
            WHERE reservation_id = %s AND person_id = %s
            AND status IN ('PENDING', 'CONFIRMED')
        """, (reservation_id, person_id))

        if cursor.rowcount == 0:
            return False, "Reservation not found or cannot be cancelled."

        conn.commit()
        return True, "Reservation cancelled successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Cancellation failed: {e}"

    finally:
        close_connection(conn, cursor)

def get_customer_orders(person_id):
    """Retrieves all orders associated with a customer via their party history."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT o.order_id, o.order_datetime, o.order_status,
                   o.subtotal, o.tax_amount, o.total_amount,
                   b.branch_name
            FROM orders o
            JOIN branch b ON o.branch_id = b.branch_id
            JOIN party pa ON o.party_id = pa.party_id
            JOIN reservation r ON pa.reservation_id = r.reservation_id
            WHERE r.person_id = %s
            ORDER BY o.order_datetime DESC
        """, (person_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving customer orders: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def submit_review(person_id, branch_id, rating, comments=None):
    """Submits a customer review for a branch."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO review (person_id, branch_id, rating, comments)
            VALUES (%s, %s, %s, %s)
        """, (person_id, branch_id, rating, comments))

        conn.commit()
        return True, "Review submitted successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Review submission failed: {e}"

    finally:
        close_connection(conn, cursor)