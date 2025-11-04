"""
product.py
Defines a ProductManager class responsible for product CRUD operations,
category handling, and inventory adjustments. Products are stored in
the `products` table and categories in the `categories` table. The
manager also supports importing and exporting products via CSV files.

The application uses SKUs (stock keeping units) as unique identifiers for
products. A SKU can be scanned or entered manually at checkout. When
scanning a product not found in the database, the cashier can quickly
add it via this module.
"""

from __future__ import annotations

import sqlite3
from typing import Iterable, List, Dict, Optional
from utils import read_csv, write_csv


class ProductManager:
    """Encapsulates product and category operations."""

    def __init__(self, db: 'Database') -> None:
        from db import Database  # avoid top-level circular import
        if not isinstance(db, Database):
            raise TypeError("db must be a Database instance")
        self.db = db

    # Category operations
    def add_category(self, name: str, description: str = "") -> int:
        """Insert a new category and return its id."""
        with self.db.connection as conn:
            cursor = conn.execute(
                "INSERT INTO categories (name, description) VALUES (?, ?)",
                (name, description),
            )
            return cursor.lastrowid

    def get_categories(self) -> List[sqlite3.Row]:
        """Return all categories."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")
        return cursor.fetchall()

    # Product operations
    def add_product(self, **product_data) -> int:
        """Insert a new product and return its id.

        product_data should include keys: name, sku, purchase_price,
        selling_price, stock, category_id, supplier_id, description,
        image_path, min_stock. Unknown keys are ignored.
        """
        keys = [
            "name",
            "sku",
            "purchase_price",
            "selling_price",
            "stock",
            "category_id",
            "supplier_id",
            "description",
            "image_path",
            "min_stock",
        ]
        values = [product_data.get(k) for k in keys]
        with self.db.connection as conn:
            cursor = conn.execute(
                """
                INSERT INTO products (
                    name, sku, purchase_price, selling_price, stock,
                    category_id, supplier_id, description, image_path, min_stock
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            return cursor.lastrowid

    def update_product(self, product_id: int, **updates) -> None:
        """Update fields of a product by id."""
        keys = [
            "name",
            "sku",
            "purchase_price",
            "selling_price",
            "stock",
            "category_id",
            "supplier_id",
            "description",
            "image_path",
            "min_stock",
        ]
        fields = []
        values = []
        for key in keys:
            if key in updates:
                fields.append(f"{key} = ?")
                values.append(updates[key])
        values.append(product_id)
        if fields:
            with self.db.connection as conn:
                conn.execute(
                    f"UPDATE products SET {', '.join(fields)} WHERE id = ?",
                    values,
                )

    def delete_product(self, product_id: int) -> None:
        """Delete a product by id."""
        with self.db.connection as conn:
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))

    def get_product_by_sku(self, sku: str) -> Optional[sqlite3.Row]:
        """Return product information by SKU or None if not found."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT * FROM products WHERE sku = ?", (sku,))
        return cursor.fetchone()

    def search_products(self, query: str) -> List[sqlite3.Row]:
        """Search products by name or SKU (case insensitive)."""
        pattern = f"%{query}%"
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            SELECT p.*, c.name as category_name, s.name as supplier_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.name LIKE ? OR p.sku LIKE ?
            ORDER BY p.name
            """,
            (pattern, pattern),
        )
        return cursor.fetchall()

    def import_from_csv(self, file_path: str) -> int:
        """Import products from a CSV file. Returns number of products added.

        The CSV must contain headers: name, sku, purchase_price,
        selling_price, stock, category, supplier, description, image_path,
        min_stock. Category and supplier will be created if they do not
        already exist. Rows with missing mandatory fields are skipped.
        """
        rows = read_csv(file_path)
        added = 0
        for row in rows:
            name = row.get("name")
            sku = row.get("sku")
            purchase_price = row.get("purchase_price")
            selling_price = row.get("selling_price")
            stock = row.get("stock", 0)
            category_name = row.get("category")
            supplier_name = row.get("supplier")
            description = row.get("description", "")
            image_path = row.get("image_path", "")
            min_stock = row.get("min_stock", 0)
            if not name or not sku or not purchase_price or not selling_price:
                continue  # skip incomplete rows
            # Resolve category
            category_id = None
            if category_name:
                # find or create category
                c = self.get_category_by_name(category_name)
                if c:
                    category_id = c["id"]
                else:
                    category_id = self.add_category(category_name)
            # TODO: suppliers not implemented; skip supplier_id for now
            supplier_id = None
            try:
                self.add_product(
                    name=name,
                    sku=sku,
                    purchase_price=float(purchase_price),
                    selling_price=float(selling_price),
                    stock=int(stock),
                    category_id=category_id,
                    supplier_id=supplier_id,
                    description=description,
                    image_path=image_path,
                    min_stock=int(min_stock),
                )
                added += 1
            except sqlite3.IntegrityError:
                # Duplicate SKU: skip
                continue
        return added

    def export_to_csv(self, file_path: str) -> int:
        """Export all products to a CSV file. Returns number of products exported."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()
        fieldnames = [
            "id",
            "name",
            "sku",
            "purchase_price",
            "selling_price",
            "stock",
            "category_id",
            "supplier_id",
            "description",
            "image_path",
            "min_stock",
        ]
        csv_rows = []
        for row in rows:
            csv_rows.append({k: row[k] for k in fieldnames})
        write_csv(file_path, fieldnames, csv_rows)
        return len(rows)

    def get_category_by_name(self, name: str) -> Optional[sqlite3.Row]:
        """Retrieve a category by name or return None."""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT * FROM categories WHERE name = ?", (name,))
        return cursor.fetchone()

    def adjust_stock(self, product_id: int, change: int, reason: str = "") -> None:
        """Adjust the stock level of a product and record in history.

        change can be positive (stock-in) or negative (stock-out).
        """
        with self.db.connection as conn:
            conn.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (change, product_id))
            conn.execute(
                "INSERT INTO inventory_history (product_id, change, reason) VALUES (?, ?, ?)",
                (product_id, change, reason),
            )
