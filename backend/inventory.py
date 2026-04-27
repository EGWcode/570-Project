'''
 inventory.py

     FLOW - Enterprise Restaurant Management System
     CSC 570 Sp 26'
     Created by Day Ekoi - March 23 - April 10, 2026

 This file handles all inventory and procurement related database queries
 for the FLOW system. It provides functions for viewing and updating stock
 levels, managing suppliers, and creating purchase orders. It is used
 primarily by the manager and staff interfaces.

 Functions:
   - get_inventory_by_branch()      : retrieves all inventory items for a branch
   - get_low_stock_items()          : retrieves items below their reorder level
   - update_inventory_quantity()    : updates the stock level of an inventory item
   - add_inventory_item()           : adds a new inventory item to a branch
   - get_all_suppliers()            : retrieves all suppliers
   - get_supplier_by_id()           : retrieves a single supplier by id
   - create_purchase_order()        : creates a new purchase order
   - add_purchase_order_item()      : adds an item to a purchase order
   - get_purchase_orders()          : retrieves all purchase orders for a branch
   - update_purchase_order_status() : updates the status of a purchase order
   - receive_purchase_order()       : marks order as received and updates inventory

  !!!! Important Notes to self: refer to auth.py notes !!!!! 
   
   '''

from config.db_config import get_connection, close_connection
import json


def _publish_inventory_low(branch_id, inventory_item):
    try:
        from config.redis_config import get_redis
        payload = json.dumps({
            "event": "inventory_low",
            "branch_id": branch_id,
            "reference_id": inventory_item["inventory_item_id"],
            "details": {
                "item_name": inventory_item["item_name"],
                "quantity_on_hand": float(inventory_item["quantity_on_hand"]),
                "reorder_level": float(inventory_item["reorder_level"]),
            },
        })
        get_redis().publish("flow:inventory", payload)
    except Exception:
        pass


def _aggregate_requirements(cursor, branch_id, items):
    """
    Converts ordered menu item names into branch inventory requirements.
    items: [{"name": str, "quantity": int}]
    """
    requirements = {}
    for item in items:
        item_name = item.get("name")
        quantity = int(item.get("quantity", 1) or 1)
        cursor.execute("""
            SELECT branch_inv.inventory_item_id,
                   branch_inv.item_name,
                   branch_inv.quantity_on_hand,
                   branch_inv.reorder_level,
                   mii.quantity_required
            FROM menu_item mi
            JOIN menu_item_ingredient mii ON mi.menu_item_id = mii.menu_item_id
            JOIN inventory_item mapped_inv ON mii.inventory_item_id = mapped_inv.inventory_item_id
            JOIN inventory_item branch_inv
                ON branch_inv.branch_id = %s
               AND branch_inv.item_name = mapped_inv.item_name
            WHERE mi.item_name = %s
        """, (branch_id, item_name))
        for row in cursor.fetchall():
            inventory_item_id = row["inventory_item_id"]
            needed = float(row["quantity_required"]) * quantity
            if inventory_item_id not in requirements:
                requirements[inventory_item_id] = {
                    "inventory_item_id": inventory_item_id,
                    "item_name": row["item_name"],
                    "quantity_on_hand": float(row["quantity_on_hand"]),
                    "reorder_level": float(row["reorder_level"]),
                    "quantity_needed": 0.0,
                }
            requirements[inventory_item_id]["quantity_needed"] += needed
    return list(requirements.values())


def check_order_inventory(branch_id, items):
    """Returns whether all ingredients are available for an order."""
    conn = get_connection()
    if not conn:
        return False, ["Database connection failed."]

    cursor = conn.cursor(dictionary=True)
    try:
        requirements = _aggregate_requirements(cursor, branch_id, items)
        shortages = [
            f"{row['item_name']} needs {row['quantity_needed']:.2f}, has {row['quantity_on_hand']:.2f}"
            for row in requirements
            if row["quantity_on_hand"] < row["quantity_needed"]
        ]
        return len(shortages) == 0, shortages
    except Exception as e:
        return False, [f"Inventory check failed: {e}"]
    finally:
        close_connection(conn, cursor)


def get_menu_availability(branch_id):
    """Returns sold-out status for active menu items at a branch."""
    conn = get_connection()
    if not conn:
        return {}

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT item_name FROM menu_item WHERE active_status = TRUE")
        menu_names = [row["item_name"] for row in cursor.fetchall()]
        availability = {}
        for item_name in menu_names:
            ok, shortages = check_order_inventory(branch_id, [{"name": item_name, "quantity": 1}])
            availability[item_name] = {"available": ok, "shortages": shortages}
        return availability
    except Exception:
        return {}
    finally:
        close_connection(conn, cursor)


def decrement_order_inventory(branch_id, items):
    """Decrements inventory for an order after confirming all ingredients are available."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor(dictionary=True)
    try:
        requirements = _aggregate_requirements(cursor, branch_id, items)
        inventory_ids = [row["inventory_item_id"] for row in requirements]
        locked = {}
        for inventory_item_id in inventory_ids:
            cursor.execute("""
                SELECT inventory_item_id, item_name, quantity_on_hand, reorder_level
                FROM inventory_item
                WHERE inventory_item_id = %s
                FOR UPDATE
            """, (inventory_item_id,))
            row = cursor.fetchone()
            if row:
                locked[inventory_item_id] = row

        shortages = []
        for req in requirements:
            row = locked.get(req["inventory_item_id"])
            if not row or float(row["quantity_on_hand"]) < req["quantity_needed"]:
                available = float(row["quantity_on_hand"]) if row else 0
                shortages.append(f"{req['item_name']} needs {req['quantity_needed']:.2f}, has {available:.2f}")

        if shortages:
            conn.rollback()
            return False, "Sold out: " + "; ".join(shortages)

        low_items = []
        for req in requirements:
            row = locked[req["inventory_item_id"]]
            new_quantity = round(float(row["quantity_on_hand"]) - req["quantity_needed"], 2)
            cursor.execute(
                "UPDATE inventory_item SET quantity_on_hand = %s WHERE inventory_item_id = %s",
                (new_quantity, req["inventory_item_id"]),
            )
            if new_quantity <= float(row["reorder_level"]):
                low_items.append({
                    "inventory_item_id": req["inventory_item_id"],
                    "item_name": row["item_name"],
                    "quantity_on_hand": new_quantity,
                    "reorder_level": float(row["reorder_level"]),
                })

        conn.commit()
        for item in low_items:
            _publish_inventory_low(branch_id, item)
        return True, "Inventory decremented."
    except Exception as e:
        conn.rollback()
        return False, f"Inventory decrement failed: {e}"
    finally:
        close_connection(conn, cursor)


def get_inventory_by_branch(branch_id):
    """Retrieves all inventory items for a specific branch."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT i.inventory_item_id, i.item_name, i.quantity_on_hand,
                   i.unit_type, i.reorder_level, i.cost_per_unit,
                   s.supplier_name,
                   CASE WHEN i.quantity_on_hand <= i.reorder_level
                        THEN 'LOW' ELSE 'OK' END as stock_status
            FROM inventory_item i
            LEFT JOIN supplier s ON i.supplier_id = s.supplier_id
            WHERE i.branch_id = %s
            ORDER BY i.item_name ASC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving inventory: {e}")
        return []

    finally:
        close_connection(conn, cursor)


def get_low_stock_items(branch_id):
    """Retrieves all inventory items that are at or below their reorder level."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT i.inventory_item_id, i.item_name, i.quantity_on_hand,
                   i.unit_type, i.reorder_level, i.cost_per_unit,
                   s.supplier_name, s.supplier_id
            FROM inventory_item i
            LEFT JOIN supplier s ON i.supplier_id = s.supplier_id
            WHERE i.branch_id = %s
            AND i.quantity_on_hand <= i.reorder_level
            ORDER BY i.quantity_on_hand ASC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving low stock items: {e}")
        return []

    finally:
        close_connection(conn, cursor)


def update_inventory_quantity(inventory_item_id, new_quantity):
    """Updates the stock level of an inventory item."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE inventory_item
            SET quantity_on_hand = %s
            WHERE inventory_item_id = %s
        """, (new_quantity, inventory_item_id))

        if cursor.rowcount == 0:
            return False, "Inventory item not found."

        conn.commit()
        return True, "Inventory updated successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Inventory update failed: {e}"

    finally:
        close_connection(conn, cursor)


def add_inventory_item(branch_id, item_name, quantity_on_hand, unit_type, reorder_level, cost_per_unit, supplier_id=None):
    """Adds a new inventory item to a branch."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO inventory_item (branch_id, item_name, quantity_on_hand,
                                        unit_type, reorder_level, cost_per_unit, supplier_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (branch_id, item_name, quantity_on_hand, unit_type, reorder_level, cost_per_unit, supplier_id))

        conn.commit()
        return True, "Inventory item added successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Failed to add inventory item: {e}"

    finally:
        close_connection(conn, cursor)


def get_all_suppliers():
    """Retrieves all suppliers in the system."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT supplier_id, supplier_name, contact_name,
                   phone, email, address
            FROM supplier
            ORDER BY supplier_name ASC
        """)
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving suppliers: {e}")
        return []

    finally:
        close_connection(conn, cursor)


def get_supplier_by_id(supplier_id):
    """Retrieves a single supplier by supplier_id."""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT supplier_id, supplier_name, contact_name,
                   phone, email, address
            FROM supplier
            WHERE supplier_id = %s
        """, (supplier_id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"Error retrieving supplier: {e}")
        return None

    finally:
        close_connection(conn, cursor)


def create_purchase_order(supplier_id, branch_id, order_date, delivery_date=None):
    """
    Creates a new purchase order with CREATED status.
    Items are added separately using add_purchase_order_item().
    Returns the new purchase_order_id on success.
    """
    conn = get_connection()
    if not conn:
        return None, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO purchase_order (supplier_id, branch_id, order_date,
                                        delivery_date, status, total_cost)
            VALUES (%s, %s, %s, %s, 'CREATED', 0.00)
        """, (supplier_id, branch_id, order_date, delivery_date))

        purchase_order_id = cursor.lastrowid
        conn.commit()
        return purchase_order_id, "Purchase order created successfully."

    except Exception as e:
        conn.rollback()
        return None, f"Purchase order creation failed: {e}"

    finally:
        close_connection(conn, cursor)


def add_purchase_order_item(purchase_order_id, inventory_item_id, quantity_ordered, unit_cost):
    """
    Adds an item to an existing purchase order.
    Recalculates and updates the purchase order total cost after adding.
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        # Insert the purchase order item
        cursor.execute("""
            INSERT INTO purchase_order_item (purchase_order_id, inventory_item_id,
                                             quantity_ordered, unit_cost)
            VALUES (%s, %s, %s, %s)
        """, (purchase_order_id, inventory_item_id, quantity_ordered, unit_cost))

        # Recalculate total cost
        cursor.execute("""
            SELECT SUM(quantity_ordered * unit_cost) as total
            FROM purchase_order_item
            WHERE purchase_order_id = %s
        """, (purchase_order_id,))

        result = cursor.fetchone()
        total_cost = float(result[0]) if result[0] else 0.00

        # Update purchase order total
        cursor.execute("""
            UPDATE purchase_order
            SET total_cost = %s
            WHERE purchase_order_id = %s
        """, (total_cost, purchase_order_id))

        conn.commit()
        return True, "Item added to purchase order successfully."

    except Exception as e:
        conn.rollback()
        return False, f"Failed to add purchase order item: {e}"

    finally:
        close_connection(conn, cursor)


def get_purchase_orders(branch_id):
    """Retrieves all purchase orders for a branch."""
    conn = get_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT po.purchase_order_id, po.order_date, po.delivery_date,
                   po.status, po.total_cost,
                   s.supplier_name, s.contact_name, s.phone
            FROM purchase_order po
            JOIN supplier s ON po.supplier_id = s.supplier_id
            WHERE po.branch_id = %s
            ORDER BY po.order_date DESC
        """, (branch_id,))
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving purchase orders: {e}")
        return []

    finally:
        close_connection(conn, cursor)


def update_purchase_order_status(purchase_order_id, status):
    """Updates the status of a purchase order."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE purchase_order
            SET status = %s
            WHERE purchase_order_id = %s
        """, (status, purchase_order_id))

        if cursor.rowcount == 0:
            return False, "Purchase order not found."

        conn.commit()
        return True, f"Purchase order status updated to {status}."

    except Exception as e:
        conn.rollback()
        return False, f"Status update failed: {e}"

    finally:
        close_connection(conn, cursor)


def receive_purchase_order(purchase_order_id):
    """
    Marks a purchase order as RECEIVED and updates inventory quantities
    for all items in the order based on quantities ordered.
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."

    cursor = conn.cursor(dictionary=True)

    try:
        # Get all items in the purchase order
        cursor.execute("""
            SELECT inventory_item_id, quantity_ordered
            FROM purchase_order_item
            WHERE purchase_order_id = %s
        """, (purchase_order_id,))

        items = cursor.fetchall()

        # Update inventory quantities for each item
        for item in items:
            cursor.execute("""
                UPDATE inventory_item
                SET quantity_on_hand = quantity_on_hand + %s
                WHERE inventory_item_id = %s
            """, (item['quantity_ordered'], item['inventory_item_id']))

        # Mark purchase order as RECEIVED
        cursor.execute("""
            UPDATE purchase_order
            SET status = 'RECEIVED'
            WHERE purchase_order_id = %s
        """, (purchase_order_id,))

        conn.commit()
        return True, "Purchase order received and inventory updated."

    except Exception as e:
        conn.rollback()
        return False, f"Failed to receive purchase order: {e}"

    finally:
        close_connection(conn, cursor)
