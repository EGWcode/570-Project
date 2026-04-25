# login.py
#
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


import tkinter as tk
from tkinter import ttk

# color palette -- matches the rest of the FLOW UI
BG_DARK   = "#0D1117"
BG_PANEL  = "#161B22"
GOLD      = "#D4A843"
TEXT      = "#E6EDF3"
MUTED     = "#8B949E"
RED       = "#F85149"


# valid dummy logins -- username doubles as the role, password is always "123"
VALID_ROLES    = ["Customer", "Manager", "Staff", "Admin"]
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
        self.geometry("420x500")
        self.resizable(False, False)

        # form values
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        self.build_ui()


    # builds all the widgets on the login window
    def build_ui(self):

        # top branding strip
        header = tk.Frame(self, bg=BG_PANEL, height=90)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(header, text="Soul By The Sea", bg=BG_PANEL,
                 fg=GOLD, font=("Segoe UI", 16, "bold")).pack(pady=(18, 0))
        tk.Label(header, text="FLOW Login", bg=BG_PANEL,
                 fg=MUTED, font=("Segoe UI", 9)).pack()

        # form area
        form = tk.Frame(self, bg=BG_DARK)
        form.pack(fill="both", expand=True, padx=40, pady=24)

        # username field
        tk.Label(form, text="Username", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 2))
        user_entry = tk.Entry(form, textvariable=self.username_var,
                              bg=BG_PANEL, fg=TEXT, insertbackground=TEXT,
                              relief="flat", font=("Segoe UI", 11))
        user_entry.pack(fill="x", ipady=6)

        # password field
        tk.Label(form, text="Password", bg=BG_DARK, fg=TEXT,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(14, 2))
        pass_entry = tk.Entry(form, textvariable=self.password_var, show="*",
                              bg=BG_PANEL, fg=TEXT, insertbackground=TEXT,
                              relief="flat", font=("Segoe UI", 11))
        pass_entry.pack(fill="x", ipady=6)

        # sign in button
        btn = tk.Button(form, text="Sign In", bg=GOLD, fg="#000000",
                        activebackground="#B8902E", relief="flat",
                        font=("Segoe UI", 11, "bold"), cursor="hand2",
                        command=self.try_login)
        btn.pack(fill="x", pady=(28, 8), ipady=8)

        # error / status label
        self.status_label = tk.Label(form, text="", bg=BG_DARK, fg=RED,
                                      font=("Segoe UI", 9))
        self.status_label.pack(pady=(6, 0))

        # tiny hint at the bottom
        hint = tk.Label(form,
                        text="Dummy logins:  Customer / Manager / Staff / Admin   ·   pw: 123",
                        bg=BG_DARK, fg=MUTED, font=("Segoe UI", 8, "italic"))
        hint.pack(side="bottom", pady=(10, 0))

        # let the user press Enter to submit
        self.bind("<Return>", lambda e: self.try_login())
        user_entry.focus()


    # validates the entered credentials and opens the right UI
    def try_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        # basic input check
        if username == "" or password == "":
            self.status_label.config(text="Please enter username and password.")
            return

        # check the password
        if password != DUMMY_PASSWORD:
            self.status_label.config(text="Invalid password.")
            return

        # normalize the username so "manager" / "MANAGER" / "Manager" all work
        role = username.capitalize()

        # check the username is one of the four valid roles
        found = False
        for r in VALID_ROLES:
            if r == role:
                found = True
                break

        if not found:
            self.status_label.config(text="Unknown user. Try Customer, Manager, Staff, or Admin.")
            return

        # success -- close login and try to open the matching UI
        self.status_label.config(text="")
        self.open_role_ui(role)


    # closes the login window and tries to launch the matching UI for
    # the role. if the import or launch fails, drop into the black
    # placeholder screen so we can see the routing fired.
    def open_role_ui(self, role):
        self.destroy()

        launched = False

        if role == "Customer":
            # customer front end file name
            try:
                from customer_ui import CustomerUI
                app = CustomerUI()
                app.mainloop()
                launched = True
            except Exception as e:
                print(f"Could not load Customer UI: {e}")

        elif role == "Manager":
            try:
                from manager_ui import ManagerUI
                app = ManagerUI(manager_name="Manager", branch_id=1)
                app.mainloop()
                launched = True
            except Exception as e:
                print(f"Could not load Manager UI: {e}")

        elif role == "Staff":
            # staff front end file name (currently "Front-end Screen.py", will be renamed)
            launched = self.launch_staff_ui()

        elif role == "Admin":
            # admin front end file name
            try:
                from admin_ui import AdminUI
                app = AdminUI()
                app.mainloop()
                launched = True
            except Exception as e:
                print(f"Could not load Admin UI: {e}")

        # if the real UI could not be loaded, show the placeholder
        if not launched:
            placeholder = PlaceholderEnv(role)
            placeholder.mainloop()


    # tries to launch the staff UI. handles the legacy "Front-end Screen.py"
    # filename which has a space in it (cannot use a normal import).
    def launch_staff_ui(self):

        # try the future clean module name first
        try:
            from staff_ui import StaffUI
            app = StaffUI()
            app.mainloop()
            return True
        except Exception:
            pass  # fall through to the legacy file load

        # fall back to the current spaced filename
        try:
            import importlib.util
            import os

            # build a path to "Front-end Screen.py" sitting next to this file
            here = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(here, "Front-end Screen.py")

            spec   = importlib.util.spec_from_file_location("front_end_screen", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            app = module.FLOWApp()
            app.mainloop()
            return True
        except Exception as e:
            print(f"Could not load Staff UI: {e}")
            return False


# minimal driver
if __name__ == "__main__":
    win = LoginScreen()
    win.mainloop()
