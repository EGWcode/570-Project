# login.py
#Created by Jonah Goodwine
#     FLOW - Enterprise Restaurant Management System
#
# This file is the login screen for the FLOW system. The user enters one
# of four role names (Customer, Manager, Staff, Admin) as the username,
# with password "123" for all dummy logins. On success the screen tries
# to launch the matching UI file.
#
# If the matching UI file cannot be loaded a black placeholder screen is
# shown instead so we can confirm the login routing is working even when
# the target file is missing or broken. Check the console for the import
# error in that case.


import os
import sys
import tkinter as tk
import webbrowser
from tkinter import ttk

# project root on path so backend.* and config.* imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from backend.auth import login_user as db_login_user
    AUTH_AVAILABLE = True
except Exception:
    AUTH_AVAILABLE = False

# color palette -- matches the Soul by the Sea / Customer UI ocean theme
BG_DARK  = "#0a0a0f"
BG_PANEL = "#0d1b2a"
TEAL     = "#00bfa5"
TEXT     = "#ffffff"
MUTED    = "#9ab5c0"
RED      = "#F85149"

# images folder sits one level above frontend/
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images")

# valid employee/admin dummy logins -- fallback when DB is unavailable
VALID_ROLES    = ["Manager", "Staff", "Admin"]
DUMMY_PASSWORD = "123"


# ----------------------------------------------------------------------
# Placeholder Environment
#   shown when the real UI for a role cannot be loaded. just a black
#   screen with the role name in white so we can troubleshoot whether
#   the routing actually fired.
# ----------------------------------------------------------------------
class PlaceholderEnv(tk.Tk):

    # full-arg constructor
    def __init__(self, role_name):
        super().__init__()
        self.role_name = role_name
        self.title("FLOW - " + role_name + " Env")
        self.configure(bg="#000000")
        self.geometry("700x450")

        # big white role label in the middle
        tk.Label(self, text=role_name + " Env",
                 bg="#000000", fg="#FFFFFF",
                 font=("Segoe UI", 36, "bold")).pack(expand=True)

        # small hint underneath
        tk.Label(self, text="placeholder screen -- real UI not loaded",
                 bg="#000000", fg="#FFFFFF",
                 font=("Segoe UI", 10)).pack(pady=(0, 6))
        tk.Label(self, text="check console output for the import error",
                 bg="#000000", fg="#888888",
                 font=("Segoe UI", 9)).pack(pady=(0, 30))


# ----------------------------------------------------------------------
# Login Screen
# ----------------------------------------------------------------------
class LoginScreen(tk.Tk):

    # no-arg constructor -- login does not need any startup info
    def __init__(self):
        super().__init__()
        self.title("FLOW - Login")
        self.configure(bg=BG_DARK)
        self.geometry("560x720")
        self.resizable(False, False)

        # keep image references alive so tkinter doesn't garbage-collect them
        self.soul_logo_img = None
        self.flow_logo_img = None

        # form values
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        self.build_ui()


    def _load_image(self, filename, width, height):
        """Load and resize a PNG from the images folder. Returns None on failure."""
        path = os.path.join(IMAGES_DIR, filename)
        if PIL_AVAILABLE:
            try:
                img = Image.open(path).resize((width, height), Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception:
                return None
        try:
            # native tk.PhotoImage works for PNG without PIL but can't resize smoothly
            return tk.PhotoImage(file=path)
        except Exception:
            return None


    # builds all the widgets on the login window
    def build_ui(self):

        # full-window background frame so we can center the card
        bg_frame = tk.Frame(self, bg=BG_DARK)
        bg_frame.pack(fill="both", expand=True)

        # centered login card
        card = tk.Frame(bg_frame, bg=BG_PANEL)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # ---- Soul by the Sea logo ----
        self.soul_logo_img = self._load_image("SoulByTheSeaLogo.png", 300, 118)
        if self.soul_logo_img:
            tk.Label(card, image=self.soul_logo_img,
                     bg=BG_PANEL).pack(pady=(32, 0))
        else:
            # text fallback if image can't load
            tk.Label(card, text="Soul by the Sea",
                     font=("Georgia", 22, "bold"),
                     fg=TEAL, bg=BG_PANEL).pack(pady=(32, 0))

        tk.Label(card, text="Restaurant Management System",
                 font=("Segoe UI", 9), fg=MUTED, bg=BG_PANEL
                 ).pack(pady=(4, 20))

        # ---- customer entrance (no login required) ----
        cust_frame = tk.Frame(card, bg=BG_PANEL)
        cust_frame.pack(fill="x", padx=50, pady=(0, 8))

        tk.Button(cust_frame, text="Order Here  →",
                  bg=TEAL, fg="#000000",
                  activebackground="#009980", activeforeground="#000000",
                  relief="flat", font=("Segoe UI", 12, "bold"),
                  cursor="hand2", command=self.open_customer_ui
                  ).pack(fill="x", ipady=11)

        tk.Label(cust_frame, text="Tap to browse the menu and place an order",
                 font=("Segoe UI", 8), fg=MUTED, bg=BG_PANEL
                 ).pack(pady=(5, 0))

        ttk.Separator(card, orient="horizontal").pack(fill="x", padx=40, pady=(14, 0))

        # ---- employee / admin login form ----
        tk.Label(card, text="Employee & Admin Login",
                 font=("Segoe UI", 9, "bold"), fg=MUTED, bg=BG_PANEL
                 ).pack(pady=(10, 0))

        form = tk.Frame(card, bg=BG_PANEL)
        form.pack(padx=50, pady=(10, 24))

        tk.Label(form, text="Username", bg=BG_PANEL, fg=TEXT,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 2))
        user_entry = tk.Entry(form, textvariable=self.username_var,
                              bg=BG_DARK, fg=TEXT, insertbackground=TEXT,
                              relief="flat", font=("Segoe UI", 11), width=32)
        user_entry.pack(fill="x", ipady=7)

        tk.Label(form, text="Password", bg=BG_PANEL, fg=TEXT,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(14, 2))
        pass_entry = tk.Entry(form, textvariable=self.password_var, show="*",
                              bg=BG_DARK, fg=TEXT, insertbackground=TEXT,
                              relief="flat", font=("Segoe UI", 11), width=32)
        pass_entry.pack(fill="x", ipady=7)

        tk.Button(form, text="Sign In",
                  bg=TEAL, fg="#000000",
                  activebackground="#009980", activeforeground="#000000",
                  relief="flat", font=("Segoe UI", 11, "bold"),
                  cursor="hand2", command=self.try_login
                  ).pack(fill="x", pady=(26, 6), ipady=9)

        self.status_label = tk.Label(form, text="", bg=BG_PANEL, fg=RED,
                                     font=("Segoe UI", 9))
        self.status_label.pack(pady=(4, 0))

        ttk.Separator(card, orient="horizontal").pack(fill="x", padx=40, pady=(16, 0))

        # ---- FLOW logo (bottom of card) ----
        self.flow_logo_img = self._load_image("FlowLogo.png", 240, 96)
        flow_bottom = tk.Frame(card, bg=BG_PANEL)
        flow_bottom.pack(pady=(16, 32))

        if self.flow_logo_img:
            tk.Label(flow_bottom, image=self.flow_logo_img,
                     bg=BG_PANEL).pack(pady=(0, 8))
        else:
            tk.Label(flow_bottom, text="Powered by FLOW",
                     font=("Segoe UI", 9), fg=MUTED, bg=BG_PANEL).pack(pady=(0, 8))

        tk.Label(flow_bottom,
                 text="Manager / Staff / Admin   ·   pw: 123",
                 font=("Segoe UI", 8, "italic"), fg=MUTED, bg=BG_PANEL
                 ).pack()

        # let the user press Enter to submit
        self.bind("<Return>", lambda e: self.try_login())
        user_entry.focus()


    # validates the entered credentials and opens the right UI
    def try_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if username == "" or password == "":
            self.status_label.config(text="Please enter username and password.")
            return

        # try real DB auth first
        if AUTH_AVAILABLE:
            user, msg = db_login_user(username, password)
            if user:
                role = user["role"].capitalize()
                if role in VALID_ROLES:
                    self.status_label.config(text="")
                    self.open_role_ui(role)
                    return
            # if DB is up but credentials are wrong, show the error and stop
            if "connection" not in msg.lower():
                self.status_label.config(text=msg)
                return
            # DB is down — fall through to dummy login below

        # dummy fallback (used when DB is unavailable)
        if password != DUMMY_PASSWORD:
            self.status_label.config(text="Invalid password.")
            return

        role = username.capitalize()
        if role not in VALID_ROLES:
            self.status_label.config(text="Unknown user. Try Customer, Manager, Staff, or Admin.")
            return

        self.status_label.config(text="")
        self.open_role_ui(role)


    def open_customer_ui(self):
        """Opens the browser-based customer ordering screen."""
        self.destroy()
        webbrowser.open("http://127.0.0.1:5001")

    # closes the login window and tries to launch the matching UI for
    # the role. if the import or launch fails, drop into the black
    # placeholder screen so we can see the routing fired.
    def open_role_ui(self, role):
        self.destroy()

        launched = False

        if role == "Manager":
            try:
                from manager_ui import ManagerUI
                app = ManagerUI(manager_name="Manager", branch_id=1)
                app.mainloop()
                launched = True
            except Exception as e:
                print(f"Could not load Manager UI: {e}")

        elif role == "Staff":
            try:
                from employee_ui import FLOWApp
                app = FLOWApp()
                app.mainloop()
                launched = True
            except Exception as e:
                print(f"Could not load Staff UI: {e}")

        elif role == "Admin":
            try:
                from HQ_ui import HQApp
                app = HQApp()
                app.mainloop()
                launched = True
            except Exception as e:
                print(f"Could not load Admin/HQ UI: {e}")

        # if the real UI could not be loaded, show the placeholder
        if not launched:
            placeholder = PlaceholderEnv(role)
            placeholder.mainloop()




# minimal driver
if __name__ == "__main__":
    win = LoginScreen()
    win.mainloop()
