"""
sales.py
This module manages sales transactions including adding products to a
cart, applying discounts, calculating tax and totals, and storing
completed sales and their line items into the database. A sale can be
held (saved temporarily without finalizing) and resumed later.

Sales are stored in the `sales` table and their individual items in the
`sale_items` table. When a sale is completed the stock quantities of
products are decreased accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from decimal import Decimal, ROUND_HALF_UP
from db import Database


def money(value: float) -> float:
    """Round a monetary value to two decimal places using bankers rounding."""
    return float(Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


@dataclass
class CartItem:
    product_id: int
    name: str
    unit_price: float
    quantity: int = 1
    def subtotal(self) -> float:
        return money(self.unit_price * self.quantity)


class SalesManager:
    def __init__(self, db: Database, tax_rate: float = 0.0) -> None:
        self.db = db
        self.cart: List[CartItem] = []
        self.tax_rate = tax_rate  # e.g. 0.07 for 7%
        self.discount_amount: float = 0.0
        self.discount_percent: float = 0.0

    def clear_cart(self) -> None:
        self.cart.clear()
        self.discount_amount = 0.0
        self.discount_percent = 0.0

    def add_item(self, product_id: int, name: str, price: float, quantity: int = 1) -> None:
        """Add an item to the cart, increasing quantity if already present."""
        # check existing
        for item in self.cart:
            if item.product_id == product_id:
                item.quantity += quantity
                return
        self.cart.append(CartItem(product_id, name, price, quantity))

    def remove_item(self, product_id: int) -> None:
        """Remove an item from the cart by product id."""
        self.cart = [item for item in self.cart if item.product_id != product_id]

    def set_discount(self, amount: float = 0.0, percent: float = 0.0) -> None:
        """Set discount (either absolute amount or percentage)."""
        self.discount_amount = amount
        self.discount_percent = percent

    def subtotal(self) -> float:
        return money(sum(item.subtotal() for item in self.cart))

    def discount(self) -> float:
        subtotal = self.subtotal()
        amount = self.discount_amount
        if self.discount_percent:
            amount = subtotal * (self.discount_percent / 100.0)
        return money(amount)

    def tax(self) -> float:
        taxable = self.subtotal() - self.discount()
        return money(taxable * self.tax_rate)

    def total(self) -> float:
        return money(self.subtotal() - self.discount() + self.tax())

    def finalize_sale(
        self, payment_method: str, user_id: Optional[int] = None, held: bool = False
    ) -> int:
        """Persist the sale to the database and adjust inventory.

        Returns the sale id. After finalizing the cart is cleared.
        """
        if not self.cart:
            raise ValueError("Cannot finalize an empty cart")
        with self.db.connection as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sales (total, tax, discount, payment_method, held, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (self.total(), self.tax(), self.discount(), payment_method, int(held), user_id),
            )
            sale_id = cursor.lastrowid
            for item in self.cart:
                cursor.execute(
                    """
                    INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (sale_id, item.product_id, item.quantity, item.unit_price),
                )
                # deduct stock if sale is not held
                if not held:
                    conn.execute(
                        "UPDATE products SET stock = stock - ? WHERE id = ?",
                        (item.quantity, item.product_id),
                    )
            # Log inventory change for each item
            for item in self.cart:
                # negative change for stock-out
                conn.execute(
                    "INSERT INTO inventory_history (product_id, change, reason) VALUES (?, ?, ?)",
                    (item.product_id, -item.quantity if not held else 0, 'sale'),
                )
        self.clear_cart()
        return sale_id
