# schema.sql
#
#     FLOW - Enterprise Restaurant Management System
#   CSC 570 Sp 26'
#     Created by Jonah Goodwine - March 6, 2026
#     Updated/Refined by Day Ekoi - April 6-9, 2026
#
# This file defines the full relational database schema for the FLOW system.
# It creates the flow_db MySQL database and all associated tables that support
# the enterprise restaurant operations of Soul by the Sea.
#
# Tables defined here support the following system features:
#   - Multi-branch operational support (branch, branch_hours)
#   - User authentication and role based access (user_account)
#   - Customer and employee management (person, customer, employee, manager, staff)
#   - Reservations and party management (reservation, party)
#   - Order processing and POS (orders, order_item, payment)
#   - Menu management (menu_item, menu_item_ingredient)
#   - Inventory and procurement (inventory_item, supplier, purchase_order, purchase_order_item)
#   - Workforce scheduling (shift_schedule)
#   - Customer feedback and sentiment (review)
#
# The three tables added by Day Ekoi (user_account, menu_item_ingredient, branch_hours)
# were added to support login functionality, inventory decrement on order placement,
# and reservation validation against branch operating hours.

DROP DATABASE IF EXISTS flow_db;
CREATE DATABASE flow_db;
USE flow_db;

CREATE TABLE branch (
    branch_id INT AUTO_INCREMENT PRIMARY KEY,
    branch_name VARCHAR(50) NOT NULL UNIQUE,
    address VARCHAR(100),
    phone VARCHAR(15),
    manager_id INT NULL
);

CREATE TABLE person (
    person_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    dob DATE,
    phone VARCHAR(15),
    address VARCHAR(100),
    email VARCHAR(60) UNIQUE
);

CREATE TABLE customer (
    person_id INT PRIMARY KEY,
    dietary_restrictions VARCHAR(100),
    CONSTRAINT fk_customer_person
        FOREIGN KEY (person_id) REFERENCES person(person_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE employee (
    person_id INT PRIMARY KEY,
    branch_id INT NOT NULL,
    job_title VARCHAR(30) NOT NULL,
    hire_date DATE NOT NULL,
    employment_status VARCHAR(15) NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT fk_employee_person
        FOREIGN KEY (person_id) REFERENCES person(person_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_employee_branch
        FOREIGN KEY (branch_id) REFERENCES branch(branch_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT chk_employee_status
        CHECK (employment_status IN ('ACTIVE', 'INACTIVE', 'LEAVE', 'TERMINATED'))
);

CREATE TABLE manager (
    person_id INT PRIMARY KEY,
    salary DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_manager_employee
        FOREIGN KEY (person_id) REFERENCES employee(person_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT chk_manager_salary
        CHECK (salary >= 0)
);

CREATE TABLE staff (
    person_id INT PRIMARY KEY,
    hourly_rate DECIMAL(10,2) NOT NULL,
    role VARCHAR(30) NOT NULL,
    CONSTRAINT fk_staff_employee
        FOREIGN KEY (person_id) REFERENCES employee(person_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT chk_staff_hourly_rate
        CHECK (hourly_rate >= 0)
);

ALTER TABLE branch
    ADD CONSTRAINT fk_branch_manager
    FOREIGN KEY (manager_id) REFERENCES manager(person_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE;

CREATE TABLE supplier (
    supplier_id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_name VARCHAR(50) NOT NULL UNIQUE,
    contact_name VARCHAR(50),
    phone VARCHAR(15),
    email VARCHAR(60) UNIQUE,
    address VARCHAR(100)
);

CREATE TABLE menu_item (
    menu_item_id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(50) NOT NULL,
    category VARCHAR(30) NOT NULL,
    description VARCHAR(120),
    price DECIMAL(10,2) NOT NULL,
    active_status BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_menu_item_price
        CHECK (price > 0)
);

CREATE TABLE reservation (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
    person_id INT NOT NULL,
    branch_id INT NOT NULL,
    reservation_datetime DATETIME NOT NULL,
    party_size INT NOT NULL,
    status VARCHAR(15) NOT NULL,
    CONSTRAINT fk_reservation_person
        FOREIGN KEY (person_id) REFERENCES person(person_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_reservation_branch
        FOREIGN KEY (branch_id) REFERENCES branch(branch_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT chk_reservation_party_size
        CHECK (party_size BETWEEN 1 AND 20),
    CONSTRAINT chk_reservation_status
        CHECK (status IN ('CONFIRMED', 'PENDING', 'CANCELLED', 'COMPLETED', 'SEATED'))
);

CREATE TABLE party (
    party_id INT AUTO_INCREMENT PRIMARY KEY,
    reservation_id INT NULL,
    branch_id INT NOT NULL,
    table_number TINYINT NOT NULL,
    party_size INT NOT NULL,
    check_in_datetime DATETIME,
    check_out_datetime DATETIME,
    CONSTRAINT fk_party_reservation
        FOREIGN KEY (reservation_id) REFERENCES reservation(reservation_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT fk_party_branch
        FOREIGN KEY (branch_id) REFERENCES branch(branch_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT chk_party_size
        CHECK (party_size BETWEEN 1 AND 20),
    CONSTRAINT chk_party_checkout
        CHECK (check_out_datetime IS NULL OR check_in_datetime IS NULL OR check_out_datetime >= check_in_datetime)
);

CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    party_id INT NOT NULL,
    branch_id INT NOT NULL,
    employee_id INT NOT NULL,
    order_datetime DATETIME NOT NULL,
    order_status VARCHAR(15) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_orders_party
        FOREIGN KEY (party_id) REFERENCES party(party_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_orders_branch
        FOREIGN KEY (branch_id) REFERENCES branch(branch_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_orders_employee
        FOREIGN KEY (employee_id) REFERENCES employee(person_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT chk_order_status
        CHECK (order_status IN ('IN_PROGRESS', 'SERVED', 'CANCELLED', 'COMPLETED')),
    CONSTRAINT chk_order_subtotal
        CHECK (subtotal >= 0),
    CONSTRAINT chk_order_tax
        CHECK (tax_amount >= 0),
    CONSTRAINT chk_order_total
        CHECK (total_amount >= 0)
);

CREATE TABLE order_item (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    menu_item_id INT NOT NULL,
    quantity TINYINT NOT NULL,
    item_price DECIMAL(10,2) NOT NULL,
    special_instructions VARCHAR(120),
    CONSTRAINT fk_order_item_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_order_item_menu_item
        FOREIGN KEY (menu_item_id) REFERENCES menu_item(menu_item_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT chk_order_item_quantity
        CHECK (quantity > 0),
    CONSTRAINT chk_order_item_price
        CHECK (item_price >= 0)
);

CREATE TABLE payment (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    payment_type VARCHAR(15) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    tip_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    payment_datetime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT chk_payment_type
        CHECK (payment_type IN ('CASH', 'CREDIT', 'DEBIT', 'GIFT_CARD', 'MOBILE')),
    CONSTRAINT chk_payment_amount
        CHECK (amount >= 0),
    CONSTRAINT chk_tip_amount
        CHECK (tip_amount >= 0)
);

CREATE TABLE inventory_item (
    inventory_item_id INT AUTO_INCREMENT PRIMARY KEY,
    branch_id INT NOT NULL,
    item_name VARCHAR(50) NOT NULL,
    quantity_on_hand INT NOT NULL,
    unit_type VARCHAR(10) NOT NULL,
    reorder_level DECIMAL(10,2) NOT NULL,
    cost_per_unit DECIMAL(10,2) NOT NULL,
    supplier_id INT NULL,
    CONSTRAINT fk_inventory_branch
        FOREIGN KEY (branch_id) REFERENCES branch(branch_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_inventory_supplier
        FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT chk_inventory_qty
        CHECK (quantity_on_hand >= 0),
    CONSTRAINT chk_inventory_unit_type
        CHECK (unit_type IN ('LB', 'LBS', 'OZ', 'GAL', 'L', 'KG', 'G', 'ML', 'CASE', 'CASES', 'PACK', 'PACKS', 'EA')),
    CONSTRAINT chk_inventory_reorder
        CHECK (reorder_level >= 0),
    CONSTRAINT chk_inventory_cost
        CHECK (cost_per_unit >= 0)
);

CREATE TABLE purchase_order (
    purchase_order_id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_id INT NOT NULL,
    branch_id INT NOT NULL,
    order_date DATE NOT NULL,
    delivery_date DATE NULL,
    status VARCHAR(15) NOT NULL,
    total_cost DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_purchase_order_supplier
        FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_purchase_order_branch
        FOREIGN KEY (branch_id) REFERENCES branch(branch_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT chk_purchase_order_dates
        CHECK (delivery_date IS NULL OR delivery_date >= order_date),
    CONSTRAINT chk_purchase_order_status
        CHECK (status IN ('CREATED', 'SENT', 'RECEIVED', 'CANCELLED', 'IN_PROGRESS')),
    CONSTRAINT chk_purchase_order_total
        CHECK (total_cost >= 0)
);

CREATE TABLE purchase_order_item (
    purchase_order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_order_id INT NOT NULL,
    inventory_item_id INT NOT NULL,
    quantity_ordered INT NOT NULL,
    unit_cost DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_purchase_order_item_po
        FOREIGN KEY (purchase_order_id) REFERENCES purchase_order(purchase_order_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_purchase_order_item_inventory
        FOREIGN KEY (inventory_item_id) REFERENCES inventory_item(inventory_item_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT chk_purchase_order_item_qty
        CHECK (quantity_ordered > 0),
    CONSTRAINT chk_purchase_order_item_cost
        CHECK (unit_cost >= 0)
);

CREATE TABLE shift_schedule (
    shift_id INT AUTO_INCREMENT PRIMARY KEY,
    person_id INT NOT NULL,
    branch_id INT NOT NULL,
    shift_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    role_assigned VARCHAR(30) NOT NULL,
    CONSTRAINT fk_shift_employee
        FOREIGN KEY (person_id) REFERENCES employee(person_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_shift_branch
        FOREIGN KEY (branch_id) REFERENCES branch(branch_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT chk_shift_times
        CHECK (end_time > start_time)
);

CREATE TABLE review (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    person_id INT NOT NULL,
    branch_id INT NOT NULL,
    rating TINYINT NOT NULL,
    comments VARCHAR(250),
    sentiment_score DECIMAL(3,2),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_review_person
        FOREIGN KEY (person_id) REFERENCES person(person_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_review_branch
        FOREIGN KEY (branch_id) REFERENCES branch(branch_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT chk_review_rating
        CHECK (rating BETWEEN 1 AND 5),
    CONSTRAINT chk_review_sentiment
        CHECK (sentiment_score IS NULL OR sentiment_score BETWEEN -1.00 AND 1.00)
);

# ---------------------------------------------------------------
# Tables below added by Day Ekoi - April 6-9, 2026
# ---------------------------------------------------------------

# user_account
# Stores login credentials for all system users.
# Required to support the role based login screen in the Tkinter application.
# Each account is linked to a person and assigned a role that determines
# which interface they are routed to upon login.

CREATE TABLE user_account (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    person_id INT NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(15) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_account_person
        FOREIGN KEY (person_id) REFERENCES person(person_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT chk_account_role
        CHECK (role IN ('CUSTOMER', 'STAFF', 'MANAGER', 'ADMIN'))
);

# menu_item_ingredient
# Links menu items to the inventory ingredients they require.
# Supports automatic inventory decrement when an order is placed,
# ensuring stock levels stay accurate after each transaction.

CREATE TABLE menu_item_ingredient (
    id INT AUTO_INCREMENT PRIMARY KEY,
    menu_item_id INT NOT NULL,
    inventory_item_id INT NOT NULL,
    quantity_required DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_ingredient_menu_item
        FOREIGN KEY (menu_item_id) REFERENCES menu_item(menu_item_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_ingredient_inventory
        FOREIGN KEY (inventory_item_id) REFERENCES inventory_item(inventory_item_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

# branch_hours
# Stores the operating hours for each branch by day of the week.
# Used to validate reservation requests against actual branch availability,
# preventing bookings outside of operating hours.

CREATE TABLE branch_hours (
    hours_id INT AUTO_INCREMENT PRIMARY KEY,
    branch_id INT NOT NULL,
    day_of_week VARCHAR(10) NOT NULL,
    open_time TIME NOT NULL,
    close_time TIME NOT NULL,
    CONSTRAINT fk_hours_branch
        FOREIGN KEY (branch_id) REFERENCES branch(branch_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT chk_day_of_week
        CHECK (day_of_week IN ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'))
);