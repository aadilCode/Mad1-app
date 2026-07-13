import sqlite3
import config
from werkzeug.security import generate_password_hash

def get_db():
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():

    connection = get_db()

    # ---------------- USERS TABLE ----------------
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # ---------------- TREKS TABLE ----------------
    connection.execute("""
        CREATE TABLE IF NOT EXISTS treks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            duration INTEGER NOT NULL,
            total_slots INTEGER NOT NULL,
            available_slots INTEGER NOT NULL,
            staff_id INTEGER,
            status TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            description TEXT
        )
    """)

    # ---------------- BOOKINGS TABLE ----------------
    connection.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            trek_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # Check if admin already exists
    admin = connection.execute(
        "SELECT * FROM users WHERE role = ?",
        ("admin",)
    ).fetchone()

    # If not, create one
    if admin is None:
        connection.execute(
            """
            INSERT INTO users
            (name, email, phone, password, role, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "System Admin",
                config.ADMIN_EMAIL,
                "0000000000",
                generate_password_hash(config.ADMIN_PASSWORD),
                "admin",
                "active"
            )
        )

    connection.commit()
    connection.close()