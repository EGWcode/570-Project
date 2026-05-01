# manager_ui.py
# Created by Zoe Battle
# Extended by Day Ekoi
#
#     FLOW - Enterprise Restaurant Management System
#
# Tabs:
#   Inventory  – view + add item + adjust quantity
#   Suppliers  – view + add supplier
#   Schedule   – view + add shift + delete shift
#   Employees  – view all + add employee (creates login account) + set status
#   Menu       – view + add item + toggle active/inactive
#   Analytics  – branch summary + top items + sales report

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date

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

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

try:
    from config.db_config import get_connection
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False

try:
    from backend.employee import get_all_employees, update_employee_status
    from backend.auth import register_user
    from backend.manager import (
        get_menu_items, add_menu_item, toggle_menu_item_status,
        get_sales_report, get_top_menu_items, get_all_branches,
        get_branch_summary, add_supplier, update_menu_item,
        get_food_cost_percentage, get_labor_report, get_sales_by_hour,
        get_payroll_summary,
    )
    from backend.inventory import (
        get_inventory_by_branch, add_inventory_item,
        update_inventory_quantity, get_all_suppliers,
    )
    from backend.reviews import get_recent_reviews
    from backend.shifts import get_shifts_by_branch, create_shift, delete_shift
    BACKEND_AVAILABLE = True
except Exception as _be:
    BACKEND_AVAILABLE = False
    print(f"Manager UI backend import error: {_be}")

# ── Color palette ─────────────────────────────────────────────────────────────
BG_DARK  = "#0D1117"
BG_PANEL = "#161B22"
BG_HOVER = "#1F2530"
GOLD     = "#D4A843"
TEXT     = "#E6EDF3"
MUTED    = "#8B949E"
BORDER   = "#30363D"
RED      = "#F85149"
GREEN    = "#3FB950"

STAFF_JOB_ROLES = ["Server", "Waiter", "Cook", "Bartender", "Host", "Busser", "Cashier", "Dishwasher"]
UNIT_TYPES      = ["LB", "LBS", "OZ", "GAL", "L", "KG", "G", "ML", "CASE", "CASES", "PACK", "PACKS", "EA"]
MENU_CATEGORIES = ["Appetizers", "Above Sea", "Sea Level", "Under the Sea", "Sides", "Drinks", "Desserts"]
EMP_STATUSES    = ["ACTIVE", "INACTIVE", "LEAVE", "TERMINATED"]

TABS = ["Inventory", "Suppliers", "Schedule", "Employees", "Menu", "Analytics", "Reviews"]


# ══════════════════════════════════════════════════════════════════════════════
class ManagerUI(tk.Tk):

    def __init__(self, manager_name="Manager", branch_id=1):
        super().__init__()
        self.manager_name = manager_name
        self.branch_id    = branch_id

        self.title("FLOW - Manager")
        self.configure(bg=BG_DARK)
        self.geometry("1360x760")
        try:
            self.state("zoomed")
        except tk.TclError:
            pass

        self.current_tab   = None
        self.content_frame = None
        self._inv_refresh_job = None
        self._inv_last_updated_var = tk.StringVar(value="")
        self._setup_style()
        self._build_shell()
        self.show_tab("Inventory")

    @classmethod
    def with_name(cls, manager_name):
        return cls(manager_name=manager_name, branch_id=1)

    # ── Style ────────────────────────────────────────────────────────────────
    def _setup_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Flow.Treeview",
                    background=BG_PANEL, foreground=TEXT,
                    fieldbackground=BG_PANEL, rowheight=26,
                    bordercolor=BORDER, borderwidth=0,
                    font=("Segoe UI", 10))
        s.configure("Flow.Treeview.Heading",
                    background=BG_HOVER, foreground=GOLD,
                    font=("Segoe UI", 9, "bold"), relief="flat")
        s.map("Flow.Treeview",
              background=[("selected", "#2A3441")],
              foreground=[("selected", TEXT)])
        # Dark styling for all Combobox widgets so text is always visible
        s.configure("TCombobox",
                    fieldbackground=BG_DARK, background=BG_PANEL,
                    foreground=TEXT, selectforeground=TEXT,
                    selectbackground=BG_HOVER, bordercolor=BORDER,
                    arrowcolor=GOLD, insertcolor=TEXT)
        s.map("TCombobox",
              fieldbackground=[("readonly", BG_DARK), ("disabled", BG_PANEL)],
              foreground=[("readonly", TEXT), ("disabled", MUTED)],
              background=[("readonly", BG_PANEL), ("active", BG_HOVER)],
              arrowcolor=[("readonly", GOLD), ("active", GOLD)])
        # Also apply to Separator and Scrollbar for consistency
        s.configure("TScrollbar", background=BG_PANEL, troughcolor=BG_DARK,
                    arrowcolor=MUTED, bordercolor=BG_DARK)

    # ── Shell (top bar + sidebar + content area) ─────────────────────────────
    def _dark_button(self, parent, text, command, fg=TEXT, bg=BG_PANEL,
                     active_fg=GOLD, active_bg=BG_HOVER, font=("Segoe UI", 10, "bold"),
                     anchor="center"):
        """macOS-safe dark button using Label so Tk cannot repaint it white."""
        btn = tk.Label(parent, text=text, bg=bg, fg=fg, font=font, anchor=anchor,
                       padx=10, pady=7, cursor="hand2", relief="solid", bd=1,
                       highlightthickness=1, highlightbackground=BORDER,
                       highlightcolor=GOLD)
        btn._normal_bg = bg
        btn._normal_fg = fg
        btn._active_bg = active_bg
        btn._active_fg = active_fg
        btn._command = command

        def on_enter(_event):
            btn.config(bg=btn._active_bg, fg=btn._active_fg)

        def on_leave(_event):
            btn.config(bg=btn._normal_bg, fg=btn._normal_fg)

        def on_click(_event):
            if btn._command:
                btn._command()

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.bind("<Button-1>", on_click)
        return btn

    def _build_shell(self):
        topbar = tk.Frame(self, bg=BG_PANEL, height=50)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)
        tk.Label(topbar, text="Soul By The Sea", bg=BG_PANEL,
                 fg=GOLD, font=("Segoe UI", 15, "bold")).pack(side="left", padx=(16,4), pady=12)
        tk.Label(topbar, text="FLOW Manager", bg=BG_PANEL,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="left", pady=12)
        tk.Label(topbar, text=f"Manager: {self.manager_name}  ·  Branch #{self.branch_id}",
                 bg=BG_PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(side="right", padx=16)
        tk.Label(topbar, text=date.today().strftime("%A, %B %d %Y"),
                 bg=BG_PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(side="right", padx=8)

        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=BG_PANEL, width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="MENU", bg=BG_PANEL, fg="#444D56",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(14,8))

        self.tab_buttons = {}
        for label in TABS:
            btn = self._dark_button(sidebar, label, lambda l=label: self.show_tab(l),
                                    fg=TEXT, bg=BG_PANEL, anchor="w",
                                    font=("Segoe UI", 11))
            btn.pack(fill="x", padx=8, pady=3)
            self.tab_buttons[label] = btn

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", pady=10)
        self._dark_button(sidebar, "HQ Access", self._open_hq_access,
                          fg="#A371F7", bg="#1A1030", active_fg="#C9A7FF",
                          active_bg="#241544", font=("Segoe UI", 10, "bold")).pack(side="bottom", fill="x", padx=8, pady=(0, 4))
        self._dark_button(sidebar, "Sign Out", self._sign_out,
                          fg=MUTED, active_fg=RED,
                          font=("Segoe UI", 10, "bold")).pack(side="bottom", fill="x", padx=8, pady=10)

        self.main_area = tk.Frame(body, bg=BG_DARK)
        self.main_area.pack(side="left", fill="both", expand=True)

    # ── Tab switcher ─────────────────────────────────────────────────────────
    def show_tab(self, name):
        # Cancel inventory auto-refresh when leaving that tab
        if self._inv_refresh_job is not None:
            self.after_cancel(self._inv_refresh_job)
            self._inv_refresh_job = None
        self.current_tab = name
        for n, btn in self.tab_buttons.items():
            normal_bg = BG_HOVER if n == name else BG_PANEL
            normal_fg = GOLD if n == name else TEXT
            btn._normal_bg = normal_bg
            btn._normal_fg = normal_fg
            btn.config(fg=normal_fg, bg=normal_bg)
        if self.content_frame:
            self.content_frame.destroy()
        self.content_frame = tk.Frame(self.main_area, bg=BG_DARK)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        {
            "Inventory": self._build_inventory,
            "Suppliers":  self._build_suppliers,
            "Schedule":   self._build_schedule,
            "Employees":  self._build_employees,
            "Menu":       self._build_menu,
            "Analytics":  self._build_analytics,
            "Reviews":    self._build_reviews,
        }[name]()

    # ── Shared helpers ────────────────────────────────────────────────────────
    def _header(self, title, subtitle, *actions):
        """Renders title row with optional action buttons. Returns the frame."""
        row = tk.Frame(self.content_frame, bg=BG_DARK)
        row.pack(fill="x", pady=(0, 10))
        tk.Label(row, text=title, bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        tk.Label(row, text=f"·  {subtitle}", bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9, "italic")).pack(side="left", padx=8, pady=(6,0))
        for (label, cmd) in reversed(actions):
            self._dark_button(row, label, cmd, font=("Segoe UI", 9, "bold")).pack(side="right", padx=4)
        return row

    def _tree(self, cols):
        """Creates a scrollable Treeview. Returns (tree, frame)."""
        frame = tk.Frame(self.content_frame, bg=BG_DARK)
        frame.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(frame, orient="vertical")
        sb.pack(side="right", fill="y")
        tree = ttk.Treeview(frame, columns=cols, show="headings",
                            style="Flow.Treeview", yscrollcommand=sb.set)
        sb.config(command=tree.yview)
        tree.pack(fill="both", expand=True)
        return tree

    def _footer(self, *labels):
        row = tk.Frame(self.content_frame, bg=BG_DARK)
        row.pack(fill="x", pady=(8,0))
        for i, (text, side, color) in enumerate(labels):
            tk.Label(row, text=text, bg=BG_DARK, fg=color or MUTED,
                     font=("Segoe UI", 9)).pack(side=side)

    def _dialog(self, title, width=420, height=480):
        """Returns a styled modal Toplevel."""
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=BG_PANEL)
        win.geometry(f"{width}x{height}")
        win.resizable(False, False)
        win.grab_set()
        return win

    def _field(self, parent, label, row_num, widget_factory=None):
        """Label + entry grid row. Returns the entry widget."""
        tk.Label(parent, text=label, bg=BG_PANEL, fg=TEXT,
                 font=("Segoe UI", 10)).grid(row=row_num, column=0,
                 sticky="w", padx=14, pady=(8,2))
        if widget_factory:
            w = widget_factory(parent)
        else:
            v = tk.StringVar()
            w = tk.Entry(parent, textvariable=v, bg=BG_DARK, fg=TEXT,
                         insertbackground=TEXT, relief="flat",
                         font=("Segoe UI", 11), width=28)
        w.grid(row=row_num, column=1, sticky="ew", padx=(4,14), pady=(8,2))
        return w

    def _submit_btn(self, parent, text, cmd):
        self._dark_button(parent, text, cmd, fg=GREEN, bg="#0F2419",
                          active_fg=GREEN, active_bg="#1a3a28",
                          font=("Segoe UI", 11, "bold")).pack(fill="x", padx=14, pady=(16,4))

    def _get_branches(self):
        if BACKEND_AVAILABLE:
            rows = get_all_branches()
            if rows:
                return {r["branch_name"]: r["branch_id"] for r in rows}
        return {
            "Soul by the Sea - Hampton": 1,
            "Soul by the Sea - Norfolk": 2,
            "Soul by the Sea - Chesapeake": 3,
        }

    def _get_suppliers_map(self):
        if BACKEND_AVAILABLE:
            rows = get_all_suppliers()
            if rows:
                return {"(none)": None, **{r["supplier_name"]: r["supplier_id"] for r in rows}}
        return {"(none)": None}

    # ══════════════════════════════════════════════════════════════════════════
    # INVENTORY TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_inventory(self):
        self._header("Inventory", "inventory_item",
                     ("Refresh",     lambda: self._refresh_inv_data()),
                     ("Adjust Qty",  self._adjust_qty_dialog),
                     ("Add Item",    self._add_inventory_dialog))

        cols = ("id", "name", "qty", "unit", "reorder", "status", "cost", "supplier")
        tree = self._tree(cols)
        self._inv_tree = tree
        for cid, heading, width in [
            ("id", "ID", 50), ("name", "Item", 220), ("qty", "Qty", 70),
            ("unit", "Unit", 70), ("reorder", "Reorder Lvl", 110),
            ("status", "Status", 150),
            ("cost", "Cost/Unit", 110), ("supplier", "Supplier", 200)
        ]:
            tree.heading(cid, text=heading)
            tree.column(cid, width=width, anchor="w")
        tree.tag_configure("soldout", foreground=RED)
        tree.tag_configure("low", foreground="#F0883E")

        # Footer with live "last updated" timestamp
        foot_row = tk.Frame(self.content_frame, bg=BG_DARK)
        foot_row.pack(fill="x", pady=(8, 0))
        self._inv_count_label = tk.Label(foot_row, text="", bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9))
        self._inv_count_label.pack(side="left")
        self._inv_alert_label = tk.Label(foot_row, text="", bg=BG_DARK, fg=RED, font=("Segoe UI", 9))
        self._inv_alert_label.pack(side="left", padx=(12, 0))
        tk.Label(foot_row, textvariable=self._inv_last_updated_var, bg=BG_DARK, fg=MUTED,
                 font=("Segoe UI", 9, "italic")).pack(side="right")

        self._refresh_inv_data()

    def _refresh_inv_data(self):
        """Repopulate the inventory tree from DB and schedule next refresh."""
        if not hasattr(self, "_inv_tree") or not self._inv_tree.winfo_exists():
            return
        rows = get_inventory_by_branch(self.branch_id) if BACKEND_AVAILABLE else []
        self._inv_tree.delete(*self._inv_tree.get_children())
        low = 0
        for r in rows:
            qty = float(r["quantity_on_hand"] or 0)
            reorder = float(r["reorder_level"] or 0)
            status = "Temporarily Unavailable" if qty <= 0 else "Low Stock" if qty <= reorder else "Available"
            tag = "soldout" if qty <= 0 else "low" if qty <= reorder else ""
            if tag:
                low += 1
            self._inv_tree.insert("", "end", tag=tag, values=(
                r["inventory_item_id"], r["item_name"],
                f"{qty:g}", r["unit_type"],
                r["reorder_level"], status, f"${r['cost_per_unit']:.2f}",
                r.get("supplier_name") or "—"
            ))
        from datetime import datetime as _dt
        self._inv_last_updated_var.set(f"Updated {_dt.now().strftime('%I:%M:%S %p')}")
        self._inv_count_label.config(text=f"{len(rows)} items")
        self._inv_alert_label.config(
            text=f"  ⚠ {low} item(s) at or below reorder level" if low else ""
        )
        # Reschedule — 20 seconds
        if self.current_tab == "Inventory":
            self._inv_refresh_job = self.after(20000, self._refresh_inv_data)

    def _add_inventory_dialog(self):
        win = self._dialog("Add Inventory Item", 440, 460)
        suppliers = self._get_suppliers_map()

        f = tk.Frame(win, bg=BG_PANEL)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        name_e  = self._field(f, "Item Name *", 0)
        qty_e   = self._field(f, "Quantity *", 1)
        unit_v  = tk.StringVar(value=UNIT_TYPES[0])
        unit_e  = self._field(f, "Unit *", 2,
                    lambda p: ttk.Combobox(p, textvariable=unit_v, values=UNIT_TYPES, state="readonly", width=26))
        reorder_e = self._field(f, "Reorder Level *", 3)
        cost_e  = self._field(f, "Cost Per Unit *", 4)
        sup_v   = tk.StringVar(value="(none)")
        sup_e   = self._field(f, "Supplier", 5,
                    lambda p: ttk.Combobox(p, textvariable=sup_v,
                                           values=list(suppliers.keys()), state="readonly", width=26))

        def submit():
            try:
                ok, msg = add_inventory_item(
                    self.branch_id,
                    name_e.get().strip(),
                    float(qty_e.get()),
                    unit_v.get(),
                    float(reorder_e.get()),
                    float(cost_e.get()),
                    suppliers.get(sup_v.get()),
                )
                if ok:
                    messagebox.showinfo("Added", f"Inventory item added.", parent=win)
                    win.destroy()
                    self.show_tab("Inventory")
                else:
                    messagebox.showerror("Error", msg, parent=win)
            except ValueError:
                messagebox.showerror("Error", "Qty, Reorder Level, and Cost must be numbers.", parent=win)

        self._submit_btn(win, "Add Item", submit)

    def _adjust_qty_dialog(self):
        sel = self._inv_tree.selection()
        if not sel:
            messagebox.showinfo("Select Row", "Select an inventory item first.")
            return
        row  = self._inv_tree.item(sel[0], "values")
        item_id, item_name, cur_qty = int(row[0]), row[1], row[2]

        win = self._dialog("Adjust Quantity", 360, 200)
        f   = tk.Frame(win, bg=BG_PANEL)
        f.pack(fill="both", expand=True, padx=14, pady=14)
        tk.Label(f, text=f"Item: {item_name}", bg=BG_PANEL, fg=GOLD,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(f, text=f"Current qty: {cur_qty}", bg=BG_PANEL, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(4,12))
        tk.Label(f, text="New Quantity *", bg=BG_PANEL, fg=TEXT,
                 font=("Segoe UI", 10)).pack(anchor="w")
        qty_var = tk.StringVar()
        tk.Entry(f, textvariable=qty_var, bg=BG_DARK, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=("Segoe UI", 11)).pack(fill="x", pady=(4,12))

        def submit():
            try:
                ok, msg = update_inventory_quantity(item_id, float(qty_var.get()))
                if ok:
                    win.destroy()
                    self.show_tab("Inventory")
                else:
                    messagebox.showerror("Error", msg, parent=win)
            except ValueError:
                messagebox.showerror("Error", "Quantity must be a number.", parent=win)

        self._submit_btn(win, "Update", submit)

    # ══════════════════════════════════════════════════════════════════════════
    # SUPPLIERS TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_suppliers(self):
        self._header("Suppliers", "supplier",
                     ("Refresh",      lambda: self.show_tab("Suppliers")),
                     ("Add Supplier", self._add_supplier_dialog))

        cols = ("id", "name", "contact", "phone", "email", "address")
        tree = self._tree(cols)
        for cid, heading, width in [
            ("id","ID",50), ("name","Supplier",200), ("contact","Contact",160),
            ("phone","Phone",130), ("email","Email",220), ("address","Address",220)
        ]:
            tree.heading(cid, text=heading)
            tree.column(cid, width=width, anchor="w")

        rows = get_all_suppliers() if BACKEND_AVAILABLE else []
        if not rows:
            rows = [
                {"supplier_id":1,"supplier_name":"Atlantic Seafood","contact_name":"Marcus Hill","phone":"757-555-0142","email":"orders@atlantic.com","address":"210 Pier Rd, VA Beach"},
                {"supplier_id":2,"supplier_name":"Coastal Dairy","contact_name":"Linda Park","phone":"757-555-0188","email":"linda@coastaldairy.com","address":"55 Farm Way, Suffolk"},
                {"supplier_id":3,"supplier_name":"Garden Greens","contact_name":"Tina Owens","phone":"757-555-0203","email":"tina@gardengreens.co","address":"1100 Farm Ln, Chesapeake"},
            ]
        for r in rows:
            tree.insert("", "end", values=(
                r["supplier_id"], r["supplier_name"],
                r.get("contact_name") or "—", r.get("phone") or "—",
                r.get("email") or "—",  r.get("address") or "—",
            ))
        self._footer((f"{len(rows)} suppliers", "left", MUTED))

    def _add_supplier_dialog(self):
        win = self._dialog("Add Supplier", 440, 400)
        f   = tk.Frame(win, bg=BG_PANEL)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        name_e    = self._field(f, "Supplier Name *", 0)
        contact_e = self._field(f, "Contact Name",    1)
        phone_e   = self._field(f, "Phone",           2)
        email_e   = self._field(f, "Email",           3)
        address_e = self._field(f, "Address",         4)

        def submit():
            name = name_e.get().strip()
            if not name:
                messagebox.showerror("Error", "Supplier name is required.", parent=win)
                return
            ok, msg = add_supplier(name, contact_e.get().strip() or None,
                                   phone_e.get().strip() or None,
                                   email_e.get().strip() or None,
                                   address_e.get().strip() or None)
            if ok:
                messagebox.showinfo("Added", "Supplier added.", parent=win)
                win.destroy()
                self.show_tab("Suppliers")
            else:
                messagebox.showerror("Error", msg, parent=win)

        self._submit_btn(win, "Add Supplier", submit)

    # ══════════════════════════════════════════════════════════════════════════
    # SCHEDULE TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_schedule(self):
        self._header("Staff Schedule", "shift_schedule",
                     ("Refresh",      lambda: self.show_tab("Schedule")),
                     ("Delete Shift", self._delete_shift),
                     ("Add Shift",    self._add_shift_dialog))

        cols = ("id", "employee", "role", "date", "start", "end", "hours")
        tree = self._tree(cols)
        self._sched_tree = tree
        for cid, heading, width in [
            ("id","Shift ID",80), ("employee","Employee",200), ("role","Role",140),
            ("date","Date",110), ("start","Start",90), ("end","End",90), ("hours","Hours",80)
        ]:
            tree.heading(cid, text=heading)
            tree.column(cid, width=width, anchor="w")

        rows = get_shifts_by_branch(self.branch_id) if BACKEND_AVAILABLE else []
        if not rows:
            rows = [
                {"shift_id":101,"employee_name":"Janet Pierce","role_assigned":"Server","shift_date":"2026-04-25","start_time":"10:00","end_time":"16:00"},
                {"shift_id":102,"employee_name":"Marcus Lin","role_assigned":"Cook","shift_date":"2026-04-25","start_time":"09:00","end_time":"17:00"},
                {"shift_id":103,"employee_name":"Devon Carter","role_assigned":"Host","shift_date":"2026-04-25","start_time":"16:00","end_time":"22:00"},
            ]
        total_hours = 0.0
        for r in rows:
            h = self._shift_hours(str(r["start_time"])[:5], str(r["end_time"])[:5])
            total_hours += h
            employee_name = (
                r.get("employee_name")
                or " ".join(part for part in [r.get("first_name"), r.get("last_name")] if part)
                or f"ID {r.get('person_id','')}"
            )
            tree.insert("", "end", iid=str(r["shift_id"]), values=(
                r["shift_id"],
                employee_name,
                r["role_assigned"], str(r["shift_date"]),
                str(r["start_time"])[:5], str(r["end_time"])[:5],
                f"{h:.1f}"
            ))
        self._footer(
            (f"{len(rows)} shifts", "left", MUTED),
            (f"{total_hours:.1f} total hrs", "right", MUTED)
        )

    def _shift_hours(self, start, end):
        try:
            sh, sm = start.split(":"); eh, em = end.split(":")
            s = int(sh)*60+int(sm); e = int(eh)*60+int(em)
            if e < s: e += 1440
            return (e-s)/60
        except Exception:
            return 0.0

    def _add_shift_dialog(self):
        win = self._dialog("Add Shift", 440, 400)
        employees = get_all_employees(self.branch_id) if BACKEND_AVAILABLE else []
        emp_map   = {f"{r['last_name']}, {r['first_name']} (ID {r['person_id']})": r["person_id"]
                     for r in employees}
        emp_names = list(emp_map.keys()) or ["No employees found"]

        f = tk.Frame(win, bg=BG_PANEL)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        emp_v = tk.StringVar(value=emp_names[0] if emp_names else "")
        emp_e = self._field(f, "Employee *", 0,
                    lambda p: ttk.Combobox(p, textvariable=emp_v,
                                           values=emp_names, state="readonly", width=26))
        date_e  = self._field(f, "Date * (YYYY-MM-DD)", 1)
        date_e.insert(0, str(date.today()))
        start_e = self._field(f, "Start Time * (HH:MM)", 2)
        end_e   = self._field(f, "End Time * (HH:MM)",   3)
        role_v  = tk.StringVar(value=STAFF_JOB_ROLES[0])
        role_e  = self._field(f, "Role *", 4,
                    lambda p: ttk.Combobox(p, textvariable=role_v,
                                           values=STAFF_JOB_ROLES, width=26))

        def submit():
            person_id = emp_map.get(emp_v.get())
            if not person_id:
                messagebox.showerror("Error", "Select a valid employee.", parent=win); return
            ok, msg = create_shift(person_id, self.branch_id,
                                   date_e.get().strip(), start_e.get().strip(),
                                   end_e.get().strip(), role_v.get())
            if ok:
                win.destroy(); self.show_tab("Schedule")
            else:
                messagebox.showerror("Error", msg, parent=win)

        self._submit_btn(win, "Add Shift", submit)

    def _delete_shift(self):
        sel = self._sched_tree.selection()
        if not sel:
            messagebox.showinfo("Select Row", "Select a shift to delete."); return
        shift_id = int(self._sched_tree.item(sel[0], "values")[0])
        if not messagebox.askyesno("Confirm", f"Delete shift #{shift_id}?"):
            return
        ok, msg = delete_shift(shift_id)
        if ok:
            self.show_tab("Schedule")
        else:
            messagebox.showerror("Error", msg)

    # ══════════════════════════════════════════════════════════════════════════
    # EMPLOYEES TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_employees(self):
        self._header("Employees", "employee / staff / manager",
                     ("Refresh",     lambda: self.show_tab("Employees")),
                     ("Set Status",  self._set_employee_status),
                     ("Add Employee", self._add_employee_dialog))

        cols = ("id", "name", "job_title", "job_role", "pay", "status")
        tree = self._tree(cols)
        self._emp_tree = tree
        for cid, heading, width in [
            ("id","ID",60), ("name","Name",200), ("job_title","Job Title",160),
            ("job_role","Role",130), ("pay","Pay",100), ("status","Status",110)
        ]:
            tree.heading(cid, text=heading)
            tree.column(cid, width=width, anchor="w")

        rows = get_all_employees(self.branch_id) if BACKEND_AVAILABLE else []
        for r in rows:
            name  = f"{r['last_name']}, {r['first_name']}"
            pay   = (f"${r['salary']:.0f}/yr" if r.get("salary")
                     else f"${r['hourly_rate']:.2f}/hr" if r.get("hourly_rate")
                     else "—")
            color = {"ACTIVE": "", "INACTIVE": MUTED,
                     "TERMINATED": RED, "LEAVE": GOLD}.get(r["employment_status"], "")
            iid = str(r["person_id"])
            tree.insert("", "end", iid=iid, tags=(r["employment_status"],), values=(
                r["person_id"], name,
                r.get("job_title") or "—",
                r.get("staff_role") or "Manager",
                pay, r["employment_status"]
            ))
        tree.tag_configure("TERMINATED", foreground=RED)
        tree.tag_configure("LEAVE",      foreground=GOLD)
        tree.tag_configure("INACTIVE",   foreground=MUTED)

        active = sum(1 for r in rows if r["employment_status"] == "ACTIVE")
        self._footer(
            (f"{len(rows)} employees", "left", MUTED),
            (f"{active} active", "right", GREEN)
        )

    def _add_employee_dialog(self):
        win = self._dialog("Add Employee", 480, 620)
        branches = self._get_branches()

        f = tk.Frame(win, bg=BG_PANEL)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        first_e  = self._field(f, "First Name *",  0)
        last_e   = self._field(f, "Last Name *",   1)
        email_e  = self._field(f, "Email *",       2)
        phone_e  = self._field(f, "Phone",         3)
        user_e   = self._field(f, "Username *",    4)
        pass_e   = self._field(f, "Password *",    5)
        pass_e.config(show="*")

        role_v = tk.StringVar(value="STAFF")
        role_e = self._field(f, "Login Role *", 6,
                    lambda p: ttk.Combobox(p, textvariable=role_v,
                                           values=["STAFF","MANAGER"], state="readonly", width=26))

        jr_v = tk.StringVar(value=STAFF_JOB_ROLES[0])
        jr_e = self._field(f, "Job Role *", 7,
                    lambda p: ttk.Combobox(p, textvariable=jr_v,
                                           values=STAFF_JOB_ROLES, width=26))

        title_e   = self._field(f, "Job Title *",  8)
        branch_v  = tk.StringVar(value=list(branches.keys())[self.branch_id-1]
                                       if self.branch_id <= len(branches)
                                       else list(branches.keys())[0])
        branch_e  = self._field(f, "Branch *", 9,
                      lambda p: ttk.Combobox(p, textvariable=branch_v,
                                             values=list(branches.keys()), state="readonly", width=26))
        pay_e = self._field(f, "Hourly Rate (Staff) / Salary (Mgr) *", 10)
        hire_e = self._field(f, "Hire Date (YYYY-MM-DD)", 11)
        hire_e.insert(0, str(date.today()))

        def submit():
            first    = first_e.get().strip()
            last     = last_e.get().strip()
            email    = email_e.get().strip()
            username = user_e.get().strip()
            password = pass_e.get().strip()
            role     = role_v.get()
            jr       = jr_v.get()
            title    = title_e.get().strip()
            bname    = branch_v.get()
            bid      = branches.get(bname, self.branch_id)
            hire     = hire_e.get().strip() or str(date.today())

            if not all([first, last, email, username, password, title]):
                messagebox.showerror("Missing Fields", "Fill in all required fields (*)", parent=win)
                return
            try:
                pay_val = float(pay_e.get())
            except ValueError:
                messagebox.showerror("Error", "Pay must be a number.", parent=win)
                return

            hourly = pay_val if role == "STAFF" else None
            salary = pay_val if role == "MANAGER" else None

            ok, msg = register_user(
                first_name=first, last_name=last, email=email, phone=phone_e.get().strip() or None,
                username=username, password=password, role=role,
                branch_id=bid, job_title=title, hire_date=hire,
                hourly_rate=hourly, staff_role=jr if role == "STAFF" else None,
                salary=salary,
            )
            if ok:
                # get the new person_id to show as employee ID
                conn = get_connection() if DB_AVAILABLE else None
                new_id = "—"
                if conn:
                    try:
                        cur = conn.cursor()
                        cur.execute("SELECT person_id FROM user_account WHERE username=%s", (username,))
                        row = cur.fetchone()
                        if row: new_id = row[0]
                        cur.close(); conn.close()
                    except Exception:
                        pass
                messagebox.showinfo("Employee Created",
                    f"Account created!\n\nEmployee ID: {new_id}\nUsername: {username}\n"
                    f"Role: {role}  ·  Job: {jr if role=='STAFF' else 'Manager'}\n\n"
                    f"They can now log in at the login screen.", parent=win)
                win.destroy()
                self.show_tab("Employees")
            else:
                messagebox.showerror("Error", msg, parent=win)

        self._submit_btn(win, "Create Employee Account", submit)

    def _set_employee_status(self):
        sel = self._emp_tree.selection()
        if not sel:
            messagebox.showinfo("Select Row", "Select an employee first."); return
        row       = self._emp_tree.item(sel[0], "values")
        person_id = int(row[0])
        name      = row[1]
        cur_status = row[5]

        win = self._dialog("Set Employee Status", 340, 220)
        f   = tk.Frame(win, bg=BG_PANEL)
        f.pack(fill="both", expand=True, padx=14, pady=14)
        tk.Label(f, text=name, bg=BG_PANEL, fg=GOLD,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(f, text=f"Current status: {cur_status}", bg=BG_PANEL, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(4,12))
        status_v = tk.StringVar(value=cur_status)
        ttk.Combobox(f, textvariable=status_v, values=EMP_STATUSES,
                     state="readonly", font=("Segoe UI", 11)).pack(fill="x", pady=(0,12))

        def submit():
            ok, msg = update_employee_status(person_id, status_v.get())
            if ok:
                win.destroy(); self.show_tab("Employees")
            else:
                messagebox.showerror("Error", msg, parent=win)

        self._submit_btn(win, "Update Status", submit)

    # ══════════════════════════════════════════════════════════════════════════
    # MENU TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_menu(self):
        self._header("Menu Items", "menu_item",
                     ("Refresh",       lambda: self.show_tab("Menu")),
                     ("Toggle Active", self._toggle_menu_item),
                     ("Add Item",      self._add_menu_item_dialog))

        cols = ("id", "name", "category", "price", "status")
        tree = self._tree(cols)
        self._menu_tree = tree
        for cid, heading, width in [
            ("id","ID",60), ("name","Item",260), ("category","Category",160),
            ("price","Price",90), ("status","Status",90)
        ]:
            tree.heading(cid, text=heading)
            tree.column(cid, width=width, anchor="w")

        rows = get_menu_items() if BACKEND_AVAILABLE else []
        active_count = 0
        for r in rows:
            active = bool(r.get("active_status", True))
            if active: active_count += 1
            tag = "active" if active else "inactive"
            tree.insert("", "end", iid=str(r["menu_item_id"]), tags=(tag,), values=(
                r["menu_item_id"], r["item_name"], r["category"],
                f"${float(r['price']):.2f}", "Active" if active else "Inactive"
            ))
        tree.tag_configure("inactive", foreground=MUTED)

        self._footer(
            (f"{len(rows)} items", "left", MUTED),
            (f"{active_count} active", "right", GREEN)
        )

    def _add_menu_item_dialog(self):
        win = self._dialog("Add Menu Item", 440, 360)
        f   = tk.Frame(win, bg=BG_PANEL)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        name_e = self._field(f, "Item Name *", 0)
        cat_v  = tk.StringVar(value=MENU_CATEGORIES[0])
        cat_e  = self._field(f, "Category *", 1,
                    lambda p: ttk.Combobox(p, textvariable=cat_v,
                                           values=MENU_CATEGORIES, state="readonly", width=26))
        price_e = self._field(f, "Price *", 2)
        desc_e  = self._field(f, "Description", 3)

        def submit():
            name = name_e.get().strip()
            if not name:
                messagebox.showerror("Error", "Item name is required.", parent=win); return
            try:
                price = float(price_e.get())
            except ValueError:
                messagebox.showerror("Error", "Price must be a number.", parent=win); return

            ok, msg = add_menu_item(name, cat_v.get(), price,
                                    desc_e.get().strip() or None)
            if ok:
                win.destroy(); self.show_tab("Menu")
            else:
                messagebox.showerror("Error", msg, parent=win)

        self._submit_btn(win, "Add Menu Item", submit)

    def _toggle_menu_item(self):
        sel = self._menu_tree.selection()
        if not sel:
            messagebox.showinfo("Select Row", "Select a menu item first."); return
        item_id   = int(self._menu_tree.item(sel[0], "values")[0])
        item_name = self._menu_tree.item(sel[0], "values")[1]
        ok, msg   = toggle_menu_item_status(item_id)
        if ok:
            self.show_tab("Menu")
        else:
            messagebox.showerror("Error", msg)

    # ══════════════════════════════════════════════════════════════════════════
    # REVIEWS TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_reviews(self):
        self._header("Customer Reviews", "ratings · comments · sentiment",
                     ("Refresh", lambda: self.show_tab("Reviews")))

        cf = self.content_frame
        rows = get_recent_reviews(self.branch_id, 50) if BACKEND_AVAILABLE else []

        summary = tk.Frame(cf, bg=BG_DARK)
        summary.pack(fill="x", pady=(0, 12))
        total = len(rows)
        avg = sum(float(r.get("rating") or 0) for r in rows) / total if total else None
        positive = sum(1 for r in rows if float(r.get("sentiment_score") or 0) > 0)
        negative = sum(1 for r in rows if float(r.get("sentiment_score") or 0) < 0)

        for label, value in [
            ("Total Reviews", str(total)),
            ("Avg Rating", f"{avg:.2f}" if avg is not None else "—"),
            ("Positive", str(positive)),
            ("Negative", str(negative)),
        ]:
            card = tk.Frame(summary, bg=BG_PANEL, padx=14, pady=10)
            card.pack(side="left", expand=True, fill="x", padx=(0, 8))
            tk.Label(card, text=label, bg=BG_PANEL, fg=MUTED,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(card, text=value, bg=BG_PANEL, fg=GOLD,
                     font=("Segoe UI", 17, "bold")).pack(anchor="w")

        cols = ("date", "customer", "rating", "sentiment", "comment")
        frame = tk.Frame(cf, bg=BG_DARK)
        frame.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(frame, orient="vertical")
        sb.pack(side="right", fill="y")
        tree = ttk.Treeview(frame, columns=cols, show="headings",
                            style="Flow.Treeview", height=18, yscrollcommand=sb.set)
        sb.config(command=tree.yview)
        tree.pack(fill="both", expand=True)

        for cid, heading, width in [
            ("date", "Date", 145),
            ("customer", "Customer", 170),
            ("rating", "Rating", 70),
            ("sentiment", "Sentiment", 90),
            ("comment", "Comment", 520),
        ]:
            tree.heading(cid, text=heading)
            tree.column(cid, width=width, anchor="w")

        if rows:
            for r in rows:
                first = r.get("first_name") or ""
                last = r.get("last_name") or ""
                customer = " ".join(part for part in [first, last] if part).strip() or "Guest"
                sentiment = r.get("sentiment_score")
                sentiment_text = "—" if sentiment is None else f"{float(sentiment):.2f}"
                tree.insert("", "end", values=(
                    str(r.get("created_at") or ""),
                    customer,
                    r.get("rating") or "—",
                    sentiment_text,
                    r.get("comments") or "",
                ))
        else:
            tree.insert("", "end", values=("", "—", "—", "—", "No customer reviews submitted for this branch yet."))

    # ══════════════════════════════════════════════════════════════════════════
    # ANALYTICS TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_analytics(self):
        self._header("Analytics", "sales · labor · top items")

        cf = self.content_frame

        # ── Branch summary cards ───────────────────────────────────────────
        summary = get_branch_summary(self.branch_id) if BACKEND_AVAILABLE else None
        card_row = tk.Frame(cf, bg=BG_DARK)
        card_row.pack(fill="x", pady=(0,16))
        metrics = [
            ("Total Orders",   str(summary.get("total_orders") or 0)    if summary else "—"),
            ("Total Revenue",  f"${float(summary.get('total_revenue') or 0):,.2f}" if summary else "—"),
            ("Active Staff",   str(summary.get("total_employees") or 0) if summary else "—"),
            ("Avg Rating",     str(summary.get("average_rating") or "—")if summary else "—"),
        ]
        for label, value in metrics:
            card = tk.Frame(card_row, bg=BG_PANEL, padx=16, pady=12)
            card.pack(side="left", expand=True, fill="x", padx=(0,8))
            tk.Label(card, text=label, bg=BG_PANEL, fg=MUTED,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(card, text=value, bg=BG_PANEL, fg=GOLD,
                     font=("Segoe UI", 18, "bold")).pack(anchor="w")

        # ── Sales by Hour ──────────────────────────────────────────────────
        hour_section = tk.Frame(cf, bg=BG_DARK)
        hour_section.pack(fill="x", pady=(0, 16))

        hour_head = tk.Frame(hour_section, bg=BG_DARK)
        hour_head.pack(fill="x", pady=(0, 6))
        tk.Label(hour_head, text="Sales by Hour", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        hour_date_v = tk.StringVar(value=str(date.today()))
        tk.Entry(hour_head, textvariable=hour_date_v, bg=BG_PANEL, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
                 width=12).pack(side="left", padx=(12, 4))

        hour_canvas_frame = tk.Frame(hour_section, bg=BG_DARK)
        hour_canvas_frame.pack(fill="x")

        def run_hourly(hdate=None):
            for w in hour_canvas_frame.winfo_children():
                w.destroy()
            d = hdate or hour_date_v.get()
            rows = get_sales_by_hour(self.branch_id, d) if BACKEND_AVAILABLE else []
            if not rows:
                tk.Label(hour_canvas_frame, text=f"No completed orders on {d}.",
                         bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9, "italic")).pack(anchor="w")
                return
            max_rev = max(float(r["total_revenue"] or 0) for r in rows) or 1
            bar_w = max(18, min(38, 600 // max(len(rows), 1)))
            for r in rows:
                rev   = float(r["total_revenue"] or 0)
                ords  = int(r["total_orders"] or 0)
                hour  = int(r["hour_of_day"])
                label = f"{hour % 12 or 12}{'am' if hour < 12 else 'pm'}"
                bar_h = max(4, int((rev / max_rev) * 60))
                col   = tk.Frame(hour_canvas_frame, bg=BG_DARK)
                col.pack(side="left", padx=2, anchor="s")
                tk.Label(col, text=f"${rev:.0f}", bg=BG_DARK, fg=MUTED,
                         font=("Segoe UI", 7)).pack()
                bar = tk.Frame(col, bg=GOLD, width=bar_w, height=bar_h)
                bar.pack()
                bar.pack_propagate(False)
                tk.Label(col, text=label, bg=BG_DARK, fg=TEXT,
                         font=("Segoe UI", 8)).pack()
                tk.Label(col, text=str(ords), bg=BG_DARK, fg=MUTED,
                         font=("Segoe UI", 7)).pack()

        self._dark_button(hour_head, "Go", run_hourly,
                          font=("Segoe UI", 9, "bold")).pack(side="left")
        run_hourly()

        # ── Two-column bottom section ──────────────────────────────────────
        bottom = tk.Frame(cf, bg=BG_DARK)
        bottom.pack(fill="both", expand=True)
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=1)

        # Top Items ──────────────────────────────────────────────────────
        left = tk.Frame(bottom, bg=BG_DARK)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,10))
        tk.Label(left, text="Top Menu Items", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0,8))

        cols = ("name", "category", "qty", "revenue")
        top_frame = tk.Frame(left, bg=BG_DARK)
        top_frame.pack(fill="both", expand=True)
        sb1 = ttk.Scrollbar(top_frame, orient="vertical")
        sb1.pack(side="right", fill="y")
        top_tree = ttk.Treeview(top_frame, columns=cols, show="headings",
                                style="Flow.Treeview", height=12, yscrollcommand=sb1.set)
        sb1.config(command=top_tree.yview)
        top_tree.pack(fill="both", expand=True)
        for cid, heading, width in [
            ("name","Item",200), ("category","Category",120),
            ("qty","Ordered",80), ("revenue","Revenue",100)
        ]:
            top_tree.heading(cid, text=heading)
            top_tree.column(cid, width=width, anchor="w")
        top_rows = get_top_menu_items(self.branch_id, 15) if BACKEND_AVAILABLE else []
        for r in top_rows:
            top_tree.insert("", "end", values=(
                r["item_name"], r["category"],
                r["total_ordered"], f"${float(r['total_revenue']):.2f}"
            ))

        # Sales Report ───────────────────────────────────────────────────
        right = tk.Frame(bottom, bg=BG_DARK)
        right.grid(row=0, column=1, sticky="nsew")
        tk.Label(right, text="Sales Trend", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0,8))

        ctrl = tk.Frame(right, bg=BG_DARK)
        ctrl.pack(fill="x", pady=(0,8))
        tk.Label(ctrl, text="From", bg=BG_DARK, fg=MUTED, font=("Segoe UI",9)).pack(side="left")
        start_v = tk.StringVar(value="2026-01-01")
        tk.Entry(ctrl, textvariable=start_v, bg=BG_PANEL, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=("Segoe UI",10),
                 width=12).pack(side="left", padx=(4,12))
        tk.Label(ctrl, text="To", bg=BG_DARK, fg=MUTED, font=("Segoe UI",9)).pack(side="left")
        end_v   = tk.StringVar(value=str(date.today()))
        tk.Entry(ctrl, textvariable=end_v, bg=BG_PANEL, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=("Segoe UI",10),
                 width=12).pack(side="left", padx=(4,12))

        sales_frame = tk.Frame(right, bg=BG_DARK)
        sales_frame.pack(fill="both", expand=True)

        def run_report():
            for w in sales_frame.winfo_children():
                w.destroy()
            data = get_sales_report(self.branch_id, start_v.get(), end_v.get()) if BACKEND_AVAILABLE else []
            if not data:
                tk.Label(sales_frame, text="No completed orders in that range.",
                         bg=BG_DARK, fg=MUTED, font=("Segoe UI",10)).pack(anchor="w", pady=8)
                return
            total_rev = sum(float(r["total_revenue"] or 0) for r in data)
            total_ord = sum(int(r["total_orders"] or 0) for r in data)
            avg_order = total_rev / total_ord if total_ord else 0

            fcp_row = get_food_cost_percentage(self.branch_id, start_v.get(), end_v.get()) if BACKEND_AVAILABLE else None
            food_cost_pct = float(fcp_row["food_cost_percentage"] or 0) if fcp_row and fcp_row.get("food_cost_percentage") else None
            fcp_str = f"{food_cost_pct:.1f}%" if food_cost_pct is not None else "N/A"
            fcp_color = RED if (food_cost_pct or 0) > 35 else GREEN

            for label, value, color in [
                ("Total Revenue",   f"${total_rev:,.2f}", GOLD),
                ("Total Orders",    str(total_ord),       GOLD),
                ("Avg Order Value", f"${avg_order:.2f}",  GOLD),
                ("Food Cost %",     fcp_str,              fcp_color),
            ]:
                row_f = tk.Frame(sales_frame, bg=BG_PANEL, padx=12, pady=8)
                row_f.pack(fill="x", pady=3)
                tk.Label(row_f, text=label, bg=BG_PANEL, fg=MUTED,
                         font=("Segoe UI",9)).pack(side="left")
                tk.Label(row_f, text=value, bg=BG_PANEL, fg=color,
                         font=("Segoe UI",12,"bold")).pack(side="right")

            tk.Label(sales_frame, text="Daily Trend", bg=BG_DARK, fg=TEXT,
                     font=("Segoe UI",11,"bold")).pack(anchor="w", pady=(12,4))
            sb2 = ttk.Scrollbar(sales_frame, orient="vertical")
            sb2.pack(side="right", fill="y")
            dt = ttk.Treeview(sales_frame, columns=("date","orders","revenue"),
                              show="headings", style="Flow.Treeview",
                              height=6, yscrollcommand=sb2.set)
            sb2.config(command=dt.yview)
            dt.pack(fill="both", expand=True)
            for cid, h, w in [("date","Date",110),("orders","Orders",70),("revenue","Revenue",110)]:
                dt.heading(cid, text=h); dt.column(cid, width=w, anchor="w")
            for r in data:
                dt.insert("", "end", values=(
                    str(r["sale_date"]), r["total_orders"],
                    f"${float(r['total_revenue']):.2f}"
                ))

        self._dark_button(ctrl, "Run Report", run_report,
                          font=("Segoe UI", 9, "bold")).pack(side="left")
        run_report()

        # ── Labor Report (today) ─────────────────────────────────────────
        tk.Label(cf, text="Labor Report — Today", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(18, 6))

        labor_cols = ("name", "role", "start", "end", "hours", "rate", "est_cost")
        labor_frame = tk.Frame(cf, bg=BG_DARK)
        labor_frame.pack(fill="x")
        lsb = ttk.Scrollbar(labor_frame, orient="vertical")
        lsb.pack(side="right", fill="y")
        labor_tree = ttk.Treeview(labor_frame, columns=labor_cols, show="headings",
                                  style="Flow.Treeview", height=6, yscrollcommand=lsb.set)
        lsb.config(command=labor_tree.yview)
        labor_tree.pack(fill="x")
        for cid, heading, width in [
            ("name","Employee",180), ("role","Role",120), ("start","Start",80),
            ("end","End",80), ("hours","Hrs",55), ("rate","$/hr",70), ("est_cost","Est. Cost",90)
        ]:
            labor_tree.heading(cid, text=heading)
            labor_tree.column(cid, width=width, anchor="w")

        labor_rows = get_labor_report(self.branch_id, str(date.today())) if BACKEND_AVAILABLE else []
        total_labor = 0.0
        total_hours = 0.0
        for r in labor_rows:
            hrs  = float(r.get("hours_scheduled") or 0)
            rate = float(r.get("hourly_rate") or 0)
            cost = float(r.get("estimated_labor_cost") or 0)
            total_hours += hrs
            total_labor += cost
            labor_tree.insert("", "end", values=(
                f"{r['first_name']} {r['last_name']}",
                r.get("role_assigned") or "—",
                str(r.get("start_time", ""))[:5],
                str(r.get("end_time", ""))[:5],
                f"{hrs:.0f}",
                f"${rate:.2f}" if rate else "—",
                f"${cost:.2f}" if cost else "—",
            ))
        if not labor_rows:
            tk.Label(cf, text="No shifts scheduled today.", bg=BG_DARK, fg=MUTED,
                     font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=4)
        else:
            summary_row = tk.Frame(cf, bg=BG_DARK)
            summary_row.pack(fill="x", pady=(6, 0))
            tk.Label(summary_row, text=f"{len(labor_rows)} staff scheduled  ·  {total_hours:.0f} hrs  ·  Est. labor cost:",
                     bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
            tk.Label(summary_row, text=f"  ${total_labor:,.2f}",
                     bg=BG_DARK, fg=GOLD, font=("Segoe UI", 10, "bold")).pack(side="left")

        # ── Payroll Summary ──────────────────────────────────────────────────
        tk.Label(cf, text="Payroll Summary", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(18, 6))

        pay_cols = ("name", "start", "end", "hours", "gross", "deductions", "net", "status")
        pay_frame = tk.Frame(cf, bg=BG_DARK)
        pay_frame.pack(fill="x")
        psb = ttk.Scrollbar(pay_frame, orient="vertical")
        psb.pack(side="right", fill="y")
        pay_tree = ttk.Treeview(pay_frame, columns=pay_cols, show="headings",
                                style="Flow.Treeview", height=6, yscrollcommand=psb.set)
        psb.config(command=pay_tree.yview)
        pay_tree.pack(fill="x")
        for cid, heading, width in [
            ("name","Employee",180), ("start","Period Start",110), ("end","Period End",110),
            ("hours","Hrs",60), ("gross","Gross Pay",100),
            ("deductions","Deductions",100), ("net","Net Pay",100), ("status","Status",100)
        ]:
            pay_tree.heading(cid, text=heading)
            pay_tree.column(cid, width=width, anchor="w")

        pay_rows = get_payroll_summary(self.branch_id) if BACKEND_AVAILABLE else []
        total_gross = 0.0
        for r in pay_rows:
            gross = float(r.get("gross_pay") or 0)
            ded   = float(r.get("deductions") or 0)
            net   = float(r.get("net_pay") or gross - ded)
            total_gross += gross
            pay_tree.insert("", "end", values=(
                r.get("employee_name") or "—",
                str(r.get("pay_period_start", ""))[:10],
                str(r.get("pay_period_end", ""))[:10],
                f"{float(r.get('hours_worked') or 0):.1f}",
                f"${gross:.2f}",
                f"${ded:.2f}",
                f"${net:.2f}",
                r.get("status") or "—",
            ))
        if not pay_rows:
            tk.Label(cf, text="No payroll records. Run shifts to generate estimated data.",
                     bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=4)
        else:
            pr = tk.Frame(cf, bg=BG_DARK)
            pr.pack(fill="x", pady=(6, 0))
            tk.Label(pr, text=f"{len(pay_rows)} records  ·  Total gross:",
                     bg=BG_DARK, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
            tk.Label(pr, text=f"  ${total_gross:,.2f}",
                     bg=BG_DARK, fg=GOLD, font=("Segoe UI", 10, "bold")).pack(side="left")

    # ── Sign out ─────────────────────────────────────────────────────────────
    def _open_hq_access(self):
        password = simpledialog.askstring(
            "HQ Access",
            "Enter HQ password:",
            parent=self,
            show="*",
        )
        if password is None:
            return
        if password.strip() != "123":
            messagebox.showerror("Access Denied", "Incorrect HQ password.")
            return

        hq_path = os.path.join(PROJECT_ROOT, "frontend", "HQ_ui.py")
        try:
            subprocess.Popen([sys.executable, hq_path], cwd=PROJECT_ROOT)
            messagebox.showinfo("HQ Access", "Opening HQ dashboard.")
        except Exception as exc:
            messagebox.showerror("HQ Access Failed", f"Could not open HQ dashboard: {exc}")

    def _sign_out(self):
        if not messagebox.askyesno("Sign Out", "Sign out of FLOW?"):
            return
        self.destroy()
        try:
            from login import LoginScreen
            LoginScreen().mainloop()
        except Exception as e:
            print(f"Error returning to login: {e}")


# ── Minimal driver ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _sys
    _name   = _sys.argv[1] if len(_sys.argv) > 1 else "Manager"
    _branch = int(_sys.argv[2]) if len(_sys.argv) > 2 else 1
    ManagerUI(manager_name=_name, branch_id=_branch).mainloop()
