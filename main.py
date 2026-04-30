"""
main.py
    FLOW - Enterprise Restaurant Management System
    CSC 570 Sp 26'

Entry point for the full FLOW application.

What this does:
  1. Starts the Flask customer-website (port 5001) in a background thread
  2. Seeds the MySQL database with branches, menu, inventory, and demo
     login accounts (Manager / Staff / Admin, password "123") if empty
  3. Opens the Tkinter login screen

Run with:
    python main.py
"""

import os
import sys
import threading
import time

# Set to True only when you want background demo activity.
RUN_SIMULATION = False

# ── path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, FRONTEND_DIR)


# ── Flask (customer website) ───────────────────────────────────────────────────

def run_flask():
    """Runs the Flask app in a daemon thread so it stops when the main UI closes."""
    try:
        from customer_web.app import app
        app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[FLASK] Failed to start: {e}")


# ── Activity simulator ────────────────────────────────────────────────────────

def run_simulator():
    """Runs the activity simulator in a daemon thread to populate live feeds."""
    try:
        import simulate_activity
        simulate_activity.main()
    except SystemExit:
        pass
    except Exception as e:
        print(f"[SIM] Simulator stopped: {e}")


# ── Database seeding ──────────────────────────────────────────────────────────

def seed_database():
    """Seeds branches, menu items, inventory and demo accounts if the DB is empty."""
    try:
        from config.db_config import get_connection, close_connection
        conn = get_connection()
        if not conn:
            print("[SEED] MySQL not available — skipping seed.")
            return

        # Reuse the full seeder from simulate_activity (branches, menu, inventory)
        try:
            from simulate_activity import seed_if_empty
            seed_if_empty(conn)
        except Exception as e:
            print(f"[SEED] Full seed skipped: {e}")

        _ensure_demo_accounts(conn)
        close_connection(conn)

    except Exception as e:
        print(f"[SEED] Seed error: {e}")


def _ensure_demo_accounts(conn):
    """
    Creates the three demo login accounts used in the classroom demo:
      Manager / 123  →  Manager UI
      Staff   / 123  →  Employee / Staff UI
      Admin   / 123  →  HQ Admin UI

    Safe to call repeatedly — skips accounts that already exist.
    """
    import bcrypt

    cur = conn.cursor(dictionary=True)

    DEMO = [
        # (first, last, email,                         username,  password, db_role, job_title)
        ("Maya",    "Bennett",  "demo.manager@soulbythesea.local", "Manager", "123", "MANAGER", "General Manager"),
        ("Jordan",  "Ellis",    "demo.staff@soulbythesea.local",   "Staff",   "123", "STAFF",   "Server"),
        ("Avery",   "Mitchell", "demo.admin@soulbythesea.local",   "Admin",   "123", "ADMIN",   "HQ Administrator"),
    ]

    try:
        cur.execute("SELECT branch_id FROM branch ORDER BY branch_id LIMIT 1")
        row = cur.fetchone()
        branch_id = row["branch_id"] if row else 1

        for first, last, email, username, password, db_role, job_title in DEMO:
            cur.execute("""
                SELECT ua.account_id, ua.person_id
                FROM user_account ua
                WHERE ua.username = %s
            """, (username,))
            account = cur.fetchone()
            if account:
                person_id = account["person_id"]
                cur.execute(
                    "UPDATE person SET first_name = %s, last_name = %s, email = %s WHERE person_id = %s",
                    (first, last, email, person_id),
                )
                cur.execute("SELECT person_id FROM employee WHERE person_id = %s", (person_id,))
                if cur.fetchone():
                    cur.execute(
                        "UPDATE employee SET branch_id = %s, job_title = %s, employment_status = 'ACTIVE' WHERE person_id = %s",
                        (branch_id, job_title, person_id),
                    )
                else:
                    cur.execute(
                        "INSERT INTO employee (person_id, branch_id, job_title, hire_date, employment_status) "
                        "VALUES (%s, %s, %s, CURDATE(), 'ACTIVE')",
                        (person_id, branch_id, job_title),
                    )
                if db_role in ("MANAGER", "ADMIN"):
                    cur.execute("SELECT person_id FROM manager WHERE person_id = %s", (person_id,))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO manager (person_id, salary) VALUES (%s, 65000.00)", (person_id,))
                else:
                    cur.execute("SELECT person_id FROM staff WHERE person_id = %s", (person_id,))
                    if cur.fetchone():
                        cur.execute("UPDATE staff SET role = 'SERVER' WHERE person_id = %s", (person_id,))
                    else:
                        cur.execute(
                            "INSERT INTO staff (person_id, hourly_rate, role) VALUES (%s, 15.00, 'SERVER')",
                            (person_id,),
                        )
                cur.execute(
                    "UPDATE user_account SET role = %s WHERE account_id = %s",
                    (db_role, account["account_id"]),
                )
                continue

            # find or create person
            cur.execute("SELECT person_id FROM person WHERE email = %s", (email,))
            row = cur.fetchone()
            if row:
                person_id = row["person_id"]
            else:
                cur.execute(
                    "INSERT INTO person (first_name, last_name, email) VALUES (%s, %s, %s)",
                    (first, last, email),
                )
                person_id = cur.lastrowid

            # employee record (required for manager/staff FK)
            cur.execute("SELECT person_id FROM employee WHERE person_id = %s", (person_id,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO employee (person_id, branch_id, job_title, hire_date, employment_status) "
                    "VALUES (%s, %s, %s, CURDATE(), 'ACTIVE')",
                    (person_id, branch_id, job_title),
                )

            # role-specific record
            if db_role in ("MANAGER", "ADMIN"):
                cur.execute("SELECT person_id FROM manager WHERE person_id = %s", (person_id,))
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO manager (person_id, salary) VALUES (%s, 65000.00)",
                        (person_id,),
                    )
            else:
                cur.execute("SELECT person_id FROM staff WHERE person_id = %s", (person_id,))
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO staff (person_id, hourly_rate, role) VALUES (%s, 15.00, 'SERVER')",
                        (person_id,),
                    )

            # user_account
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cur.execute(
                "INSERT INTO user_account (person_id, username, password_hash, role) "
                "VALUES (%s, %s, %s, %s)",
                (person_id, username, hashed, db_role),
            )
            print(f"[SEED] Created demo account → username: {username}  password: {password}")

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"[SEED] Demo account error: {e}")

    finally:
        cur.close()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  FLOW - Enterprise Restaurant Management System")
    print("  Soul By The Sea")
    print("=" * 60)

    # 1. Start Flask in the background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("[FLOW] Customer website starting at http://127.0.0.1:5001")

    # 2. Seed database (non-blocking — skips gracefully if DB is offline)
    print("[FLOW] Seeding database...")
    seed_database()

    # 3. Optional activity simulator. Disabled for normal demo startup.
    if RUN_SIMULATION:
        sim_thread = threading.Thread(target=run_simulator, daemon=True)
        sim_thread.start()
        print("[FLOW] Activity simulator running in background.")
    else:
        print("[FLOW] Activity simulator disabled.")

    # 4. Brief pause so Flask finishes binding before the browser link is clickable
    time.sleep(1)

    # 5. Open the login screen (blocks until the user closes all windows)
    print("[FLOW] Opening login screen...")
    from login import LoginScreen
    LoginScreen().mainloop()

    print("[FLOW] Application closed.")
