"""
report.py
Provides functions to generate basic sales and inventory reports. Reports
are returned as lists of dictionaries or rows that can later be used to
present information in tables or charts. More sophisticated reporting
could be added, including PDF or Excel exports using third party
libraries; however those are not included here to avoid external
dependencies.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import List, Tuple

from db import Database


class ReportManager:
    def __init__(self, db: Database) -> None:
        self.db = db

    def sales_summary(self, start_date: str, end_date: str) -> dict:
        """Return sales summary for a date range.

        start_date and end_date should be ISO formatted strings 'YYYY-MM-DD'.
        The result includes total revenue, total tax, total discount,
        transaction count and total items sold.
        """
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) as transaction_count,
                COALESCE(SUM(total),0) as total_revenue,
                COALESCE(SUM(tax),0) as total_tax,
                COALESCE(SUM(discount),0) as total_discount
            FROM sales
            WHERE DATE(timestamp) >= DATE(?) AND DATE(timestamp) <= DATE(?)
            AND held = 0
            """,
            (start_date, end_date),
        )
        summary = cursor.fetchone()
        # count total items
        cursor.execute(
            """
            SELECT COALESCE(SUM(quantity),0) as total_items
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            WHERE DATE(s.timestamp) >= DATE(?) AND DATE(s.timestamp) <= DATE(?)
            AND s.held = 0
            """,
            (start_date, end_date),
        )
        items_row = cursor.fetchone()
        result = {
            "transaction_count": summary["transaction_count"],
            "total_revenue": summary["total_revenue"],
            "total_tax": summary["total_tax"],
            "total_discount": summary["total_discount"],
            "total_items": items_row["total_items"],
        }
        return result

    def best_selling_products(self, start_date: str, end_date: str, limit: int = 10) -> List[sqlite3.Row]:
        """Return the top selling products by quantity in a date range."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            """
            SELECT p.id, p.name, SUM(si.quantity) as quantity_sold
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON si.product_id = p.id
            WHERE DATE(s.timestamp) >= DATE(?) AND DATE(s.timestamp) <= DATE(?)
            AND s.held = 0
            GROUP BY p.id, p.name
            ORDER BY quantity_sold DESC
            LIMIT ?
            """,
            (start_date, end_date, limit),
        )
        return cursor.fetchall()

    def inventory_valuation(self) -> float:
        """Calculate the current inventory valuation based on purchase price."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            "SELECT SUM(purchase_price * stock) as valuation FROM products"
        )
        row = cursor.fetchone()
        return row["valuation"] if row and row["valuation"] is not None else 0.0
