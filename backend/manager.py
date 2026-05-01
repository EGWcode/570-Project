'''
 manager.py

     FLOW - Enterprise Restaurant Management System
     CSC 570 Sp 26'
     Created by Day Ekoi - March 23 - April 10, 2026

 This file handles all manager level database queries for the FLOW system.
 It provides functions for branch analytics, sales reporting, performance
 comparisons, supplier management, and enterprise level oversight. It is
 used exclusively by the manager and admin interfaces to support data
 driven decision making across all branches of Soul by the Sea.

 Functions:
   - get_branch_summary()           : retrieves key metrics for a branch
   - get_all_branches()             : retrieves all branches in the system
   - get_branch_by_id()             : retrieves a single branch by branch_id
   - get_sales_report()             : retrieves sales data for a branch by date range
   - get_top_menu_items()           : retrieves best selling menu items for a branch
   - get_food_cost_percentage()     : calculates food cost percentage for a branch
   - get_labor_report()             : retrieves labor and shift data for a branch
   - get_cross_branch_summary()     : compares performance across all branches
   - add_branch()                   : adds a new branch to the system
   - update_branch_manager()        : assigns a manager to a branch
   - get_menu_items()               : retrieves all menu items
   - add_menu_item()                : adds a new menu item
   - update_menu_item()             : updates an existing menu item
   - toggle_menu_item_status()      : activates or deactivates a menu item
   - add_supplier()                 : adds a new supplier to the system
   - update_supplier()              : updates supplier contact information
   - get_supplier_inventory_items() : retrieves all inventory items linked to a supplier
   - get_purchase_order_summary()   : retrieves purchase order overview for a branch
'''

from config.db_config import get_connection, close_connection

def get_branch_summary(branch_id):
    """
    Retrieves key operational metrics for a branch including
    total orders, revenue, active employees, and average rating.
    """
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                b.branch_id, b.branch_name, b.address, b.phone,
                COALESCE(os.total_orders, 0) as total_orders,
                COALESCE(os.total_revenue, 0) as total_revenue,
                COALESCE(es.total_employees, 0) as total_employees,
                rs.average_rating
            FROM branch b
            LEFT JOIN (
                SELECT branch_id,
                       COUNT(order_id) as total_orders,
                       SUM(total_amount) as total_revenue
                FROM orders
                WHERE order_status = 'COMPLETED'
                GROUP BY branch_id
            ) os ON b.branch_id = os.branch_id
            LEFT JOIN (
                SELECT branch_id,
                       COUNT(person_id) as total_employees
                FROM employee
                WHERE employment_status = 'ACTIVE'
                GROUP BY branch_id
            ) es ON b.branch_id = es.branch_id
            LEFT JOIN (
                SELECT branch_id,
                       ROUND(AVG(rating), 2) as average_rating
                FROM review
                GROUP BY branch_id
            ) rs ON b.branch_id = rs.branch_id
            WHERE b.branch_id = %s
        """, (branch_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving branch summary: {e}")
        return None

    finally:
        close_connection(conn, cursor)

def get_all_branches():
    """Retrieves all branches in the system."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT b.branch_id, b.branch_name, b.address, b.phone,
                   p.first_name, p.last_name
            FROM branch b
            LEFT JOIN manager m ON b.manager_id = m.person_id
            LEFT JOIN person p ON m.person_id = p.person_id
            ORDER BY b.branch_name ASC
        """)
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving branches: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_branch_by_id(branch_id):
    """Retrieves a single branch by branch_id."""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT b.branch_id, b.branch_name, b.address, b.phone,
                   p.first_name, p.last_name, p.person_id as manager_person_id
            FROM branch b
            LEFT JOIN manager m ON b.manager_id = m.person_id
            LEFT JOIN person p ON m.person_id = p.person_id
            WHERE b.branch_id = %s
        """, (branch_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving branch: {e}")
        return None

    finally:
        close_connection(conn, cursor)

def get_sales_report(branch_id, start_date, end_date):
    """
    Retrieves sales data for a branch within a date range.
    Returns daily totals including order count and revenue.
    """
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                DATE(o.order_datetime) as sale_date,
                COUNT(o.order_id) as total_orders,
                SUM(o.subtotal) as total_subtotal,
                SUM(o.tax_amount) as total_tax,
                SUM(o.total_amount) as total_revenue,
                SUM(p.tip_amount) as total_tips
            FROM orders o
            LEFT JOIN payment p ON o.order_id = p.order_id
            WHERE o.branch_id = %s
            AND DATE(o.order_datetime) BETWEEN %s AND %s
            AND o.order_status = 'COMPLETED'
            GROUP BY DATE(o.order_datetime)
            ORDER BY sale_date ASC
        """, (branch_id, start_date, end_date))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving sales report: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_sales_by_hour(branch_id, report_date):
    """
    Returns order count and revenue grouped by hour of day for a given date.
    Used for the 'sales by hour' analytics view.
    """
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                HOUR(o.order_datetime)  AS hour_of_day,
                COUNT(o.order_id)       AS total_orders,
                SUM(o.total_amount)     AS total_revenue
            FROM orders o
            WHERE o.branch_id = %s
              AND DATE(o.order_datetime) = %s
              AND o.order_status = 'COMPLETED'
            GROUP BY HOUR(o.order_datetime)
            ORDER BY hour_of_day ASC
        """, (branch_id, report_date))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving sales by hour: {e}")
        return []

    finally:
        close_connection(conn, cursor)


def get_top_menu_items(branch_id, limit=10):
    """
    Retrieves the best selling menu items for a branch
    based on total quantity ordered.
    """
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                mi.menu_item_id, mi.item_name, mi.category, mi.price,
                SUM(oi.quantity) as total_ordered,
                SUM(oi.quantity * oi.item_price) as total_revenue
            FROM order_item oi
            JOIN menu_item mi ON oi.menu_item_id = mi.menu_item_id
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.branch_id = %s
            AND o.order_status = 'COMPLETED'
            GROUP BY mi.menu_item_id, mi.item_name, mi.category, mi.price
            ORDER BY total_ordered DESC
            LIMIT %s
        """, (branch_id, limit))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving top menu items: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_food_cost_percentage(branch_id, start_date, end_date):
    """
    Calculates the food cost percentage for a branch within a date range.
    Food cost percentage = (total inventory cost / total revenue) x 100.
    """
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                COALESCE(revenue.total_revenue, 0) AS total_revenue,
                COALESCE(costs.total_inventory_cost, 0) AS total_inventory_cost,
                ROUND(
                    COALESCE(costs.total_inventory_cost, 0) /
                    NULLIF(COALESCE(revenue.total_revenue, 0), 0) * 100, 2
                ) AS food_cost_percentage
            FROM (
                SELECT SUM(total_amount) AS total_revenue
                FROM orders
                WHERE branch_id = %s
                  AND DATE(order_datetime) BETWEEN %s AND %s
                  AND order_status = 'COMPLETED'
            ) revenue
            CROSS JOIN (
                SELECT SUM(oi.quantity * COALESCE(mii.quantity_required, 0) * COALESCE(ii.cost_per_unit, 0)) AS total_inventory_cost
                FROM orders o
                JOIN order_item oi ON o.order_id = oi.order_id
                LEFT JOIN menu_item_ingredient mii ON oi.menu_item_id = mii.menu_item_id
                LEFT JOIN inventory_item ii ON mii.inventory_item_id = ii.inventory_item_id
                    AND ii.branch_id = o.branch_id
                WHERE o.branch_id = %s
                  AND DATE(o.order_datetime) BETWEEN %s AND %s
                  AND o.order_status = 'COMPLETED'
            ) costs
        """, (branch_id, start_date, end_date, branch_id, start_date, end_date))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error calculating food cost percentage: {e}")
        return None

    finally:
        close_connection(conn, cursor)

def get_labor_report(branch_id, date):
    """
    Retrieves labor and shift data for a branch on a specific date
    including total hours scheduled and employees on shift.
    """
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                p.first_name, p.last_name,
                s.role_assigned, s.start_time, s.end_time,
                TIMESTAMPDIFF(HOUR, s.start_time, s.end_time) as hours_scheduled,
                st.hourly_rate,
                TIMESTAMPDIFF(HOUR, s.start_time, s.end_time) * st.hourly_rate as estimated_labor_cost
            FROM shift_schedule s
            JOIN person p ON s.person_id = p.person_id
            LEFT JOIN staff st ON s.person_id = st.person_id
            WHERE s.branch_id = %s AND s.shift_date = %s
            ORDER BY s.start_time ASC
        """, (branch_id, date))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving labor report: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_cross_branch_summary():
    """
    Compares performance across all branches.
    Returns total orders, revenue, and average rating per branch.
    """
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                b.branch_id, b.branch_name,
                COALESCE(os.total_orders, 0) as total_orders,
                COALESCE(os.total_revenue, 0) as total_revenue,
                COALESCE(es.total_employees, 0) as total_employees,
                rs.average_rating
            FROM branch b
            LEFT JOIN (
                SELECT branch_id,
                       COUNT(order_id) as total_orders,
                       SUM(total_amount) as total_revenue
                FROM orders
                WHERE order_status = 'COMPLETED'
                GROUP BY branch_id
            ) os ON b.branch_id = os.branch_id
            LEFT JOIN (
                SELECT branch_id,
                       COUNT(person_id) as total_employees
                FROM employee
                WHERE employment_status = 'ACTIVE'
                GROUP BY branch_id
            ) es ON b.branch_id = es.branch_id
            LEFT JOIN (
                SELECT branch_id,
                       ROUND(AVG(rating), 2) as average_rating
                FROM review
                GROUP BY branch_id
            ) rs ON b.branch_id = rs.branch_id
            ORDER BY total_revenue DESC
        """)
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving cross branch summary: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_menu_items():
    """Retrieves all menu items including inactive ones for manager view."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT menu_item_id, item_name, category,
                   description, price, active_status
            FROM menu_item
            ORDER BY category ASC, item_name ASC
        """)
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving menu items: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def add_menu_item(item_name, category, price, description=None):
    """Adds a new menu item to the system."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO menu_item (item_name, category, description, price, active_status)
            VALUES (%s, %s, %s, %s, TRUE)
        """, (item_name, category, description, price))

        conn.commit()
        return True, "Menu item added successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Failed to add menu item: {e}"

    finally:
        close_connection(conn, cursor)

def update_menu_item(menu_item_id, item_name=None, category=None, price=None, description=None):
    """Updates an existing menu item."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE menu_item
            SET item_name = COALESCE(%s, item_name),
                category = COALESCE(%s, category),
                price = COALESCE(%s, price),
                description = COALESCE(%s, description)
            WHERE menu_item_id = %s
        """, (item_name, category, price, description, menu_item_id))

        if cursor.rowcount == 0:
            return False, "Menu item not found."

        conn.commit()
        return True, "Menu item updated successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Failed to update menu item: {e}"

    finally:
        close_connection(conn, cursor)

def toggle_menu_item_status(menu_item_id):
    """Toggles the active status of a menu item on or off."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE menu_item
            SET active_status = NOT active_status
            WHERE menu_item_id = %s
        """, (menu_item_id,))

        if cursor.rowcount == 0:
            return False, "Menu item not found."

        conn.commit()
        return True, "Menu item status toggled successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Failed to toggle menu item status: {e}"

    finally:
        close_connection(conn, cursor)

def add_supplier(supplier_name, contact_name=None, phone=None, email=None, address=None):
    """Adds a new supplier to the system."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO supplier (supplier_name, contact_name, phone, email, address)
            VALUES (%s, %s, %s, %s, %s)
        """, (supplier_name, contact_name, phone, email, address))

        conn.commit()
        return True, "Supplier added successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Failed to add supplier: {e}"

    finally:
        close_connection(conn, cursor)

def update_supplier(supplier_id, supplier_name=None, contact_name=None, phone=None, email=None, address=None):
    """Updates supplier contact information."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE supplier
            SET supplier_name = COALESCE(%s, supplier_name),
                contact_name = COALESCE(%s, contact_name),
                phone = COALESCE(%s, phone),
                email = COALESCE(%s, email),
                address = COALESCE(%s, address)
            WHERE supplier_id = %s
        """, (supplier_name, contact_name, phone, email, address, supplier_id))

        if cursor.rowcount == 0:
            return False, "Supplier not found."

        conn.commit()
        return True, "Supplier updated successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Failed to update supplier: {e}"

    finally:
        close_connection(conn, cursor)

def get_supplier_inventory_items(supplier_id):
    """
    Retrieves all inventory items linked to a specific supplier
    across all branches so managers can see supplier dependencies.
    """
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT i.inventory_item_id, i.item_name, i.quantity_on_hand,
                   i.unit_type, i.reorder_level, i.cost_per_unit,
                   b.branch_name, b.branch_id,
                   CASE WHEN i.quantity_on_hand <= i.reorder_level
                        THEN 'LOW' ELSE 'OK' END as stock_status
            FROM inventory_item i
            JOIN branch b ON i.branch_id = b.branch_id
            WHERE i.supplier_id = %s
            ORDER BY b.branch_name ASC, i.item_name ASC
        """, (supplier_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving supplier inventory items: {e}")
        return []

    finally:
        close_connection(conn, cursor)

def get_payroll_summary(branch_id):
    """
    Returns payroll records for a branch joined with employee names.
    Falls back to calculating estimated payroll from shift_schedule if
    the payroll table has no rows yet.
    """
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT p.payroll_id,
                   CONCAT(pe.first_name, ' ', pe.last_name) AS employee_name,
                   p.pay_period_start, p.pay_period_end,
                   p.hours_worked, p.gross_pay, p.deductions,
                   p.net_pay, p.pay_date, p.status
            FROM payroll p
            JOIN person pe ON p.person_id = pe.person_id
            WHERE p.branch_id = %s
            ORDER BY p.pay_period_start DESC
            LIMIT 50
        """, (branch_id,))
        rows = cursor.fetchall()

        if not rows:
            # Estimated payroll from shifts — used until payroll runs are processed
            cursor.execute("""
                SELECT CONCAT(pe.first_name, ' ', pe.last_name) AS employee_name,
                       SUM(TIMESTAMPDIFF(HOUR, s.start_time, s.end_time)) AS hours_worked,
                       SUM(TIMESTAMPDIFF(HOUR, s.start_time, s.end_time) * COALESCE(st.hourly_rate, 0)) AS gross_pay,
                       MIN(s.shift_date) AS pay_period_start,
                       MAX(s.shift_date) AS pay_period_end,
                       'ESTIMATED' AS status
                FROM shift_schedule s
                JOIN person pe ON s.person_id = pe.person_id
                LEFT JOIN staff st ON s.person_id = st.person_id
                WHERE s.branch_id = %s
                GROUP BY s.person_id, pe.first_name, pe.last_name
                ORDER BY gross_pay DESC
            """, (branch_id,))
            rows = cursor.fetchall()

        return rows

    except Exception as e:
        print(f"Error retrieving payroll summary: {e}")
        return []

    finally:
        close_connection(conn, cursor)
