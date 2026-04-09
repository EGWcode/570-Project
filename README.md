# FLOW — Enterprise Restaurant Management System

**FLOW is a centralized database management system for Soul by the Sea restaurant chain**

**Designed & Built by:**
Zoe Battle,
Day Ekoi,
Jonah Goodwine,
Vaughn Huey, 
Miles Walker, &
Ethan Williams


CSC 570 - Database Management Systems | Spring 26' | Hampton University: Computer Science Department

---

## What is FLOW?

FLOW is a desktop-based enterprise management system built for Soul by the Sea, a multi-branch restaurant chain. The platform centralizes all restaurant operations into a single system, allowing customers, staff, managers, and admins to interact with the database through role-based interfaces. FLOW uses a hybrid SQL and NoSQL architecture to handle both structured transactional data and unstructured data like customer feedback and real-time order updates.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python |
| Frontend | Tkinter (Desktop GUI) |
| Primary Database | MySQL |
| NoSQL Database | MongoDB |
| Caching Layer | Redis |
| Database Connector | mysql-connector-python, pymongo |
| Environment Management | python-dotenv |
| Version Control | GitHub |
| Collaboration | Google Drive, Imessage |
| IDE | VS Code |
| Mobile Prototype | SwiftUI (Xcode) |

---

## System Architecture

FLOW follows a layered architecture where the Tkinter frontend communicates with the Python backend, which routes requests to either MySQL or MongoDB depending on the type of data being processed. Redis sits between the application and the databases as a caching layer for frequently accessed data.

```
Tkinter Desktop App (Role-Based UI)
            ↓
    Python Application Layer
            ↓
    ┌───────────────────────┐
    │       MySQL           │  Orders, Payments, Reservations,
    │  (Transactional)      │  Employees, Inventory, Schedules
    └───────────────────────┘
            ↓
    ┌───────────────────────┐
    │      MongoDB          │  Customer Feedback, Active Orders,
    │  (Unstructured)       │  Table Availability, Sentiment
    └───────────────────────┘
            ↓
    ┌───────────────────────┐
    │       Redis           │  Menu Items, Branch Dashboards,
    │  (Cache Layer)        │  Frequently Accessed Records
    └───────────────────────┘
```

---

## Role Based Interfaces

| Role | Access |
|---|---|
| Customer | View menu, place orders, make reservations, leave reviews |
| Staff/Employee | POS order entry, update order status, assign tables, check inventory, view schedule |
| Manager | All staff access plus branch analytics, purchase orders, employee scheduling, menu management |
| Admin | Cross-branch reporting, enterprise analytics, manage all branches and employees |

---

## Features

### Authentication
- Role based login screen routes users to the correct interface
- Passwords stored as hashed values in the database
- Roles: CUSTOMER, STAFF, MANAGER, ADMIN

### Customer Interface
- Browse active menu items
- Place orders
- Make and view reservations
- Submit feedback and ratings

### Staff Interface
- POS order entry and management
- Update order status (IN_PROGRESS, SERVED, COMPLETED, CANCELLED)
- Assign tables and check in/out parties
- View assigned shifts and schedules
- Check inventory levels

### Manager Interface
- View and manage all orders and payments across branch
- Manage employee schedules and shifts
- View and update inventory levels
- Create and manage purchase orders
- View branch analytics and sales reports
- View customer feedback and sentiment scores
- Manage menu items and pricing

### Admin Interface
- Cross-branch performance comparison
- Enterprise-wide analytics dashboard
- Manage all branch locations
- Manage all employees across branches

### Mobile Prototype (SwiftUI)
- A SwiftUI iOS application was developed as a visual prototype
- Demonstrates role-based interfaces for customers, staff, managers, and admins
- Uses hardcoded mock data and does not connect to the live database
- Serves as a demonstration tool for the final presentation

---

## Project Structure

```
570-PROJECT/
│
├── main.py                      # Entry point, launches the Tkinter app
├── test_connection.py           # Quick script to verify database connection
├── requirements.txt             # All Python dependencies
├── .env                         # Environment variables (credentials)
├── .gitignore                   # Files excluded from version control
├── README.md                    # Project documentation
│
├── config/
│   └── db_config.py             # Database connection config, loads from .env
│
├── database/
│   └── schema.sql               # Full MySQL schema for flow_db
│
├── backend/
│   ├── init.py
│   ├── customer.py              # Customer related queries (orders, reservations, reviews)
│   ├── employee.py              # Employee lookup and management queries
│   ├── manager.py               # Manager level queries and reporting
│   ├── orders.py                # Order and order item queries
│   ├── reservations.py          # Reservation queries and availability checks
│   ├── inventory.py             # Inventory and purchase order queries
│   ├── payments.py              # Payment processing queries
│   ├── reviews.py               # Review and feedback queries
│   └── shifts.py                # Shift schedule queries
│
└── frontend/
├── init.py
├── login.py                 # Login screen, routes to correct interface by role
├── customer_ui.py           # Customer interface windows and screens
├── employee_ui.py           # Staff/employee interface windows and screens
├── manager_ui.py            # Manager interface windows and screens
└── admin_ui.py              # Admin interface windows and screens
```
---

## Database Schema

The following tables are defined in `database/schema.sql`:

**Core Entities**
- **person** — base table for all individuals in the system
- **customer** — subtype of person, stores dietary restrictions
- **employee** — subtype of person, linked to a branch
- **manager** — subtype of employee, stores salary
- **staff** — subtype of employee, stores hourly rate and role
- **user_account** — login credentials and role assignment for all users

**Branch & Operations**
- **branch** — individual restaurant locations
- **branch_hours** — operating hours per branch per day of week

**Reservations & Dining**
- **reservation** — customer reservation records
- **party** — dining party check-in and check-out tracking

**Orders & Payments**
- **orders** — order records linked to party, branch, and employee
- **order_item** — individual line items per order
- **payment** — payment records linked to orders

**Menu**
- **menu_item** — all menu items with pricing and availability
- **menu_item_ingredient** — links menu items to inventory ingredients

**Inventory & Procurement**
- **inventory_item** — stock levels per branch
- **supplier** — external supplier records
- **purchase_order** — procurement orders placed with suppliers
- **purchase_order_item** — individual items per purchase order

**Workforce**
- **shift_schedule** — employee shift assignments per branch

**Feedback**
- **review** — customer ratings, comments, and sentiment scores

---

## Setup & Running Locally

### Prerequisites
- Python 3.12+
- MySQL
- pip3

### Installation

```bash
# Clone the repo
git clone https://github.com/EGWcode/570-Project.git
cd flow-app

# Install dependencies
pip3 install -r requirements.txt
```

### Database Setup

```bash
# Load the schema into MySQL
mysql -u root -p < database/schema.sql
```

### Environment Configuration

The `.env` file is included in the repo for team collaboration. It is pre-configured with the following shared credentials:

DB_HOST=localhost
DB_USER=root
DB_PASSWORD=flow
DB_NAME=flow_db

### Verify Connection

```bash
python3 test_connection.py
```

You should see: `Connection successful!`

### Run the App

```bash
python3 main.py
```

---

## Team (Update this with contribution)

| Name | Role |
|---|---|
| Day Ekoi | Physical Design, Backend Development |
| Jonah Goodwine |  |
| Zoe Battle |  |
| Vaughn Huey | |
| Miles Walker | |
| Ethan Williams | |

---

## Current Status

FLOW is currently in active development as part of CSC 570 Milestone 4. The database schema and connection layer are complete. Backend query modules and Tkinter frontend interfaces are currently being developed and will be connected to the live MySQL database for the final presentation.
