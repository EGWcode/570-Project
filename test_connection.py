from config.db_config import get_connection, close_connection

conn = get_connection()
if conn:
    print("Connection successful!")
    close_connection(conn)
else:
    print("Connection failed.")

from backend.auth import register_user, login_user




# Test registration
success, message = register_user(
    first_name="Day",
    last_name="Ekoi",
    email="day@example.com",
    phone="7571234567",
    username="day_ekoi",
    password="flow",
    role="ADMIN"
)
print(f"Register: {message}")

# Test login
user, message = login_user("day_ekoi", "flow")
print(f"Login: {message}")
if user:
    print(f"Welcome {user['first_name']} {user['last_name']} - Role: {user['role']}")