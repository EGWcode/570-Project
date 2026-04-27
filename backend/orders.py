'''
orders.py

     FLOW - Enterprise Restaurant Management System
     CSC 570 Sp 26'
     Created by Day Ekoi - March 23 - April 10, 2026

 This file handles all order related database queries for the FLOW system.
 It provides functions for creating orders, adding items to orders,
 updating order status, and retrieving order details for both staff and manager interfaces.

 Functions:
   - create_order()          : creates a new order linked to a party and employee
   - add_order_item()        : adds a menu item to an existing order
   - get_order_items()       : retrieves all items for a specific order
   - update_order_status()   : updates the status of an order
   - get_active_orders()     : retrieves all active orders for a branch
   - get_order_by_id()       : retrieves a single order by order_id
   - get_orders_by_party()   : retrieves all orders for a specific party
   - calculate_order_total() : calculates subtotal, tax, and total for an order
   - cancel_order()          : cancels an existing order
'''

from config.db_config import get_connection, close_connection

TAX_RATE = 0.08


def _has_column(cursor, table_name, column_name):
    try:
        cursor.execute("""
            SELECT COUNT(*) AS column_exists
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
        """, (table_name, column_name))
        row = cursor.fetchone()
        if isinstance(row, dict):
            return row.get("column_exists", 0) > 0
        return (row[0] if row else 0) > 0
    except Exception:
        return False


def create_order(party_id, branch_id, employee_id):
    """
    Creates a new order linked to a party and employee.
    Order starts with zero totals and IN_PROGRESS status.
    Items are added separately using add_order_item().
    Returns the new order_id on success.
    """
    conn = get_connection()
    if not conn:
        return None, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO orders (party_id, branch_id, employee_id, order_datetime,
                                order_status, subtotal, tax_amount, total_amount)
            VALUES (%s, %s, %s, NOW(), 'IN_PROGRESS', 0.00, 0.00, 0.00)
        """, (party_id, branch_id, employee_id))

        order_id = cursor.lastrowid
        conn.commit()
        return order_id, "Order created successfully."

    except Exception as e:
        conn.rollback()
        return None, f"Order creation failed: {e}"

    finally:
        close_connection(conn, cursor)

def add_order_item(order_id, menu_item_id, quantity, item_price, special_instructions=None):
    """
    Adds a menu item to an existing order.
    After adding the item, recalculates and updates the order total.
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        if _has_column(cursor, "order_item", "special_instructions"):
            cursor.execute("""
                INSERT INTO order_item (order_id, menu_item_id, quantity, item_price, special_instructions)
                VALUES (%s, %s, %s, %s, %s)
            """, (order_id, menu_item_id, quantity, item_price, special_instructions))
        else:
            cursor.execute("""
                INSERT INTO order_item (order_id, menu_item_id, quantity, item_price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, menu_item_id, quantity, item_price))

        # Recalculate order totals
        cursor.execute("""
            SELECT SUM(quantity * item_price) as subtotal
            FROM order_item
            WHERE order_id = %s
        """, (order_id,))

        result = cursor.fetchone()
        subtotal = float(result[0]) if result[0] else 0.00
        tax_amount = round(subtotal * TAX_RATE, 2)
        total_amount = round(subtotal + tax_amount, 2)

        # Update order totals
        cursor.execute("""
            UPDATE orders
            SET subtotal = %s, tax_amount = %s, total_amount = %s
            WHERE order_id = %s
        """, (subtotal, tax_amount, total_amount, order_id))

        conn.commit()
        return True, "Item added successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Failed to add item: {e}"

    finally:
        close_connection(conn, cursor)

def get_order_items(order_id):
    """Retrieves all items for a specific order."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        special_select = "oi.special_instructions" if _has_column(cursor, "order_item", "special_instructions") else "NULL AS special_instructions"
        cursor.execute(f"""
            SELECT oi.order_item_id, oi.quantity, oi.item_price,
                   {special_select},
                   mi.item_name, mi.category,
                   (oi.quantity * oi.item_price) as line_total
            FROM order_item oi
            JOIN menu_item mi ON oi.menu_item_id = mi.menu_item_id
            WHERE oi.order_id = %s
        """, (order_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving order items: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def update_order_status(order_id, status):
    """Updates the status of an order and publishes the change to Redis and MongoDB."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT branch_id FROM orders WHERE order_id = %s", (order_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Order not found."
        branch_id = row["branch_id"]

        cursor.execute("""
            UPDATE orders
            SET order_status = %s
            WHERE order_id = %s
        """, (status, order_id))

        conn.commit()

        try:
            from config.redis_config import publish_order_update
            from config.mongo_config import log_order_event
            publish_order_update(branch_id, order_id, status)
            log_order_event(order_id, branch_id, "STATUS_CHANGED", {"new_status": status})
        except Exception:
            pass

        return True, f"Order status updated to {status}."

    except Exception as e:
        conn.rollback()
        return False, f"Status update failed: {e}"

    finally:
        close_connection(conn, cursor)

def get_active_orders(branch_id=None):
    """Retrieves all active in-progress orders, optionally filtered by branch."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        branch_filter = "AND o.branch_id = %s" if branch_id else ""
        params = (branch_id,) if branch_id else ()
        cursor.execute(f"""
            SELECT o.order_id, o.order_datetime, o.order_status,
                   o.subtotal, o.tax_amount, o.total_amount, o.notes,
                   o.party_id, o.branch_id, b.branch_name,
                   pa.table_number,
                   COALESCE(p.first_name, 'Online') AS first_name,
                   COALESCE(p.last_name, 'Order') AS last_name
            FROM orders o
            LEFT JOIN party pa ON o.party_id = pa.party_id
            LEFT JOIN branch b ON o.branch_id = b.branch_id
            LEFT JOIN employee e ON o.employee_id = e.person_id
            LEFT JOIN person p ON e.person_id = p.person_id
            WHERE o.order_status = 'IN_PROGRESS'
              {branch_filter}
            ORDER BY o.order_datetime ASC
        """, params)
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving active orders: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_order_by_id(order_id):
    """Retrieves a single order by order_id."""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT o.order_id, o.order_datetime, o.order_status,
                   o.subtotal, o.tax_amount, o.total_amount,
                   o.party_id, o.branch_id, o.employee_id,
                   pa.table_number, b.branch_name
            FROM orders o
            JOIN party pa ON o.party_id = pa.party_id
            JOIN branch b ON o.branch_id = b.branch_id
            WHERE o.order_id = %s
        """, (order_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving order: {e}")
        return None

    finally:
        close_connection(conn, cursor)

def get_orders_by_party(party_id):
    """Retrieves all orders for a specific party."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT o.order_id, o.order_datetime, o.order_status,
                   o.subtotal, o.tax_amount, o.total_amount
            FROM orders o
            WHERE o.party_id = %s
            ORDER BY o.order_datetime ASC
        """, (party_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving orders by party: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def cancel_order(order_id):
    """Cancels an existing order if it is still in progress."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE orders
            SET order_status = 'CANCELLED'
            WHERE order_id = %s AND order_status = 'IN_PROGRESS'
        """, (order_id,))

        if cursor.rowcount == 0:
            return False, "Order not found or cannot be cancelled."

        conn.commit()
        return True, "Order cancelled successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Cancellation failed: {e}"

    finally:
        close_connection(conn, cursor)
