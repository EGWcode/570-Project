"""
FLOW Database Test
CSC 570 - Enterprise Restaurant Management System

Report-friendly test script for screenshots.
Checks that MySQL, Redis, and MongoDB are connected, then runs basic
database operations for each service.

Run with:
    python3 test_connection.py
"""

import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.db_config import get_connection, close_connection


passed = 0
failed = 0


def line(char="-"):
    print(char * 68)


def title(text):
    print()
    line("=")
    print(f"  {text}")
    line("=")


def section(text):
    print()
    line()
    print(f"  {text}")
    line()


def check(label, condition, detail=""):
    global passed, failed
    icon = "PASS" if condition else "FAIL"
    print(f"  [{icon}] {label}")
    if detail:
        print(f"         {detail}")
    if condition:
        passed += 1
    else:
        failed += 1
    return condition


def fail(label, error):
    return check(label, False, str(error))


def format_value(value):
    text = str(value)
    if len(text) > 24:
        return text[:21] + "..."
    return text


def print_table(label, rows):
    print()
    print(f"  {label}")
    if not rows:
        print("    (no rows found)")
        return

    columns = list(rows[0].keys())
    widths = {
        column: max(len(column), *(len(format_value(row.get(column))) for row in rows))
        for column in columns
    }
    header = " | ".join(column.ljust(widths[column]) for column in columns)
    divider = "-+-".join("-" * widths[column] for column in columns)

    print(f"    {header}")
    print(f"    {divider}")
    for row in rows:
        values = " | ".join(format_value(row.get(column)).ljust(widths[column]) for column in columns)
        print(f"    {values}")


def mysql_connection_test():
    conn = get_connection()
    if not conn:
        return None
    return conn


def redis_connection_test():
    from config.redis_config import get_redis

    redis_client = get_redis()
    redis_client.ping()
    return redis_client


def mongo_connection_test():
    from config.mongo_config import get_mongo_db

    mongo_db = get_mongo_db()
    mongo_db.command("ping")
    return mongo_db


def cleanup_mysql_test_data(conn):
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT branch_id
            FROM branch
            WHERE branch_name = 'Soul by the Sea Test Branch'
            """
        )
        branch_ids = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT person_id
            FROM person
            WHERE email IN ('soul.test.customer@test.com', 'soul.test.staff@test.com')
            """
        )
        person_ids = [row[0] for row in cursor.fetchall()]

        if branch_ids:
            placeholders = ",".join(["%s"] * len(branch_ids))
            cursor.execute(
                f"SELECT person_id FROM employee WHERE branch_id IN ({placeholders})",
                branch_ids,
            )
            employee_ids = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                f"""
                DELETE FROM payment
                WHERE order_id IN (
                    SELECT order_id FROM orders WHERE branch_id IN ({placeholders})
                )
                """,
                branch_ids,
            )
            cursor.execute(
                f"""
                DELETE FROM order_item
                WHERE order_id IN (
                    SELECT order_id FROM orders WHERE branch_id IN ({placeholders})
                )
                """,
                branch_ids,
            )
            cursor.execute(f"DELETE FROM orders WHERE branch_id IN ({placeholders})", branch_ids)
            cursor.execute(f"DELETE FROM party WHERE branch_id IN ({placeholders})", branch_ids)
            cursor.execute(f"DELETE FROM reservation WHERE branch_id IN ({placeholders})", branch_ids)
            cursor.execute(f"DELETE FROM review WHERE branch_id IN ({placeholders})", branch_ids)
            cursor.execute(f"DELETE FROM inventory_item WHERE branch_id IN ({placeholders})", branch_ids)

            if employee_ids:
                employee_placeholders = ",".join(["%s"] * len(employee_ids))
                cursor.execute(
                    f"DELETE FROM user_account WHERE person_id IN ({employee_placeholders})",
                    employee_ids,
                )
                cursor.execute(
                    f"DELETE FROM staff WHERE person_id IN ({employee_placeholders})",
                    employee_ids,
                )
                cursor.execute(
                    f"DELETE FROM manager WHERE person_id IN ({employee_placeholders})",
                    employee_ids,
                )
                cursor.execute(
                    f"DELETE FROM employee WHERE person_id IN ({employee_placeholders})",
                    employee_ids,
                )

            cursor.execute(f"DELETE FROM branch WHERE branch_id IN ({placeholders})", branch_ids)

        if person_ids:
            placeholders = ",".join(["%s"] * len(person_ids))
            cursor.execute(f"DELETE FROM user_account WHERE person_id IN ({placeholders})", person_ids)
            cursor.execute(f"DELETE FROM customer WHERE person_id IN ({placeholders})", person_ids)
            cursor.execute(f"DELETE FROM staff WHERE person_id IN ({placeholders})", person_ids)
            cursor.execute(f"DELETE FROM employee WHERE person_id IN ({placeholders})", person_ids)
            cursor.execute(f"DELETE FROM person WHERE person_id IN ({placeholders})", person_ids)

        cursor.execute("DELETE FROM menu_item WHERE item_name = 'Soul by the Sea Test Entree'")
        cursor.execute("DELETE FROM supplier WHERE supplier_name = 'Soul by the Sea Test Supplier'")
        conn.commit()
    finally:
        cursor.close()


def test_mysql_crud(conn):
    cleanup_mysql_test_data(conn)
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            INSERT INTO branch (branch_name, address, phone)
            VALUES ('Soul by the Sea Test Branch', '100 Ocean Test Ave', '555-0100')
            """
        )
        branch_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO supplier (supplier_name, contact_name, phone, email, address)
            VALUES ('Soul by the Sea Test Supplier', 'Test Supplier', '555-0101',
                    'soul.test.supplier@test.com', '200 Ocean Test Ave')
            """
        )
        supplier_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO menu_item (item_name, category, description, price)
            VALUES ('Soul by the Sea Test Entree', 'ENTREE', 'Test menu item', 12.50)
            """
        )
        menu_item_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO inventory_item
                (branch_id, item_name, quantity_on_hand, unit_type,
                 reorder_level, cost_per_unit, supplier_id)
            VALUES (%s, 'Soul by the Sea Test Ingredient', 20, 'EA', 5, 2.25, %s)
            """,
            (branch_id, supplier_id),
        )

        cursor.execute(
            """
            INSERT INTO person (first_name, last_name, phone, email)
            VALUES ('Soul', 'Customer', '555-0102', 'soul.test.customer@test.com')
            """
        )
        customer_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO customer (person_id, dietary_restrictions) VALUES (%s, 'None')",
            (customer_id,),
        )

        cursor.execute(
            """
            INSERT INTO person (first_name, last_name, phone, email)
            VALUES ('Soul', 'Staff', '555-0103', 'soul.test.staff@test.com')
            """
        )
        staff_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO employee (person_id, branch_id, job_title, hire_date)
            VALUES (%s, %s, 'Server', CURDATE())
            """,
            (staff_id, branch_id),
        )
        cursor.execute(
            "INSERT INTO staff (person_id, hourly_rate, role) VALUES (%s, 18.00, 'SERVER')",
            (staff_id,),
        )

        cursor.execute(
            """
            INSERT INTO reservation
                (person_id, branch_id, reservation_datetime, party_size, status)
            VALUES (%s, %s, NOW(), 2, 'PENDING')
            """,
            (customer_id, branch_id),
        )
        reservation_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO party
                (reservation_id, branch_id, table_number, party_size, check_in_datetime)
            VALUES (%s, %s, 4, 2, NOW())
            """,
            (reservation_id, branch_id),
        )
        party_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO orders
                (party_id, branch_id, employee_id, order_datetime,
                 order_status, subtotal, tax_amount, total_amount)
            VALUES (%s, %s, %s, NOW(), 'IN_PROGRESS', 0.00, 0.00, 0.00)
            """,
            (party_id, branch_id, staff_id),
        )
        order_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO order_item (order_id, menu_item_id, quantity, item_price)
            VALUES (%s, %s, 2, 12.50)
            """,
            (order_id, menu_item_id),
        )
        cursor.execute(
            """
            UPDATE orders
            SET subtotal = 25.00, tax_amount = 2.00, total_amount = 27.00
            WHERE order_id = %s
            """,
            (order_id,),
        )

        cursor.execute(
            """
            INSERT INTO payment (order_id, payment_type, amount, tip_amount)
            VALUES (%s, 'CREDIT', 27.00, 4.00)
            """,
            (order_id,),
        )
        cursor.execute(
            """
            INSERT INTO review (person_id, branch_id, rating, comments, sentiment_score)
            VALUES (%s, %s, 5, 'Test review for Soul by the Sea', 0.90)
            """,
            (customer_id, branch_id),
        )

        conn.commit()
        check("MySQL CREATE - inserted branch, users, reservation, order, payment, review", True)

        cursor.execute(
            """
            SELECT branch_id, branch_name, phone
            FROM branch
            WHERE branch_id = %s
            """,
            (branch_id,),
        )
        print_table("MySQL table: branch", cursor.fetchall())

        cursor.execute(
            """
            SELECT person_id, first_name, last_name, email
            FROM person
            WHERE person_id IN (%s, %s)
            ORDER BY person_id
            """,
            (customer_id, staff_id),
        )
        print_table("MySQL table: person", cursor.fetchall())

        cursor.execute(
            """
            SELECT reservation_id, branch_id, person_id, party_size, status
            FROM reservation
            WHERE reservation_id = %s
            """,
            (reservation_id,),
        )
        print_table("MySQL table: reservation", cursor.fetchall())

        cursor.execute(
            """
            SELECT order_id, party_id, order_status, subtotal, tax_amount, total_amount
            FROM orders
            WHERE order_id = %s
            """,
            (order_id,),
        )
        print_table("MySQL table: orders", cursor.fetchall())

        cursor.execute(
            """
            SELECT payment_id, order_id, payment_type, amount, tip_amount
            FROM payment
            WHERE order_id = %s
            """,
            (order_id,),
        )
        print_table("MySQL table: payment", cursor.fetchall())

        cursor.execute(
            """
            SELECT review_id, person_id, branch_id, rating, comments
            FROM review
            WHERE branch_id = %s
            """,
            (branch_id,),
        )
        print_table("MySQL table: review", cursor.fetchall())

        cursor.execute(
            """
            SELECT b.branch_name, o.order_status, o.total_amount, p.payment_type, r.rating
            FROM branch b
            JOIN orders o ON b.branch_id = o.branch_id
            JOIN payment p ON o.order_id = p.order_id
            JOIN review r ON b.branch_id = r.branch_id
            WHERE b.branch_id = %s
            """,
            (branch_id,),
        )
        row = cursor.fetchone()
        check(
            "MySQL READ - joined restaurant records were retrieved",
            row is not None and row["branch_name"] == "Soul by the Sea Test Branch",
            f"order_status={row['order_status']}, total=${row['total_amount']}" if row else "",
        )

        cursor.execute(
            """
            UPDATE orders
            SET order_status = 'COMPLETED'
            WHERE order_id = %s
            """,
            (order_id,),
        )
        conn.commit()
        cursor.execute(
            """
            SELECT order_id, order_status, subtotal, tax_amount, total_amount
            FROM orders
            WHERE order_id = %s
            """,
            (order_id,),
        )
        updated = cursor.fetchone()
        check(
            "MySQL UPDATE - order status changed to COMPLETED",
            updated is not None and updated["order_status"] == "COMPLETED",
        )
        print_table("MySQL updated row: orders", [updated] if updated else [])

        cleanup_mysql_test_data(conn)
        cursor.execute("SELECT branch_id FROM branch WHERE branch_name = 'Soul by the Sea Test Branch'")
        deleted = cursor.fetchone()
        check("MySQL DELETE - test data cleaned up", deleted is None)

    except Exception as error:
        conn.rollback()
        fail("MySQL basic database functions", error)
        cleanup_mysql_test_data(conn)
    finally:
        cursor.close()


def test_redis_functions(redis_client):
    key = "flow:test:connection"
    channel = "flow:test:updates"

    try:
        redis_client.set(key, "connected", ex=60)
        check("Redis SET - cached a test value", True)

        value = redis_client.get(key)
        check("Redis GET - retrieved cached value", value == "connected", f"value={value}")
        print_table(
            "Redis key/value data",
            [{"key": key, "value": value, "ttl_seconds": redis_client.ttl(key)}],
        )

        subscribers = redis_client.publish(channel, "FLOW test message")
        check("Redis PUBLISH - sent update message", subscribers >= 0, f"subscribers={subscribers}")
        print_table(
            "Redis published message",
            [{"channel": channel, "message": "FLOW test message"}],
        )

        redis_client.delete(key)
        check("Redis DELETE - removed cached value", redis_client.get(key) is None)

    except Exception as error:
        fail("Redis basic database functions", error)


def test_mongo_functions(mongo_db):
    collection = mongo_db.flow_test_data
    test_id = f"flow-test-{datetime.now(UTC).isoformat()}"

    try:
        collection.delete_many({"test_suite": "FLOW_TEST"})

        collection.insert_one(
            {
                "test_id": test_id,
                "test_suite": "FLOW_TEST",
                "database": "MongoDB",
                "status": "created",
                "created_at": datetime.now(UTC),
            }
        )
        check("MongoDB INSERT - created test document", True)

        document = collection.find_one({"test_id": test_id})
        check(
            "MongoDB FIND - retrieved test document",
            document is not None and document["status"] == "created",
        )
        if document:
            print_table(
                "MongoDB collection: flow_test_data",
                [
                    {
                        "test_id": document["test_id"],
                        "database": document["database"],
                        "status": document["status"],
                        "created_at": document["created_at"],
                    }
                ],
            )

        collection.update_one({"test_id": test_id}, {"$set": {"status": "updated"}})
        updated = collection.find_one({"test_id": test_id})
        check(
            "MongoDB UPDATE - changed document status",
            updated is not None and updated["status"] == "updated",
        )
        if updated:
            print_table(
                "MongoDB updated document",
                [{"test_id": updated["test_id"], "status": updated["status"]}],
            )

        collection.delete_one({"test_id": test_id})
        deleted = collection.find_one({"test_id": test_id})
        check("MongoDB DELETE - removed test document", deleted is None)

    except Exception as error:
        fail("MongoDB basic database functions", error)
    finally:
        collection.delete_many({"test_suite": "FLOW_TEST"})


def main():
    title("FLOW DATABASE CONNECTION TEST")

    section("CONNECTION STATUS")
    mysql_conn = None
    redis_client = None
    mongo_db = None

    try:
        mysql_conn = mysql_connection_test()
        check("MySQL connected to flow_db", mysql_conn is not None)
    except Exception as error:
        fail("MySQL connected to flow_db", error)

    try:
        redis_client = redis_connection_test()
        check("Redis connected on localhost:6379", True)
    except Exception as error:
        fail("Redis connected on localhost:6379", error)

    try:
        mongo_db = mongo_connection_test()
        check("MongoDB connected on localhost:27017", True)
    except Exception as error:
        fail("MongoDB connected on localhost:27017", error)

    if mysql_conn is not None and redis_client is not None and mongo_db is not None:
        print()
        print("  >>> ALL DATABASES CONNECTED SUCCESSFULLY <<<")
    else:
        print()
        print("  >>> One or more database connections failed. Check services and .env. <<<")

    if mysql_conn:
        section("MYSQL BASIC DATABASE FUNCTIONS")
        test_mysql_crud(mysql_conn)

    if redis_client:
        section("REDIS BASIC DATABASE FUNCTIONS")
        test_redis_functions(redis_client)

    if mongo_db is not None:
        section("MONGODB BASIC DATABASE FUNCTIONS")
        test_mongo_functions(mongo_db)

    if mysql_conn:
        close_connection(mysql_conn)

    section("TEST SUMMARY")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")

    if failed == 0:
        print()
        print("  RESULT: FLOW database test completed successfully.")
        return 0

    print()
    print("  RESULT: FLOW database test found an issue.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
