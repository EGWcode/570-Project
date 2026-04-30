# FLOW — Enterprise Restaurant Chain Operations & Analytics

FLOW is a centralized restaurant operations platform built for the fictional **Soul by the Sea** restaurant chain. It supports customer ordering and reservations, staff POS workflows, manager operations, and HQ/admin analytics across multiple branches.

Built for **CSC 570 - Database Management Systems | Spring 2026 | Hampton University**.

**Team:** Zoe Battle, Day Ekoi, Jonah Goodwine, Vaughn Huey, Miles Walker, and Ethan Williams

---

## Scenario Coverage

This project implements Scenario 5: **Enterprise Restaurant Chain Operations & Analytics Platform**.

FLOW demonstrates:

- Customer-facing menu browsing, reservations, online ordering, and feedback
- Staff POS operations for table orders, online orders, reservations, and kitchen status
- Manager tools for inventory, suppliers, menu items, staff scheduling, payroll summaries, and branch reports
- Admin/HQ tools for branches, users/roles, cross-branch analytics, reviews, and clickstream behavior
- SQL storage for consistent operational data
- NoSQL storage for reviews, sentiment, clickstream behavior, and flexible activity data

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python |
| Customer Web UI | Flask, HTML, CSS, JavaScript |
| Desktop UIs | Tkinter |
| Relational Database | MySQL |
| NoSQL Database | MongoDB |
| Realtime/Cache Layer | Redis |
| Python DB Libraries | mysql-connector-python, pymongo, redis |
| Auth Support | bcrypt |
| Environment Config | python-dotenv |

---

## Application Interfaces

### Customer Web UI

Runs at:

```text
http://127.0.0.1:5001
```

Features:

- Browse menu items loaded from SQL
- Place online orders and payments
- Make reservations
- Submit ratings and feedback
- Generate clickstream events when browsing menu behavior

### Staff POS UI

Features:

- View online orders from the customer website
- Create in-restaurant table orders
- View and manage table status
- Accept/cancel reservations
- Open Kitchen Board
- Mark orders served/completed

### Manager UI

Features:

- View inventory and low-stock items
- Inventory decrement after orders
- Manage suppliers
- Manage menu items and pricing
- Manage staff scheduling
- View payroll/estimated payroll
- View reports: sales by hour, food cost percentage, top menu items, labor reports

### Admin/HQ UI

Features:

- Cross-branch dashboard
- Branch setup
- Employee/user role management
- Enterprise inventory and reservations views
- Branch performance comparison
- Review and sentiment analytics
- Clickstream analytics

---

## Architecture

FLOW uses a hybrid SQL/NoSQL design:

```text
Customer Web UI / Tkinter Desktop UIs
              |
              v
        Python Backend Modules
              |
      -------------------------
      |           |           |
      v           v           v
    MySQL      MongoDB      Redis
```

**MySQL** is the source of truth for structured operations:

- Branches
- Users and roles
- Menu items and pricing
- Reservations
- Orders and order items
- Payments
- Tables/parties
- Inventory
- Suppliers
- Shifts and payroll
- SQL reports

**MongoDB** stores flexible analytics data:

- Reviews/ratings mirror
- Sentiment fields
- Clickstream/menu browsing behavior
- Table availability/status documents
- Order event logs

**Redis** supports real-time behavior:

- Pub/sub order and inventory events
- Low-stock alerts
- Cached table/order status helpers

---

## Project Structure

```text
570-Project/
├── main.py                       # Starts Flask, seeds DB, opens login UI
├── requirements.txt              # Python dependencies
├── test_connection.py            # Database connection test
├── simulate_activity.py          # Seed/simulation utilities
├── database/
│   └── schema.sql                # MySQL schema
├── config/
│   ├── db_config.py              # MySQL connection
│   ├── mongo_config.py           # MongoDB helpers
│   └── redis_config.py           # Redis helpers
├── backend/
│   ├── auth.py                   # Login/user auth helpers
│   ├── customer.py               # Customer data helpers
│   ├── employee.py               # Employee data helpers
│   ├── inventory.py              # Inventory checks/decrement/alerts
│   ├── manager.py                # Manager reporting and operations
│   ├── orders.py                 # POS/order helpers
│   ├── payments.py               # Payment processing helpers
│   ├── reservations.py           # Reservation helpers
│   ├── reviews.py                # Review/sentiment helpers
│   └── shifts.py                 # Workforce scheduling helpers
├── customer_web/
│   ├── app.py                    # Flask customer website/API
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── script.js
│       └── style.css
└── frontend/
    ├── login.py                  # Role-based login screen
    ├── employee_ui.py            # Staff POS
    ├── manager_ui.py             # Manager dashboard
    └── HQ_ui.py                  # Admin/HQ dashboard
```

---

## Setup

### 1. Install Requirements

Python 3.12+ is recommended.

```bash
pip3 install -r requirements.txt
```

### 2. Start Services

The full demo expects these services to be running locally:

- MySQL on `localhost:3306`
- MongoDB on `localhost:27017`
- Redis on `localhost:6379`

Run all three services for the full demo.

### 3. Configure Environment

Create or update `.env` in the project root:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=flow
DB_NAME=flow_db

MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=flow_db

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

Use the credentials that match the local MySQL setup.

### 4. Load the SQL Schema

```bash
mysql -u root -p < database/schema.sql
```

### 5. Verify Database Connection

```bash
python3 test_connection.py
```

### 6. Run the Full App

```bash
python3 main.py
```

`main.py` will:

1. Start the Flask customer website on port `5001`
2. Seed branches, menu items, inventory, suppliers, schedules, and demo accounts when needed
3. Open the Tkinter login screen

If port `5001` is already in use, stop the old Flask process and run `main.py` again.

---

## Demo Login Accounts

The app seeds these demo accounts if they are missing:

| Role | Username | Password |
|---|---|---|
| Staff | `Staff` | `123` |
| Manager | `Manager` | `123` |
| Admin/HQ | `Admin` | `123` |

---

## Demo Walkthrough

Use this path to demonstrate the scenario end-to-end:

1. Open the customer web UI at `http://127.0.0.1:5001`
2. Browse menu categories and items
3. Submit a reservation for today
4. Login as Staff and confirm the reservation appears in POS
5. Accept or cancel the reservation to clear it from the POS list
6. Place an online customer order
7. Confirm the order appears in Staff POS and Kitchen Board
8. Complete the order from the POS/Kitchen workflow
9. Create an in-restaurant table order from Staff POS
10. Send the table order to the kitchen and complete payment
11. Login as Manager and show inventory
12. Place another order and show inventory decrement/low-stock behavior
13. Show Manager suppliers, staff scheduling, menu management, and reports
14. Login as Admin and show branches, users/roles, branch comparison, reviews, and clickstream analytics

---

## Scenario Requirement Checklist

| Requirement | Status |
|---|---|
| POS & billing | Implemented |
| Inventory & supplier management | Implemented |
| Workforce scheduling | Implemented |
| Customer experience analytics | Implemented |
| Branch performance comparison | Implemented |
| Customer UI: menu, reservations, feedback | Implemented |
| Staff UI: orders, tables, kitchen status | Implemented |
| Manager UI: inventory, suppliers, scheduling | Implemented |
| Admin UI: branch setup, users/roles, analytics | Implemented |
| Order & POS Service | Implemented |
| Reservation Service | Implemented |
| Inventory decrement + reorder alerts | Implemented |
| Supplier/Procurement Service | Implemented |
| Feedback & Sentiment Service | Implemented |
| Reporting: sales by hour, food cost, trends | Implemented |
| SQL operational data | Implemented |
| NoSQL reviews/sentiment/clickstream | Implemented |

---

## Notes on Data Behavior

- Customer and POS menu data use the SQL `menu_item` table.
- Online orders create SQL `orders`, `order_item`, and `payment` records.
- Inventory decrements through menu item ingredient mappings.
- Reviews are stored in SQL and mirrored into MongoDB for analytics.
- Clickstream events are stored in MongoDB when customers browse the menu.
- Manager food cost reports use SQL order/item/ingredient/inventory data.
- Payroll data is shown through processed payroll records and shift-based payroll summaries.

---

## AI Usage

AI tools were used during development. ChatGPT and Claude helped with:

- Debugging Flask reservation and order endpoint issues
- Auditing scenario requirements against the implemented code
- Updating backend functions for inventory decrement, reporting, and food cost calculations
- Improving customer web form behavior and JSON API submission
- Fixing Tkinter UI issues, including button visibility and POS window behavior
- Reviewing frontend/backend data flow across Customer, Staff, Manager, and Admin interfaces
- Formatting and cleaning project documentation
- Creating and improving the simulation/seed script used to populate demo activity
- Generating implementation suggestions, test commands, and demo walkthrough checklists

Code updates were reviewed and adapted to fit the project structure, database schema, and demo requirements.

---

## Current Status

FLOW is demo-ready for the CSC 570 restaurant chain operations scenario. The system demonstrates a hybrid SQL/NoSQL restaurant management platform with customer ordering, staff POS, manager operations, and HQ analytics.
