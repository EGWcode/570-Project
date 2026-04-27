import json
import os
import sys
from datetime import datetime, time, timedelta

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from backend.auth import get_current_user
    from backend.inventory import get_menu_availability
    from backend.reviews import submit_review as db_submit_review
    from config.db_config import close_connection, get_connection
    from config.redis_config import get_redis

    BACKEND_AVAILABLE = True
except Exception:
    BACKEND_AVAILABLE = False


app = Flask(__name__)

TAX_RATE = 0.08
PAYMENT_TYPES = ["CASH", "CREDIT", "DEBIT", "GIFT_CARD", "MOBILE"]
CATEGORIES = [
    "Appetizers",
    "Above Sea",
    "Sea Level",
    "Under the Sea",
    "Sides",
    "Drinks",
    "Desserts",
]
BRANCHES = [
    {"branch_id": 1, "branch_name": "Soul by the Sea - Hampton", "address": "100 Ocean Avenue, Hampton, VA", "phone": "555-0100"},
    {"branch_id": 2, "branch_name": "Soul by the Sea - Norfolk", "address": "200 Harbor Street, Norfolk, VA", "phone": "555-0101"},
    {"branch_id": 3, "branch_name": "Soul by the Sea - Chesapeake", "address": "300 Bay Road, Chesapeake, VA", "phone": "555-0102"},
]
MENU_ITEMS = [
    {"name": "Bread or Cornbread Basket", "category": "Appetizers", "price": 0.00, "description": "Complimentary bread service. Choose white, sourdough, wheat, or warm cornbread with honey butter.", "tags": "Complimentary", "complimentary": True},
    {"name": "Soul by the Sea Dip", "category": "Appetizers", "price": 14.99, "description": "Creamy seafood dip with crab, shrimp, and cheese served with pita or chips.", "tags": "Signature"},
    {"name": "Bayou Mussels", "category": "Appetizers", "price": 15.99, "description": "Mussels simmered in cajun garlic butter broth.", "tags": "Signature"},
    {"name": "Chicken Wings", "category": "Appetizers", "price": 11.99, "description": "5 wings with BBQ, buffalo, lemon pepper, or honey hot.", "tags": "Popular"},
    {"name": "Soul Food Egg Rolls", "category": "Appetizers", "price": 12.99, "description": "Collard greens and mac & cheese filling.", "tags": "Signature"},
    {"name": "Fried Green Tomatoes", "category": "Appetizers", "price": 9.99, "description": "Crispy fried green tomatoes.", "tags": "Classic"},
    {"name": "Cajun Calamari", "category": "Appetizers", "price": 12.99, "description": "Seasoned fried calamari.", "tags": "Spicy"},
    {"name": "Crab Cakes", "category": "Appetizers", "price": 16.99, "description": "2 golden crab cakes.", "tags": "Premium"},
    {"name": "Shrimp Cocktail", "category": "Appetizers", "price": 13.99, "description": "Chilled shrimp with cocktail sauce.", "tags": "Classic"},
    {"name": "Loaded Fries", "category": "Appetizers", "price": 10.99, "description": "Fries topped with cheese, bacon, and soul sauce.", "tags": "Shareable"},
    {"name": "Burger", "category": "Above Sea", "price": 14.99, "description": "Classic or bacon cheeseburger with fries.", "tags": "Classic"},
    {"name": "Mama's Fried Chicken", "category": "Above Sea", "price": 18.99, "description": "Crispy fried chicken with sides.", "tags": "Popular"},
    {"name": "Smothered Turkey Wings", "category": "Above Sea", "price": 20.99, "description": "Slow cooked in rich gravy.", "tags": "Soul Food"},
    {"name": "Jerk Chicken Plate", "category": "Above Sea", "price": 19.99, "description": "Seasoned jerk chicken with sides.", "tags": "Spicy"},
    {"name": "BBQ Ribs", "category": "Above Sea", "price": 24.99, "description": "Slow cooked ribs with BBQ sauce.", "tags": "Popular"},
    {"name": "Ribeye Steak", "category": "Above Sea", "price": 34.99, "description": "Grilled ribeye steak.", "tags": "Premium"},
    {"name": "Burnt Ends", "category": "Above Sea", "price": 22.99, "description": "Tender BBQ beef bites.", "tags": "BBQ"},
    {"name": "Oxtail Plate", "category": "Above Sea", "price": 29.99, "description": "Slow cooked oxtail with rice and gravy.", "tags": "Premium"},
    {"name": "Surf and Turf", "category": "Sea Level", "price": 34.99, "description": "Steak with shrimp.", "tags": "Premium"},
    {"name": "Seafood Platter", "category": "Sea Level", "price": 32.99, "description": "Fish, shrimp, and crab combo.", "tags": "Popular"},
    {"name": "The Soul Platter", "category": "Sea Level", "price": 29.99, "description": "Fish, shrimp, and chicken with sides.", "tags": "Signature"},
    {"name": "Cajun Shrimp Scampi", "category": "Sea Level", "price": 21.99, "description": "Pasta with shrimp or chicken.", "tags": "Spicy"},
    {"name": "Bay Breeze Alfredo", "category": "Sea Level", "price": 21.99, "description": "Creamy alfredo with chicken or shrimp.", "tags": "Signature"},
    {"name": "Jerk Salmon Dinner", "category": "Sea Level", "price": 26.99, "description": "Seasoned salmon with sides.", "tags": "Spicy"},
    {"name": "Fried Fish Platter", "category": "Under the Sea", "price": 21.99, "description": "Catfish or whiting with sides.", "tags": "Classic"},
    {"name": "Shrimp Basket", "category": "Under the Sea", "price": 18.99, "description": "Fried shrimp with fries.", "tags": "Popular"},
    {"name": "Stuffed Salmon", "category": "Under the Sea", "price": 26.99, "description": "Salmon stuffed with crab.", "tags": "Signature"},
    {"name": "Lobster Mac and Cheese", "category": "Under the Sea", "price": 27.99, "description": "Mac and cheese with lobster.", "tags": "Premium"},
    {"name": "Grilled Salmon Plate", "category": "Under the Sea", "price": 24.99, "description": "Seasoned grilled salmon.", "tags": "Healthy"},
    {"name": "Mac & Cheese", "category": "Sides", "price": 5.99, "description": "Classic baked mac.", "tags": "Popular"},
    {"name": "Collard Greens", "category": "Sides", "price": 5.99, "description": "Slow cooked greens.", "tags": "Soul Food"},
    {"name": "Candied Yams", "category": "Sides", "price": 5.99, "description": "Sweet yams with cinnamon.", "tags": "Sweet"},
    {"name": "Yellow Rice", "category": "Sides", "price": 3.99, "description": "Seasoned rice.", "tags": "Classic"},
    {"name": "Cornbread", "category": "Sides", "price": 3.99, "description": "Warm cornbread.", "tags": "Classic"},
    {"name": "Fries", "category": "Sides", "price": 3.99, "description": "Crispy seasoned fries.", "tags": "Classic"},
    {"name": "Roasted Corn on the Cob", "category": "Sides", "price": 4.99, "description": "Grilled corn.", "tags": "Classic"},
    {"name": "Mashed Potatoes w/ Gravy", "category": "Sides", "price": 5.99, "description": "Creamy potatoes with gravy.", "tags": "Classic"},
    {"name": "Green Beans", "category": "Sides", "price": 4.99, "description": "Seasoned green beans.", "tags": "Classic"},
    {"name": "Rice & Gravy", "category": "Sides", "price": 4.99, "description": "Classic southern side.", "tags": "Soul Food"},
    {"name": "Baked Beans", "category": "Sides", "price": 4.99, "description": "Sweet baked beans.", "tags": "BBQ"},
    {"name": "Side Salad", "category": "Sides", "price": 4.99, "description": "Fresh mixed greens.", "tags": "Fresh"},
    {"name": "Sweet Potato Fries", "category": "Sides", "price": 4.99, "description": "Crispy sweet fries.", "tags": "Sweet"},
    {"name": "Coca-Cola Products", "category": "Drinks", "price": 2.99, "description": "Coke, Sprite, Fanta, and more.", "tags": "Non-Alcoholic"},
    {"name": "Apple Juice", "category": "Drinks", "price": 2.99, "description": "Chilled apple juice.", "tags": "Non-Alcoholic"},
    {"name": "Orange Juice", "category": "Drinks", "price": 2.99, "description": "Fresh orange juice.", "tags": "Non-Alcoholic"},
    {"name": "Bottled Water", "category": "Drinks", "price": 1.99, "description": "Purified water.", "tags": "Non-Alcoholic"},
    {"name": "Blue Sea Lemonade", "category": "Drinks", "price": 4.99, "description": "Signature lemonade. Flavors: strawberry, peach, mango, passionfruit, pineapple.", "tags": "Signature"},
    {"name": "Sweet Tea", "category": "Drinks", "price": 3.99, "description": "Classic southern tea. Flavors: peach, mango, strawberry, passionfruit, pineapple.", "tags": "Non-Alcoholic"},
    {"name": "Unsweet Tea", "category": "Drinks", "price": 3.99, "description": "Unsweetened iced tea. Flavors: peach, mango, strawberry, passionfruit, pineapple.", "tags": "Non-Alcoholic"},
    {"name": "Arnold Palmer", "category": "Drinks", "price": 3.99, "description": "Tea and lemonade mix.", "tags": "Non-Alcoholic"},
    {"name": "Blue Sea Margarita", "category": "Drinks", "price": 10.99, "description": "Signature tropical margarita.", "tags": "21+"},
    {"name": "Strawberry Margarita", "category": "Drinks", "price": 10.99, "description": "Strawberry flavored margarita.", "tags": "21+"},
    {"name": "Mango Margarita", "category": "Drinks", "price": 10.99, "description": "Mango margarita.", "tags": "21+"},
    {"name": "Classic Mojito", "category": "Drinks", "price": 11.99, "description": "Mint and lime cocktail.", "tags": "21+"},
    {"name": "Pineapple Mojito", "category": "Drinks", "price": 11.99, "description": "Pineapple twist.", "tags": "21+"},
    {"name": "Peach Whiskey Smash", "category": "Drinks", "price": 11.99, "description": "Whiskey with peach and citrus.", "tags": "21+"},
    {"name": "Sweet Potato Pie", "category": "Desserts", "price": 7.99, "description": "Classic southern pie.", "tags": "Classic"},
    {"name": "Chocolate Cake", "category": "Desserts", "price": 7.99, "description": "Rich chocolate cake.", "tags": "Sweet"},
    {"name": "Cheesecake", "category": "Desserts", "price": 7.99, "description": "Creamy cheesecake.", "tags": "Classic"},
    {"name": "Grandma's Poundcake", "category": "Desserts", "price": 8.99, "description": "Served with ice cream.", "tags": "Signature"},
    {"name": "Banana Pudding", "category": "Desserts", "price": 6.99, "description": "Classic pudding dessert.", "tags": "Soul Food"},
    {"name": "Peach Cobbler", "category": "Desserts", "price": 7.99, "description": "Warm cobbler with ice cream.", "tags": "Popular"},
    {"name": "Bread Pudding", "category": "Desserts", "price": 6.99, "description": "Sweet baked dessert.", "tags": "Classic"},
    {"name": "Red Velvet Cake", "category": "Desserts", "price": 7.99, "description": "Classic red velvet.", "tags": "Popular"},
    {"name": "Ice Cream", "category": "Desserts", "price": 4.99, "description": "Vanilla, chocolate, or butter pecan.", "tags": "Sweet"},
]


def api_error(message, status=400):
    return {"ok": False, "message": message}, status


def publish_event(event_type, payload):
    try:
        redis_client = get_redis() if BACKEND_AVAILABLE else None
        if redis_client:
            redis_client.publish("flow:customer_events", json.dumps({"event": event_type, "data": payload}))
    except Exception:
        pass


def publish_order_event(event_type, branch_id, reference_id, details):
    branch = next((item for item in BRANCHES if item["branch_id"] == branch_id), BRANCHES[0])
    payload = {
        "event": event_type,
        "branch_id": branch_id,
        "branch_name": branch["branch_name"],
        "reference_id": reference_id,
        "details": details,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        redis_client = get_redis() if BACKEND_AVAILABLE else None
        if redis_client:
            redis_client.publish("flow:orders", json.dumps(payload))
    except Exception:
        pass


def publish_inventory_low(branch_id, inventory_item):
    try:
        redis_client = get_redis() if BACKEND_AVAILABLE else None
        if redis_client:
            redis_client.publish("flow:inventory", json.dumps({
                "event": "inventory_low",
                "branch_id": branch_id,
                "reference_id": inventory_item["inventory_item_id"],
                "details": inventory_item,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }))
    except Exception:
        pass


def track_ordered_items(cart_items):
    try:
        redis_client = get_redis() if BACKEND_AVAILABLE else None
        if redis_client:
            for item in cart_items:
                redis_client.zincrby("flow:popular_items", 1, item["name"])
    except Exception:
        pass


def get_branches():
    if not BACKEND_AVAILABLE:
        return BRANCHES

    conn = get_connection()
    if not conn:
        return BRANCHES

    cursor = conn.cursor(dictionary=True)
    try:
        for branch in BRANCHES:
            cursor.execute(
                """
                INSERT INTO branch (branch_id, branch_name, address, phone)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    branch_name = VALUES(branch_name),
                    address = VALUES(address),
                    phone = VALUES(phone)
                """,
                (branch["branch_id"], branch["branch_name"], branch["address"], branch["phone"]),
            )
        conn.commit()
        return BRANCHES
    except Exception:
        return BRANCHES
    finally:
        close_connection(conn, cursor)


def branch_exists(branch_id):
    return any(branch["branch_id"] == branch_id for branch in get_branches())


def normalize_time(value):
    if isinstance(value, time):
        return value
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
        return time(hour=seconds // 3600, minute=(seconds % 3600) // 60)
    return value


def branch_hours_for_date(branch_id, selected_date):
    default_open = datetime.strptime("11:00 AM", "%I:%M %p").time()
    default_close = datetime.strptime("9:00 PM", "%I:%M %p").time()

    if not BACKEND_AVAILABLE:
        return default_open, default_close

    conn = get_connection()
    if not conn:
        return default_open, default_close

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT open_time, close_time
            FROM branch_hours
            WHERE branch_id = %s AND day_of_week = %s
            """,
            (branch_id, selected_date.strftime("%A").upper()),
        )
        row = cursor.fetchone()
        if row:
            return normalize_time(row["open_time"]), normalize_time(row["close_time"])
    except Exception:
        pass
    finally:
        close_connection(conn, cursor)

    return default_open, default_close


def get_available_reservation_times(branch_id, selected_date):
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

    open_time, close_time = branch_hours_for_date(branch_id, selected_date)
    start_dt = datetime.combine(selected_date, open_time)
    end_dt = datetime.combine(selected_date, close_time)
    slot_counts = {}

    if BACKEND_AVAILABLE:
        conn = get_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    """
                    SELECT TIME(reservation_datetime) AS slot_time,
                           COUNT(*) AS reservation_count,
                           COALESCE(SUM(party_size), 0) AS guest_count
                    FROM reservation
                    WHERE branch_id = %s
                      AND DATE(reservation_datetime) = %s
                      AND status IN ('PENDING', 'CONFIRMED', 'SEATED')
                    GROUP BY TIME(reservation_datetime)
                    """,
                    (branch_id, selected_date),
                )
                for row in cursor.fetchall():
                    slot_counts[str(row["slot_time"])] = row
            except Exception:
                pass
            finally:
                close_connection(conn, cursor)

    slots = []
    current = start_dt
    while current <= end_dt:
        slot_key = current.strftime("%H:%M:%S")
        totals = slot_counts.get(slot_key, {"reservation_count": 0, "guest_count": 0})
        if totals["reservation_count"] < 5 and totals["guest_count"] < 40:
            slots.append(current.strftime("%I:%M %p").lstrip("0"))
        current += timedelta(minutes=30)
    return slots


def get_or_create_customer(name, phone):
    user = get_current_user() if BACKEND_AVAILABLE else None
    if user:
        return user["person_id"]

    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor()
    try:
        safe_phone = "".join(ch for ch in phone if ch.isdigit()) or "guest"
        email = f"guest.{safe_phone}@soulbythesea.local"
        cursor.execute("SELECT person_id FROM person WHERE email = %s", (email,))
        row = cursor.fetchone()
        if row:
            return row[0]

        parts = name.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else "Guest"
        cursor.execute(
            """
            INSERT INTO person (first_name, last_name, phone, email)
            VALUES (%s, %s, %s, %s)
            """,
            (first_name, last_name, phone, email),
        )
        person_id = cursor.lastrowid
        cursor.execute("INSERT INTO customer (person_id, dietary_restrictions) VALUES (%s, NULL)", (person_id,))
        conn.commit()
        return person_id
    except Exception:
        conn.rollback()
        return None
    finally:
        close_connection(conn, cursor)


def get_or_create_online_staff(branch_id):
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor()
    try:
        email = f"online.ordering.{branch_id}@soulbythesea.local"
        cursor.execute("SELECT person_id FROM person WHERE email = %s", (email,))
        row = cursor.fetchone()
        if row:
            person_id = row[0]
        else:
            cursor.execute(
                "INSERT INTO person (first_name, last_name, phone, email) VALUES ('Online', 'Ordering', '555-0000', %s)",
                (email,),
            )
            person_id = cursor.lastrowid

        cursor.execute("SELECT person_id FROM employee WHERE person_id = %s", (person_id,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO employee (person_id, branch_id, job_title, hire_date) VALUES (%s, %s, 'Online Ordering', CURDATE())",
                (person_id, branch_id),
            )
        cursor.execute("SELECT person_id FROM staff WHERE person_id = %s", (person_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO staff (person_id, hourly_rate, role) VALUES (%s, 0.00, 'ONLINE_ORDERING')", (person_id,))
        conn.commit()
        return person_id
    except Exception:
        conn.rollback()
        return None
    finally:
        close_connection(conn, cursor)


def get_or_create_menu_item_id(cursor, item):
    cursor.execute("SELECT menu_item_id FROM menu_item WHERE item_name = %s ORDER BY menu_item_id LIMIT 1", (item["name"],))
    row = cursor.fetchone()
    if row:
        return row[0]

    columns = ["item_name", "category", "description", "price"]
    values = [item["name"], item["category"], item["description"], item["price"]]
    if has_column(cursor, "menu_item", "active_status"):
        columns.append("active_status")
        values.append(True)
    if has_column(cursor, "menu_item", "tags"):
        columns.append("tags")
        values.append(item["tags"])

    placeholders = ", ".join(["%s"] * len(columns))
    cursor.execute(
        f"INSERT INTO menu_item ({', '.join(columns)}) VALUES ({placeholders})",
        tuple(values),
    )
    return cursor.lastrowid


def has_column(cursor, table_name, column_name):
    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
            """,
            (table_name, column_name),
        )
        row = cursor.fetchone()
        if isinstance(row, dict):
            return next(iter(row.values()), 0) > 0
        return (row[0] if row else 0) > 0
    except Exception:
        return False


def column_is_nullable(cursor, table_name, column_name):
    try:
        cursor.execute(
            """
            SELECT IS_NULLABLE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
            """,
            (table_name, column_name),
        )
        row = cursor.fetchone()
        value = row.get("IS_NULLABLE") if isinstance(row, dict) else (row[0] if row else "YES")
        return value == "YES"
    except Exception:
        return True


def row_value(row, key, index):
    if isinstance(row, dict):
        return row[key]
    return row[index]


def insert_order_item(cursor, order_id, menu_item_id, item, notes):
    if has_column(cursor, "order_item", "special_instructions"):
        cursor.execute(
            """
            INSERT INTO order_item (order_id, menu_item_id, quantity, item_price, special_instructions)
            VALUES (%s, %s, 1, %s, %s)
            """,
            (order_id, menu_item_id, item["price"], notes or None),
        )
    else:
        cursor.execute(
            """
            INSERT INTO order_item (order_id, menu_item_id, quantity, item_price)
            VALUES (%s, %s, 1, %s)
            """,
            (order_id, menu_item_id, item["price"]),
        )


def insert_payment(cursor, order_id, payment_type, card_last4, total_amount, tip_amount):
    columns = ["order_id", "payment_type", "amount"]
    values = [order_id, payment_type, total_amount]
    if has_column(cursor, "payment", "card_last4"):
        columns.insert(2, "card_last4")
        values.insert(2, card_last4)
    if has_column(cursor, "payment", "tip_amount"):
        columns.append("tip_amount")
        values.append(tip_amount)
    if has_column(cursor, "payment", "payment_datetime"):
        columns.append("payment_datetime")
        values.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    placeholders = ", ".join(["%s"] * len(columns))
    cursor.execute(
        f"INSERT INTO payment ({', '.join(columns)}) VALUES ({placeholders})",
        tuple(values),
    )


def aggregate_inventory_requirements(cursor, branch_id, cart):
    requirements = {}
    for item in cart:
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
        """, (branch_id, item["name"]))
        for row in cursor.fetchall():
            inventory_item_id = row_value(row, "inventory_item_id", 0)
            item_name = row_value(row, "item_name", 1)
            quantity_on_hand = row_value(row, "quantity_on_hand", 2)
            reorder_level = row_value(row, "reorder_level", 3)
            quantity_required = row_value(row, "quantity_required", 4)
            if inventory_item_id not in requirements:
                requirements[inventory_item_id] = {
                    "inventory_item_id": inventory_item_id,
                    "item_name": item_name,
                    "quantity_on_hand": float(quantity_on_hand),
                    "reorder_level": float(reorder_level),
                    "quantity_needed": 0.0,
                }
            requirements[inventory_item_id]["quantity_needed"] += float(quantity_required)
    return list(requirements.values())


def decrement_inventory_for_cart(cursor, branch_id, cart):
    requirements = aggregate_inventory_requirements(cursor, branch_id, cart)
    low_items = []
    for req in requirements:
        cursor.execute("""
            SELECT inventory_item_id, item_name, quantity_on_hand, reorder_level
            FROM inventory_item
            WHERE inventory_item_id = %s
            FOR UPDATE
        """, (req["inventory_item_id"],))
        row = cursor.fetchone()
        available = float(row_value(row, "quantity_on_hand", 2)) if row else 0
        if not row or available < req["quantity_needed"]:
            raise ValueError(f"Sold out: {req['item_name']} needs {req['quantity_needed']:.2f}, has {available:.2f}")

        new_quantity = round(available - req["quantity_needed"], 2)
        cursor.execute(
            "UPDATE inventory_item SET quantity_on_hand = %s WHERE inventory_item_id = %s",
            (new_quantity, req["inventory_item_id"]),
        )
        reorder_level = float(row_value(row, "reorder_level", 3))
        if new_quantity <= reorder_level:
            low_items.append({
                "inventory_item_id": req["inventory_item_id"],
                "item_name": row_value(row, "item_name", 1),
                "quantity_on_hand": new_quantity,
                "reorder_level": reorder_level,
            })
    return low_items


def parse_cart(raw_cart):
    if not isinstance(raw_cart, list) or not raw_cart:
        raise ValueError("Please add at least one item before placing an order.")

    menu_by_name = {item["name"]: item for item in MENU_ITEMS}
    cart = []
    for entry in raw_cart:
        name = entry.get("name") if isinstance(entry, dict) else None
        if name not in menu_by_name:
            raise ValueError("One or more cart items are unavailable.")
        if not menu_by_name[name].get("complimentary"):
            cart.append(menu_by_name[name])
    if not cart:
        raise ValueError("Please add at least one paid item before placing an order.")
    return cart


def create_order_with_payment(cart, notes, payment_type, tip_amount, card_last4):
    if not BACKEND_AVAILABLE:
        return None, "Database unavailable."

    branch_id = BRANCHES[0]["branch_id"]
    employee_id = get_or_create_online_staff(branch_id)
    if not employee_id:
        return None, "No staff account available for online order processing."

    conn = get_connection()
    if not conn:
        return None, "Database connection failed."

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO party (reservation_id, branch_id, table_number, party_size, check_in_datetime)
            VALUES (NULL, %s, 0, 1, NOW())
            """,
            (branch_id,),
        )
        party_id = cursor.lastrowid
        subtotal = round(sum(item["price"] for item in cart), 2)
        tax_amount = round(subtotal * TAX_RATE, 2)
        total_amount = round(subtotal + tax_amount, 2)

        if has_column(cursor, "orders", "notes"):
            cursor.execute(
                """
                INSERT INTO orders
                    (party_id, branch_id, employee_id, order_datetime, order_status,
                     subtotal, tax_amount, total_amount, notes)
                VALUES (%s, %s, %s, NOW(), 'IN_PROGRESS', %s, %s, %s, %s)
                """,
                (party_id, branch_id, employee_id, subtotal, tax_amount, total_amount, notes or None),
            )
        else:
            cursor.execute(
                """
                INSERT INTO orders
                    (party_id, branch_id, employee_id, order_datetime, order_status,
                     subtotal, tax_amount, total_amount)
                VALUES (%s, %s, %s, NOW(), 'IN_PROGRESS', %s, %s, %s)
                """,
                (party_id, branch_id, employee_id, subtotal, tax_amount, total_amount),
            )
        order_id = cursor.lastrowid

        for item in cart:
            menu_item_id = get_or_create_menu_item_id(cursor, item)
            insert_order_item(cursor, order_id, menu_item_id, item, notes)

        low_inventory_items = decrement_inventory_for_cart(cursor, branch_id, cart)
        insert_payment(cursor, order_id, payment_type, card_last4, total_amount, tip_amount)
        conn.commit()
        for item in low_inventory_items:
            publish_inventory_low(branch_id, item)

        event_payload = {
            "order_id": order_id,
            "branch_id": branch_id,
            "status": "IN_PROGRESS",
            "subtotal": subtotal,
            "tax": tax_amount,
            "total": total_amount,
            "payment_type": payment_type,
            "card_last4": card_last4,
            "items": [item["name"] for item in cart],
        }
        publish_event(
            "new_order",
            event_payload,
        )
        publish_order_event("new_order", branch_id, order_id, event_payload)
        track_ordered_items(cart)
        return order_id, "Order sent to the kitchen."
    except Exception as exc:
        conn.rollback()
        return None, f"Order failed: {exc}"
    finally:
        close_connection(conn, cursor)


@app.route("/")
def index():
    dates = [(datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d") for offset in range(7)]
    bootstrap = {
        "branches": get_branches(),
        "categories": CATEGORIES,
        "dates": dates,
        "menuItems": MENU_ITEMS,
        "paymentTypes": PAYMENT_TYPES,
        "taxRate": TAX_RATE,
    }
    return render_template("index.html", bootstrap_json=json.dumps(bootstrap))


@app.get("/api/reservation-times")
def reservation_times():
    try:
        branch_id = int(request.args.get("branch_id", ""))
        selected_date = request.args.get("date", "")
        datetime.strptime(selected_date, "%Y-%m-%d")
    except ValueError:
        payload, status = api_error("Please select a valid branch and date.")
        return jsonify(payload), status

    if not branch_exists(branch_id):
        payload, status = api_error("Please select a valid branch.")
        return jsonify(payload), status

    return jsonify({"ok": True, "times": get_available_reservation_times(branch_id, selected_date)})


@app.get("/api/menu-availability")
def menu_availability():
    try:
        branch_id = int(request.args.get("branch_id", BRANCHES[0]["branch_id"]))
    except ValueError:
        branch_id = BRANCHES[0]["branch_id"]

    if not BACKEND_AVAILABLE:
        return jsonify({"ok": True, "availability": {}})

    return jsonify({"ok": True, "availability": get_menu_availability(branch_id)})


@app.post("/api/reservations")
def create_reservation():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    selected_date = (data.get("date") or "").strip()
    selected_time = (data.get("time") or "").strip()

    if not all([name, phone, selected_date, selected_time, data.get("branch_id"), data.get("party_size")]):
        return api_error("Please complete all reservation fields.")

    try:
        branch_id = int(data["branch_id"])
        party_size = int(data["party_size"])
        selected_dt = datetime.strptime(f"{selected_date} {selected_time}", "%Y-%m-%d %I:%M %p")
    except ValueError:
        return api_error("Please select a valid reservation date, time, and party size.")

    if not branch_exists(branch_id):
        return api_error("Please select a valid branch.")
    if party_size < 1 or party_size > 20:
        return api_error("Party size must be between 1 and 20.")
    if selected_time not in get_available_reservation_times(branch_id, selected_date):
        return api_error("That reservation slot is full or outside branch hours.")
    if not BACKEND_AVAILABLE:
        return api_error("Reservation system is not connected.", 503)

    person_id = get_or_create_customer(name, phone)
    if not person_id:
        return api_error("Could not create or find a customer record.", 500)

    conn = get_connection()
    if not conn:
        return api_error("Database connection failed.", 503)

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO reservation (person_id, branch_id, reservation_datetime, party_size, status)
            VALUES (%s, %s, %s, %s, 'CONFIRMED')
            """,
            (person_id, branch_id, selected_dt.strftime("%Y-%m-%d %H:%M:%S"), party_size),
        )
        reservation_id = cursor.lastrowid
        conn.commit()
    except Exception as exc:
        conn.rollback()
        return api_error(f"Reservation could not be created: {exc}", 500)
    finally:
        close_connection(conn, cursor)

    publish_event(
        "new_reservation",
        {"reservation_id": reservation_id, "branch_id": branch_id, "date": selected_date, "time": selected_time, "party_size": party_size},
    )
    return jsonify({"ok": True, "message": "Your reservation has been confirmed.", "reservation_id": reservation_id})


@app.post("/api/orders")
def place_order():
    data = request.get_json(silent=True) or {}
    try:
        cart = parse_cart(data.get("cart"))
    except ValueError as exc:
        return api_error(str(exc))

    payment = data.get("payment") or {}
    cardholder = (payment.get("cardholder") or "").strip()
    card_number = (payment.get("card_number") or "").replace(" ", "").replace("-", "")
    expiration = (payment.get("expiration") or "").strip()
    cvv = (payment.get("cvv") or "").strip()
    payment_type = (payment.get("payment_type") or "").strip()

    if not all([cardholder, card_number, expiration, cvv, payment_type]):
        return api_error("Please complete all payment fields.")
    if payment_type not in PAYMENT_TYPES:
        return api_error("Please select a valid payment type.")
    if not card_number.isdigit() or len(card_number) not in (13, 14, 15, 16, 19):
        return api_error("Card number must contain 13-19 digits.")
    if not cvv.isdigit() or len(cvv) not in (3, 4):
        return api_error("CVV must contain 3 or 4 digits.")

    try:
        tip_amount = round(float(payment.get("tip_amount") or 0), 2)
    except ValueError:
        return api_error("Tip amount must be a valid number.")
    if tip_amount < 0:
        return api_error("Tip amount cannot be negative.")

    notes = (data.get("notes") or "").strip()
    card_last4 = card_number[-4:]
    order_id, message = create_order_with_payment(cart, notes, payment_type, tip_amount, card_last4)
    if not order_id:
        return api_error(message, 500)

    subtotal = round(sum(item["price"] for item in cart), 2)
    tax_amount = round(subtotal * TAX_RATE, 2)
    total_amount = round(subtotal + tax_amount, 2)
    return jsonify({
        "ok": True,
        "message": "Order paid and sent to the kitchen.",
        "order_id": order_id,
        "status": "IN_PROGRESS",
        "subtotal": subtotal,
        "tax": tax_amount,
        "total": total_amount,
        "tip": tip_amount,
        "payment_type": payment_type,
        "masked_card": f"**** **** **** {card_last4}",
        "token": f"tok_soul_{card_last4}",
    })


@app.post("/api/reviews")
def create_review():
    data = request.get_json(silent=True) or {}
    comments = (data.get("comments") or "").strip()

    try:
        branch_id = int(data.get("branch_id") or BRANCHES[0]["branch_id"])
        rating = int(data.get("rating") or 0)
    except ValueError:
        return api_error("Please select a valid branch and rating.")

    if not branch_exists(branch_id):
        return api_error("Please select a valid branch.")
    if rating < 1 or rating > 5:
        return api_error("Rating must be between 1 and 5.")
    if not comments:
        return api_error("Please enter review comments.")
    if not BACKEND_AVAILABLE:
        return api_error("Review system is not connected.", 503)

    person_id = None
    user = get_current_user()
    if user:
        person_id = user["person_id"]
    elif BACKEND_AVAILABLE:
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                if not column_is_nullable(cursor, "review", "person_id"):
                    person_id = get_or_create_customer("Website Guest", "0000000000")
            finally:
                close_connection(conn, cursor)

    ok, message = db_submit_review(person_id, branch_id, rating, comments)
    if not ok:
        return api_error(message, 500)

    publish_event("new_review", {"person_id": person_id, "branch_id": branch_id, "rating": rating})
    return jsonify({"ok": True, "message": "Thank you for your feedback."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5001)
