"""
db.py
This module provides functions to interact with the SQLite database used by the
POS application. It is responsible for creating the database schema on
first use and providing a simple wrapper around the sqlite3 module to
perform common operations. The database schema covers products, categories,
suppliers, users, sales and sale items, as well as basic configuration tables.

The choice of SQLite ensures that all data remains on the local machine and
that the application can run completely offline. SQLite is reliable,
light‑weight and supports transactions, making it a good fit for a POS
application.  See https://sqlite.org/index.html for details on SQLite.

Usage:
    from db import Database
    db = Database('pos.db')
    db.init_db()  # create tables if they don't exist
    # Use db.connection to execute SQL commands
"""

import os
import sqlite3
from pathlib import Path


class Database:
    """Encapsulates a connection to a SQLite database.

    On instantiation the database will be created if it does not already
    exist. The `init_db` method creates all necessary tables. For every
    operation you can use the `connection` attribute directly or use helper
    methods provided in this class.
    """

    def __init__(self, db_path: str = "pos.db") -> None:
        self.db_path = db_path
        # Ensure the directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row  # access columns by name

    def init_db(self) -> None:
        """Create the database schema if it does not already exist."""
        cursor = self.connection.cursor()
        # Enable foreign key support
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Categories table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT
            );
            """
        )

        # Suppliers table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                contact TEXT,
                phone TEXT,
                email TEXT
            );
            """
        )

        # Products table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sku TEXT UNIQUE,
                purchase_price REAL NOT NULL,
                selling_price REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                category_id INTEGER,
                supplier_id INTEGER,
                description TEXT,
                image_path TEXT,
                min_stock INTEGER DEFAULT 0,
                FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL,
                FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
            );
            """
        )

        # Users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin','manager','cashier')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Sales table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total REAL NOT NULL,
                tax REAL NOT NULL,
                discount REAL NOT NULL,
                payment_method TEXT NOT NULL,
                held BOOLEAN DEFAULT 0,
                user_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )

        # Sale items table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
            """
        )

        # Inventory history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                change INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT,
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        """Close the database connection."""
        self.connection.close()
