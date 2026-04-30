# HQ_ui.py
#
#     FLOW - Enterprise Restaurant Management System
#     CSC 570 Sp 26'
#     Created by Jonah Goodwine
#
#
# This file is the HQ / Admin dashboard for the FLOW system. Unlike the
# manager UI which watches one branch at a time, this view monitors every
# Soul By The Sea branch at once and refreshes the live feed in real time.
#
# Sidebar tabs:
#     - Dashboard     KPIs + branch performance cards + live activity feed
#     - Branches      list and manage every branch location
#     - Employees     every employee across every branch
#     - Orders        active orders across all branches
#     - Reservations  today's reservations across all branches
#     - Inventory     low stock alerts across all branches
#     - Reviews       recent customer reviews + sentiment scores
#     - Staffing      who is scheduled today across all branches
#     - Analytics     visual cross-branch revenue comparison
#
# Data sources (all with dummy fallbacks if the service is down):
#     MySQL    orders, payments, reservations, inventory, branches, employees
#     MongoDB  reviews + sentiment, clickstream
#     Redis    live event feed (new_order, inventory_low, new_review, etc.)


import os
import sys
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

# ── macOS: native tk.Button ignores bg/fg; replace with Frame+Label ───────────
import platform as _platform
if _platform.system() == "Darwin":
    _TkFrame, _TkLabel = tk.Frame, tk.Label
    class _ColorButton(_TkFrame):
        def __init__(self, parent, text="", command=None,
                     bg="#1C2128", fg="#E6EDF3",
                     font=("Segoe UI", 10, "bold"),
                     padx=8, pady=5, cursor="hand2",
                     width=None, **_ignored):
            super().__init__(parent, bg=bg, cursor=cursor)
            kw = dict(text=text, bg=bg, fg=fg, font=font, padx=padx, pady=pady, cursor=cursor)
            if width is not None:
                kw["width"] = width
            self._lbl = _TkLabel(self, **kw)
            self._lbl.pack(fill="both", expand=True)
            if command:
                self._attach_cmd(command)
        def _attach_cmd(self, cmd):
            self._lbl.unbind("<Button-1>")
            self.unbind("<Button-1>")
            self._lbl.bind("<Button-1>", lambda e: cmd())
            self.bind("<Button-1>", lambda e: cmd())
        def config(self, bg=None, fg=None, text=None,
                   cursor=None, command=None, **_ignored):
            if bg is not None:
                _TkFrame.config(self, bg=bg); self._lbl.config(bg=bg)
            if fg is not None:
                self._lbl.config(fg=fg)
            if text is not None:
                self._lbl.config(text=text)
            if cursor is not None:
                _TkFrame.config(self, cursor=cursor); self._lbl.config(cursor=cursor)
            if command is not None:
                self._attach_cmd(command)
        configure = config
    tk.Button = _ColorButton
del _platform
# ──────────────────────────────────────────────────────────────────────────────
import json
import random


# try to grab the project DB connection
try:
    from config.db_config import get_connection
    MYSQL_AVAILABLE = True
except Exception:
    MYSQL_AVAILABLE = False

try:
    from backend.auth import register_user
    from backend.employee import update_employee_status
    HQ_BACKEND = True
except Exception:
    HQ_BACKEND = False

# try Redis for the live activity feed
try:
    import redis
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False

# try MongoDB for reviews / sentiment
try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except Exception:
    MONGO_AVAILABLE = False


# color palette -- matches the rest of the FLOW UI
BG_DARK    = "#0D1117"
BG_PANEL   = "#161B22"
BG_HOVER   = "#1F2530"
GOLD       = "#D4A843"
TEXT       = "#E6EDF3"
MUTED      = "#8B949E"
BORDER     = "#30363D"
RED        = "#F85149"
GREEN      = "#3FB950"

# branch color codes for the live activity feed (per the HQ spec)
BRANCH_COLORS = {
    "Hampton":        "#58A6FF",   # blue
    "Norfolk":        "#3FB950",   # green
    "Virginia Beach": "#F0883E",   # orange
    "Chesapeake":     "#A371F7"    # purple (extra branch)
}


# helper -- returns the branch color for the live feed line
def get_branch_color(branch_name):
    if branch_name is None:
        return TEXT
    for key in BRANCH_COLORS:
        if key in branch_name:
            return BRANCH_COLORS[key]
    return TEXT


# helper -- shortens a full branch name down to the city portion
# example: "Virginia Beach Boardwalk" -> "Virginia Beach"
def short_branch_name(full_name):
    if full_name is None:
        return "?"
    for key in BRANCH_COLORS:
        if key in full_name:
            return key
    return full_name


# ══════════════════════════════════════════════════════════════════════════════
# MAIN HQ DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

class HQDashboard(tk.Tk):

    # full-arg constructor
    def __init__(self, admin_name="Admin"):
        super().__init__()
        self.admin_name = admin_name

        self.title("FLOW - HQ Dashboard")
        self.configure(bg=BG_DARK)
        self.geometry("1280x720")

        # try to maximize -- works on Windows + Linux
        try:
            self.state("zoomed")
        except tk.TclError:
            pass

        # which tab is showing right now
        self.current_tab   = "Dashboard"
        self.content_frame = None

        # live feed bits -- used by the auto refresh loop
        self.live_feed_listbox = None
        self.last_update_label = None
        self.refresh_seconds   = 5

        # set up the table styling once for the whole window
        self.setup_table_style()

        self.build_ui()
        self.show_tab("Dashboard")

        # kick off the auto refresh timer
        self.schedule_refresh()


    # no-arg constructor convenience
    @classmethod
    def default(cls):
        return cls(admin_name="Admin")


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
        tk.Label(topbar, text="FLOW HQ Dashboard", bg=BG_PANEL,
                 fg=MUTED, font=("Segoe UI", 9)
                 ).pack(side="left", pady=12)

        admin_text = "Admin: " + self.admin_name + "  ·  All Branches"
        tk.Label(topbar, text=admin_text, bg=BG_PANEL, fg=MUTED,
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

        tk.Label(self.sidebar, text="HQ MENU", bg=BG_PANEL, fg="#444D56",
                 font=("Segoe UI", 8, "bold")
                 ).pack(anchor="w", padx=14, pady=(14, 8))

        # sidebar tab buttons -- nine total
        tab_labels = ["Dashboard", "Branches", "Employees", "Orders",
                      "Reservations", "Inventory", "Reviews", "Staffing",
                      "Analytics", "Clickstream"]
        self.tab_buttons = {}
        for label in tab_labels:
            btn = tk.Button(self.sidebar, text=label, bg=BG_PANEL, fg=TEXT,
                            activebackground=BG_HOVER, activeforeground=GOLD,
                            relief="flat", anchor="w", cursor="hand2",
                            font=("Segoe UI", 11),
                            command=lambda l=label: self.show_tab(l))
            btn.pack(fill="x", padx=8, pady=2, ipady=7)
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

        # leaving the dashboard means the live feed listbox no longer exists
        if tab_name != "Dashboard":
            self.live_feed_listbox = None
            self.last_update_label = None

        # wipe the old content
        if self.content_frame is not None:
            self.content_frame.destroy()

        # build a fresh content frame
        self.content_frame = tk.Frame(self.main_area, bg=BG_DARK)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        if   tab_name == "Dashboard":    self.build_dashboard_view()
        elif tab_name == "Branches":     self.build_branch_view()
        elif tab_name == "Employees":    self.build_employee_view()
        elif tab_name == "Orders":       self.build_orders_view()
        elif tab_name == "Reservations": self.build_reservations_view()
        elif tab_name == "Inventory":    self.build_inventory_view()
        elif tab_name == "Reviews":      self.build_reviews_view()
        elif tab_name == "Staffing":     self.build_staffing_view()
        elif tab_name == "Analytics":    self.build_analytics_view()
        elif tab_name == "Clickstream":  self.build_clickstream_view()


    # ══════════════════════════════════════════════════════════════════════════
    # AUTO REFRESH (live activity feed)
    # ══════════════════════════════════════════════════════════════════════════

    # arms the next auto refresh tick
    def schedule_refresh(self):
        try:
            self.after(self.refresh_seconds * 1000, self.auto_refresh)
        except Exception:
            pass


    # called every few seconds. only updates the live feed in place so the
    # rest of the dashboard does not flicker.
    def auto_refresh(self):
        # bail out if the window is gone
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        # only update the live feed if the dashboard is showing
        if self.current_tab == "Dashboard" and self.live_feed_listbox is not None:
            try:
                self.refresh_live_feed()
            except Exception as e:
                print(f"Live feed refresh error: {e}")

        # arm the next tick
        self.schedule_refresh()


    # clears and repopulates the live feed listbox with the latest events
    def refresh_live_feed(self):
        if self.live_feed_listbox is None:
            return

        events = self.load_live_events()

        lb = self.live_feed_listbox
        lb.delete(0, "end")

        for i in range(len(events)):
            ev = events[i]
            short = short_branch_name(ev["branch"])
            line = "[" + short + "]  " + ev["message"]
            lb.insert("end", line)

            color = get_branch_color(ev["branch"])
            lb.itemconfig(i, foreground=color)

        # update the "last refreshed" timestamp label
        if self.last_update_label is not None:
            now_str = datetime.now().strftime("%H:%M:%S")
            self.last_update_label.config(text="Last update: " + now_str)


    # ══════════════════════════════════════════════════════════════════════════
    # 1.  DASHBOARD TAB
    #     - 5 KPI cards across the top (per HQ spec section 1)
    #     - branch performance cards on the left
    #     - live activity feed on the right (HQ spec section 3)
    # ══════════════════════════════════════════════════════════════════════════

    def build_dashboard_view(self):

        # header row
        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 14))
        tk.Label(head, text="HQ Dashboard", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  enterprise overview", bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))

        # last update label, lives in the header on the right
        self.last_update_label = tk.Label(head, text="Last update: --",
                                          bg=BG_DARK, fg=MUTED,
                                          font=("Segoe UI", 8, "italic"))
        self.last_update_label.pack(side="right", padx=8)

        tk.Button(head, text="Refresh Now", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Dashboard")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        # ---- KPI cards row (5 cards per the HQ spec) ----
        kpis = self.load_kpis()

        cards = tk.Frame(self.content_frame, bg=BG_DARK)
        cards.pack(fill="x", pady=(0, 14))

        self.draw_kpi_card(cards, "Total Sales (Today)",
                           f"${kpis['total_sales']:,.2f}", 0)
        self.draw_kpi_card(cards, "Active Orders",
                           str(kpis['active_orders']),       1)
        self.draw_kpi_card(cards, "Reservations Today",
                           str(kpis['reservations_today']),  2)

        # rating card -- color the value depending on how good it is
        if kpis["avg_rating"] is None:
            rating_text  = "—"
        else:
            rating_text  = f"{kpis['avg_rating']:.2f} / 5"
        self.draw_kpi_card(cards, "Average Rating", rating_text, 3)

        # low inventory card -- if there are issues, color the value red
        low_count = kpis["low_inventory_count"]
        low_color = GOLD
        if low_count > 0:
            low_color = RED
        self.draw_kpi_card(cards, "Low Inventory", str(low_count), 4,
                           value_color=low_color)

        # ---- middle band: branch perf cards on left, live feed on right ----
        middle = tk.Frame(self.content_frame, bg=BG_DARK)
        middle.pack(fill="both", expand=True)

        # left column: branch performance cards
        left_col = tk.Frame(middle, bg=BG_DARK)
        left_col.pack(side="left", fill="both", expand=True)

        tk.Label(left_col, text="Branch Performance",
                 bg=BG_DARK, fg=TEXT, font=("Segoe UI", 12, "bold")
                 ).pack(anchor="w", pady=(0, 6))

        # one card per branch, with all six stat fields the HQ spec wants
        perf_rows = self.load_branch_performance()
        for r in perf_rows:
            self.draw_branch_perf_card(left_col, r)

        # right column: live activity feed
        right_col = tk.Frame(middle, bg=BG_DARK, width=360)
        right_col.pack(side="right", fill="y", padx=(14, 0))
        right_col.pack_propagate(False)

        feed_head = tk.Frame(right_col, bg=BG_DARK)
        feed_head.pack(fill="x", pady=(0, 6))
        tk.Label(feed_head, text="Live Activity",
                 bg=BG_DARK, fg=TEXT, font=("Segoe UI", 12, "bold")
                 ).pack(side="left")

        # tiny status dot showing where events are coming from
        if REDIS_AVAILABLE:
            status_text = "redis"
        else:
            status_text = "simulated"
        tk.Label(feed_head, text="·  " + status_text,
                 bg=BG_DARK, fg=MUTED, font=("Segoe UI", 8, "italic")
                 ).pack(side="left", padx=6, pady=(4, 0))

        # listbox holds the actual events. each row colored per branch.
        self.live_feed_listbox = tk.Listbox(right_col, bg=BG_PANEL, fg=TEXT,
                                            selectbackground="#2A3441",
                                            selectforeground=TEXT,
                                            font=("Consolas", 10),
                                            bd=0, highlightthickness=1,
                                            highlightbackground=BORDER,
                                            relief="flat", activestyle="none")
        self.live_feed_listbox.pack(fill="both", expand=True)

        # populate it once right away (auto refresh handles the rest)
        self.refresh_live_feed()


    # draws one KPI box. col index spaces them evenly across the row.
    def draw_kpi_card(self, parent, label, value, col_index, value_color=GOLD):
        card = tk.Frame(parent, bg=BG_PANEL, bd=0, highlightthickness=1,
                        highlightbackground=BORDER)
        card.grid(row=0, column=col_index, sticky="nsew", padx=4,
                  ipadx=10, ipady=8)
        parent.grid_columnconfigure(col_index, weight=1)

        tk.Label(card, text=label.upper(), bg=BG_PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")
                 ).pack(anchor="w", padx=12, pady=(6, 0))
        tk.Label(card, text=value, bg=BG_PANEL, fg=value_color,
                 font=("Segoe UI", 20, "bold")
                 ).pack(anchor="w", padx=12, pady=(2, 6))


    # draws a single branch performance card showing all six stat fields
    # the HQ spec asks for in section 2
    def draw_branch_perf_card(self, parent, row):
        card = tk.Frame(parent, bg=BG_PANEL, bd=0, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="x", pady=4, ipady=8)

        # color stripe on the left edge by branch
        stripe_color = get_branch_color(row["branch_name"])
        stripe = tk.Frame(card, bg=stripe_color, width=4)
        stripe.pack(side="left", fill="y")

        # branch name + manager up top
        inside = tk.Frame(card, bg=BG_PANEL)
        inside.pack(fill="both", expand=True, padx=12, pady=4)

        head = tk.Frame(inside, bg=BG_PANEL)
        head.pack(fill="x")
        tk.Label(head, text=row["branch_name"], bg=BG_PANEL, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        manager = row["manager_name"]
        if manager is None or manager == "":
            manager = "(unassigned)"
        tk.Label(head, text="  ·  " + manager, bg=BG_PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left")

        # stats row -- six little label/value pairs side by side
        stats = tk.Frame(inside, bg=BG_PANEL)
        stats.pack(fill="x", pady=(4, 0))

        # rating coloring
        rating_color = TEXT
        if row["avg_rating"] is not None:
            if row["avg_rating"] >= 4.2:
                rating_color = GREEN
            elif row["avg_rating"] < 3.5:
                rating_color = RED
        if row["avg_rating"] is None:
            rating_text = "—"
        else:
            rating_text = f"{row['avg_rating']:.2f}"

        # low stock coloring
        low_color = TEXT
        if row["low_stock_count"] > 0:
            low_color = RED

        self.draw_stat_pair(stats, "Sales",
                            f"${row['total_sales']:,.2f}", GOLD)
        self.draw_stat_pair(stats, "Active Orders",
                            str(row["active_orders"]),     TEXT)
        self.draw_stat_pair(stats, "Reservations",
                            str(row["reservations_today"]),TEXT)
        self.draw_stat_pair(stats, "Avg Rating",
                            rating_text,                   rating_color)
        self.draw_stat_pair(stats, "Low Stock",
                            str(row["low_stock_count"]),   low_color)


    # one tiny "label / bigger value" pair packed left-to-right
    def draw_stat_pair(self, parent, label, value, value_color):
        cell = tk.Frame(parent, bg=BG_PANEL)
        cell.pack(side="left", padx=(0, 22))
        tk.Label(cell, text=label, bg=BG_PANEL, fg=MUTED,
                 font=("Segoe UI", 8)).pack(anchor="w")
        tk.Label(cell, text=value, bg=BG_PANEL, fg=value_color,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")


    # ---- dashboard data loaders ----

    # pulls the five KPIs the HQ spec asks for
    def load_kpis(self):
        kpis = {
            "total_sales":          0.0,
            "active_orders":        0,
            "reservations_today":   0,
            "avg_rating":           None,
            "low_inventory_count":  0
        }

        if MYSQL_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)

                    # total sales today (sum payment.amount for today)
                    cur.execute("SELECT COALESCE(SUM(amount), 0) AS s "
                                "FROM payment "
                                "WHERE DATE(payment_datetime) = CURDATE()")
                    row = cur.fetchone()
                    kpis["total_sales"] = float(row["s"])

                    # active orders right now (status IN_PROGRESS)
                    cur.execute("SELECT COUNT(*) AS c FROM orders "
                                "WHERE order_status = 'IN_PROGRESS'")
                    row = cur.fetchone()
                    kpis["active_orders"] = row["c"]

                    # reservations scheduled for today
                    cur.execute("SELECT COUNT(*) AS c FROM reservation "
                                "WHERE DATE(reservation_datetime) = CURDATE()")
                    row = cur.fetchone()
                    kpis["reservations_today"] = row["c"]

                    # avg rating across the last 30 days
                    cur.execute("SELECT AVG(rating) AS r FROM review "
                                "WHERE created_at >= NOW() - INTERVAL 30 DAY")
                    row = cur.fetchone()
                    if row["r"] is not None:
                        kpis["avg_rating"] = float(row["r"])

                    # how many items below their reorder line
                    cur.execute("SELECT COUNT(*) AS c FROM inventory_item "
                                "WHERE quantity_on_hand < reorder_level")
                    row = cur.fetchone()
                    kpis["low_inventory_count"] = row["c"]

                    cur.close()
                    conn.close()
                    return kpis
            except Exception as e:
                print(f"Error loading KPIs: {e}")

        # dummy fallback
        kpis["total_sales"]         = 9842.55
        kpis["active_orders"]       = 23
        kpis["reservations_today"]  = 41
        kpis["avg_rating"]          = 4.15
        kpis["low_inventory_count"] = 6
        return kpis


    # one row per branch with all six stat fields the HQ spec wants
    def load_branch_performance(self):
        rows = []

        if MYSQL_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    sql = ("SELECT b.branch_id, b.branch_name, "
                           "CONCAT(p.first_name, ' ', p.last_name) AS manager_name, "
                           "(SELECT COALESCE(SUM(pay.amount), 0) "
                           "  FROM payment pay JOIN orders o ON pay.order_id = o.order_id "
                           "  WHERE o.branch_id = b.branch_id "
                           "    AND DATE(pay.payment_datetime) = CURDATE()) AS total_sales, "
                           "(SELECT COUNT(*) FROM orders o "
                           "  WHERE o.branch_id = b.branch_id "
                           "    AND o.order_status = 'IN_PROGRESS') AS active_orders, "
                           "(SELECT COUNT(*) FROM reservation r "
                           "  WHERE r.branch_id = b.branch_id "
                           "    AND DATE(r.reservation_datetime) = CURDATE()) AS reservations_today, "
                           "(SELECT AVG(rv.rating) FROM review rv "
                           "  WHERE rv.branch_id = b.branch_id "
                           "    AND rv.created_at >= NOW() - INTERVAL 30 DAY) AS avg_rating, "
                           "(SELECT COUNT(*) FROM inventory_item ii "
                           "  WHERE ii.branch_id = b.branch_id "
                           "    AND ii.quantity_on_hand < ii.reorder_level) AS low_stock_count "
                           "FROM branch b "
                           "LEFT JOIN person p ON b.manager_id = p.person_id "
                           "ORDER BY b.branch_name")
                    cur.execute(sql)
                    rows = cur.fetchall()

                    # tidy DB types so the cards render right
                    for r in rows:
                        r["total_sales"] = float(r["total_sales"])
                        if r["avg_rating"] is not None:
                            r["avg_rating"] = float(r["avg_rating"])

                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"Error loading branch performance: {e}")
                rows = []

        if len(rows) == 0:
            rows = [
                {"branch_id": 1, "branch_name": "Virginia Beach Boardwalk", "manager_name": "Pat Reyes",   "total_sales": 3284.10, "active_orders": 7, "reservations_today": 14, "avg_rating": 4.4, "low_stock_count": 1},
                {"branch_id": 2, "branch_name": "Norfolk Waterside",        "manager_name": "Tasha King",  "total_sales": 2415.75, "active_orders": 5, "reservations_today": 10, "avg_rating": 4.1, "low_stock_count": 2},
                {"branch_id": 3, "branch_name": "Hampton Pier",             "manager_name": "Marcus Hill", "total_sales": 2102.40, "active_orders": 6, "reservations_today":  9, "avg_rating": 3.9, "low_stock_count": 0},
                {"branch_id": 4, "branch_name": "Chesapeake Bay",           "manager_name": "Linda Park",  "total_sales": 2040.30, "active_orders": 5, "reservations_today":  8, "avg_rating": 3.4, "low_stock_count": 3}
            ]

        return rows


    # pulls the latest events for the live feed.
    # tries Redis first, then synthesizes events from MySQL, then dummy.
    def load_live_events(self):

        # try Redis first
        if REDIS_AVAILABLE:
            try:
                r = redis.Redis(host="localhost", port=6379, db=0,
                                decode_responses=True,
                                socket_connect_timeout=1)
                raw = r.lrange("flow:events", 0, 19)
                events = []
                for item in raw:
                    try:
                        ev = json.loads(item)
                        events.append(ev)
                    except Exception:
                        # if it is not JSON, keep the raw string
                        events.append({"branch": "?", "message": str(item)})
                if len(events) > 0:
                    return events
            except Exception as e:
                print(f"Redis read error: {e}")

        # fallback: synthesize a feed from recent MySQL activity
        if MYSQL_AVAILABLE:
            try:
                events = self.synthesize_events_from_mysql()
                if len(events) > 0:
                    return events
            except Exception as e:
                print(f"Synthesized feed error: {e}")

        # last resort: dummy events that shuffle each refresh so it feels alive
        return self.dummy_live_events()


    # builds a feed by reading the most recent rows from the active tables
    def synthesize_events_from_mysql(self):
        events = []
        try:
            conn = get_connection()
            if conn is None:
                return events
            cur = conn.cursor(dictionary=True)

            # latest orders
            cur.execute("SELECT o.order_id, o.order_datetime, o.total_amount, "
                        "       b.branch_name "
                        "FROM orders o JOIN branch b ON o.branch_id = b.branch_id "
                        "ORDER BY o.order_datetime DESC LIMIT 5")
            for r in cur.fetchall():
                msg = f"New Order Created (Order ID: {r['order_id']}, ${float(r['total_amount']):.2f})"
                events.append({"branch": r["branch_name"],
                               "message": msg,
                               "ts": str(r["order_datetime"])})

            # latest reservations
            cur.execute("SELECT r.reservation_id, r.reservation_datetime, "
                        "       r.party_size, r.status, b.branch_name "
                        "FROM reservation r JOIN branch b ON r.branch_id = b.branch_id "
                        "ORDER BY r.reservation_datetime DESC LIMIT 5")
            for r in cur.fetchall():
                if r["status"] == "SEATED":
                    msg = f"Reservation Seated (Party Size: {r['party_size']})"
                else:
                    msg = f"Reservation Created (Party Size: {r['party_size']})"
                events.append({"branch": r["branch_name"],
                               "message": msg,
                               "ts": str(r["reservation_datetime"])})

            # latest reviews
            cur.execute("SELECT rv.rating, rv.created_at, b.branch_name "
                        "FROM review rv JOIN branch b ON rv.branch_id = b.branch_id "
                        "ORDER BY rv.created_at DESC LIMIT 5")
            for r in cur.fetchall():
                msg = f"New Review Posted ({r['rating']}/5)"
                events.append({"branch": r["branch_name"],
                               "message": msg,
                               "ts": str(r["created_at"])})

            # any items currently low on stock
            cur.execute("SELECT ii.item_name, b.branch_name "
                        "FROM inventory_item ii JOIN branch b ON ii.branch_id = b.branch_id "
                        "WHERE ii.quantity_on_hand < ii.reorder_level LIMIT 5")
            for r in cur.fetchall():
                msg = f"Inventory Low: {r['item_name']}"
                events.append({"branch": r["branch_name"],
                               "message": msg,
                               "ts": ""})

            cur.close()
            conn.close()
        except Exception as e:
            print(f"Synthesized events DB error: {e}")
            return []

        # sort by timestamp descending so the freshest stuff lands on top
        events.sort(key=lambda e: e.get("ts", ""), reverse=True)
        # keep the latest 20 only
        return events[:20]


    # makes up a list of fake events for when nothing real is available.
    # shuffles each call so the feed visibly changes every few seconds.
    def dummy_live_events(self):
        templates = [
            ("Virginia Beach Boardwalk", "New Order Created (Order ID: %d, $%0.2f)"),
            ("Norfolk Waterside",        "Reservation Created (Party Size: %d)"),
            ("Hampton Pier",             "Inventory Low: Shrimp"),
            ("Chesapeake Bay",           "Order Completed (Order ID: %d)"),
            ("Hampton Pier",             "Reservation Seated (Party Size: %d)"),
            ("Norfolk Waterside",        "New Review Posted (%d/5)"),
            ("Virginia Beach Boardwalk", "New Order Created (Order ID: %d, $%0.2f)"),
            ("Chesapeake Bay",           "Inventory Low: Heavy Cream"),
            ("Hampton Pier",             "New Order Created (Order ID: %d, $%0.2f)"),
            ("Norfolk Waterside",        "Order Completed (Order ID: %d)"),
            ("Virginia Beach Boardwalk", "New Review Posted (%d/5)"),
            ("Chesapeake Bay",           "Reservation Created (Party Size: %d)")
        ]

        events = []
        for branch, tmpl in templates:
            # fill in the placeholders with random-ish numbers
            try:
                if "%0.2f" in tmpl:
                    msg = tmpl % (random.randint(100, 999),
                                  random.uniform(15.00, 85.00))
                elif "Party Size" in tmpl:
                    msg = tmpl % random.randint(2, 8)
                elif "/5" in tmpl:
                    msg = tmpl % random.randint(3, 5)
                elif "Order ID" in tmpl:
                    msg = tmpl % random.randint(100, 999)
                else:
                    msg = tmpl
            except Exception:
                msg = tmpl
            events.append({"branch": branch, "message": msg})

        # shuffle so the feed visibly changes every refresh tick
        random.shuffle(events)
        return events


    # ══════════════════════════════════════════════════════════════════════════
    # 2.  BRANCHES TAB  (kept from admin_ui)
    # ══════════════════════════════════════════════════════════════════════════

    def build_branch_view(self):

        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Branches", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  flow_db.branch", bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(head, text="Add Branch", bg=GOLD, fg="#000000",
                  activebackground="#B8902E", relief="flat",
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  command=self.add_branch_stub
                  ).pack(side="right", padx=4, ipadx=10, ipady=4)
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Branches")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        cols = ("id", "name", "address", "phone", "manager", "employees")
        tree = ttk.Treeview(self.content_frame, columns=cols, show="headings",
                            style="Flow.Treeview", height=18)
        col_setup = [
            ("id",        "ID",        50),
            ("name",      "Branch",    240),
            ("address",   "Address",   260),
            ("phone",     "Phone",     130),
            ("manager",   "Manager",   180),
            ("employees", "Employees", 100)
        ]
        for col_id, heading, width in col_setup:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        rows = self.load_branches()
        for r in rows:
            address = r["address"]
            if address is None or address == "":
                address = "—"
            phone = r["phone"]
            if phone is None or phone == "":
                phone = "—"
            manager = r["manager_name"]
            if manager is None or manager == "":
                manager = "(unassigned)"
            tree.insert("", "end", values=(r["branch_id"], r["branch_name"],
                                            address, phone, manager,
                                            r["employee_count"]))
        tree.pack(fill="both", expand=True)

        footer = tk.Frame(self.content_frame, bg=BG_DARK)
        footer.pack(fill="x", pady=(8, 0))
        tk.Label(footer, text=f"{len(rows)} branches", bg=BG_DARK,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="left")


    def add_branch_stub(self):
        win = self._hq_dialog("Add Branch", 420, 320)
        f = tk.Frame(win, bg=BG_PANEL)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        name_e  = self._hq_field(f, "Branch Name *", 0)
        addr_e  = self._hq_field(f, "Address", 1)
        phone_e = self._hq_field(f, "Phone", 2)

        def submit():
            name = name_e.get().strip()
            if not name:
                messagebox.showerror("Missing Field", "Branch name is required.", parent=win)
                return
            try:
                from config.db_config import get_connection as _get_conn
                conn = _get_conn()
                if conn is None:
                    messagebox.showerror("DB Error", "Could not connect to database.", parent=win)
                    return
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO branch (branch_name, address, phone) VALUES (%s, %s, %s)",
                    (name, addr_e.get().strip() or None, phone_e.get().strip() or None),
                )
                conn.commit()
                cur.close()
                conn.close()
                messagebox.showinfo("Branch Added", f'"{name}" was added successfully.', parent=win)
                win.destroy()
                self.show_tab("Branches")
            except Exception as exc:
                messagebox.showerror("Add Branch Failed", str(exc), parent=win)

        tk.Button(win, text="Create Branch", bg="#0F2419", fg=GREEN,
                  font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2",
                  command=submit).pack(fill="x", padx=14, pady=(14, 4))


    def load_branches(self):
        rows = []
        if MYSQL_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    sql = ("SELECT b.branch_id, b.branch_name, b.address, b.phone, "
                           "CONCAT(p.first_name, ' ', p.last_name) AS manager_name, "
                           "(SELECT COUNT(*) FROM employee e "
                           "  WHERE e.branch_id = b.branch_id "
                           "    AND e.employment_status = 'ACTIVE') AS employee_count "
                           "FROM branch b "
                           "LEFT JOIN person p ON b.manager_id = p.person_id "
                           "ORDER BY b.branch_name")
                    cur.execute(sql)
                    rows = cur.fetchall()
                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"Error loading branches: {e}")
                rows = []

        if len(rows) == 0:
            rows = [
                {"branch_id": 1, "branch_name": "Virginia Beach Boardwalk", "address": "1200 Atlantic Ave, Virginia Beach, VA", "phone": "757-555-0101", "manager_name": "Pat Reyes",   "employee_count": 18},
                {"branch_id": 2, "branch_name": "Norfolk Waterside",        "address": "300 Waterside Dr, Norfolk, VA",         "phone": "757-555-0140", "manager_name": "Tasha King",  "employee_count": 15},
                {"branch_id": 3, "branch_name": "Hampton Pier",             "address": "44 Settlers Landing Rd, Hampton, VA",   "phone": "757-555-0188", "manager_name": "Marcus Hill", "employee_count": 14},
                {"branch_id": 4, "branch_name": "Chesapeake Bay",           "address": "725 Volvo Pkwy, Chesapeake, VA",        "phone": "757-555-0210", "manager_name": "Linda Park",  "employee_count": 15}
            ]
        return rows


    # ══════════════════════════════════════════════════════════════════════════
    # 3.  EMPLOYEES TAB  (kept from admin_ui)
    # ══════════════════════════════════════════════════════════════════════════

    def build_employee_view(self):

        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Employees", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  flow_db.employee  (all branches)", bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Employees")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)
        tk.Button(head, text="Change Role", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=self._hq_change_role_dialog
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)
        tk.Button(head, text="Add User", bg=BG_PANEL, fg=GOLD, relief="flat",
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  command=self._hq_add_user_dialog
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        cols = ("id", "name", "branch", "title", "status", "hire_date")
        tree = ttk.Treeview(self.content_frame, columns=cols, show="headings",
                            style="Flow.Treeview", height=18)
        self._hq_emp_tree = tree
        col_setup = [
            ("id",        "ID",         60),
            ("name",      "Name",       200),
            ("branch",    "Branch",     220),
            ("title",     "Job Title",  160),
            ("status",    "Status",     110),
            ("hire_date", "Hire Date",  120)
        ]
        for col_id, heading, width in col_setup:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        rows = self.load_all_employees()

        active_count   = 0
        inactive_count = 0

        for r in rows:
            tag = ""
            if r["employment_status"] == "ACTIVE":
                active_count += 1
            else:
                inactive_count += 1
                tag = "inactive"
            tree.insert("", "end", tag=tag, values=(r["person_id"],
                                                     r["full_name"],
                                                     r["branch_name"],
                                                     r["job_title"],
                                                     r["employment_status"],
                                                     str(r["hire_date"])))

        tree.tag_configure("inactive", foreground=MUTED)
        tree.pack(fill="both", expand=True)

        footer = tk.Frame(self.content_frame, bg=BG_DARK)
        footer.pack(fill="x", pady=(8, 0))
        tk.Label(footer, text=f"{len(rows)} employees total", bg=BG_DARK,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        right_text = f"{active_count} active   ·   {inactive_count} inactive"
        tk.Label(footer, text=right_text, bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="right")


    def load_all_employees(self):
        rows = []
        if MYSQL_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    sql = ("SELECT e.person_id, "
                           "CONCAT(p.first_name, ' ', p.last_name) AS full_name, "
                           "b.branch_name, e.job_title, e.employment_status, "
                           "e.hire_date "
                           "FROM employee e "
                           "JOIN person p  ON e.person_id = p.person_id "
                           "JOIN branch b  ON e.branch_id = b.branch_id "
                           "ORDER BY b.branch_name, p.last_name, p.first_name")
                    cur.execute(sql)
                    rows = cur.fetchall()
                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"Error loading employees: {e}")
                rows = []

        if len(rows) == 0:
            rows = [
                {"person_id":  1, "full_name": "Pat Reyes",     "branch_name": "Virginia Beach Boardwalk", "job_title": "Manager",   "employment_status": "ACTIVE",   "hire_date": "2023-04-12"},
                {"person_id":  2, "full_name": "Janet Pierce",  "branch_name": "Virginia Beach Boardwalk", "job_title": "Server",    "employment_status": "ACTIVE",   "hire_date": "2024-08-02"},
                {"person_id":  3, "full_name": "Marcus Lin",    "branch_name": "Virginia Beach Boardwalk", "job_title": "Cook",      "employment_status": "ACTIVE",   "hire_date": "2024-01-19"},
                {"person_id":  4, "full_name": "Tasha King",    "branch_name": "Norfolk Waterside",        "job_title": "Manager",   "employment_status": "ACTIVE",   "hire_date": "2022-09-30"},
                {"person_id":  5, "full_name": "Devon Carter",  "branch_name": "Norfolk Waterside",        "job_title": "Host",      "employment_status": "ACTIVE",   "hire_date": "2025-02-11"},
                {"person_id":  6, "full_name": "Brianna Smith", "branch_name": "Norfolk Waterside",        "job_title": "Bartender", "employment_status": "ACTIVE",   "hire_date": "2024-05-22"},
                {"person_id":  7, "full_name": "Marcus Hill",   "branch_name": "Hampton Pier",             "job_title": "Manager",   "employment_status": "ACTIVE",   "hire_date": "2023-07-05"},
                {"person_id":  8, "full_name": "Tyrone Green",  "branch_name": "Hampton Pier",             "job_title": "Busser",    "employment_status": "ACTIVE",   "hire_date": "2025-09-14"},
                {"person_id":  9, "full_name": "Linda Park",    "branch_name": "Chesapeake Bay",           "job_title": "Manager",   "employment_status": "ACTIVE",   "hire_date": "2023-11-08"},
                {"person_id": 10, "full_name": "Henry Brooks",  "branch_name": "Chesapeake Bay",           "job_title": "Cook",      "employment_status": "INACTIVE", "hire_date": "2022-12-01"},
                {"person_id": 11, "full_name": "Gail Sutton",   "branch_name": "Chesapeake Bay",           "job_title": "Server",    "employment_status": "LEAVE",    "hire_date": "2024-03-17"}
            ]
        return rows


    def _hq_dialog(self, title, width=460, height=500):
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=BG_PANEL)
        win.geometry(f"{width}x{height}")
        win.resizable(False, False)
        win.grab_set()
        return win

    def _hq_field(self, parent, label, row, show=None):
        tk.Label(parent, text=label, bg=BG_PANEL, fg=TEXT,
                 font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", padx=14, pady=(8,2))
        v = tk.StringVar()
        e = tk.Entry(parent, textvariable=v, bg=BG_DARK, fg=TEXT, insertbackground=TEXT,
                     relief="flat", font=("Segoe UI", 11), width=28, show=show or "")
        e.grid(row=row, column=1, sticky="ew", padx=(4,14), pady=(8,2))
        return e

    def _hq_add_user_dialog(self):
        """Admin creates a new employee login account across any branch."""
        if not MYSQL_AVAILABLE:
            messagebox.showerror("Unavailable", "Database not connected.")
            return

        win = self._hq_dialog("Add User Account", 480, 580)
        f = tk.Frame(win, bg=BG_PANEL)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        first_e  = self._hq_field(f, "First Name *",  0)
        last_e   = self._hq_field(f, "Last Name *",   1)
        email_e  = self._hq_field(f, "Email *",       2)
        user_e   = self._hq_field(f, "Username *",    3)
        pass_e   = self._hq_field(f, "Password *",    4, show="*")
        title_e  = self._hq_field(f, "Job Title *",   5)

        tk.Label(f, text="Role *", bg=BG_PANEL, fg=TEXT,
                 font=("Segoe UI", 10)).grid(row=6, column=0, sticky="w", padx=14, pady=(8,2))
        role_v = tk.StringVar(value="STAFF")
        ttk.Combobox(f, textvariable=role_v, values=["STAFF","MANAGER","ADMIN"],
                     state="readonly", width=26).grid(row=6, column=1, sticky="ew", padx=(4,14), pady=(8,2))

        tk.Label(f, text="Branch ID *", bg=BG_PANEL, fg=TEXT,
                 font=("Segoe UI", 10)).grid(row=7, column=0, sticky="w", padx=14, pady=(8,2))
        branch_v = tk.StringVar(value="1")
        branches = []
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT branch_id, branch_name FROM branch ORDER BY branch_id")
            branches = cur.fetchall()
            cur.close(); conn.close()
        except Exception:
            pass
        branch_names = [f"{b['branch_id']} — {b['branch_name']}" for b in branches] or ["1 — Branch 1"]
        branch_map   = {f"{b['branch_id']} — {b['branch_name']}": b["branch_id"] for b in branches} if branches else {"1 — Branch 1": 1}
        ttk.Combobox(f, textvariable=branch_v, values=branch_names,
                     state="readonly", width=26).grid(row=7, column=1, sticky="ew", padx=(4,14), pady=(8,2))
        if branch_names:
            branch_v.set(branch_names[0])

        pay_e = self._hq_field(f, "Hourly Rate (Staff)\nor Salary (Mgr/Admin)", 8)

        def submit():
            first = first_e.get().strip(); last = last_e.get().strip()
            email = email_e.get().strip(); username = user_e.get().strip()
            password = pass_e.get().strip(); title = title_e.get().strip()
            role  = role_v.get()
            bid   = branch_map.get(branch_v.get(), 1)
            if not all([first, last, email, username, password, title]):
                messagebox.showerror("Missing Fields", "All starred fields are required.", parent=win)
                return
            try:
                pay = float(pay_e.get())
            except ValueError:
                messagebox.showerror("Error", "Pay must be a number.", parent=win); return
            hourly = pay if role == "STAFF" else None
            salary = pay if role in ("MANAGER", "ADMIN") else None
            ok, msg = register_user(
                first_name=first, last_name=last, email=email,
                phone=None, username=username, password=password, role=role,
                branch_id=bid, job_title=title,
                hourly_rate=hourly, salary=salary,
            )
            if ok:
                messagebox.showinfo("Created", f"Account created.\nUsername: {username}  Role: {role}", parent=win)
                win.destroy()
                self.show_tab("Employees")
            else:
                messagebox.showerror("Error", msg, parent=win)

        tk.Button(win, text="Create Account", bg="#0F2419", fg=GREEN,
                  font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2",
                  command=submit).pack(fill="x", padx=14, pady=(14,4))

    def _hq_change_role_dialog(self):
        """Admin changes the login role of a selected employee."""
        tree = getattr(self, "_hq_emp_tree", None)
        if tree is None or not tree.selection():
            messagebox.showinfo("Select Row", "Select an employee row first.")
            return
        row = tree.item(tree.selection()[0], "values")
        person_id = int(row[0]); emp_name = row[1]

        if not MYSQL_AVAILABLE:
            messagebox.showerror("Unavailable", "Database not connected.")
            return

        # look up existing role
        cur_role = "STAFF"
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT role FROM user_account WHERE person_id = %s", (person_id,))
            ua = cur.fetchone()
            if ua:
                cur_role = ua["role"]
            cur.close(); conn.close()
        except Exception:
            pass

        win = self._hq_dialog("Change Role", 360, 230)
        f = tk.Frame(win, bg=BG_PANEL)
        f.pack(fill="both", expand=True, padx=14, pady=14)
        tk.Label(f, text=emp_name, bg=BG_PANEL, fg=GOLD,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(f, text=f"Current role: {cur_role}", bg=BG_PANEL, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(4,12))
        role_v = tk.StringVar(value=cur_role)
        ttk.Combobox(f, textvariable=role_v, values=["STAFF","MANAGER","ADMIN"],
                     state="readonly", font=("Segoe UI", 11)).pack(fill="x", pady=(0,12))

        def submit():
            new_role = role_v.get()
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("UPDATE user_account SET role = %s WHERE person_id = %s",
                            (new_role, person_id))
                conn.commit()
                cur.close(); conn.close()
                messagebox.showinfo("Updated", f"Role changed to {new_role}.", parent=win)
                win.destroy()
                self.show_tab("Employees")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=win)

        tk.Button(win, text="Update Role", bg="#0F2419", fg=GREEN,
                  font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2",
                  command=submit).pack(fill="x", pady=4)

    # ══════════════════════════════════════════════════════════════════════════
    # 4.  ORDERS TAB  (HQ spec section 4)
    # ══════════════════════════════════════════════════════════════════════════

    def build_orders_view(self):

        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Orders", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  flow_db.orders  (all branches)", bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Orders")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        cols = ("id", "branch", "status", "datetime", "total")
        tree = ttk.Treeview(self.content_frame, columns=cols, show="headings",
                            style="Flow.Treeview", height=20)
        col_setup = [
            ("id",       "Order ID",      80),
            ("branch",   "Branch",        260),
            ("status",   "Status",        130),
            ("datetime", "Order Time",    180),
            ("total",    "Total Amount",  130)
        ]
        for col_id, heading, width in col_setup:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        rows = self.load_orders()

        in_progress = 0
        for r in rows:
            # tag rows by status so we can color them
            tag = r["order_status"].lower()
            if r["order_status"] == "IN_PROGRESS":
                in_progress += 1

            tree.insert("", "end", tag=tag, values=(r["order_id"],
                                                     r["branch_name"],
                                                     r["order_status"],
                                                     str(r["order_datetime"]),
                                                     f"${float(r['total_amount']):,.2f}"))

        # color tags: in progress = gold, served = green, completed = muted, cancelled = red
        tree.tag_configure("in_progress", foreground=GOLD)
        tree.tag_configure("served",      foreground=GREEN)
        tree.tag_configure("completed",   foreground=MUTED)
        tree.tag_configure("cancelled",   foreground=RED)
        tree.pack(fill="both", expand=True)

        footer = tk.Frame(self.content_frame, bg=BG_DARK)
        footer.pack(fill="x", pady=(8, 0))
        tk.Label(footer, text=f"{len(rows)} orders shown", bg=BG_DARK,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        tk.Label(footer, text=f"{in_progress} in progress", bg=BG_DARK,
                 fg=GOLD, font=("Segoe UI", 9, "bold")).pack(side="right")


    def load_orders(self):
        rows = []
        if MYSQL_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    sql = ("SELECT o.order_id, o.order_status, o.order_datetime, "
                           "       o.total_amount, b.branch_name "
                           "FROM orders o "
                           "JOIN branch b ON o.branch_id = b.branch_id "
                           "ORDER BY o.order_datetime DESC "
                           "LIMIT 100")
                    cur.execute(sql)
                    rows = cur.fetchall()
                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"Error loading orders: {e}")
                rows = []

        if len(rows) == 0:
            rows = [
                {"order_id": 1041, "branch_name": "Virginia Beach Boardwalk", "order_status": "IN_PROGRESS", "order_datetime": "2026-04-29 18:42:10", "total_amount": 67.40},
                {"order_id": 1040, "branch_name": "Norfolk Waterside",        "order_status": "SERVED",      "order_datetime": "2026-04-29 18:38:04", "total_amount": 42.15},
                {"order_id": 1039, "branch_name": "Hampton Pier",             "order_status": "IN_PROGRESS", "order_datetime": "2026-04-29 18:35:50", "total_amount": 88.20},
                {"order_id": 1038, "branch_name": "Chesapeake Bay",           "order_status": "COMPLETED",   "order_datetime": "2026-04-29 18:30:21", "total_amount": 51.75},
                {"order_id": 1037, "branch_name": "Virginia Beach Boardwalk", "order_status": "IN_PROGRESS", "order_datetime": "2026-04-29 18:28:11", "total_amount": 33.10},
                {"order_id": 1036, "branch_name": "Norfolk Waterside",        "order_status": "COMPLETED",   "order_datetime": "2026-04-29 18:24:55", "total_amount": 76.80},
                {"order_id": 1035, "branch_name": "Hampton Pier",             "order_status": "CANCELLED",   "order_datetime": "2026-04-29 18:20:33", "total_amount":  0.00},
                {"order_id": 1034, "branch_name": "Chesapeake Bay",           "order_status": "SERVED",      "order_datetime": "2026-04-29 18:18:14", "total_amount": 49.20},
                {"order_id": 1033, "branch_name": "Virginia Beach Boardwalk", "order_status": "COMPLETED",   "order_datetime": "2026-04-29 18:15:02", "total_amount": 92.50},
                {"order_id": 1032, "branch_name": "Norfolk Waterside",        "order_status": "IN_PROGRESS", "order_datetime": "2026-04-29 18:12:45", "total_amount": 28.95}
            ]
        return rows


    # ══════════════════════════════════════════════════════════════════════════
    # 5.  RESERVATIONS TAB  (HQ spec section 5)
    # ══════════════════════════════════════════════════════════════════════════

    def build_reservations_view(self):

        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Reservations", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  flow_db.reservation  (today, all branches)",
                 bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Reservations")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        cols = ("id", "datetime", "branch", "party_size", "status")
        tree = ttk.Treeview(self.content_frame, columns=cols, show="headings",
                            style="Flow.Treeview", height=20)
        col_setup = [
            ("id",         "ID",          70),
            ("datetime",   "Date/Time",   180),
            ("branch",     "Branch",      260),
            ("party_size", "Party Size",  100),
            ("status",     "Status",      130)
        ]
        for col_id, heading, width in col_setup:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        rows = self.load_reservations()

        seated = 0
        confirmed = 0
        for r in rows:
            tag = r["status"].lower()
            if r["status"] == "SEATED":
                seated += 1
            elif r["status"] == "CONFIRMED":
                confirmed += 1

            tree.insert("", "end", tag=tag, values=(r["reservation_id"],
                                                     str(r["reservation_datetime"]),
                                                     r["branch_name"],
                                                     r["party_size"],
                                                     r["status"]))

        tree.tag_configure("seated",    foreground=GREEN)
        tree.tag_configure("confirmed", foreground=GOLD)
        tree.tag_configure("pending",   foreground=MUTED)
        tree.tag_configure("cancelled", foreground=RED)
        tree.tag_configure("completed", foreground=MUTED)
        tree.pack(fill="both", expand=True)

        footer = tk.Frame(self.content_frame, bg=BG_DARK)
        footer.pack(fill="x", pady=(8, 0))
        tk.Label(footer, text=f"{len(rows)} reservations today", bg=BG_DARK,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        right_text = f"{seated} seated   ·   {confirmed} confirmed"
        tk.Label(footer, text=right_text, bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="right")


    def load_reservations(self):
        rows = []
        if MYSQL_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    sql = ("SELECT r.reservation_id, r.reservation_datetime, "
                           "       r.party_size, r.status, b.branch_name "
                           "FROM reservation r "
                           "JOIN branch b ON r.branch_id = b.branch_id "
                           "WHERE DATE(r.reservation_datetime) = CURDATE() "
                           "ORDER BY r.reservation_datetime ASC")
                    cur.execute(sql)
                    rows = cur.fetchall()
                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"Error loading reservations: {e}")
                rows = []

        if len(rows) == 0:
            rows = [
                {"reservation_id": 501, "reservation_datetime": "2026-04-29 17:30:00", "party_size": 4, "status": "SEATED",    "branch_name": "Virginia Beach Boardwalk"},
                {"reservation_id": 502, "reservation_datetime": "2026-04-29 18:00:00", "party_size": 6, "status": "CONFIRMED", "branch_name": "Norfolk Waterside"},
                {"reservation_id": 503, "reservation_datetime": "2026-04-29 18:15:00", "party_size": 2, "status": "SEATED",    "branch_name": "Hampton Pier"},
                {"reservation_id": 504, "reservation_datetime": "2026-04-29 18:30:00", "party_size": 4, "status": "CONFIRMED", "branch_name": "Chesapeake Bay"},
                {"reservation_id": 505, "reservation_datetime": "2026-04-29 19:00:00", "party_size": 8, "status": "CONFIRMED", "branch_name": "Virginia Beach Boardwalk"},
                {"reservation_id": 506, "reservation_datetime": "2026-04-29 19:00:00", "party_size": 3, "status": "PENDING",   "branch_name": "Norfolk Waterside"},
                {"reservation_id": 507, "reservation_datetime": "2026-04-29 19:30:00", "party_size": 5, "status": "CONFIRMED", "branch_name": "Hampton Pier"},
                {"reservation_id": 508, "reservation_datetime": "2026-04-29 20:00:00", "party_size": 2, "status": "CONFIRMED", "branch_name": "Chesapeake Bay"},
                {"reservation_id": 509, "reservation_datetime": "2026-04-29 20:30:00", "party_size": 6, "status": "CONFIRMED", "branch_name": "Virginia Beach Boardwalk"},
                {"reservation_id": 510, "reservation_datetime": "2026-04-29 21:00:00", "party_size": 4, "status": "PENDING",   "branch_name": "Norfolk Waterside"}
            ]
        return rows


    # ══════════════════════════════════════════════════════════════════════════
    # 6.  INVENTORY ALERTS TAB  (HQ spec section 6)
    # ══════════════════════════════════════════════════════════════════════════

    def build_inventory_view(self):

        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Inventory Alerts", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  flow_db.inventory_item  (qty < reorder)",
                 bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Inventory")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        cols = ("item", "branch", "qty", "unit", "reorder", "supplier")
        tree = ttk.Treeview(self.content_frame, columns=cols, show="headings",
                            style="Flow.Treeview", height=20)
        col_setup = [
            ("item",     "Item",         220),
            ("branch",   "Branch",       240),
            ("qty",      "Qty on Hand",  110),
            ("unit",     "Unit",         70),
            ("reorder",  "Reorder Lvl",  110),
            ("supplier", "Supplier",     180)
        ]
        for col_id, heading, width in col_setup:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        rows = self.load_low_inventory()

        for r in rows:
            supplier = r["supplier_name"]
            if supplier is None:
                supplier = "—"
            tree.insert("", "end", tag="low", values=(r["item_name"],
                                                       r["branch_name"],
                                                       r["quantity_on_hand"],
                                                       r["unit_type"],
                                                       r["reorder_level"],
                                                       supplier))

        # every row in this view is by definition low stock, paint them all red
        tree.tag_configure("low", foreground=RED)
        tree.pack(fill="both", expand=True)

        footer = tk.Frame(self.content_frame, bg=BG_DARK)
        footer.pack(fill="x", pady=(8, 0))
        tk.Label(footer, text=f"{len(rows)} items below reorder level",
                 bg=BG_DARK, fg=RED, font=("Segoe UI", 9, "bold")
                 ).pack(side="left")


    def load_low_inventory(self):
        rows = []
        if MYSQL_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    sql = ("SELECT ii.item_name, ii.quantity_on_hand, ii.unit_type, "
                           "       ii.reorder_level, b.branch_name, s.supplier_name "
                           "FROM inventory_item ii "
                           "JOIN branch b   ON ii.branch_id   = b.branch_id "
                           "LEFT JOIN supplier s ON ii.supplier_id = s.supplier_id "
                           "WHERE ii.quantity_on_hand < ii.reorder_level "
                           "ORDER BY b.branch_name, ii.item_name")
                    cur.execute(sql)
                    rows = cur.fetchall()
                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"Error loading low inventory: {e}")
                rows = []

        if len(rows) == 0:
            rows = [
                {"item_name": "Shrimp",        "branch_name": "Hampton Pier",             "quantity_on_hand": 8,  "unit_type": "LB",   "reorder_level": 30, "supplier_name": "Atlantic Seafood"},
                {"item_name": "Heavy Cream",   "branch_name": "Chesapeake Bay",           "quantity_on_hand": 2,  "unit_type": "GAL",  "reorder_level":  4, "supplier_name": "Coastal Dairy"},
                {"item_name": "Butter",        "branch_name": "Chesapeake Bay",           "quantity_on_hand": 5,  "unit_type": "LB",   "reorder_level": 12, "supplier_name": "Coastal Dairy"},
                {"item_name": "Sweet Tea Mix", "branch_name": "Virginia Beach Boardwalk", "quantity_on_hand": 3,  "unit_type": "CASE", "reorder_level":  5, "supplier_name": None},
                {"item_name": "Lemons",        "branch_name": "Norfolk Waterside",        "quantity_on_hand": 12, "unit_type": "EA",   "reorder_level": 20, "supplier_name": "Garden Greens"},
                {"item_name": "Salmon Filet",  "branch_name": "Norfolk Waterside",        "quantity_on_hand": 6,  "unit_type": "LB",   "reorder_level": 20, "supplier_name": "Atlantic Seafood"}
            ]
        return rows


    # ══════════════════════════════════════════════════════════════════════════
    # 7.  REVIEWS TAB  (HQ spec section 7)
    #     reads from MongoDB first, falls back to MySQL `review` table
    # ══════════════════════════════════════════════════════════════════════════

    def build_reviews_view(self):

        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Customer Reviews", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  reviews + sentiment", bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Reviews")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        cols = ("rating", "branch", "sentiment", "comment", "date")
        tree = ttk.Treeview(self.content_frame, columns=cols, show="headings",
                            style="Flow.Treeview", height=20)
        col_setup = [
            ("rating",    "Rating",     80),
            ("branch",    "Branch",     220),
            ("sentiment", "Sentiment",  100),
            ("comment",   "Comment",    520),
            ("date",      "Date",       110)
        ]
        for col_id, heading, width in col_setup:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        rows = self.load_reviews()

        rating_sum   = 0
        rating_count = 0

        for r in rows:
            # turn the numeric rating into stars
            stars = "★" * int(r["rating"]) + "☆" * (5 - int(r["rating"]))

            # sentiment text + tag for color
            if r["sentiment_score"] is None:
                sent_text = "—"
                tag = "neutral"
            else:
                sent_text = f"{r['sentiment_score']:+.2f}"
                if r["sentiment_score"] >= 0.25:
                    tag = "positive"
                elif r["sentiment_score"] <= -0.25:
                    tag = "negative"
                else:
                    tag = "neutral"

            comment = r["comments"]
            if comment is None or comment == "":
                comment = "—"

            tree.insert("", "end", tag=tag, values=(stars,
                                                     r["branch_name"],
                                                     sent_text,
                                                     comment,
                                                     str(r["created_at"])[:10]))
            rating_sum   += r["rating"]
            rating_count += 1

        tree.tag_configure("positive", foreground=GREEN)
        tree.tag_configure("negative", foreground=RED)
        tree.tag_configure("neutral",  foreground=TEXT)
        tree.pack(fill="both", expand=True)

        footer = tk.Frame(self.content_frame, bg=BG_DARK)
        footer.pack(fill="x", pady=(8, 0))
        tk.Label(footer, text=f"{len(rows)} reviews shown", bg=BG_DARK,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        if rating_count > 0:
            avg = rating_sum / rating_count
            tk.Label(footer, text=f"Average: {avg:.2f} / 5", bg=BG_DARK,
                     fg=GOLD, font=("Segoe UI", 9, "bold")).pack(side="right")


    def load_reviews(self):
        rows = []

        # Mongo first, since the project intent is reviews live in NoSQL
        if MONGO_AVAILABLE:
            try:
                client = MongoClient("mongodb://localhost:27017/",
                                     serverSelectionTimeoutMS=1000)
                db  = client["flow_db"]
                col = db["reviews"]
                cursor = col.find().sort("created_at", -1).limit(30)
                for d in cursor:
                    rows.append({
                        "rating":          int(d.get("rating", 0)),
                        "branch_name":     d.get("branch_name", "—"),
                        "sentiment_score": d.get("sentiment_score"),
                        "comments":        d.get("comments", ""),
                        "created_at":      d.get("created_at", "")
                    })
                client.close()
                if len(rows) > 0:
                    return rows
            except Exception as e:
                print(f"Mongo reviews error: {e}")
                rows = []

        # fall back to MySQL review table
        if MYSQL_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    sql = ("SELECT rv.rating, rv.comments, rv.sentiment_score, "
                           "       rv.created_at, b.branch_name "
                           "FROM review rv "
                           "JOIN branch b ON rv.branch_id = b.branch_id "
                           "ORDER BY rv.created_at DESC "
                           "LIMIT 30")
                    cur.execute(sql)
                    rows = cur.fetchall()
                    # tidy types
                    for r in rows:
                        if r["sentiment_score"] is not None:
                            r["sentiment_score"] = float(r["sentiment_score"])
                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"MySQL reviews error: {e}")
                rows = []

        if len(rows) == 0:
            rows = [
                {"rating": 5, "branch_name": "Virginia Beach Boardwalk", "sentiment_score":  0.85, "comments": "Best she-crab soup I have ever had. Will be back.",         "created_at": "2026-04-28"},
                {"rating": 4, "branch_name": "Norfolk Waterside",        "sentiment_score":  0.55, "comments": "Solid food, slow service though.",                          "created_at": "2026-04-28"},
                {"rating": 5, "branch_name": "Hampton Pier",             "sentiment_score":  0.92, "comments": "Loved the view and the shrimp tasted incredible.",          "created_at": "2026-04-27"},
                {"rating": 2, "branch_name": "Chesapeake Bay",           "sentiment_score": -0.62, "comments": "Order took over an hour. Server seemed overwhelmed.",       "created_at": "2026-04-27"},
                {"rating": 4, "branch_name": "Virginia Beach Boardwalk", "sentiment_score":  0.40, "comments": "Good vibes. A little pricey but portions were generous.",   "created_at": "2026-04-26"},
                {"rating": 3, "branch_name": "Hampton Pier",             "sentiment_score":  0.05, "comments": "Decent. Nothing special.",                                  "created_at": "2026-04-26"},
                {"rating": 5, "branch_name": "Norfolk Waterside",        "sentiment_score":  0.78, "comments": "Bartender was awesome. Great drinks.",                      "created_at": "2026-04-25"},
                {"rating": 1, "branch_name": "Chesapeake Bay",           "sentiment_score": -0.88, "comments": "Cold food and a rude host. Will not return.",               "created_at": "2026-04-25"},
                {"rating": 4, "branch_name": "Virginia Beach Boardwalk", "sentiment_score":  0.50, "comments": "Brunch was great. Mimosas were a bit weak.",                "created_at": "2026-04-24"},
                {"rating": 5, "branch_name": "Hampton Pier",             "sentiment_score":  0.95, "comments": "Anniversary dinner. Staff went above and beyond.",          "created_at": "2026-04-24"}
            ]
        return rows


    # ══════════════════════════════════════════════════════════════════════════
    # 8.  STAFFING TAB  (HQ spec section 8 -- optional but included)
    # ══════════════════════════════════════════════════════════════════════════

    def build_staffing_view(self):

        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Staffing Today", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  flow_db.shift_schedule  (today, all branches)",
                 bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Staffing")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        cols = ("employee", "branch", "role", "start", "end")
        tree = ttk.Treeview(self.content_frame, columns=cols, show="headings",
                            style="Flow.Treeview", height=18)
        col_setup = [
            ("employee", "Employee",  220),
            ("branch",   "Branch",    240),
            ("role",     "Role",      150),
            ("start",    "Start",     100),
            ("end",      "End",       100)
        ]
        for col_id, heading, width in col_setup:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        rows = self.load_today_staffing()

        # also tally the headcount per branch for the coverage summary at the bottom
        branch_counts = {}

        for r in rows:
            tree.insert("", "end", values=(r["employee_name"],
                                            r["branch_name"],
                                            r["role_assigned"],
                                            r["start_time"],
                                            r["end_time"]))
            bn = r["branch_name"]
            if bn in branch_counts:
                branch_counts[bn] = branch_counts[bn] + 1
            else:
                branch_counts[bn] = 1

        tree.pack(fill="both", expand=True)

        # branch coverage summary row
        coverage = tk.Frame(self.content_frame, bg=BG_DARK)
        coverage.pack(fill="x", pady=(10, 0))
        tk.Label(coverage, text="Branch Coverage:",
                 bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9, "bold")
                 ).pack(side="left")

        # show one little chip per branch with its headcount
        for bn in branch_counts:
            count = branch_counts[bn]
            chip_color = get_branch_color(bn)
            chip_text = f"  {short_branch_name(bn)}: {count}  "
            tk.Label(coverage, text=chip_text, bg=BG_PANEL, fg=chip_color,
                     font=("Segoe UI", 9, "bold")
                     ).pack(side="left", padx=4, ipadx=4, ipady=2)


    def load_today_staffing(self):
        rows = []
        if MYSQL_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    sql = ("SELECT s.shift_id, "
                           "CONCAT(p.first_name, ' ', p.last_name) AS employee_name, "
                           "b.branch_name, s.role_assigned, "
                           "s.start_time, s.end_time "
                           "FROM shift_schedule s "
                           "JOIN person p ON s.person_id = p.person_id "
                           "JOIN branch b ON s.branch_id = b.branch_id "
                           "WHERE s.shift_date = CURDATE() "
                           "ORDER BY b.branch_name, s.start_time")
                    cur.execute(sql)
                    rows = cur.fetchall()

                    # tidy DB time types
                    for r in rows:
                        r["start_time"] = str(r["start_time"])[:5]
                        r["end_time"]   = str(r["end_time"])[:5]
                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"Error loading staffing: {e}")
                rows = []

        if len(rows) == 0:
            rows = [
                {"employee_name": "Henry Brooks",   "branch_name": "Chesapeake Bay",           "role_assigned": "Cook",      "start_time": "09:00", "end_time": "17:00"},
                {"employee_name": "Linda Park",     "branch_name": "Chesapeake Bay",           "role_assigned": "Manager",   "start_time": "10:00", "end_time": "18:00"},
                {"employee_name": "Marcus Hill",    "branch_name": "Hampton Pier",             "role_assigned": "Manager",   "start_time": "10:00", "end_time": "20:00"},
                {"employee_name": "Tyrone Green",   "branch_name": "Hampton Pier",             "role_assigned": "Busser",    "start_time": "11:00", "end_time": "19:00"},
                {"employee_name": "Tasha King",     "branch_name": "Norfolk Waterside",        "role_assigned": "Manager",   "start_time": "10:00", "end_time": "20:00"},
                {"employee_name": "Devon Carter",   "branch_name": "Norfolk Waterside",        "role_assigned": "Host",      "start_time": "16:00", "end_time": "22:00"},
                {"employee_name": "Brianna Smith",  "branch_name": "Norfolk Waterside",        "role_assigned": "Bartender", "start_time": "17:00", "end_time": "23:00"},
                {"employee_name": "Pat Reyes",      "branch_name": "Virginia Beach Boardwalk", "role_assigned": "Manager",   "start_time": "10:00", "end_time": "20:00"},
                {"employee_name": "Janet Pierce",   "branch_name": "Virginia Beach Boardwalk", "role_assigned": "Server",    "start_time": "10:00", "end_time": "16:00"},
                {"employee_name": "Marcus Lin",     "branch_name": "Virginia Beach Boardwalk", "role_assigned": "Cook",      "start_time": "09:00", "end_time": "17:00"}
            ]
        return rows


    # ══════════════════════════════════════════════════════════════════════════
    # 9.  ANALYTICS TAB  (kept from admin_ui)
    #     visual revenue comparison with bars for each branch
    # ══════════════════════════════════════════════════════════════════════════

    def build_analytics_view(self):

        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Analytics", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  branch revenue comparison (last 30 days)",
                 bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9, "italic")
                 ).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Analytics")
                  ).pack(side="right", padx=4, ipadx=8, ipady=4)

        rows = self.load_30day_performance()

        # work out the leader so we can scale the bars
        max_revenue = 0.0
        for r in rows:
            if r["revenue_30d"] > max_revenue:
                max_revenue = r["revenue_30d"]
        if max_revenue <= 0:
            max_revenue = 1.0

        for r in rows:
            self.draw_analytics_card(r, max_revenue)

        footer = tk.Frame(self.content_frame, bg=BG_DARK)
        footer.pack(fill="x", pady=(10, 0))
        tk.Label(footer, text="Bar shows revenue relative to top branch",
                 bg=BG_DARK, fg=MUTED, font=("Segoe UI", 8, "italic")
                 ).pack(side="left")


    def draw_analytics_card(self, r, max_revenue):
        card = tk.Frame(self.content_frame, bg=BG_PANEL,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", pady=4, ipady=8)

        # color stripe by branch
        stripe_color = get_branch_color(r["branch_name"])
        stripe = tk.Frame(card, bg=stripe_color, width=4)
        stripe.pack(side="left", fill="y")

        left = tk.Frame(card, bg=BG_PANEL)
        left.pack(side="left", padx=14, pady=4)
        tk.Label(left, text=r["branch_name"], bg=BG_PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        manager = r["manager_name"]
        if manager is None or manager == "":
            manager = "(unassigned)"
        tk.Label(left, text="Manager: " + manager, bg=BG_PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")

        right = tk.Frame(card, bg=BG_PANEL)
        right.pack(side="right", fill="x", expand=True, padx=14, pady=4)

        nums = tk.Frame(right, bg=BG_PANEL)
        nums.pack(fill="x")

        rev_text = f"Revenue: ${r['revenue_30d']:,.2f}"
        ord_text = f"Orders: {r['order_count']}"
        rating   = r["avg_rating"]
        if rating is None:
            rating_text = "Avg Rating: —"
        else:
            rating_text = f"Avg Rating: {rating:.2f} / 5"

        rating_color = TEXT
        if rating is not None:
            if rating >= 4.2:
                rating_color = GREEN
            elif rating < 3.5:
                rating_color = RED

        tk.Label(nums, text=rev_text, bg=BG_PANEL, fg=GOLD,
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 16))
        tk.Label(nums, text=ord_text, bg=BG_PANEL, fg=TEXT,
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 16))
        tk.Label(nums, text=rating_text, bg=BG_PANEL, fg=rating_color,
                 font=("Segoe UI", 10)).pack(side="left")

        # revenue bar canvas
        bar = tk.Canvas(right, bg=BG_PANEL, height=14, bd=0,
                        highlightthickness=0)
        bar.pack(fill="x", pady=(6, 2))

        bar.update_idletasks()
        full_width = bar.winfo_width()
        if full_width <= 1:
            full_width = 600

        ratio = r["revenue_30d"] / max_revenue
        if ratio < 0:
            ratio = 0
        if ratio > 1:
            ratio = 1
        fill_w = int(full_width * ratio)

        bar.create_rectangle(0, 0, full_width, 14, fill=BG_HOVER, outline="")
        bar.create_rectangle(0, 0, fill_w, 14, fill=GOLD, outline="")


    def load_30day_performance(self):
        rows = []
        if MYSQL_AVAILABLE:
            try:
                conn = get_connection()
                if conn is not None:
                    cur = conn.cursor(dictionary=True)
                    sql = ("SELECT b.branch_id, b.branch_name, "
                           "CONCAT(p.first_name, ' ', p.last_name) AS manager_name, "
                           "(SELECT COALESCE(SUM(o.total_amount), 0) FROM orders o "
                           "  WHERE o.branch_id = b.branch_id "
                           "    AND o.order_datetime >= NOW() - INTERVAL 30 DAY) AS revenue_30d, "
                           "(SELECT COUNT(*) FROM orders o "
                           "  WHERE o.branch_id = b.branch_id "
                           "    AND o.order_datetime >= NOW() - INTERVAL 30 DAY) AS order_count, "
                           "(SELECT AVG(r.rating) FROM review r "
                           "  WHERE r.branch_id = b.branch_id "
                           "    AND r.created_at >= NOW() - INTERVAL 30 DAY) AS avg_rating "
                           "FROM branch b "
                           "LEFT JOIN person p ON b.manager_id = p.person_id "
                           "ORDER BY revenue_30d DESC")
                    cur.execute(sql)
                    rows = cur.fetchall()
                    for r in rows:
                        r["revenue_30d"] = float(r["revenue_30d"])
                        if r["avg_rating"] is not None:
                            r["avg_rating"] = float(r["avg_rating"])
                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"Error loading 30-day performance: {e}")
                rows = []

        if len(rows) == 0:
            rows = [
                {"branch_id": 1, "branch_name": "Virginia Beach Boardwalk", "manager_name": "Pat Reyes",   "revenue_30d": 96420.50, "order_count": 1820, "avg_rating": 4.4},
                {"branch_id": 2, "branch_name": "Norfolk Waterside",        "manager_name": "Tasha King",  "revenue_30d": 78310.25, "order_count": 1510, "avg_rating": 4.1},
                {"branch_id": 3, "branch_name": "Hampton Pier",             "manager_name": "Marcus Hill", "revenue_30d": 64880.10, "order_count": 1290, "avg_rating": 3.9},
                {"branch_id": 4, "branch_name": "Chesapeake Bay",           "manager_name": "Linda Park",  "revenue_30d": 58220.75, "order_count": 1145, "avg_rating": 3.4}
            ]
        return rows


    # ══════════════════════════════════════════════════════════════════════════
    # SIGN OUT
    # ══════════════════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════════════════
    # CLICKSTREAM TAB  — menu browsing analytics from MongoDB
    # ══════════════════════════════════════════════════════════════════════════

    def build_clickstream_view(self):
        head = tk.Frame(self.content_frame, bg=BG_DARK)
        head.pack(fill="x", pady=(0, 14))
        tk.Label(head, text="Clickstream Analytics", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, text="·  menu browsing behavior",
                 bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9, "italic")).pack(side="left", padx=8, pady=(8,0))
        tk.Button(head, text="Refresh", bg=BG_PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self.show_tab("Clickstream")).pack(side="right", ipadx=8, ipady=4)

        # ── load data from MongoDB ──────────────────────────────────────────
        events = []
        if MONGO_AVAILABLE:
            try:
                client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
                db = client["flow_db"]
                cursor = db.clickstream.find(
                    {"event_type": "menu_view"},
                    {"_id": 0, "category": 1, "items_viewed": 1, "item_count": 1, "timestamp": 1}
                ).sort("timestamp", -1).limit(500)
                events = list(cursor)
            except Exception as e:
                print(f"[HQ] Clickstream load error: {e}")

        if not events:
            tk.Label(self.content_frame,
                     text="No clickstream data yet.\nBrowse the customer menu at http://127.0.0.1:5001 to generate events.",
                     bg=BG_DARK, fg=MUTED, font=("Segoe UI", 12), justify="center").pack(expand=True)
            return

        # ── Category breakdown ──────────────────────────────────────────────
        cat_counts = {}
        item_counts = {}
        for ev in events:
            cat = ev.get("category") or "Unknown"
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            for item in (ev.get("items_viewed") or []):
                name = item.get("name") or "?"
                item_counts[name] = item_counts.get(name, 0) + 1

        tk.Label(self.content_frame, text="Category Browse Frequency",
                 bg=BG_DARK, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0,6))

        bar_frame = tk.Frame(self.content_frame, bg=BG_DARK)
        bar_frame.pack(fill="x", pady=(0, 18))
        max_cat = max(cat_counts.values()) if cat_counts else 1
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
            row = tk.Frame(bar_frame, bg=BG_DARK)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=cat, bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9),
                     width=18, anchor="w").pack(side="left")
            bar_w = max(4, int((cnt / max_cat) * 300))
            tk.Frame(row, bg=GOLD, height=16, width=bar_w).pack(side="left")
            tk.Label(row, text=f"  {cnt} views", bg=BG_DARK, fg=TEXT,
                     font=("Segoe UI", 9)).pack(side="left")

        # ── Top browsed items ───────────────────────────────────────────────
        tk.Label(self.content_frame, text="Most Viewed Menu Items",
                 bg=BG_DARK, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0,6))

        cols = ("item", "views")
        tree_f = tk.Frame(self.content_frame, bg=BG_DARK)
        tree_f.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(tree_f, orient="vertical")
        sb.pack(side="right", fill="y")
        tree = ttk.Treeview(tree_f, columns=cols, show="headings",
                            style="Flow.Treeview", height=12, yscrollcommand=sb.set)
        sb.config(command=tree.yview)
        tree.pack(fill="both", expand=True)
        tree.heading("item",  text="Menu Item")
        tree.heading("views", text="Times Viewed")
        tree.column("item",  width=300, anchor="w")
        tree.column("views", width=120, anchor="center")
        for name, cnt in sorted(item_counts.items(), key=lambda x: -x[1])[:50]:
            tree.insert("", "end", values=(name, cnt))

        tk.Label(self.content_frame,
                 text=f"{len(events)} browse events recorded  ·  {len(item_counts)} unique items seen",
                 bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(8,0))

    def sign_out(self):
        if not messagebox.askyesno("Sign Out", "Sign out of FLOW?"):
            return
        # killing the window also stops the after() refresh chain
        self.destroy()
        try:
            from login import LoginScreen
            login_win = LoginScreen()
            login_win.mainloop()
        except Exception as e:
            print(f"Error returning to login: {e}")


# minimal driver -- lets you run HQ_ui.py directly for testing
if __name__ == "__main__":
    app = HQDashboard(admin_name="Admin")
    app.mainloop()
