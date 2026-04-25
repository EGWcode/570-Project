
"""
FLOW POS — Soul By The Sea
File: employee_ui.py

Run with:  python employee_ui.py

Database connections (fill in your credentials):
  SQL    → sqlite3  (or swap for mysql.connector / psycopg2)
  NoSQL  → pymongo  (MongoDB)

Each section that touches the database is clearly marked with:
  # ── SQL:   what table / query is used
  # ── MONGO: what collection is used
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import sqlite3
from datetime import date

# ── Try MongoDB (optional — app still runs without it) ─────────────────────
try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE CONNECTIONS
#  Replace paths/URIs with your actual credentials
# ══════════════════════════════════════════════════════════════════════════════

SQL_DB_PATH   = "restaurant.db"       # your SQLite file path
MONGO_URI     = "mongodb://localhost:27017/"
MONGO_DB_NAME = "flow_db"

def get_sql_conn():
    """Returns a SQLite connection. Swap for MySQL/Postgres if needed."""
    conn = sqlite3.connect(SQL_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_mongo_db():
    """Returns MongoDB database object."""
    if not MONGO_AVAILABLE:
        return None
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB_NAME]

# ── Load table statuses from MongoDB (table_availability collection) ───────
def load_table_statuses():
    """
    MONGO: collection = table_availability
    Documents: { table_id: "T-01", status: "available" }
    Returns dict: { "T-01": "available", ... }
    """
    try:
        db = get_mongo_db()
        if db is None:
            raise Exception("No MongoDB")
        statuses = {}
        for doc in db.table_availability.find({}, {"_id": 0}):
            statuses[doc["table_id"]] = doc.get("status", "available")
        return statuses
    except Exception:
        # Fallback mock data if MongoDB not connected
        mock = ["available","occupied","reserved","dirty","available",
                "available","occupied","available","reserved","occupied",
                "available","available","occupied","available","available",
                "occupied","dirty","available","available","available",
                "available","available","available","available"]
        return {t["id"]: mock[i] for i, t in enumerate(TABLE_LAYOUT)}

def update_table_status_db(table_id, status):
    """
    MONGO: collection = table_availability
    Updates or inserts status for a table.
    """
    try:
        db = get_mongo_db()
        if db is None:
            return
        db.table_availability.update_one(
            {"table_id": table_id},
            {"$set": {"status": status}},
            upsert=True
        )
    except Exception:
        pass  # graceful fallback

def load_todays_reservations():
    """
    SQL: SELECT from Reservation table WHERE date = today
    Returns list of dicts: [{ name, party_size, time, table_id }]
    """
    try:
        conn = get_sql_conn()
        today = date.today().isoformat()
        rows = conn.execute(
            "SELECT * FROM Reservation WHERE DATE(reservation_date) = ?", (today,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        # Fallback mock reservations
        return [
            {"customer_name": "Johnson, M.", "party_size": 4, "reservation_time": "6:00 PM", "table_id": "T-03"},
            {"customer_name": "Williams, T.", "party_size": 2, "reservation_time": "7:30 PM", "table_id": "RT-02"},
            {"customer_name": "Davis, K.",    "party_size": 6, "reservation_time": "8:00 PM", "table_id": "T-01"},
        ]

def save_order_to_db(table_id, employee_id, branch_id, items):
    """
    SQL: INSERT into Orders table, then INSERT each item into Order_Items table
    Returns order_id
    """
    try:
        conn = get_sql_conn()
        total = sum(i["price"] * i["qty"] for i in items)
        cur = conn.execute(
            "INSERT INTO Orders (table_id, employee_id, branch_id, status, total) VALUES (?,?,?,?,?)",
            (table_id, employee_id, branch_id, "pending", total)
        )
        order_id = cur.lastrowid
        for item in items:
            conn.execute(
                "INSERT INTO Order_Items (order_id, item_name, quantity, price) VALUES (?,?,?,?)",
                (order_id, item["name"], item["qty"], item["price"])
            )
        conn.commit()
        conn.close()
        return order_id
    except Exception as e:
        print(f"DB error saving order: {e}")
        return None

def save_payment_to_db(order_id, payment_type, tip_amount, total):
    """
    SQL: INSERT into Payment table, UPDATE Orders status = 'completed'
    """
    try:
        conn = get_sql_conn()
        conn.execute(
            "INSERT INTO Payment (order_id, payment_type, tip_amount, total_amount) VALUES (?,?,?,?)",
            (order_id, payment_type, tip_amount, total)
        )
        conn.execute("UPDATE Orders SET status='completed' WHERE id=?", (order_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB error saving payment: {e}")

def load_menu_from_db():
    """
    MONGO: collection = menu_items
    Returns list: [{ item_id, name, category, price }]
    """
    try:
        db = get_mongo_db()
        if db is None:
            raise Exception("No MongoDB")
        items = list(db.menu_items.find({"available": True}, {"_id": 0}))
        return items
    except Exception:
        # Fallback mock menu — Soul By The Sea themed
        return [
            {"item_id":"M01","name":"Crab Cakes",       "category":"Starters", "price":14.99},
            {"item_id":"M02","name":"Shrimp Cocktail",  "category":"Starters", "price":12.99},
            {"item_id":"M03","name":"Clam Chowder",     "category":"Starters", "price":10.99},
            {"item_id":"M04","name":"Lobster Bisque",   "category":"Starters", "price":13.99},
            {"item_id":"M05","name":"Grilled Snapper",  "category":"Mains",    "price":28.99},
            {"item_id":"M06","name":"Shrimp & Grits",   "category":"Mains",    "price":24.99},
            {"item_id":"M07","name":"Seafood Platter",  "category":"Mains",    "price":38.99},
            {"item_id":"M08","name":"Blackened Salmon", "category":"Mains",    "price":26.99},
            {"item_id":"M09","name":"Crab Pasta",       "category":"Mains",    "price":22.99},
            {"item_id":"M10","name":"Key Lime Pie",     "category":"Desserts", "price": 8.99},
            {"item_id":"M11","name":"Bread Pudding",    "category":"Desserts", "price": 7.99},
            {"item_id":"M12","name":"Sweet Potato Pie", "category":"Desserts", "price": 7.99},
            {"item_id":"M13","name":"Sweet Tea",        "category":"Drinks",   "price": 3.99},
            {"item_id":"M14","name":"Lemonade",         "category":"Drinks",   "price": 3.99},
            {"item_id":"M15","name":"House Wine",       "category":"Drinks",   "price": 8.99},
        ]

# ══════════════════════════════════════════════════════════════════════════════
#  STATIC TABLE LAYOUT
#  Positions are pixel coordinates on the canvas (set once by manager)
# ══════════════════════════════════════════════════════════════════════════════

TABLE_LAYOUT = [
    # Booths — left zone
    {"id":"BT-1","type":"rect", "x":30,  "y":55,  "w":80,"h":52,"seats":2,"zone":"Booth"},
    {"id":"BT-2","type":"rect", "x":30,  "y":118, "w":80,"h":52,"seats":2,"zone":"Booth"},
    {"id":"BT-3","type":"rect", "x":30,  "y":181, "w":80,"h":52,"seats":2,"zone":"Booth"},
    {"id":"BT-4","type":"rect", "x":30,  "y":244, "w":80,"h":52,"seats":2,"zone":"Booth"},
    {"id":"BT-5","type":"rect", "x":30,  "y":307, "w":80,"h":52,"seats":2,"zone":"Booth"},
    {"id":"BT-6","type":"rect", "x":125, "y":72,  "w":90,"h":52,"seats":4,"zone":"Booth"},
    {"id":"BT-7","type":"rect", "x":125, "y":140, "w":90,"h":52,"seats":4,"zone":"Booth"},
    {"id":"BT-8","type":"rect", "x":125, "y":208, "w":90,"h":52,"seats":4,"zone":"Booth"},
    {"id":"BT-9","type":"rect", "x":125, "y":276, "w":90,"h":52,"seats":4,"zone":"Booth"},
    # Main floor — center zone
    {"id":"T-01","type":"rect", "x":240, "y":58,  "w":92,"h":58,"seats":6,"zone":"Main"},
    {"id":"T-02","type":"rect", "x":240, "y":132, "w":92,"h":58,"seats":4,"zone":"Main"},
    {"id":"T-03","type":"rect", "x":240, "y":206, "w":92,"h":58,"seats":4,"zone":"Main"},
    {"id":"T-04","type":"rect", "x":240, "y":280, "w":92,"h":58,"seats":4,"zone":"Main"},
    {"id":"T-05","type":"rect", "x":240, "y":354, "w":92,"h":58,"seats":4,"zone":"Main"},
    # Round tables — right zone
    {"id":"RT-01","type":"oval","x":450,"y":60,  "r":48,"seats":4,"zone":"Round"},
    {"id":"RT-02","type":"oval","x":570,"y":60,  "r":48,"seats":4,"zone":"Round"},
    {"id":"RT-03","type":"oval","x":450,"y":175, "r":48,"seats":6,"zone":"Round"},
    {"id":"RT-04","type":"oval","x":570,"y":175, "r":48,"seats":6,"zone":"Round"},
    # Bar stools — bottom right
    {"id":"B-1","type":"bar","x":435,"y":300,"r":22,"seats":1,"zone":"Bar"},
    {"id":"B-2","type":"bar","x":478,"y":300,"r":22,"seats":1,"zone":"Bar"},
    {"id":"B-3","type":"bar","x":521,"y":300,"r":22,"seats":1,"zone":"Bar"},
    {"id":"B-4","type":"bar","x":564,"y":300,"r":22,"seats":1,"zone":"Bar"},
    {"id":"B-5","type":"bar","x":607,"y":300,"r":22,"seats":1,"zone":"Bar"},
]

# Status colors: (fill, outline, text)
STATUS_COLORS = {
    "available": ("#0F2419", "#3FB950", "#7EE89A"),
    "occupied":  ("#2D1117", "#F85149", "#FF9491"),
    "reserved":  ("#1A1030", "#A371F7", "#C9A8FF"),
    "dirty":     ("#2A1F00", "#E3B341", "#F0D080"),
}
STATUS_LABELS = {
    "available": "Available",
    "occupied":  "Occupied",
    "reserved":  "Reserved",
    "dirty":     "Needs Clean",
}

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

class FLOWApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FLOW POS — Soul By The Sea")
        self.configure(bg="#0D1117")
        self.attributes("-zoomed", True)         # open maximised; use fullscreen on Mac

        # App state
        self.table_statuses  = {}     # loaded from MongoDB
        self.orders          = {}     # { table_id: [{ name, price, qty }] }
        self.selected_table  = None
        self.current_order_items = [] # items shown in order panel
        self.menu_items      = []     # loaded from MongoDB
        self.reservations    = []     # loaded from SQL
        self.active_menu_cat = "All"
        self.pay_method      = tk.StringVar(value="")
        self.tip_pct         = tk.IntVar(value=0)

        # Logged-in employee info (load from SQL Employee table in production)
        self.employee_name   = "James Carter"
        self.branch_name     = "Main Branch"
        self.employee_id     = 1
        self.branch_id       = 1

        self._build_ui()
        self._load_data()

    # ── Load data from databases ───────────────────────────────────────────
    def _load_data(self):
        self.table_statuses = load_table_statuses()
        self.menu_items     = load_menu_from_db()
        self.reservations   = load_todays_reservations()
        # Build reservation lookup: table_id → reservation info
        self.res_lookup = {}
        for r in self.reservations:
            tid = r.get("table_id") or r.get("table_id")
            if tid:
                name  = r.get("customer_name","Guest")
                time_ = r.get("reservation_time","")
                size  = r.get("party_size","")
                self.res_lookup[tid] = f"{name}  ·  {time_}  ·  Party {size}"
        self._refresh_floor()
        self._refresh_sidebar()

    # ── Build UI ───────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── TOP BAR ───────────────────────────────────────────────────────
        topbar = tk.Frame(self, bg="#161B22", height=50)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="Soul By The Sea", bg="#161B22",
                 fg="#D4A843", font=("Segoe UI", 15, "bold")).pack(side="left", padx=(16,4), pady=12)
        tk.Label(topbar, text="FLOW POS · Employee Floor Plan", bg="#161B22",
                 fg="#8B949E", font=("Segoe UI", 9)).pack(side="left", pady=12)

        tk.Label(topbar, text=f"Staff: {self.employee_name}  ·  {self.branch_name}",
                 bg="#161B22", fg="#8B949E", font=("Segoe UI", 10)).pack(side="right", padx=16)
        tk.Label(topbar, text=date.today().strftime("%A, %B %d %Y"),
                 bg="#161B22", fg="#8B949E", font=("Segoe UI", 10)).pack(side="right", padx=8)

        # ── MAIN BODY ─────────────────────────────────────────────────────
        body = tk.Frame(self, bg="#0D1117")
        body.pack(fill="both", expand=True)

        # ── SIDEBAR ───────────────────────────────────────────────────────
        self.sidebar = tk.Frame(body, bg="#161B22", width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Status legend
        tk.Label(self.sidebar, text="TABLE STATUS · MongoDB",
                 bg="#161B22", fg="#444D56", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(12,4))
        self.count_labels = {}
        for key, label in STATUS_LABELS.items():
            row = tk.Frame(self.sidebar, bg="#161B22")
            row.pack(fill="x", padx=10, pady=1)
            dot_color = STATUS_COLORS[key][1]
            tk.Canvas(row, width=10, height=10, bg="#161B22", highlightthickness=0).pack(side="left", padx=(2,6))
            c = row.winfo_children()[0]
            c.create_oval(1,1,9,9, fill=dot_color, outline=dot_color)
            tk.Label(row, text=label, bg="#161B22", fg="#E6EDF3",
                     font=("Segoe UI", 10)).pack(side="left")
            cnt = tk.Label(row, text="0", bg="#161B22", fg="#8B949E", font=("Segoe UI", 9))
            cnt.pack(side="right", padx=4)
            self.count_labels[key] = cnt

        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", pady=8)

        # Reservations
        tk.Label(self.sidebar, text="TODAY'S RESERVATIONS · SQL",
                 bg="#161B22", fg="#444D56", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(0,4))
        self.res_frame = tk.Frame(self.sidebar, bg="#161B22")
        self.res_frame.pack(fill="x", padx=8)

        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", pady=8)

        # Active orders
        tk.Label(self.sidebar, text="ACTIVE ORDERS · SQL",
                 bg="#161B22", fg="#444D56", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(0,4))
        self.orders_frame = tk.Frame(self.sidebar, bg="#161B22")
        self.orders_frame.pack(fill="both", expand=True, padx=8)

        # ── FLOOR CANVAS ──────────────────────────────────────────────────
        canvas_frame = tk.Frame(body, bg="#0D1117")
        canvas_frame.pack(side="left", fill="both", expand=True, padx=16, pady=16)

        # Zone labels above canvas
        zones = tk.Frame(canvas_frame, bg="#0D1117")
        zones.pack(fill="x", pady=(0,4))
        for zone_label, anchor in [("BOOTHS","w"),("MAIN FLOOR","center"),("ROUND TABLES","e")]:
            tk.Label(zones, text=zone_label, bg="#0D1117", fg="#30363D",
                     font=("Segoe UI", 8, "bold")).pack(side="left", expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="#161B22", highlightthickness=1,
                                highlightbackground="#30363D", cursor="hand2")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._refresh_floor())

        # ── ORDER PANEL (right side) ───────────────────────────────────────
        self.panel = tk.Frame(body, bg="#161B22", width=320)
        self.panel.pack(side="right", fill="y")
        self.panel.pack_propagate(False)

        self._build_order_panel()

    def _build_order_panel(self):
        for w in self.panel.winfo_children():
            w.destroy()

        if not self.selected_table:
            tk.Label(self.panel, text="Select a table\nto manage an order",
                     bg="#161B22", fg="#444D56", font=("Segoe UI", 13),
                     justify="center").pack(expand=True)
            return

        t = next((x for x in TABLE_LAYOUT if x["id"] == self.selected_table), None)
        st = self.table_statuses.get(self.selected_table, "available")
        col = STATUS_COLORS[st]

        # Panel header
        hdr = tk.Frame(self.panel, bg="#1C2128")
        hdr.pack(fill="x")
        tk.Label(hdr, text=self.selected_table, bg="#1C2128", fg="#D4A843",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=14, pady=10)
        info = f"{t['seats']} seats · {t['zone']} Zone" if t else ""
        tk.Label(hdr, text=info, bg="#1C2128", fg="#8B949E",
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Button(hdr, text="✕", bg="#1C2128", fg="#8B949E", bd=0,
                  font=("Segoe UI", 12), cursor="hand2",
                  command=self._close_panel).pack(side="right", padx=10)

        # Reservation banner
        if self.selected_table in self.res_lookup:
            rb = tk.Label(self.panel, text=f"📋  {self.res_lookup[self.selected_table]}",
                          bg="#1A1030", fg="#A371F7", font=("Segoe UI", 9),
                          wraplength=290, justify="left", pady=6)
            rb.pack(fill="x", padx=8, pady=(4,0))

        # Status buttons
        sf = tk.Frame(self.panel, bg="#161B22")
        sf.pack(fill="x", padx=8, pady=6)
        tk.Label(sf, text="Status:", bg="#161B22", fg="#8B949E",
                 font=("Segoe UI", 9)).pack(side="left", padx=(0,6))
        for key, label in STATUS_LABELS.items():
            c = STATUS_COLORS[key]
            active = (key == st)
            btn = tk.Button(sf, text=label,
                            bg=c[0] if active else "#1C2128",
                            fg=c[2], font=("Segoe UI", 8, "bold"),
                            relief="flat", bd=0, padx=6, pady=3,
                            cursor="hand2",
                            command=lambda k=key: self._set_status(k))
            btn.pack(side="left", padx=2)

        ttk.Separator(self.panel, orient="horizontal").pack(fill="x", pady=4)

        # Tab bar
        self.panel_tab = tk.StringVar(value="add")
        tab_bar = tk.Frame(self.panel, bg="#1C2128")
        tab_bar.pack(fill="x")
        for tab_id, tab_name in [("add","Add Items"),("order","Order"),("payment","Payment")]:
            tk.Radiobutton(tab_bar, text=tab_name, variable=self.panel_tab,
                           value=tab_id, bg="#1C2128", fg="#E6EDF3",
                           selectcolor="#0D1117", activebackground="#1C2128",
                           font=("Segoe UI", 10, "bold"),
                           indicatoron=False, relief="flat", padx=8, pady=6,
                           cursor="hand2",
                           command=self._switch_panel_tab).pack(side="left", expand=True, fill="x")

        # Tab content area
        self.tab_content = tk.Frame(self.panel, bg="#161B22")
        self.tab_content.pack(fill="both", expand=True)

        self._switch_panel_tab()

        # Footer buttons
        foot = tk.Frame(self.panel, bg="#161B22")
        foot.pack(fill="x", padx=8, pady=8)
        tk.Button(foot, text="Clear Table", bg="#2D1117", fg="#F85149",
                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                  padx=10, pady=8, cursor="hand2",
                  command=self._clear_table).pack(side="left", fill="x", expand=True, padx=(0,4))
        self.send_btn = tk.Button(foot, text="No Items", bg="#1C2128", fg="#444D56",
                                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                                  padx=10, pady=8, cursor="hand2",
                                  command=self._send_order)
        self.send_btn.pack(side="left", fill="x", expand=True)
        self._update_send_btn()

    def _switch_panel_tab(self):
        for w in self.tab_content.winfo_children():
            w.destroy()
        tab = self.panel_tab.get()
        if tab == "add":    self._build_add_tab()
        elif tab == "order": self._build_order_tab()
        elif tab == "payment": self._build_payment_tab()

    def _build_add_tab(self):
        f = self.tab_content

        # Category filter
        cats = ["All","Starters","Mains","Desserts","Drinks"]
        cat_bar = tk.Frame(f, bg="#161B22")
        cat_bar.pack(fill="x", padx=6, pady=6)
        self.cat_var = tk.StringVar(value=self.active_menu_cat)
        for c in cats:
            btn = tk.Radiobutton(cat_bar, text=c, variable=self.cat_var,
                                 value=c, bg="#1C2128", fg="#8B949E",
                                 selectcolor="#D4A843", activebackground="#1C2128",
                                 font=("Segoe UI", 9, "bold"), indicatoron=False,
                                 relief="flat", padx=6, pady=3, cursor="hand2",
                                 command=lambda: self._filter_menu())
            btn.pack(side="left", padx=2)

        # Scrollable menu list
        container = tk.Frame(f, bg="#161B22")
        container.pack(fill="both", expand=True, padx=6)
        canvas = tk.Canvas(container, bg="#161B22", highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg="#161B22")
        canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        order = self.orders.get(self.selected_table, [])
        items = self.menu_items if self.active_menu_cat == "All" else [m for m in self.menu_items if m["category"] == self.active_menu_cat]

        for item in items:
            in_order = next((x for x in order if x["name"] == item["name"]), None)
            bg = "#0F2419" if in_order else "#1C2128"
            row = tk.Frame(inner, bg=bg, pady=6, padx=8)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=item["name"], bg=bg, fg="#E6EDF3",
                     font=("Segoe UI", 11, "bold")).pack(anchor="w")
            foot_row = tk.Frame(row, bg=bg)
            foot_row.pack(fill="x")
            tk.Label(foot_row, text=item["category"], bg=bg, fg="#8B949E",
                     font=("Segoe UI", 9)).pack(side="left")
            tk.Label(foot_row, text=f"${item['price']:.2f}", bg=bg, fg="#D4A843",
                     font=("Segoe UI", 11, "bold")).pack(side="right")
            if in_order:
                tk.Label(row, text=f"× {in_order['qty']} in order", bg=bg,
                         fg="#3FB950", font=("Segoe UI", 9)).pack(anchor="w")
            row.bind("<Button-1>", lambda e, i=item: self._add_item(i))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, i=item: self._add_item(i))

    def _filter_menu(self):
        self.active_menu_cat = self.cat_var.get()
        self._switch_panel_tab()

    def _build_order_tab(self):
        f = self.tab_content
        order = self.orders.get(self.selected_table, [])
        if not order:
            tk.Label(f, text="No items added yet.\nGo to 'Add Items' to start.",
                     bg="#161B22", fg="#444D56", font=("Segoe UI", 11),
                     justify="center").pack(expand=True)
            return

        container = tk.Frame(f, bg="#161B22")
        container.pack(fill="both", expand=True, padx=8, pady=6)
        canvas = tk.Canvas(container, bg="#161B22", highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg="#161B22")
        canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        total = 0
        for item in order:
            row = tk.Frame(inner, bg="#1C2128", pady=6, padx=8)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=item["name"], bg="#1C2128", fg="#E6EDF3",
                     font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", columnspan=3)
            tk.Label(row, text=f"${item['price']:.2f} each", bg="#1C2128", fg="#8B949E",
                     font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w")
            tk.Button(row, text="−", bg="#30363D", fg="#E6EDF3", font=("Segoe UI", 12),
                      relief="flat", bd=0, width=2, cursor="hand2",
                      command=lambda i=item: self._change_qty(i, -1)).grid(row=1, column=1, padx=4)
            tk.Label(row, text=str(item["qty"]), bg="#1C2128", fg="#E6EDF3",
                     font=("Segoe UI", 12, "bold"), width=2).grid(row=1, column=2)
            tk.Button(row, text="+", bg="#30363D", fg="#E6EDF3", font=("Segoe UI", 12),
                      relief="flat", bd=0, width=2, cursor="hand2",
                      command=lambda i=item: self._change_qty(i, 1)).grid(row=1, column=3, padx=4)
            item_total = item["price"] * item["qty"]
            total += item_total
            tk.Label(row, text=f"${item_total:.2f}", bg="#1C2128", fg="#D4A843",
                     font=("Segoe UI", 11, "bold")).grid(row=1, column=4, sticky="e", padx=(8,0))
            row.columnconfigure(0, weight=1)

        total_row = tk.Frame(inner, bg="#161B22")
        total_row.pack(fill="x", pady=(8,0))
        tk.Label(total_row, text="Subtotal", bg="#161B22", fg="#E6EDF3",
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(total_row, text=f"${total:.2f}", bg="#161B22", fg="#D4A843",
                 font=("Segoe UI", 14, "bold")).pack(side="right")

    def _build_payment_tab(self):
        f = self.tab_content
        order = self.orders.get(self.selected_table, [])
        if not order:
            tk.Label(f, text="No order to pay.\nAdd items first.",
                     bg="#161B22", fg="#444D56", font=("Segoe UI", 11),
                     justify="center").pack(expand=True)
            return

        sub = sum(i["price"] * i["qty"] for i in order)
        tip_pct = self.tip_pct.get()
        tip_amt = sub * (tip_pct / 100)
        grand   = sub + tip_amt

        scr = tk.Frame(f, bg="#161B22")
        scr.pack(fill="both", expand=True, padx=10, pady=8)

        # Subtotal display
        tk.Label(scr, text="PAYMENT · SQL Payment Table", bg="#161B22", fg="#444D56",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0,6))
        row = tk.Frame(scr, bg="#1C2128", pady=6, padx=10)
        row.pack(fill="x", pady=2)
        tk.Label(row, text="Subtotal", bg="#1C2128", fg="#8B949E", font=("Segoe UI",10)).pack(side="left")
        tk.Label(row, text=f"${sub:.2f}", bg="#1C2128", fg="#E6EDF3", font=("Segoe UI",12,"bold")).pack(side="right")

        # Payment method
        tk.Label(scr, text="Payment Method", bg="#161B22", fg="#8B949E",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10,4))
        methods_f = tk.Frame(scr, bg="#161B22")
        methods_f.pack(fill="x")
        for m in ["Cash","Credit Card","Debit Card","Mobile Pay"]:
            tk.Radiobutton(methods_f, text=m, variable=self.pay_method, value=m,
                           bg="#1C2128", fg="#E6EDF3", selectcolor="#D4A843",
                           activebackground="#1C2128", font=("Segoe UI",10),
                           indicatoron=False, relief="flat", padx=8, pady=6,
                           cursor="hand2",
                           command=lambda: self._build_payment_tab_refresh()).pack(side="left", padx=2, pady=2)

        # Tip
        tk.Label(scr, text="Tip", bg="#161B22", fg="#8B949E",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10,4))
        tip_f = tk.Frame(scr, bg="#161B22")
        tip_f.pack(fill="x")
        for p in [0,15,18,20,25]:
            lbl = "No Tip" if p == 0 else f"{p}%"
            tk.Radiobutton(tip_f, text=lbl, variable=self.tip_pct, value=p,
                           bg="#1C2128", fg="#E6EDF3", selectcolor="#3FB950",
                           activebackground="#1C2128", font=("Segoe UI",10),
                           indicatoron=False, relief="flat", padx=6, pady=5,
                           cursor="hand2",
                           command=lambda: self._build_payment_tab_refresh()).pack(side="left", padx=2)

        # Total
        tot_row = tk.Frame(scr, bg="#1C2128", pady=8, padx=10)
        tot_row.pack(fill="x", pady=(10,6))
        tk.Label(tot_row, text=f"Tip ({tip_pct}%)", bg="#1C2128", fg="#8B949E", font=("Segoe UI",10)).pack(side="left")
        tk.Label(tot_row, text=f"${tip_amt:.2f}", bg="#1C2128", fg="#E6EDF3", font=("Segoe UI",10)).pack(side="right")

        grand_row = tk.Frame(scr, bg="#1C2128", pady=8, padx=10)
        grand_row.pack(fill="x", pady=2)
        tk.Label(grand_row, text="Total Due", bg="#1C2128", fg="#E6EDF3", font=("Segoe UI",13,"bold")).pack(side="left")
        tk.Label(grand_row, text=f"${grand:.2f}", bg="#1C2128", fg="#D4A843", font=("Segoe UI",15,"bold")).pack(side="right")

        pay_lbl = f"Confirm {self.pay_method.get()} — ${grand:.2f}" if self.pay_method.get() else "Select payment method"
        bg_c = "#0F2419" if self.pay_method.get() else "#1C2128"
        fg_c = "#3FB950" if self.pay_method.get() else "#444D56"
        tk.Button(scr, text=pay_lbl, bg=bg_c, fg=fg_c,
                  font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
                  pady=10, cursor="hand2" if self.pay_method.get() else "arrow",
                  command=lambda g=grand, t=tip_amt: self._confirm_payment(g, t) if self.pay_method.get() else None
                  ).pack(fill="x", pady=(8,0))

    def _build_payment_tab_refresh(self):
        """Called when tip/method changes — rebuilds payment tab."""
        self.panel_tab.set("payment")
        self._switch_panel_tab()

    # ── Floor canvas drawing ───────────────────────────────────────────────
    def _refresh_floor(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10 or h < 10:
            return

        # Zone backgrounds
        c.create_rectangle(8,8,226,h-8, fill="#1C2128", outline="#30363D", width=1)
        c.create_rectangle(232,8,452,h-8, fill="#1C2128", outline="#30363D", width=1)
        c.create_rectangle(458,8,w-8,int(h*0.68), fill="#1C2128", outline="#30363D", width=1)
        c.create_rectangle(458,int(h*0.7),w-8,h-8, fill="#12161C", outline="#30363D", width=1)
        c.create_text(117,18, text="BOOTHS", fill="#30363D", font=("Segoe UI",8,"bold"))
        c.create_text(342,18, text="MAIN FLOOR", fill="#30363D", font=("Segoe UI",8,"bold"))
        c.create_text(int((458+w)/2),18, text="ROUND TABLES", fill="#30363D", font=("Segoe UI",8,"bold"))
        c.create_text(int((458+w)/2),int(h*0.7)+10, text="BAR SEATING", fill="#30363D", font=("Segoe UI",8,"bold"))

        for t in TABLE_LAYOUT:
            self._draw_table(c, t, w, h)

    def _draw_table(self, c, t, cw, ch):
        tid   = t["id"]
        st    = self.table_statuses.get(tid, "available")
        fill, outline, fg = STATUS_COLORS[st]
        has_order = bool(self.orders.get(tid))
        sel = (tid == self.selected_table)

        # Scale factor so layout fits canvas
        sx = cw / 700
        sy = ch / 430

        def sc(v, axis):
            return int(v * (sx if axis == "x" else sy))

        if t["type"] == "oval" or t["type"] == "bar":
            rx = t["r"] * sx
            ry = t["r"] * sy
            cx, cy = sc(t["x"], "x"), sc(t["y"], "y")
            if has_order:
                c.create_oval(cx-rx-5, cy-ry-5, cx+rx+5, cy+ry+5,
                              outline="#D4A843", width=2, dash=(4,3))
            if sel:
                c.create_oval(cx-rx-3, cy-ry-3, cx+rx+3, cy+ry+3,
                              outline="#D4A843", width=3)
            oid = c.create_oval(cx-rx, cy-ry, cx+rx, cy+ry,
                                fill=fill, outline=outline, width=2)
            tid_lbl = c.create_text(cx, cy, text=tid, fill=fg,
                                    font=("Segoe UI", 8 if t["type"]=="bar" else 9, "bold"))
            if t["type"] != "bar":
                c.create_text(cx, cy+int(ry)-10, text=f"{t['seats']}p",
                              fill=fg, font=("Segoe UI", 7))
            c.tag_bind(oid,     "<Button-1>", lambda e, i=tid: self._on_table_click(i))
            c.tag_bind(tid_lbl, "<Button-1>", lambda e, i=tid: self._on_table_click(i))
        else:
            x1 = sc(t["x"], "x"); y1 = sc(t["y"], "y")
            x2 = x1 + sc(t["w"], "x"); y2 = y1 + sc(t["h"], "y")
            if has_order:
                c.create_rectangle(x1-4, y1-4, x2+4, y2+4,
                                   outline="#D4A843", width=2, dash=(4,3))
            if sel:
                c.create_rectangle(x1-3, y1-3, x2+3, y2+3,
                                   outline="#D4A843", width=3)
            rid = c.create_rectangle(x1, y1, x2, y2,
                                     fill=fill, outline=outline, width=2)
            mid_x = (x1+x2)//2; mid_y = (y1+y2)//2
            n1 = c.create_text(mid_x, mid_y-6, text=tid, fill=fg,
                                font=("Segoe UI", 9, "bold"))
            n2 = c.create_text(mid_x, mid_y+8, text=f"{t['seats']} seats", fill=fg,
                                font=("Segoe UI", 7))
            for tag in (rid, n1, n2):
                c.tag_bind(tag, "<Button-1>", lambda e, i=tid: self._on_table_click(i))

    # ── Sidebar refresh ────────────────────────────────────────────────────
    def _refresh_sidebar(self):
        for key, lbl in self.count_labels.items():
            cnt = sum(1 for t in TABLE_LAYOUT if self.table_statuses.get(t["id"]) == key)
            lbl.config(text=str(cnt))

        for w in self.res_frame.winfo_children():
            w.destroy()
        for r in self.reservations:
            name  = r.get("customer_name","Guest")
            time_ = r.get("reservation_time","")
            size  = r.get("party_size","")
            f = tk.Frame(self.res_frame, bg="#1C2128", pady=4, padx=8)
            f.pack(fill="x", pady=2)
            top = tk.Frame(f, bg="#1C2128")
            top.pack(fill="x")
            tk.Label(top, text=name, bg="#1C2128", fg="#E6EDF3",
                     font=("Segoe UI",10,"bold")).pack(side="left")
            tk.Label(top, text=time_, bg="#1C2128", fg="#D4A843",
                     font=("Segoe UI",9)).pack(side="right")
            tk.Label(f, text=f"Party of {size}", bg="#1C2128", fg="#8B949E",
                     font=("Segoe UI",9)).pack(anchor="w")

        for w in self.orders_frame.winfo_children():
            w.destroy()
        active = [(tid, items) for tid, items in self.orders.items() if items]
        if not active:
            tk.Label(self.orders_frame, text="No active orders", bg="#161B22",
                     fg="#444D56", font=("Segoe UI",10,"italic")).pack(anchor="w", pady=4)
        for tid, items in active:
            total = sum(i["price"]*i["qty"] for i in items)
            f = tk.Frame(self.orders_frame, bg="#1C2128", pady=4, padx=8, cursor="hand2")
            f.pack(fill="x", pady=2)
            top = tk.Frame(f, bg="#1C2128")
            top.pack(fill="x")
            tk.Label(top, text=tid, bg="#1C2128", fg="#D4A843",
                     font=("Segoe UI",10,"bold")).pack(side="left")
            tk.Label(top, text=f"${total:.2f}", bg="#1C2128", fg="#3FB950",
                     font=("Segoe UI",10,"bold")).pack(side="right")
            prev = ", ".join(f"{i['qty']}× {i['name']}" for i in items)
            tk.Label(f, text=prev, bg="#1C2128", fg="#8B949E",
                     font=("Segoe UI",9), wraplength=160).pack(anchor="w")
            f.bind("<Button-1>", lambda e, i=tid: self._on_table_click(i))

    # ── Actions ────────────────────────────────────────────────────────────
    def _on_table_click(self, table_id):
        self.selected_table  = table_id
        self.active_menu_cat = "All"
        self.pay_method.set("")
        self.tip_pct.set(0)
        self._build_order_panel()
        self._refresh_floor()

    def _close_panel(self):
        self.selected_table = None
        self._build_order_panel()
        self._refresh_floor()

    def _set_status(self, status):
        self.table_statuses[self.selected_table] = status
        update_table_status_db(self.selected_table, status)  # → MongoDB
        self._refresh_floor()
        self._refresh_sidebar()
        self._build_order_panel()

    def _add_item(self, item):
        if self.selected_table not in self.orders:
            self.orders[self.selected_table] = []
        order = self.orders[self.selected_table]
        ex = next((x for x in order if x["name"] == item["name"]), None)
        if ex:
            ex["qty"] += 1
        else:
            order.append({"name": item["name"], "price": item["price"],
                          "qty": 1, "item_id": item.get("item_id","")})
        self._switch_panel_tab()
        self._refresh_floor()
        self._refresh_sidebar()

    def _change_qty(self, item, delta):
        order = self.orders.get(self.selected_table, [])
        ex = next((x for x in order if x["name"] == item["name"]), None)
        if ex:
            ex["qty"] += delta
            if ex["qty"] <= 0:
                self.orders[self.selected_table].remove(ex)
        self._switch_panel_tab()
        self._refresh_floor()
        self._refresh_sidebar()

    def _update_send_btn(self):
        if not hasattr(self, "send_btn"):
            return
        order = self.orders.get(self.selected_table, [])
        total = sum(i["price"]*i["qty"] for i in order)
        if order:
            self.send_btn.config(text=f"Send to Kitchen — ${total:.2f}",
                                 bg="#1C2128", fg="#D4A843")
        else:
            self.send_btn.config(text="No Items", bg="#1C2128", fg="#444D56")

    def _send_order(self):
        order = self.orders.get(self.selected_table, [])
        if not order:
            return
        # SQL: INSERT into Orders + Order_Items tables
        order_id = save_order_to_db(self.selected_table, self.employee_id, self.branch_id, order)
        # MongoDB: update table_availability status → "occupied"
        self.table_statuses[self.selected_table] = "occupied"
        update_table_status_db(self.selected_table, "occupied")
        messagebox.showinfo("Order Sent", f"Order sent to kitchen!\nTable: {self.selected_table}\nOrder ID: {order_id or 'N/A'}")
        self.selected_table = None
        self._build_order_panel()
        self._refresh_floor()
        self._refresh_sidebar()

    def _confirm_payment(self, grand, tip_amt):
        order = self.orders.get(self.selected_table, [])
        if not order or not self.pay_method.get():
            return
        # SQL: INSERT into Payment table, UPDATE Orders status
        save_payment_to_db(None, self.pay_method.get(), tip_amt, grand)
        # MongoDB: update table → "dirty"
        self.table_statuses[self.selected_table] = "dirty"
        update_table_status_db(self.selected_table, "dirty")
        self.orders[self.selected_table] = []
        messagebox.showinfo("Payment Confirmed",
                            f"Payment received!\nMethod: {self.pay_method.get()}\nTotal: ${grand:.2f}")
        self.selected_table = None
        self._build_order_panel()
        self._refresh_floor()
        self._refresh_sidebar()

    def _clear_table(self):
        self.orders[self.selected_table] = []
        self.table_statuses[self.selected_table] = "dirty"
        update_table_status_db(self.selected_table, "dirty")
        self._close_panel()
        self._refresh_floor()
        self._refresh_sidebar()


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = FLOWApp()
    app.mainloop()