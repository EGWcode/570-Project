'''
 payments.py

     FLOW - Enterprise Restaurant Management System
     CSC 570 Sp 26'
     Created by Day Ekoi - March 23 - April 10, 2026

 This file handles all payment related database queries for the FLOW system.
 It provides functions for processing payments, retrieving payment history,
 and generating payment summaries for orders. It is used by both the staff
 interface for processing transactions and the manager interface for
 viewing payment records and branch revenue.

 Functions:
   - process_payment()           : records a payment for an order
   - get_payment_by_order()      : retrieves all payments for a specific order
   - get_payment_by_id()         : retrieves a single payment by payment_id
   - get_payments_by_branch()    : retrieves all payments for a branch
   - get_payments_by_date()      : retrieves all payments for a branch on a date
   - get_daily_revenue()         : calculates total revenue for a branch on a date
   - get_hourly_sales()          : retrieves sales broken down by hour for a branch
'''

from config.db_config import get_connection, close_connection


def process_payment(order_id, payment_type, amount, tip_amount=0.00):
    """
    Records a payment for an order.
    After payment is recorded, updates the order status to COMPLETED.
    Returns the new payment_id on success.
    """
    conn = get_connection()
    if not conn:
        return None, "Database connection failed."

    cursor = conn.cursor()

    try:
        # Insert payment record
        cursor.execute("""
            INSERT INTO payment (order_id, payment_type, amount, tip_amount, payment_datetime)
            VALUES (%s, %s, %s, %s, NOW())
        """, (order_id, payment_type, amount, tip_amount))

        payment_id = cursor.lastrowid

        # Mark order as COMPLETED
        cursor.execute("""
            UPDATE orders
            SET order_status = 'COMPLETED'
            WHERE order_id = %s
        """, (order_id,))

        conn.commit()
        return payment_id, "Payment processed successfully."

    except Exception as e:
        conn.rollback()
        return None, f"Payment failed: {e}"

    finally:
        close_connection(conn, cursor)

def get_payment_by_order(order_id):
    """Retrieves all payments associated with a specific order."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT payment_id, order_id, payment_type,
                   amount, tip_amount, payment_datetime
            FROM payment
            WHERE order_id = %s
            ORDER BY payment_datetime ASC
        """, (order_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving payments by order: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_payment_by_id(payment_id):
    """Retrieves a single payment record by payment_id."""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT pa.payment_id, pa.order_id, pa.payment_type,
                   pa.amount, pa.tip_amount, pa.payment_datetime,
                   o.subtotal, o.tax_amount, o.total_amount,
                   b.branch_name
            FROM payment pa
            JOIN orders o ON pa.order_id = o.order_id
            JOIN branch b ON o.branch_id = b.branch_id
            WHERE pa.payment_id = %s
        """, (payment_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving payment: {e}")
        return None

    finally:
        close_connection(conn, cursor)

def get_payments_by_branch(branch_id):
    """Retrieves all payments for a branch ordered by most recent."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT pa.payment_id, pa.payment_type, pa.amount,
                   pa.tip_amount, pa.payment_datetime,
                   o.order_id, o.subtotal, o.tax_amount, o.total_amount
            FROM payment pa
            JOIN orders o ON pa.order_id = o.order_id
            WHERE o.branch_id = %s
            ORDER BY pa.payment_datetime DESC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving payments by branch: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_payments_by_date(branch_id, date):
    """Retrieves all payments for a branch on a specific date."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT pa.payment_id, pa.payment_type, pa.amount,
                   pa.tip_amount, pa.payment_datetime,
                   o.order_id, o.total_amount
            FROM payment pa
            JOIN orders o ON pa.order_id = o.order_id
            WHERE o.branch_id = %s AND DATE(pa.payment_datetime) = %s
            ORDER BY pa.payment_datetime ASC
        """, (branch_id, date))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving payments by date: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_daily_revenue(branch_id, date):
    """
    Calculates total revenue for a branch on a specific date.
    Returns total sales, total tips, and total transaction count.
    """
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                COUNT(pa.payment_id) as total_transactions,
                SUM(o.subtotal) as total_subtotal,
                SUM(o.tax_amount) as total_tax,
                SUM(o.total_amount) as total_revenue,
                SUM(pa.tip_amount) as total_tips
            FROM payment pa
            JOIN orders o ON pa.order_id = o.order_id
            WHERE o.branch_id = %s AND DATE(pa.payment_datetime) = %s
        """, (branch_id, date))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving daily revenue: {e}")
        return None

    finally:
        close_connection(conn, cursor)

def get_hourly_sales(branch_id, date):
    """
    Retrieves sales broken down by hour for a branch on a specific date.
    Useful for manager analytics and identifying peak hours.
    """
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                HOUR(o.order_datetime) as hour,
                COUNT(o.order_id) as total_orders,
                SUM(o.total_amount) as total_sales
            FROM orders o
            WHERE o.branch_id = %s
            AND DATE(o.order_datetime) = %s
            AND o.order_status = 'COMPLETED'
            GROUP BY HOUR(o.order_datetime)
            ORDER BY hour ASC
        """, (branch_id, date))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving hourly sales: {e}")
        return []

    finally:
        close_connection(conn, cursor)