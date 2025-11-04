"""
user.py
Provides functions and classes for user management including creating
users, authenticating logins and enforcing role based permissions.
Users are stored in the `users` table of the SQLite database with
a hashed password and a role (admin, manager or cashier). Roles
determine which actions in the application a user can perform.

Usage:
    from db import Database
    from user import UserManager

    db = Database('pos.db')
    manager = UserManager(db)
    manager.create_user('admin', 'password', 'admin')
    assert manager.authenticate('admin', 'password')

Roles:
    - admin: full permissions
    - manager: can manage products and view reports
    - cashier: can only process sales
"""

from __future__ import annotations

import sqlite3
from typing import Optional, Tuple
from utils import hash_password, verify_password


class UserManager:
    """Encapsulates user related functionality."""

    def __init__(self, db: 'Database') -> None:
        from db import Database  # import within method to avoid circular import at top-level
        if not isinstance(db, Database):
            raise TypeError("db must be a Database instance")
        self.db = db

    def create_user(self, username: str, password: str, role: str) -> None:
        """Create a new user with the given username, password and role.

        Raises sqlite3.IntegrityError if username already exists.
        """
        password_hash = hash_password(password)
        with self.db.connection as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role),
            )

    def authenticate(self, username: str, password: str) -> Optional[Tuple[int, str]]:
        """Check if the given username and password are valid.

        Returns a tuple of (user_id, role) if authentication succeeds or
        None otherwise. Using user_id allows tracking which user carried
        out a sale or other operation.
        """
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT id, password_hash, role FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row and verify_password(password, row["password_hash"]):
            return row["id"], row["role"]
        return None

    def list_users(self) -> list:
        """Return a list of all users with their roles."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT id, username, role, created_at FROM users")
        return cursor.fetchall()

    def delete_user(self, user_id: int) -> None:
        """Delete a user by ID. Admin users should not delete themselves."""
        with self.db.connection as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
