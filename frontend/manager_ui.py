# manager_ui.py
# Created by Zoe Battle
#
#     FLOW - Enterprise Restaurant Management System
#
# This file is the Manager UI for the FLOW system. It gives the manager
# three tabs in a left sidebar:
#     - Inventory  (flow_db.inventory_item)
#     - Suppliers  (flow_db.supplier)
#     - Schedule   (flow_db.shift_schedule)
#
# Each tab tries to load its data from the flow_db MySQL database. If
# the DB is not running the screen still loads using sample rows, so
# you can see the layout without MySQL set up yet.


import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

# project root on path so config.* imports resolve from any working directory
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# try to grab the project DB connection
try:
    from config.db_config import get_connection
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False


# color palette -- matches the existing FLOW UI
BG_DARK    = "#0D1117"
BG_PANEL   = "#161B22"
BG_HOVER   = "#1F2530"
GOLD       = "#D4A843"
TEXT       = "#E6EDF3"
MUTED      = "#8B949E"
BORDER     = "#30363D"
RED        = "#F85149"


class ManagerUI(tk.Tk):

    # full-arg constructor
    def __init__(self, manager_name="Manager", branch_id=1):
        super().__init__()
        self.manager_name = manager_name
        self.branch_id    = branch_id

        self.title("FLOW - Manager")
        self.configure(bg=BG_DARK)
        self.geometry("1100x680")

        # try to maximize -- works on Windows + Linux
        try:
            self.state("zoomed")
        except tk.TclError:
            pass

        # which tab is currently showing
        self.current_tab   = "Inventory"
        self.content_frame = None

        # set up table styling once
        self.setup_table_style()

        self.build_ui()
        self.show_tab("Inventory")


    # partial-arg constructor convenience -- just a manager name, default branch
    @classmethod
    def with_name(cls, manager_name):
        return cls(manager_name=manager_name, branch_id=1)


    # makes the ttk.Treeview look like the rest of the dark UI
    def setup_table_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Flow.Treeview",
                        background=BG_PANEL,
                        foreground=TEXT,
                        fieldbackground=BG_PANEL,
                        rowheight=26,
                        bordercolor=BORDER,
                        borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("Flow.Treeview.Heading",
                        background=BG_HOVER,
                        foreground=GOLD,
                        font=("Segoe UI", 9, "bold"),
                        relief="flat")
        style.map("Flow.Treeview",
                  background=[("selected", "#2A3441")],
                  foreground=[("selected", TEXT)])


    # builds the top bar, sidebar, and main content area
    def build_ui(self):

        # top bar
        topbar = tk.Frame(self, bg=BG_PANEL, height=50)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="Soul By The Sea", bg=BG_PANEL,
                 fg=GOLD, font=("Segoe UI", 15, "bold")
                 ).pack(side="left", padx=(16, 4), pady=12)
        tk.Label(topbar, text="FLOW Manager", bg=BG_PANEL,
                 fg=MUTED, font=("Segoe UI", 9)
                 ).pack(side="left", pady=12)

        manager_text = "Manager: " + self.manager_name + "  ·  Branch #" + str(self.branch_id)
        tk.Label(topbar, text=manager_text, bg=BG_PANEL, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side="right", padx=16)
        tk.Label(topbar, text=date.today().strftime("%A, %B %d %Y"),
                 bg=BG_PANEL, fg=MUTED, font=("Segoe UI", 10)
                 ).pack(side="right", padx=8)

        # main body holds the sidebar and the right side content
        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        # sidebar
        self.sidebar = tk.Frame(body, bg=BG_PANEL, width=180)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="MENU", bg=BG_PANEL, fg="#444D56",
                 font=("Segoe UI", 8, "bold")
                 ).pack(anchor="w", padx=14, pady=(14, 8))

        # sidebar tab buttons
        self.tab_buttons = {}
        for label in ["Inventory", "Suppliers", "Schedule"]:
            btn = tk.Button(self.sidebar, text=label, bg=BG_PANEL, fg=TEXT,
                            activebackground=BG_HOVER, activeforeground=GOLD,
                            relief="flat", anchor="w", cursor="hand2",
                            font=("Segoe UI", 11),
                            command=lambda l=label: self.show_tab(l))
            btn.pack(fill="x", padx=8, pady=2, ipady=8)
            self.tab_buttons[label] = btn

        # spacer + sign out at the bottom
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", pady=10)
        sign_out = tk.Button(self.sidebar, text="Sign Out", bg=BG_PANEL, fg=MUTED,
                             activebackground=BG_HOVER, activeforeground=RED,
                             relief="flat", cursor="hand2",
                             font=("Segoe UI", 10),
                             command=self.sign_out)
        sign_out.pack(side="bottom", fill="x", padx=8, pady=10, ipady=6)

        # right-side main content area
        self.main_area = tk.Frame(body, bg=BG_DARK)
        self.main_area.pack(side="left", fill="both", expand=True)


    # switches what is shown in the main area
    def show_tab(self, tab_name):
        self.current_tab = tab_name

        # highlight the active button, dim the others
        for name in self.tab_buttons:
            btn = self.tab_buttons[name]
            if name == tab_name:
                btn.config(fg=GOLD, bg=BG_HOVER)
            else:
                btn.config(fg=TEXT, bg=BG_PANEL)

        # wipe the old content
        if self.content_frame is not None:
            self.content_frame.destroy()

        # build a fresh content frame
        self.content_frame = tk.Frame(self.main_area, bg=BG_DARK)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        if tab_name == "Inventory":
            self.build_inventory_view()
        elif tab_name == "Suppliers":
            self.build_supplier_view()
        elif tab_name == "Schedule":
            self.build_schedule_view()


    # ----------------------------------------------------------------------
    # Inventory tab
    # ----------------------------------------------------------------------
    def build_inventory_view(self):

        # header row -- title + refresh button
        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Inventory", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  flow_db.inventory_item", bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Inventory")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        # treeview table
        cols = ("id", "name", "qty", "unit", "reorder", "cost", "supplier")
        tree = ttk.Treeview(self.content_frame, columns=cols, show="headings",
                            style="Flow.Treeview", height=18)

        col_setup = [
            ("id",       "ID",          50),
            ("name",     "Item",        220),
            ("qty",      "Qty",         70),
            ("unit",     "Unit",        70),
            ("reorder",  "Reorder Lvl", 110),
            ("cost",     "Cost / Unit", 110),
            ("supplier", "Supplier",    200)
        ]
        for col_id, heading, width in col_setup:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        # load the data
        rows = self.load_inventory()
        low_stock_count = 0

        for r in rows:
            qty     = r["quantity_on_hand"]
            reorder = r["reorder_level"]

            # flag low stock with a tag
            tag = ""
            if qty <= reorder:
                tag = "low"
                low_stock_count += 1

            supplier = r["supplier_name"]
            if supplier is None:
                supplier = "—"

            tree.insert("", "end", tag=tag, values=(
                r["inventory_item_id"],
                r["item_name"],
                qty,
                r["unit_type"],
                reorder,
                f"${r['cost_per_unit']:.2f}",
                supplier
            ))

        # red text for low stock rows
        tree.tag_configure("low", foreground=RED)
        tree.pack(fill="both", expand=True)

        # footer summary
        footer = tk.Frame(self.content_frame, bg=BG_DARK)
        footer.pack(fill="x", pady=(8, 0))
        tk.Label(footer, text=f"{len(rows)} items total", bg=BG_DARK,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        if low_stock_count > 0:
            warn_text = "⚠ " + str(low_stock_count) + " item(s) at or below reorder level"
            tk.Label(footer, text=warn_text, bg=BG_DARK, fg=RED,
                     font=("Segoe UI", 9, "bold")).pack(side="right")


    # pulls inventory rows from MySQL or returns sample data on failure
    def load_inventory(self):
        rows = []

        if DB_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    sql = ("SELECT i.inventory_item_id, i.item_name, "
                           "i.quantity_on_hand, i.unit_type, i.reorder_level, "
                           "i.cost_per_unit, s.supplier_name "
                           "FROM inventory_item i "
                           "LEFT JOIN supplier s ON i.supplier_id = s.supplier_id "
                           "WHERE i.branch_id = %s "
                           "ORDER BY i.item_name")
                    cur.execute(sql, (self.branch_id,))
                    rows = cur.fetchall()
                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"Error loading inventory: {e}")
                rows = []

        # if nothing came back, fall back to sample data
        if len(rows) == 0:
            rows = [
                {"inventory_item_id": 1, "item_name": "Shrimp",        "quantity_on_hand": 25, "unit_type": "LB",   "reorder_level": 30, "cost_per_unit":  9.50, "supplier_name": "Atlantic Seafood"},
                {"inventory_item_id": 2, "item_name": "Salmon Filet",  "quantity_on_hand": 18, "unit_type": "LB",   "reorder_level": 20, "cost_per_unit": 12.75, "supplier_name": "Atlantic Seafood"},
                {"inventory_item_id": 3, "item_name": "Crab Meat",     "quantity_on_hand": 12, "unit_type": "LB",   "reorder_level": 10, "cost_per_unit": 18.00, "supplier_name": "Atlantic Seafood"},
                {"inventory_item_id": 4, "item_name": "Heavy Cream",   "quantity_on_hand":  6, "unit_type": "GAL",  "reorder_level":  4, "cost_per_unit":  5.25, "supplier_name": "Coastal Dairy"},
                {"inventory_item_id": 5, "item_name": "Butter",        "quantity_on_hand":  8, "unit_type": "LB",   "reorder_level": 12, "cost_per_unit":  4.10, "supplier_name": "Coastal Dairy"},
                {"inventory_item_id": 6, "item_name": "Lemons",        "quantity_on_hand": 40, "unit_type": "EA",   "reorder_level": 20, "cost_per_unit":  0.45, "supplier_name": "Garden Greens"},
                {"inventory_item_id": 7, "item_name": "Yellow Onion",  "quantity_on_hand": 22, "unit_type": "LB",   "reorder_level": 15, "cost_per_unit":  0.85, "supplier_name": "Garden Greens"},
                {"inventory_item_id": 8, "item_name": "Sweet Tea Mix", "quantity_on_hand":  3, "unit_type": "CASE", "reorder_level":  5, "cost_per_unit": 22.00, "supplier_name": None},
                {"inventory_item_id": 9, "item_name": "House Wine",    "quantity_on_hand": 14, "unit_type": "EA",   "reorder_level":  6, "cost_per_unit":  9.99, "supplier_name": "Coastal Spirits"}
            ]

        return rows


    # ----------------------------------------------------------------------
    # Suppliers tab
    # ----------------------------------------------------------------------
    def build_supplier_view(self):

        # header
        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Suppliers", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  flow_db.supplier", bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Suppliers")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        # table
        cols = ("id", "name", "contact", "phone", "email", "address")
        tree = ttk.Treeview(self.content_frame, columns=cols, show="headings",
                            style="Flow.Treeview", height=18)
        col_setup = [
            ("id",      "ID",       50),
            ("name",    "Supplier", 200),
            ("contact", "Contact",  160),
            ("phone",   "Phone",    130),
            ("email",   "Email",    220),
            ("address", "Address",  220)
        ]
        for col_id, heading, width in col_setup:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        rows = self.load_suppliers()
        for r in rows:
            # build display values, fill in '-' for missing fields
            contact = r["contact_name"]
            if contact is None or contact == "":
                contact = "—"
            phone = r["phone"]
            if phone is None or phone == "":
                phone = "—"
            email = r["email"]
            if email is None or email == "":
                email = "—"
            address = r["address"]
            if address is None or address == "":
                address = "—"

            tree.insert("", "end", values=(
                r["supplier_id"],
                r["supplier_name"],
                contact,
                phone,
                email,
                address
            ))

        tree.pack(fill="both", expand=True)

        # footer
        footer = tk.Frame(self.content_frame, bg=BG_DARK)
        footer.pack(fill="x", pady=(8, 0))
        tk.Label(footer, text=f"{len(rows)} suppliers", bg=BG_DARK,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="left")


    # pulls supplier rows from MySQL or returns sample data on failure
    def load_suppliers(self):
        rows = []

        if DB_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    cur.execute("SELECT * FROM supplier ORDER BY supplier_name")
                    rows = cur.fetchall()
                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"Error loading suppliers: {e}")
                rows = []

        if len(rows) == 0:
            rows = [
                {"supplier_id": 1, "supplier_name": "Atlantic Seafood", "contact_name": "Marcus Hill",  "phone": "757-555-0142", "email": "orders@atlantic.com",   "address": "210 Pier Rd, VA Beach, VA"},
                {"supplier_id": 2, "supplier_name": "Coastal Dairy",    "contact_name": "Linda Park",   "phone": "757-555-0188", "email": "linda@coastaldairy.com","address": "55 Farm Way, Suffolk, VA"},
                {"supplier_id": 3, "supplier_name": "Garden Greens",    "contact_name": "Tina Owens",   "phone": "757-555-0203", "email": "tina@gardengreens.co",  "address": "1100 Farm Ln, Chesapeake, VA"},
                {"supplier_id": 4, "supplier_name": "Coastal Spirits",  "contact_name": "Henry Brooks", "phone": "757-555-0277", "email": "h.brooks@cspirits.com", "address": "880 Ocean Blvd, Norfolk, VA"},
                {"supplier_id": 5, "supplier_name": "Bayside Bakers",   "contact_name": "Gail Sutton",  "phone": "757-555-0311", "email": "gail@baysidebakers.com","address": "44 Main St, Hampton, VA"}
            ]

        return rows


    # ----------------------------------------------------------------------
    # Schedule tab
    # ----------------------------------------------------------------------
    def build_schedule_view(self):

        # header
        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Staff Schedule", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  flow_db.shift_schedule", bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Schedule")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        # table
        cols = ("id", "employee", "role", "date", "start", "end", "hours")
        tree = ttk.Treeview(self.content_frame, columns=cols, show="headings",
                            style="Flow.Treeview", height=18)
        col_setup = [
            ("id",       "Shift ID", 80),
            ("employee", "Employee", 200),
            ("role",     "Role",     140),
            ("date",     "Date",     110),
            ("start",    "Start",    90),
            ("end",      "End",      90),
            ("hours",    "Hours",    80)
        ]
        for col_id, heading, width in col_setup:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        rows = self.load_shifts()
        total_hours = 0.0

        for r in rows:
            # work out shift length in hours
            hours = self.calc_shift_hours(r["start_time"], r["end_time"])
            total_hours += hours

            tree.insert("", "end", values=(
                r["shift_id"],
                r["employee_name"],
                r["role_assigned"],
                r["shift_date"],
                r["start_time"],
                r["end_time"],
                f"{hours:.1f}"
            ))

        tree.pack(fill="both", expand=True)

        # footer summary
        footer = tk.Frame(self.content_frame, bg=BG_DARK)
        footer.pack(fill="x", pady=(8, 0))
        tk.Label(footer, text=f"{len(rows)} shifts scheduled", bg=BG_DARK,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        tk.Label(footer, text=f"{total_hours:.1f} total hours", bg=BG_DARK,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="right")


    # pulls shift rows from MySQL or returns sample data on failure
    def load_shifts(self):
        rows = []

        if DB_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    sql = ("SELECT s.shift_id, s.shift_date, s.start_time, "
                           "s.end_time, s.role_assigned, "
                           "CONCAT(p.first_name, ' ', p.last_name) AS employee_name "
                           "FROM shift_schedule s "
                           "JOIN person p ON s.person_id = p.person_id "
                           "WHERE s.branch_id = %s "
                           "ORDER BY s.shift_date, s.start_time")
                    cur.execute(sql, (self.branch_id,))
                    rows = cur.fetchall()
                    cur.close()
                    conn.close()

                    # tidy up DB types so the treeview shows them right
                    for r in rows:
                        r["shift_date"] = str(r["shift_date"])
                        r["start_time"] = str(r["start_time"])[:5]
                        r["end_time"]   = str(r["end_time"])[:5]
            except Exception as e:
                print(f"Error loading shifts: {e}")
                rows = []

        if len(rows) == 0:
            rows = [
                {"shift_id": 101, "employee_name": "Janet Pierce",  "role_assigned": "Server",    "shift_date": "2026-04-25", "start_time": "10:00", "end_time": "16:00"},
                {"shift_id": 102, "employee_name": "Janet Pierce",  "role_assigned": "Server",    "shift_date": "2026-04-26", "start_time": "16:00", "end_time": "22:00"},
                {"shift_id": 103, "employee_name": "Marcus Lin",    "role_assigned": "Cook",      "shift_date": "2026-04-25", "start_time": "09:00", "end_time": "17:00"},
                {"shift_id": 104, "employee_name": "Marcus Lin",    "role_assigned": "Cook",      "shift_date": "2026-04-27", "start_time": "12:00", "end_time": "20:00"},
                {"shift_id": 105, "employee_name": "Devon Carter",  "role_assigned": "Host",      "shift_date": "2026-04-25", "start_time": "16:00", "end_time": "22:00"},
                {"shift_id": 106, "employee_name": "Brianna Smith", "role_assigned": "Bartender", "shift_date": "2026-04-25", "start_time": "17:00", "end_time": "23:00"},
                {"shift_id": 107, "employee_name": "Brianna Smith", "role_assigned": "Bartender", "shift_date": "2026-04-26", "start_time": "17:00", "end_time": "23:00"},
                {"shift_id": 108, "employee_name": "Tyrone Green",  "role_assigned": "Busser",    "shift_date": "2026-04-25", "start_time": "11:00", "end_time": "19:00"}
            ]

        return rows


    # works out hours between two HH:MM time strings
    def calc_shift_hours(self, start_str, end_str):
        try:
            sh, sm = start_str.split(":")
            eh, em = end_str.split(":")
            start_min = int(sh) * 60 + int(sm)
            end_min   = int(eh) * 60 + int(em)
            # shift can wrap past midnight
            if end_min < start_min:
                end_min += 24 * 60
            return (end_min - start_min) / 60.0
        except Exception:
            return 0.0


    # closes manager screen and reopens login
    def sign_out(self):
        if not messagebox.askyesno("Sign Out", "Sign out of FLOW?"):
            return
        self.destroy()
        try:
            from login import LoginScreen
            login_win = LoginScreen()
            login_win.mainloop()
        except Exception as e:
            print(f"Error returning to login: {e}")


# minimal driver -- lets you run manager_ui.py directly for testing
if __name__ == "__main__":
    app = ManagerUI(manager_name="Pat Reyes", branch_id=1)
    app.mainloop()
