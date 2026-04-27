# simulate_activity.py
#
#     FLOW - Enterprise Restaurant Management System
#     CSC 570 Sp 26'
#     Created by Day Ekoi - April 26, 2026
#
# Continuously simulates real-time restaurant operations across all branches
# in the FLOW system. Connects to MySQL (flow_db) and Redis, seeds the
# database with realistic data if it is empty, then runs an infinite loop
# that picks random branches and actions, inserts rows into MySQL, publishes
# JSON events to Redis pub/sub channels, and prints formatted console output.
#
# Redis channels published:
#   flow:orders        -- new and completed orders
#   flow:reservations  -- new reservations and check-ins
#   flow:inventory     -- inventory low-stock alerts
#   flow:reviews       -- new customer reviews
#
# Redis sorted set updated:
#   flow:popular_items -- incremented every time a menu item is ordered
#
# Run:  python simulate_activity.py

import os
import sys
import json
import random
import time
from decimal import Decimal
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.db_config import get_connection, close_connection
from config.redis_config import get_redis

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"))


def qty(value):
    return Decimal(str(value)).quantize(Decimal("0.01"))


def json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    return value


def publish(channel, event_type, branch_id, branch_name, reference_id, details):
    """Publish a JSON event to a Redis channel. Silently skips on Redis error."""
    payload = json.dumps({
        "event":        event_type,
        "branch_id":    branch_id,
        "branch_name":  branch_name,
        "reference_id": reference_id,
        "details":      json_safe(details),
        "timestamp":    now_str(),
    })
    try:
        get_redis().publish(channel, payload)
    except Exception:
        pass


def log(branch_name, message):
    print(f"[{branch_name}] {message}")


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

BRANCHES = [
    {"name": "Soul by the Sea - Hampton", "address": "100 Settlers Landing Rd, Hampton, VA 23669", "phone": "757-555-0101"},
    {"name": "Soul by the Sea - Norfolk", "address": "250 Waterside Dr, Norfolk, VA 23510",        "phone": "757-555-0202"},
    {"name": "Soul by the Sea - Suffolk", "address": "780 N Main St, Suffolk, VA 23434",           "phone": "757-555-0303"},
]

SUPPLIERS = [
    {"name": "Chesapeake Bay Seafood",   "contact": "Maria Reyes",  "phone": "757-555-1001", "email": "maria@cbseafood.com",      "address": "10 Harbor Way, Norfolk, VA 23510"},
    {"name": "Southern Prime Meats",     "contact": "James Tucker", "phone": "757-555-1002", "email": "james@southernprime.com",  "address": "42 Commerce Dr, Suffolk, VA 23434"},
    {"name": "Hampton Roads Produce Co.","contact": "Ana Cortez",   "phone": "757-555-1003", "email": "ana@hrproduce.com",        "address": "99 Farm Ln, Hampton, VA 23666"},
    {"name": "Tidewater Beverages",      "contact": "Derek Small",  "phone": "757-555-1004", "email": "derek@tidewaterbev.com",   "address": "55 Dock St, Portsmouth, VA 23704"},
]

MENU_ITEMS = [
    # Appetizers
    {"name": "Bread Basket",           "category": "Appetizers",    "price":  4.99, "description": "Choice of white, sourdough, or wheat bread.",                        "tags": "Starter"},
    {"name": "Cornbread Basket",       "category": "Appetizers",    "price":  5.99, "description": "Warm cornbread served with honey butter.",                           "tags": "Starter"},
    {"name": "Soul by the Sea Dip",    "category": "Appetizers",    "price": 14.99, "description": "Creamy seafood dip with crab, shrimp, and cheese.",                  "tags": "Signature"},
    {"name": "Bayou Mussels",          "category": "Appetizers",    "price": 15.99, "description": "Mussels simmered in cajun garlic butter broth.",                     "tags": "Signature"},
    {"name": "Chicken Wings",          "category": "Appetizers",    "price": 11.99, "description": "5 wings with BBQ, buffalo, lemon pepper, or honey hot.",             "tags": "Popular"},
    {"name": "Soul Food Egg Rolls",    "category": "Appetizers",    "price": 12.99, "description": "Collard greens and mac & cheese filling.",                           "tags": "Signature"},
    {"name": "Fried Green Tomatoes",   "category": "Appetizers",    "price":  9.99, "description": "Crispy fried green tomatoes.",                                        "tags": "Classic"},
    {"name": "Cajun Calamari",         "category": "Appetizers",    "price": 12.99, "description": "Seasoned fried calamari.",                                           "tags": "Spicy"},
    {"name": "Crab Cakes",             "category": "Appetizers",    "price": 16.99, "description": "2 golden crab cakes.",                                               "tags": "Premium"},
    {"name": "Shrimp Cocktail",        "category": "Appetizers",    "price": 13.99, "description": "Chilled shrimp with cocktail sauce.",                                "tags": "Classic"},
    {"name": "Loaded Fries",           "category": "Appetizers",    "price": 10.99, "description": "Fries topped with cheese, bacon, and soul sauce.",                   "tags": "Shareable"},
    # Above Sea
    {"name": "Burger",                 "category": "Above Sea",     "price": 14.99, "description": "Classic or bacon cheeseburger with fries.",                          "tags": "Classic"},
    {"name": "Mama's Fried Chicken",   "category": "Above Sea",     "price": 18.99, "description": "Crispy fried chicken with sides.",                                   "tags": "Popular"},
    {"name": "Smothered Turkey Wings", "category": "Above Sea",     "price": 20.99, "description": "Slow cooked in rich gravy.",                                         "tags": "Soul Food"},
    {"name": "Jerk Chicken Plate",     "category": "Above Sea",     "price": 19.99, "description": "Seasoned jerk chicken with sides.",                                  "tags": "Spicy"},
    {"name": "BBQ Ribs",               "category": "Above Sea",     "price": 24.99, "description": "Slow cooked ribs with BBQ sauce.",                                   "tags": "Popular"},
    {"name": "Ribeye Steak",           "category": "Above Sea",     "price": 34.99, "description": "Grilled ribeye steak.",                                              "tags": "Premium"},
    {"name": "Burnt Ends",             "category": "Above Sea",     "price": 22.99, "description": "Tender BBQ beef bites.",                                             "tags": "BBQ"},
    {"name": "Oxtail Plate",           "category": "Above Sea",     "price": 29.99, "description": "Slow cooked oxtail with rice and gravy.",                            "tags": "Premium"},
    # Sea Level
    {"name": "Surf and Turf",          "category": "Sea Level",     "price": 34.99, "description": "Steak with shrimp.",                                                 "tags": "Premium"},
    {"name": "Seafood Platter",        "category": "Sea Level",     "price": 32.99, "description": "Fish, shrimp, and crab combo.",                                      "tags": "Popular"},
    {"name": "The Soul Platter",       "category": "Sea Level",     "price": 29.99, "description": "Fish, shrimp, and chicken with sides.",                              "tags": "Signature"},
    {"name": "Cajun Shrimp Scampi",    "category": "Sea Level",     "price": 21.99, "description": "Pasta with shrimp or chicken.",                                      "tags": "Spicy"},
    {"name": "Bay Breeze Alfredo",     "category": "Sea Level",     "price": 21.99, "description": "Creamy alfredo with chicken or shrimp.",                             "tags": "Signature"},
    {"name": "Jerk Salmon Dinner",     "category": "Sea Level",     "price": 26.99, "description": "Seasoned salmon with sides.",                                        "tags": "Spicy"},
    # Under the Sea
    {"name": "Fried Fish Platter",     "category": "Under the Sea", "price": 21.99, "description": "Catfish or whiting with sides.",                                     "tags": "Classic"},
    {"name": "Shrimp Basket",          "category": "Under the Sea", "price": 18.99, "description": "Fried shrimp with fries.",                                           "tags": "Popular"},
    {"name": "Stuffed Salmon",         "category": "Under the Sea", "price": 26.99, "description": "Salmon stuffed with crab.",                                          "tags": "Signature"},
    {"name": "Lobster Mac and Cheese", "category": "Under the Sea", "price": 27.99, "description": "Mac and cheese with lobster.",                                       "tags": "Premium"},
    {"name": "Grilled Salmon Plate",   "category": "Under the Sea", "price": 24.99, "description": "Seasoned grilled salmon.",                                           "tags": "Healthy"},
    # Sides
    {"name": "Mac & Cheese",           "category": "Sides",         "price":  5.99, "description": "Classic baked mac.",                                                 "tags": "Popular"},
    {"name": "Collard Greens",         "category": "Sides",         "price":  5.99, "description": "Slow cooked greens.",                                                "tags": "Soul Food"},
    {"name": "Candied Yams",           "category": "Sides",         "price":  5.99, "description": "Sweet yams with cinnamon.",                                          "tags": "Sweet"},
    {"name": "Yellow Rice",            "category": "Sides",         "price":  3.99, "description": "Seasoned rice.",                                                     "tags": "Classic"},
    {"name": "Cornbread",              "category": "Sides",         "price":  3.99, "description": "Warm cornbread.",                                                    "tags": "Classic"},
    {"name": "Fries",                  "category": "Sides",         "price":  3.99, "description": "Crispy seasoned fries.",                                             "tags": "Classic"},
    {"name": "Roasted Corn on the Cob","category": "Sides",         "price":  4.99, "description": "Grilled corn.",                                                      "tags": "Classic"},
    {"name": "Mashed Potatoes w/ Gravy","category":"Sides",         "price":  5.99, "description": "Creamy potatoes with gravy.",                                        "tags": "Classic"},
    {"name": "Green Beans",            "category": "Sides",         "price":  4.99, "description": "Seasoned green beans.",                                              "tags": "Classic"},
    {"name": "Rice & Gravy",           "category": "Sides",         "price":  4.99, "description": "Classic southern side.",                                             "tags": "Soul Food"},
    {"name": "Baked Beans",            "category": "Sides",         "price":  4.99, "description": "Sweet baked beans.",                                                 "tags": "BBQ"},
    {"name": "Side Salad",             "category": "Sides",         "price":  4.99, "description": "Fresh mixed greens.",                                                "tags": "Fresh"},
    {"name": "Sweet Potato Fries",     "category": "Sides",         "price":  4.99, "description": "Crispy sweet fries.",                                                "tags": "Sweet"},
    # Drinks
    {"name": "Coca-Cola Products",     "category": "Drinks",        "price":  2.99, "description": "Coke, Sprite, Fanta, and more.",                                     "tags": "Non-Alcoholic"},
    {"name": "Apple Juice",            "category": "Drinks",        "price":  2.99, "description": "Chilled apple juice.",                                               "tags": "Non-Alcoholic"},
    {"name": "Orange Juice",           "category": "Drinks",        "price":  2.99, "description": "Fresh orange juice.",                                                "tags": "Non-Alcoholic"},
    {"name": "Bottled Water",          "category": "Drinks",        "price":  1.99, "description": "Purified water.",                                                    "tags": "Non-Alcoholic"},
    {"name": "Blue Sea Lemonade",      "category": "Drinks",        "price":  4.99, "description": "Signature lemonade with fruit flavor options.",                      "tags": "Signature"},
    {"name": "Sweet Tea",              "category": "Drinks",        "price":  3.99, "description": "Classic southern sweet tea.",                                        "tags": "Non-Alcoholic"},
    {"name": "Unsweet Tea",            "category": "Drinks",        "price":  3.99, "description": "Unsweetened iced tea.",                                              "tags": "Non-Alcoholic"},
    {"name": "Arnold Palmer",          "category": "Drinks",        "price":  3.99, "description": "Tea and lemonade mix.",                                              "tags": "Non-Alcoholic"},
    {"name": "Blue Sea Margarita",     "category": "Drinks",        "price": 10.99, "description": "Signature tropical margarita.",                                      "tags": "21+"},
    {"name": "Strawberry Margarita",   "category": "Drinks",        "price": 10.99, "description": "Strawberry flavored margarita.",                                     "tags": "21+"},
    {"name": "Mango Margarita",        "category": "Drinks",        "price": 10.99, "description": "Mango margarita.",                                                   "tags": "21+"},
    {"name": "Classic Mojito",         "category": "Drinks",        "price": 11.99, "description": "Mint and lime cocktail.",                                            "tags": "21+"},
    {"name": "Pineapple Mojito",       "category": "Drinks",        "price": 11.99, "description": "Pineapple twist mojito.",                                            "tags": "21+"},
    {"name": "Peach Whiskey Smash",    "category": "Drinks",        "price": 11.99, "description": "Whiskey with peach and citrus.",                                     "tags": "21+"},
    # Desserts
    {"name": "Sweet Potato Pie",       "category": "Desserts",      "price":  7.99, "description": "Classic southern pie.",                                              "tags": "Classic"},
    {"name": "Chocolate Cake",         "category": "Desserts",      "price":  7.99, "description": "Rich chocolate cake.",                                               "tags": "Sweet"},
    {"name": "Cheesecake",             "category": "Desserts",      "price":  7.99, "description": "Creamy cheesecake.",                                                 "tags": "Classic"},
    {"name": "Grandma's Poundcake",    "category": "Desserts",      "price":  8.99, "description": "Served with ice cream.",                                             "tags": "Signature"},
    {"name": "Banana Pudding",         "category": "Desserts",      "price":  6.99, "description": "Classic pudding dessert.",                                           "tags": "Soul Food"},
    {"name": "Peach Cobbler",          "category": "Desserts",      "price":  7.99, "description": "Warm cobbler with ice cream.",                                       "tags": "Popular"},
    {"name": "Bread Pudding",          "category": "Desserts",      "price":  6.99, "description": "Sweet baked dessert.",                                               "tags": "Classic"},
    {"name": "Red Velvet Cake",        "category": "Desserts",      "price":  7.99, "description": "Classic red velvet.",                                                "tags": "Popular"},
    {"name": "Ice Cream",              "category": "Desserts",      "price":  4.99, "description": "Vanilla, chocolate, or butter pecan.",                               "tags": "Sweet"},
]

INVENTORY_SEED = [
    {"name": "Crab Meat",        "unit": "LB",    "qty": 40,  "reorder": 10, "cost": 22.00},
    {"name": "Gulf Shrimp",      "unit": "LB",    "qty": 80,  "reorder": 20, "cost": 12.00},
    {"name": "Mussels",          "unit": "LB",    "qty": 30,  "reorder":  8, "cost": 6.00},
    {"name": "Squid",            "unit": "LB",    "qty": 20,  "reorder":  5, "cost": 7.00},
    {"name": "Lobster",          "unit": "EA",    "qty": 20,  "reorder":  5, "cost": 35.00},
    {"name": "Salmon Fillet",    "unit": "LB",    "qty": 40,  "reorder": 10, "cost": 14.00},
    {"name": "Catfish",          "unit": "LB",    "qty": 50,  "reorder": 12, "cost": 5.50},
    {"name": "Chicken Breast",   "unit": "LB",    "qty": 60,  "reorder": 15, "cost": 5.00},
    {"name": "Chicken Wings",    "unit": "LB",    "qty": 50,  "reorder": 12, "cost": 4.50},
    {"name": "Turkey Wings",     "unit": "LB",    "qty": 30,  "reorder":  8, "cost": 4.00},
    {"name": "Ground Beef",      "unit": "LB",    "qty": 40,  "reorder": 10, "cost": 6.00},
    {"name": "Ribeye",           "unit": "LB",    "qty": 25,  "reorder":  6, "cost": 22.00},
    {"name": "Baby Back Ribs",   "unit": "LB",    "qty": 40,  "reorder": 10, "cost": 8.00},
    {"name": "Beef Brisket",     "unit": "LB",    "qty": 30,  "reorder":  8, "cost": 10.00},
    {"name": "Oxtail",           "unit": "LB",    "qty": 25,  "reorder":  6, "cost": 9.00},
    {"name": "Potatoes",         "unit": "LB",    "qty": 80,  "reorder": 20, "cost": 1.00},
    {"name": "Sweet Potatoes",   "unit": "LB",    "qty": 50,  "reorder": 12, "cost": 1.25},
    {"name": "Cornmeal",         "unit": "LB",    "qty": 30,  "reorder":  8, "cost": 1.00},
    {"name": "Rice",             "unit": "LB",    "qty": 60,  "reorder": 15, "cost": 0.80},
    {"name": "Pasta",            "unit": "LB",    "qty": 30,  "reorder":  8, "cost": 1.50},
    {"name": "Collard Greens",   "unit": "LB",    "qty": 40,  "reorder": 10, "cost": 2.00},
    {"name": "Green Beans",      "unit": "LB",    "qty": 30,  "reorder":  8, "cost": 1.50},
    {"name": "Corn",             "unit": "EA",    "qty": 60,  "reorder": 15, "cost": 0.50},
    {"name": "Cheese Blend",     "unit": "LB",    "qty": 30,  "reorder":  8, "cost": 6.00},
    {"name": "Heavy Cream",      "unit": "GAL",   "qty": 15,  "reorder":  4, "cost": 8.00},
    {"name": "Bread",            "unit": "CASES", "qty": 15,  "reorder":  4, "cost": 12.00},
    {"name": "Peaches",          "unit": "EA",    "qty": 60,  "reorder": 15, "cost": 0.75},
    {"name": "Bananas",          "unit": "EA",    "qty": 60,  "reorder": 15, "cost": 0.30},
    {"name": "Chocolate",        "unit": "LB",    "qty": 15,  "reorder":  4, "cost": 9.00},
    {"name": "Limes",            "unit": "EA",    "qty": 80,  "reorder": 20, "cost": 0.25},
    {"name": "Beans",            "unit": "LB",    "qty": 35,  "reorder":  8, "cost": 1.20},
    {"name": "Mixed Greens",     "unit": "LB",    "qty": 25,  "reorder":  6, "cost": 2.50},
    {"name": "Soda Syrup",       "unit": "GAL",   "qty": 20,  "reorder":  5, "cost": 10.00},
    {"name": "Apple Juice",      "unit": "GAL",   "qty": 15,  "reorder":  4, "cost": 6.00},
    {"name": "Orange Juice",     "unit": "GAL",   "qty": 15,  "reorder":  4, "cost": 6.00},
    {"name": "Bottled Water",    "unit": "CASE",  "qty": 25,  "reorder":  6, "cost": 4.00},
    {"name": "Lemonade Mix",     "unit": "GAL",   "qty": 20,  "reorder":  5, "cost": 5.00},
    {"name": "Tea Mix",          "unit": "GAL",   "qty": 20,  "reorder":  5, "cost": 4.00},
    {"name": "Margarita Mix",    "unit": "GAL",   "qty": 12,  "reorder":  3, "cost": 12.00},
    {"name": "Whiskey",          "unit": "L",     "qty": 15,  "reorder":  4, "cost": 18.00},
    {"name": "Cheesecake",       "unit": "EA",    "qty": 30,  "reorder":  8, "cost": 3.00},
    {"name": "Red Velvet Cake",  "unit": "EA",    "qty": 30,  "reorder":  8, "cost": 3.00},
    {"name": "Ice Cream",        "unit": "GAL",   "qty": 12,  "reorder":  3, "cost": 9.00},
]

# maps menu item name -> inventory item name (ingredient relationship)
INGREDIENT_MAP = {
    # Appetizers
    "Bread Basket":            [("Bread", 0.10)],
    "Cornbread Basket":        [("Cornmeal", 0.25)],
    "Soul by the Sea Dip":     [("Crab Meat", 0.25), ("Gulf Shrimp", 0.25), ("Cheese Blend", 0.25)],
    "Bayou Mussels":           [("Mussels", 1.00)],
    "Chicken Wings":           [("Chicken Wings", 0.75)],
    "Soul Food Egg Rolls":     [("Collard Greens", 0.25), ("Cheese Blend", 0.15)],
    "Cajun Calamari":          [("Squid", 0.50)],
    "Crab Cakes":              [("Crab Meat", 0.50)],
    "Shrimp Cocktail":         [("Gulf Shrimp", 0.50)],
    "Loaded Fries":            [("Potatoes", 0.50), ("Cheese Blend", 0.15)],
    # Above Sea
    "Burger":                  [("Ground Beef", 0.50)],
    "Mama's Fried Chicken":    [("Chicken Breast", 0.75)],
    "Smothered Turkey Wings":  [("Turkey Wings", 1.00)],
    "Jerk Chicken Plate":      [("Chicken Breast", 0.75)],
    "BBQ Ribs":                [("Baby Back Ribs", 1.25)],
    "Ribeye Steak":            [("Ribeye", 0.75)],
    "Burnt Ends":              [("Beef Brisket", 0.75)],
    "Oxtail Plate":            [("Oxtail", 1.00), ("Rice", 0.50)],
    # Sea Level
    "Surf and Turf":           [("Ribeye", 0.50), ("Gulf Shrimp", 0.50)],
    "Seafood Platter":         [("Catfish", 0.50), ("Gulf Shrimp", 0.50), ("Crab Meat", 0.25)],
    "The Soul Platter":        [("Catfish", 0.50), ("Gulf Shrimp", 0.50), ("Chicken Breast", 0.50)],
    "Cajun Shrimp Scampi":     [("Gulf Shrimp", 0.75), ("Pasta", 0.50)],
    "Bay Breeze Alfredo":      [("Chicken Breast", 0.50), ("Pasta", 0.50), ("Heavy Cream", 0.15)],
    "Jerk Salmon Dinner":      [("Salmon Fillet", 0.75)],
    # Under the Sea
    "Fried Fish Platter":      [("Catfish", 0.75)],
    "Shrimp Basket":           [("Gulf Shrimp", 0.75)],
    "Stuffed Salmon":          [("Salmon Fillet", 0.75), ("Crab Meat", 0.25)],
    "Lobster Mac and Cheese":  [("Lobster", 0.50), ("Cheese Blend", 0.50)],
    "Grilled Salmon Plate":    [("Salmon Fillet", 0.75)],
    # Sides
    "Mac & Cheese":            [("Cheese Blend", 0.25)],
    "Collard Greens":          [("Collard Greens", 0.50)],
    "Candied Yams":            [("Sweet Potatoes", 0.50)],
    "Yellow Rice":             [("Rice", 0.50)],
    "Cornbread":               [("Cornmeal", 0.25)],
    "Fries":                   [("Potatoes", 0.50)],
    "Roasted Corn on the Cob": [("Corn", 1.00)],
    "Mashed Potatoes w/ Gravy":[("Potatoes", 0.75)],
    "Green Beans":             [("Green Beans", 0.50)],
    "Rice & Gravy":            [("Rice", 0.50)],
    "Baked Beans":             [("Beans", 0.50)],
    "Side Salad":              [("Mixed Greens", 0.25)],
    "Sweet Potato Fries":      [("Sweet Potatoes", 0.50)],
    # Drinks
    "Coca-Cola Products":      [("Soda Syrup", 0.05)],
    "Apple Juice":             [("Apple Juice", 0.05)],
    "Orange Juice":            [("Orange Juice", 0.05)],
    "Bottled Water":           [("Bottled Water", 0.05)],
    "Blue Sea Lemonade":       [("Lemonade Mix", 0.08)],
    "Sweet Tea":               [("Tea Mix", 0.08)],
    "Unsweet Tea":             [("Tea Mix", 0.08)],
    "Arnold Palmer":           [("Tea Mix", 0.04), ("Lemonade Mix", 0.04)],
    "Blue Sea Margarita":      [("Margarita Mix", 0.08), ("Limes", 1.00)],
    "Strawberry Margarita":    [("Margarita Mix", 0.08), ("Limes", 1.00)],
    "Mango Margarita":         [("Margarita Mix", 0.08), ("Limes", 1.00)],
    "Classic Mojito":          [("Limes", 2.00)],
    "Pineapple Mojito":        [("Limes", 1.00)],
    "Peach Whiskey Smash":     [("Whiskey", 0.08), ("Peaches", 1.00)],
    # Desserts
    "Sweet Potato Pie":        [("Sweet Potatoes", 0.75)],
    "Chocolate Cake":          [("Chocolate", 0.25)],
    "Cheesecake":              [("Cheesecake", 1.00)],
    "Grandma's Poundcake":     [("Bread", 0.10)],
    "Banana Pudding":          [("Bananas", 3.00)],
    "Peach Cobbler":           [("Peaches", 4.00)],
    "Bread Pudding":           [("Bread", 0.20)],
    "Red Velvet Cake":         [("Red Velvet Cake", 1.00)],
    "Ice Cream":               [("Ice Cream", 0.08)],
}

STAFF_ROLES   = ["Server", "Bartender", "Host", "Busser"]
REVIEW_BODIES = [
    ("Best soul food in Hampton Roads, period!", 5),
    ("The oxtail plate was everything. Will be back every week.", 5),
    ("Grandma's Poundcake took me right back home. Incredible.", 5),
    ("Mama's Fried Chicken is the real deal — crispy and seasoned perfectly.", 5),
    ("Great atmosphere right on the water. Stuffed Salmon was phenomenal.", 5),
    ("The Soul Platter is a must-order. Perfect portions.", 4),
    ("BBQ Ribs were fall-off-the-bone good. Sides were solid too.", 4),
    ("Good experience overall, service was attentive and food came out hot.", 4),
    ("Peach Cobbler is a 10/10. Wish the wait time was shorter though.", 3),
    ("Food was good but the place gets packed on weekends. Come early.", 3),
    ("Average experience for the price point. Nothing stood out.", 2),
    ("Service was slow but the Shrimp Basket made up for it.", 3),
]

FIRST_NAMES = [
    "James","Maria","David","Priya","Carlos","Aisha","Lena","Omar","Sofia","Ethan",
    "Marcus","Keisha","Darius","Tamara","Isaiah","Monique","Jaylen","Brianna","Elijah","Jasmine",
    "Andre","Tiffany","Malik","Shayla","Jordan","Destiny","Xavier","Kayla","Tre","Nadia",
    "DeShawn","Latoya","Quincy","Shay","Tyrone","Alexis","Corey","Imani","Dominic","Zoe",
    "Reginald","Crystal","Terrence","Simone","Lamar","Ebony","Kendall","Rochelle","Antoine","Janelle",
    "Christopher","Alicia","Brandon","Latasha","Raymond","Cynthia","Harold","Vanessa","Patrick","Denise",
    "Kevin","Nicole","Aaron","Theresa","Samuel","Sheila","Gregory","Patricia","Timothy","Beverly",
    "Daniel","Angela","Michael","Linda","Robert","Barbara","William","Sandra","Charles","Dorothy",
    "Steven","Betty","Thomas","Ruth","Joseph","Sharon","Paul","Amy","Mark","Helen",
    "Noah","Olivia","Liam","Emma","Benjamin","Ava","Lucas","Mia","Henry","Ella",
    "Aaliyah","DeAndre","Kiara","Jalen","Amara","Rasheed","Sasha","Deon","Niesha","Tavion",
    "Chandra","Broderick","Yolanda","Hakeem","Rochelle","Winston","Loretta","Cedric","Wanda","Leon",
]

LAST_NAMES = [
    "Johnson","Garcia","Williams","Patel","Rodriguez","Brown","Kim","Davis","Torres","Wilson",
    "Jones","Anderson","Taylor","Thomas","Jackson","White","Harris","Martin","Thompson","Moore",
    "Robinson","Walker","Lewis","Hall","Allen","Young","King","Wright","Scott","Green",
    "Baker","Adams","Nelson","Carter","Mitchell","Perez","Roberts","Turner","Phillips","Campbell",
    "Parker","Evans","Edwards","Collins","Stewart","Sanchez","Morris","Rogers","Reed","Cook",
    "Morgan","Bell","Murphy","Bailey","Rivera","Cooper","Richardson","Cox","Howard","Ward",
    "Torres","Peterson","Gray","Ramirez","James","Watson","Brooks","Kelly","Sanders","Price",
    "Bennett","Wood","Barnes","Ross","Henderson","Coleman","Jenkins","Perry","Powell","Long",
    "Patterson","Hughes","Flores","Washington","Butler","Simmons","Foster","Gonzales","Bryant","Alexander",
    "Freeman","Fields","Boyd","Hawkins","Cunningham","Dixon","Spencer","Lawson","George","Holt",
    "Watkins","Bishop","Holland","Tran","Nguyen","Manning","Garrett","Wade","Harper","Haynes",
    "Pearson","Reeves","Perkins","Jefferson","Singleton","Mosley","Chambers","Barker","Cross","Greer",
]

BRANCH_HOURS = [
    ("MONDAY",    "11:00:00", "22:00:00"),
    ("TUESDAY",   "11:00:00", "22:00:00"),
    ("WEDNESDAY", "11:00:00", "22:00:00"),
    ("THURSDAY",  "11:00:00", "23:00:00"),
    ("FRIDAY",    "11:00:00", "23:00:00"),
    ("SATURDAY",  "10:00:00", "23:00:00"),
    ("SUNDAY",    "10:00:00", "21:00:00"),
]


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def column_exists(cur, table_name, column_name):
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table_name, column_name),
    )
    return cur.fetchone()["n"] > 0


def ensure_runtime_schema(conn):
    """Bring older local databases up to the columns used by the demo code."""
    cur = conn.cursor(dictionary=True)
    updates = [
        ("menu_item", "tags", "ALTER TABLE menu_item ADD COLUMN tags VARCHAR(30) NULL"),
        ("orders", "notes", "ALTER TABLE orders ADD COLUMN notes VARCHAR(255) NULL"),
        ("payment", "card_last4", "ALTER TABLE payment ADD COLUMN card_last4 VARCHAR(4) NULL AFTER payment_type"),
        ("order_item", "special_instructions", "ALTER TABLE order_item ADD COLUMN special_instructions VARCHAR(120) NULL"),
    ]
    for table_name, column_name, sql in updates:
        if not column_exists(cur, table_name, column_name):
            print(f"[SEED] Adding missing column {table_name}.{column_name}...")
            cur.execute(sql)

    try:
        cur.execute("ALTER TABLE reservation MODIFY COLUMN person_id INT NULL")
        cur.execute("ALTER TABLE review MODIFY COLUMN person_id INT NULL")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE inventory_item MODIFY COLUMN quantity_on_hand DECIMAL(10,2) NOT NULL")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE inventory_item ADD UNIQUE KEY uq_inventory_branch_item (branch_id, item_name)")
    except Exception:
        pass

    conn.commit()
    cur.close()


def cleanup_duplicate_menu_items(conn):
    cur = conn.cursor(dictionary=True)
    canonical_names = {item["name"] for item in MENU_ITEMS}
    cur.execute("SELECT menu_item_id, item_name FROM menu_item ORDER BY menu_item_id")
    rows = cur.fetchall()
    seen = {}
    delete_ids = []
    remap = {}
    for row in rows:
        name = row["item_name"]
        if name not in canonical_names:
            delete_ids.append(row["menu_item_id"])
        elif name in seen:
            delete_ids.append(row["menu_item_id"])
            remap[row["menu_item_id"]] = seen[name]
        else:
            seen[name] = row["menu_item_id"]

    if delete_ids:
        print(f"[SEED] Removing {len(delete_ids)} duplicate/old menu item(s)...")
        for duplicate_id, canonical_id in remap.items():
            cur.execute(
                "UPDATE order_item SET menu_item_id = %s WHERE menu_item_id = %s",
                (canonical_id, duplicate_id)
            )
        placeholders = ", ".join(["%s"] * len(delete_ids))
        cur.execute(f"DELETE FROM menu_item_ingredient WHERE menu_item_id IN ({placeholders})", tuple(delete_ids))
        try:
            cur.execute(f"DELETE FROM menu_item WHERE menu_item_id IN ({placeholders})", tuple(delete_ids))
        except Exception:
            conn.rollback()
            print("[SEED] Duplicate cleanup skipped because old order history still references those menu rows.")
            cur.close()
            return
        conn.commit()
    cur.close()


def seed_if_empty(conn):
    ensure_runtime_schema(conn)
    cleanup_duplicate_menu_items(conn)
    cur = conn.cursor(dictionary=True)

    # ---- branches ----
    cur.execute("SELECT COUNT(*) AS n FROM branch")
    if cur.fetchone()["n"] == 0:
        print("[SEED] Inserting branches...")
        for b in BRANCHES:
            cur.execute(
                "INSERT INTO branch (branch_name, address, phone) VALUES (%s, %s, %s)",
                (b["name"], b["address"], b["phone"])
            )
        conn.commit()

    cur.execute("SELECT branch_id, branch_name FROM branch")
    branches = cur.fetchall()

    # ---- branch hours ----
    cur.execute("SELECT COUNT(*) AS n FROM branch_hours")
    if cur.fetchone()["n"] == 0:
        print("[SEED] Inserting branch hours...")
        for br in branches:
            for day, open_t, close_t in BRANCH_HOURS:
                cur.execute(
                    "INSERT INTO branch_hours (branch_id, day_of_week, open_time, close_time) VALUES (%s,%s,%s,%s)",
                    (br["branch_id"], day, open_t, close_t)
                )
        conn.commit()

    # ---- suppliers ----
    cur.execute("SELECT COUNT(*) AS n FROM supplier")
    if cur.fetchone()["n"] == 0:
        print("[SEED] Inserting suppliers...")
        for s in SUPPLIERS:
            cur.execute(
                "INSERT INTO supplier (supplier_name, contact_name, phone, email, address) VALUES (%s,%s,%s,%s,%s)",
                (s["name"], s["contact"], s["phone"], s["email"], s["address"])
            )
        conn.commit()

    cur.execute("SELECT supplier_id FROM supplier LIMIT 1")
    supplier_row = cur.fetchone()
    default_supplier = supplier_row["supplier_id"] if supplier_row else None

    # ---- persons / managers per branch ----
    cur.execute("SELECT COUNT(*) AS n FROM person")
    if cur.fetchone()["n"] == 0:
        print("[SEED] Inserting persons, employees, managers, staff...")
        for br in branches:
            # manager
            mgr_first = random.choice(FIRST_NAMES)
            mgr_last  = random.choice(LAST_NAMES)
            cur.execute(
                "INSERT INTO person (first_name, last_name, dob, phone, email) VALUES (%s,%s,%s,%s,%s)",
                (mgr_first, mgr_last, "1980-06-15",
                 f"757-555-{random.randint(2000,2999)}",
                 f"{mgr_first.lower()}.{mgr_last.lower()}.mgr{br['branch_id']}@soulbythesea.com")
            )
            mgr_person_id = cur.lastrowid
            cur.execute(
                "INSERT INTO employee (person_id, branch_id, job_title, hire_date, employment_status) VALUES (%s,%s,%s,%s,%s)",
                (mgr_person_id, br["branch_id"], "General Manager", "2021-03-01", "ACTIVE")
            )
            cur.execute(
                "INSERT INTO manager (person_id, salary) VALUES (%s, %s)",
                (mgr_person_id, round(random.uniform(65000, 90000), 2))
            )
            # link manager to branch
            cur.execute(
                "UPDATE branch SET manager_id = %s WHERE branch_id = %s",
                (mgr_person_id, br["branch_id"])
            )

            # 4 staff members per branch
            for _ in range(4):
                fn = random.choice(FIRST_NAMES)
                ln = random.choice(LAST_NAMES)
                uid = random.randint(3000, 9999)
                cur.execute(
                    "INSERT INTO person (first_name, last_name, dob, phone, email) VALUES (%s,%s,%s,%s,%s)",
                    (fn, ln, "1995-01-01",
                     f"786-555-{uid}",
                     f"{fn.lower()}.{ln.lower()}.{uid}@soulbythesea.com")
                )
                staff_person_id = cur.lastrowid
                role = random.choice(STAFF_ROLES)
                cur.execute(
                    "INSERT INTO employee (person_id, branch_id, job_title, hire_date, employment_status) VALUES (%s,%s,%s,%s,%s)",
                    (staff_person_id, br["branch_id"], role, "2023-06-01", "ACTIVE")
                )
                cur.execute(
                    "INSERT INTO staff (person_id, hourly_rate, role) VALUES (%s,%s,%s)",
                    (staff_person_id, round(random.uniform(14, 22), 2), role)
                )
        conn.commit()

    # ---- menu items ----
    cur.execute("SELECT COUNT(*) AS n FROM menu_item")
    menu_count = cur.fetchone()["n"]
    if menu_count < len(MENU_ITEMS):
        print(f"[SEED] Upserting menu items ({menu_count}/{len(MENU_ITEMS)} present)...")
        for item in MENU_ITEMS:
            cur.execute(
                """
                INSERT INTO menu_item (item_name, category, description, price, active_status, tags)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    category = VALUES(category),
                    description = VALUES(description),
                    price = VALUES(price),
                    active_status = VALUES(active_status),
                    tags = VALUES(tags)
                """,
                (item["name"], item["category"], item["description"], item["price"], True, item["tags"])
            )
        conn.commit()

    # ---- inventory (per branch) ----
    expected_inventory_count = len(branches) * len(INVENTORY_SEED)
    cur.execute("SELECT COUNT(*) AS n FROM inventory_item")
    inventory_count = cur.fetchone()["n"]
    if inventory_count < expected_inventory_count:
        print(f"[SEED] Upserting inventory items ({inventory_count}/{expected_inventory_count} present)...")
        for br in branches:
            for inv in INVENTORY_SEED:
                cur.execute(
                    "SELECT inventory_item_id FROM inventory_item WHERE branch_id = %s AND item_name = %s",
                    (br["branch_id"], inv["name"])
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE inventory_item
                        SET unit_type = %s,
                            reorder_level = %s,
                            cost_per_unit = %s,
                            supplier_id = %s
                        WHERE inventory_item_id = %s
                        """,
                        (inv["unit"], inv["reorder"], inv["cost"], default_supplier, existing["inventory_item_id"])
                    )
                    continue
                cur.execute(
                    """
                    INSERT INTO inventory_item (branch_id, item_name, quantity_on_hand, unit_type, reorder_level, cost_per_unit, supplier_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (br["branch_id"], inv["name"], inv["qty"], inv["unit"],
                     inv["reorder"], inv["cost"], default_supplier)
                )
        conn.commit()

    # ---- menu_item_ingredient ----
    cur.execute("SELECT COUNT(*) AS n FROM menu_item_ingredient")
    ingredient_count = cur.fetchone()["n"]
    if ingredient_count < len(INGREDIENT_MAP):
        print("[SEED] Rebuilding menu item ingredients...")
        cur.execute("DELETE FROM menu_item_ingredient")
        cur.execute("SELECT menu_item_id, item_name FROM menu_item")
        menu_rows = {r["item_name"]: r["menu_item_id"] for r in cur.fetchall()}
        # use branch 1's inventory as the canonical ingredient reference
        cur.execute("SELECT inventory_item_id, item_name FROM inventory_item WHERE branch_id = (SELECT MIN(branch_id) FROM branch)")
        inv_rows = {r["item_name"]: r["inventory_item_id"] for r in cur.fetchall()}
        for menu_name, ingredients in INGREDIENT_MAP.items():
            mid = menu_rows.get(menu_name)
            if not mid:
                continue
            for inv_name, qty in ingredients:
                iid = inv_rows.get(inv_name)
                if not iid:
                    continue
                cur.execute(
                    "INSERT INTO menu_item_ingredient (menu_item_id, inventory_item_id, quantity_required) VALUES (%s,%s,%s)",
                    (mid, iid, qty)
                )
        conn.commit()

    cur.close()
    print("[SEED] Database ready.")
    return branches


# ---------------------------------------------------------------------------
# Simulation helpers — fetch live IDs from the DB
# ---------------------------------------------------------------------------

def get_branches(conn):
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT branch_id, branch_name FROM branch")
    rows = cur.fetchall()
    cur.close()
    return rows


def get_staff_for_branch(conn, branch_id):
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT person_id FROM employee WHERE branch_id = %s AND employment_status = 'ACTIVE'",
        (branch_id,)
    )
    rows = cur.fetchall()
    cur.close()
    return [r["person_id"] for r in rows]


def get_menu_items(conn):
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT menu_item_id, item_name, price FROM menu_item WHERE active_status = TRUE")
    rows = cur.fetchall()
    cur.close()
    return rows


def get_inventory_item(conn, branch_id, item_name):
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT inventory_item_id, quantity_on_hand, reorder_level FROM inventory_item "
        "WHERE branch_id = %s AND item_name = %s",
        (branch_id, item_name)
    )
    row = cur.fetchone()
    cur.close()
    return row


def get_confirmed_reservations(conn, branch_id):
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT reservation_id FROM reservation WHERE branch_id = %s AND status = 'CONFIRMED' LIMIT 10",
        (branch_id,)
    )
    rows = cur.fetchall()
    cur.close()
    return [r["reservation_id"] for r in rows]


def get_open_parties(conn, branch_id):
    """Parties that have checked in but not yet out, and have no completed order."""
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT p.party_id FROM party p "
        "WHERE p.branch_id = %s AND p.check_in_datetime IS NOT NULL AND p.check_out_datetime IS NULL "
        "LIMIT 10",
        (branch_id,)
    )
    rows = cur.fetchall()
    cur.close()
    return [r["party_id"] for r in rows]


def get_in_progress_orders(conn, branch_id):
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT order_id, total_amount FROM orders "
        "WHERE branch_id = %s AND order_status = 'IN_PROGRESS' LIMIT 10",
        (branch_id,)
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def random_person_name():
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


# ---------------------------------------------------------------------------
# Simulation actions
# ---------------------------------------------------------------------------

def action_new_reservation(conn, branch):
    """Insert a CONFIRMED reservation for a new or existing person."""
    cur = conn.cursor()
    bid = branch["branch_id"]
    bname = branch["branch_name"]

    fn, ln = random_person_name()
    email = f"{fn.lower()}.{ln.lower()}.{random.randint(1000,9999)}@guest.com"

    # find or create the person
    cur.execute("SELECT person_id FROM person WHERE email = %s", (email,))
    row = cur.fetchone()
    if row:
        pid = row[0]
    else:
        cur.execute(
            "INSERT INTO person (first_name, last_name, dob, phone, email) VALUES (%s,%s,%s,%s,%s)",
            (fn, ln, "1990-01-01", f"305-555-{random.randint(3000,9999)}", email)
        )
        pid = cur.lastrowid
        cur.execute("INSERT INTO customer (person_id) VALUES (%s)", (pid,))

    # reservation tomorrow at a random lunch/dinner hour
    res_dt = (datetime.now() + timedelta(days=random.randint(1, 7))).replace(
        hour=random.choice([12, 13, 18, 19, 20]), minute=0, second=0, microsecond=0
    )
    party_size = random.randint(1, 8)

    cur.execute(
        "INSERT INTO reservation (person_id, branch_id, reservation_datetime, party_size, status) "
        "VALUES (%s,%s,%s,%s,'CONFIRMED')",
        (pid, bid, res_dt.strftime("%Y-%m-%d %H:%M:%S"), party_size)
    )
    res_id = cur.lastrowid
    conn.commit()
    cur.close()

    log(bname, f"New Reservation Created (Reservation ID: {res_id}, Party: {party_size}, Guest: {fn} {ln})")
    publish("flow:reservations", "new_reservation", bid, bname, res_id, {
        "guest": f"{fn} {ln}", "party_size": party_size,
        "datetime": res_dt.strftime("%Y-%m-%d %H:%M:%S")
    })


def action_checkin_party(conn, branch):
    """Seat a confirmed reservation as a new party, or create a walk-in party."""
    cur = conn.cursor(dictionary=True)
    bid = branch["branch_id"]
    bname = branch["branch_name"]

    confirmed = get_confirmed_reservations(conn, bid)
    table_num = random.randint(1, 20)
    check_in  = now_str()

    if confirmed:
        res_id     = random.choice(confirmed)
        party_size = random.randint(1, 6)
        cur.execute(
            "INSERT INTO party (reservation_id, branch_id, table_number, party_size, check_in_datetime) "
            "VALUES (%s,%s,%s,%s,%s)",
            (res_id, bid, table_num, party_size, check_in)
        )
        party_id = cur.lastrowid
        cur.execute("UPDATE reservation SET status = 'SEATED' WHERE reservation_id = %s", (res_id,))
        conn.commit()
        log(bname, f"Reservation Checked In (Party ID: {party_id}, Table: {table_num})")
        publish("flow:reservations", "reservation_checked_in", bid, bname, res_id, {
            "party_id": party_id, "table_number": table_num
        })
    else:
        party_size = random.randint(1, 6)
        cur.execute(
            "INSERT INTO party (reservation_id, branch_id, table_number, party_size, check_in_datetime) "
            "VALUES (NULL,%s,%s,%s,%s)",
            (bid, table_num, party_size, check_in)
        )
        party_id = cur.lastrowid
        conn.commit()
        log(bname, f"Walk-In Party Seated (Party ID: {party_id}, Table: {table_num}, Size: {party_size})")
        publish("flow:reservations", "walkin_seated", bid, bname, party_id, {
            "table_number": table_num, "party_size": party_size
        })

    cur.close()


def action_create_order(conn, branch, menu_items):
    """Create a new IN_PROGRESS order for an open party at this branch."""
    cur = conn.cursor(dictionary=True)
    bid   = branch["branch_id"]
    bname = branch["branch_name"]

    open_parties = get_open_parties(conn, bid)
    staff_ids    = get_staff_for_branch(conn, bid)

    if not open_parties or not staff_ids:
        cur.close()
        return

    party_id    = random.choice(open_parties)
    employee_id = random.choice(staff_ids)

    # pick 1-4 random items
    chosen     = random.sample(menu_items, k=min(random.randint(1, 4), len(menu_items)))
    subtotal   = money(sum(money(item["price"]) for item in chosen))
    tax_amount = money(subtotal * Decimal("0.07"))
    total      = money(subtotal + tax_amount)

    cur.execute(
        "INSERT INTO orders (party_id, branch_id, employee_id, order_datetime, order_status, subtotal, tax_amount, total_amount) "
        "VALUES (%s,%s,%s,%s,'IN_PROGRESS',%s,%s,%s)",
        (party_id, bid, employee_id, now_str(), subtotal, tax_amount, total)
    )
    order_id = cur.lastrowid

    item_names = []
    for item in chosen:
        qty = random.randint(1, 3)
        cur.execute(
            "INSERT INTO order_item (order_id, menu_item_id, quantity, item_price) VALUES (%s,%s,%s,%s)",
            (order_id, item["menu_item_id"], qty, item["price"])
        )
        item_names.append(item["item_name"])
        # track in Redis popular sorted set
        try:
            get_redis().zincrby("flow:popular_items", qty, item["item_name"])
        except Exception:
            pass

    conn.commit()
    cur.close()

    log(bname, f"New Order Created (Order ID: {order_id}, Items: {', '.join(item_names)}, Total: ${total:.2f})")
    publish("flow:orders", "new_order", bid, bname, order_id, {
        "party_id": party_id, "items": item_names, "total": total
    })

    # decrement inventory for the branch
    _decrement_inventory(conn, branch, chosen)


def _decrement_inventory(conn, branch, menu_items_ordered):
    """Decrement inventory for each ingredient used by the ordered items."""
    cur = conn.cursor(dictionary=True)
    bid   = branch["branch_id"]
    bname = branch["branch_name"]

    for item in menu_items_ordered:
        item_name = item["item_name"]
        ingredients = INGREDIENT_MAP.get(item_name, [])
        for inv_name, qty_used in ingredients:
            cur.execute(
                "SELECT inventory_item_id, quantity_on_hand, reorder_level FROM inventory_item "
                "WHERE branch_id = %s AND item_name = %s",
                (bid, inv_name)
            )
            inv = cur.fetchone()
            if not inv:
                continue
            new_qty = max(Decimal("0.00"), qty(inv["quantity_on_hand"]) - qty(qty_used))
            cur.execute(
                "UPDATE inventory_item SET quantity_on_hand = %s WHERE inventory_item_id = %s",
                (new_qty, inv["inventory_item_id"])
            )
            if new_qty <= qty(inv["reorder_level"]):
                log(bname, f"[INVENTORY LOW] {inv_name}: {new_qty} remaining (reorder at {inv['reorder_level']})")
                publish("flow:inventory", "inventory_low", bid, bname, inv["inventory_item_id"], {
                    "item": inv_name, "quantity_remaining": float(new_qty), "reorder_level": float(inv["reorder_level"])
                })

    conn.commit()
    cur.close()


def action_complete_order(conn, branch):
    """Mark an IN_PROGRESS order as COMPLETED and record a payment."""
    cur = conn.cursor(dictionary=True)
    bid   = branch["branch_id"]
    bname = branch["branch_name"]

    in_progress = get_in_progress_orders(conn, bid)
    if not in_progress:
        cur.close()
        return

    order = random.choice(in_progress)
    oid   = order["order_id"]
    total = float(order["total_amount"])
    tip   = round(total * random.uniform(0.15, 0.25), 2)
    ptype = random.choice(["CASH", "CREDIT", "DEBIT", "MOBILE"])

    cur.execute("UPDATE orders SET order_status = 'COMPLETED' WHERE order_id = %s", (oid,))
    cur.execute(
        "INSERT INTO payment (order_id, payment_type, amount, tip_amount, payment_datetime) VALUES (%s,%s,%s,%s,%s)",
        (oid, ptype, total, tip, now_str())
    )

    # check out the party
    cur.execute(
        "SELECT party_id FROM orders WHERE order_id = %s", (oid,)
    )
    party_row = cur.fetchone()
    if party_row:
        cur.execute(
            "UPDATE party SET check_out_datetime = %s WHERE party_id = %s AND check_out_datetime IS NULL",
            (now_str(), party_row["party_id"])
        )

    conn.commit()
    cur.close()

    log(bname, f"Order Completed (Order ID: {oid}, Total: ${total:.2f}, Tip: ${tip:.2f}, Payment: {ptype})")
    publish("flow:orders", "order_completed", bid, bname, oid, {
        "total": total, "tip": tip, "payment_type": ptype
    })


def action_new_review(conn, branch):
    """Insert a customer review for this branch."""
    cur = conn.cursor()
    bid   = branch["branch_id"]
    bname = branch["branch_name"]

    comment, rating = random.choice(REVIEW_BODIES)
    sentiment = round(random.uniform(-0.2 if rating <= 2 else 0.3, 1.0), 2)

    cur.execute(
        "INSERT INTO review (person_id, branch_id, rating, comments, sentiment_score, created_at) "
        "VALUES (NULL,%s,%s,%s,%s,%s)",
        (bid, rating, comment, sentiment, now_str())
    )
    review_id = cur.lastrowid
    conn.commit()
    cur.close()

    log(bname, f"New Review Submitted (Review ID: {review_id}, Rating: {rating}/5, Sentiment: {sentiment})")
    publish("flow:reviews", "new_review", bid, bname, review_id, {
        "rating": rating, "comment": comment, "sentiment": sentiment
    })


# ---------------------------------------------------------------------------
# Main simulation loop
# ---------------------------------------------------------------------------

ACTIONS = [
    ("new_reservation",  action_new_reservation,  2),
    ("checkin_party",    action_checkin_party,     3),
    ("create_order",     action_create_order,      5),
    ("complete_order",   action_complete_order,    4),
    ("new_review",       action_new_review,        1),
]

# weighted pool so common actions fire more often
ACTION_POOL = []
for name, fn, weight in ACTIONS:
    ACTION_POOL.extend([(name, fn)] * weight)


def main():
    print("=" * 60)
    print("  FLOW Activity Simulator - Soul by the Sea")
    print(f"  Started: {now_str()}")
    print("=" * 60)

    conn = get_connection()
    if not conn:
        print("[ERROR] Could not connect to MySQL. Is flow_db running?")
        sys.exit(1)

    try:
        get_redis().ping()
        print("[OK] Redis connected.")
    except Exception as e:
        print(f"[WARN] Redis unavailable ({e}). Events will not be published.")

    branches   = seed_if_empty(conn)
    menu_items = get_menu_items(conn)

    print(f"[OK] {len(branches)} branch(es) loaded, {len(menu_items)} menu items loaded.")
    print("-" * 60)

    tick = 0
    while True:
        tick += 1
        branch = random.choice(branches)

        action_name, action_fn = random.choice(ACTION_POOL)

        try:
            if action_name == "create_order":
                action_fn(conn, branch, menu_items)
            else:
                action_fn(conn, branch)
        except Exception as e:
            print(f"[ERROR] {action_name} on branch {branch['branch_name']}: {e}")
            # reconnect on lost connection
            try:
                conn.ping(reconnect=True)
            except Exception:
                conn = get_connection()

        delay = random.uniform(1, 5)
        time.sleep(delay)


if __name__ == "__main__":
    main()
