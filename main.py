"""
main.py

This is the entry point for the POS application. It contains a simple
command line interface (CLI) implementation and conditionally launches
the graphical user interface (GUI) defined in `gui.py` when Tkinter is
available. The CLI serves as a fallback in environments without a GUI
toolkit or where Tkinter is not installed.

When running the CLI the workflow is menu based and supports product
management, sales processing and reporting. For a more user friendly
experience use the GUI by ensuring Tkinter is installed and simply
running this script.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

try:
    import tkinter as tk  # type: ignore
except ImportError:
    tk = None

from db import Database
from user import UserManager
from product import ProductManager
from sales import SalesManager
from report import ReportManager


def run_cli(db_path: str) -> None:
    """Fallback command line interface when Tkinter is unavailable."""
    print("*** POS Application (CLI) ***")
    db = Database(db_path)
    db.init_db()
    user_manager = UserManager(db)
    product_manager = ProductManager(db)
    sales_manager = SalesManager(db, tax_rate=0.07)
    report_manager = ReportManager(db)

    # Ensure admin user exists
    if not user_manager.list_users():
        print("Creating default admin user (username: admin, password: admin)")
        user_manager.create_user("admin", "admin", "admin")

    # login
    user_id: Optional[int] = None
    role: Optional[str] = None
    while True:
        username = input("Username: ")
        password = input("Password: ")
        auth = user_manager.authenticate(username, password)
        if auth:
            user_id, role = auth
            break
        else:
            print("Invalid credentials. Try again.")

    def product_menu() -> None:
        while True:
            print("\nProduct Management")
            print("1. List products")
            print("2. Add product")
            print("3. Edit product")
            print("4. Delete product")
            print("5. Import from CSV")
            print("6. Export to CSV")
            print("7. Back to main menu")
            choice = input("Choose an option: ")
            if choice == "1":
                products = product_manager.search_products("")
                for p in products:
                    print(f"{p['id']}: {p['name']} | SKU: {p['sku']} | Price: {p['selling_price']} | Stock: {p['stock']}")
            elif choice == "2":
                name = input("Name: ")
                sku = input("SKU: ")
                purchase_price = float(input("Purchase price: "))
                selling_price = float(input("Selling price: "))
                stock = int(input("Stock: "))
                product_manager.add_product(
                    name=name,
                    sku=sku,
                    purchase_price=purchase_price,
                    selling_price=selling_price,
                    stock=stock,
                    category_id=None,
                    supplier_id=None,
                    description="",
                    image_path="",
                    min_stock=0,
                )
                print("Product added.")
            elif choice == "3":
                pid = int(input("Enter product ID to edit: "))
                new_price = float(input("New selling price: "))
                new_stock = int(input("New stock: "))
                product_manager.update_product(pid, selling_price=new_price, stock=new_stock)
                print("Product updated.")
            elif choice == "4":
                pid = int(input("Enter product ID to delete: "))
                confirm = input("Are you sure? y/n: ")
                if confirm.lower() == "y":
                    product_manager.delete_product(pid)
                    print("Product deleted.")
            elif choice == "5":
                path = input("Enter path to CSV file: ")
                count = product_manager.import_from_csv(path)
                print(f"Imported {count} products.")
            elif choice == "6":
                path = input("Enter path to save CSV file: ")
                count = product_manager.export_to_csv(path)
                print(f"Exported {count} products.")
            elif choice == "7":
                break
            else:
                print("Invalid option.")

    def sales_menu() -> None:
        while True:
            print("\nSales")
            print("1. Add item to cart")
            print("2. View cart")
            print("3. Remove item from cart")
            print("4. Apply discount")
            print("5. Finalize sale")
            print("6. Clear cart")
            print("7. Back to main menu")
            choice = input("Choose an option: ")
            if choice == "1":
                query = input("Search by name or SKU: ")
                results = product_manager.search_products(query)
                if not results:
                    print("No products found.")
                else:
                    for p in results:
                        print(f"{p['id']}: {p['name']} | {p['sku']} | Price: {p['selling_price']} | Stock: {p['stock']}")
                    pid = int(input("Enter product ID to add: "))
                    qty = int(input("Quantity: "))
                    selected = next((p for p in results if p['id'] == pid), None)
                    if selected:
                        sales_manager.add_item(
                            product_id=selected['id'],
                            name=selected['name'],
                            price=selected['selling_price'],
                            quantity=qty,
                        )
                        print("Item added to cart.")
            elif choice == "2":
                if not sales_manager.cart:
                    print("Cart is empty.")
                else:
                    for item in sales_manager.cart:
                        print(f"{item.product_id}: {item.name} x{item.quantity} @ {item.unit_price} = {item.subtotal()}")
                    print(f"Subtotal: {sales_manager.subtotal()}")
                    print(f"Discount: {sales_manager.discount()}")
                    print(f"Tax: {sales_manager.tax()}")
                    print(f"Total: {sales_manager.total()}")
            elif choice == "3":
                pid = int(input("Enter product ID to remove: "))
                sales_manager.remove_item(pid)
                print("Removed from cart.")
            elif choice == "4":
                mode = input("Percent or amount (p/a)? ")
                if mode.lower() == "p":
                    percent = float(input("Discount percent: "))
                    sales_manager.set_discount(percent=percent)
                else:
                    amount = float(input("Discount amount: "))
                    sales_manager.set_discount(amount=amount)
                print("Discount applied.")
            elif choice == "5":
                method = input("Payment method (cash/card/mobile): ")
                sale_id = sales_manager.finalize_sale(payment_method=method, user_id=user_id)
                print(f"Sale completed. ID: {sale_id}")
            elif choice == "6":
                sales_manager.clear_cart()
                print("Cart cleared.")
            elif choice == "7":
                break
            else:
                print("Invalid option.")

    def report_menu() -> None:
        while True:
            print("\nReports")
            print("1. Sales summary")
            print("2. Best selling products")
            print("3. Inventory valuation")
            print("4. Back to main menu")
            choice = input("Choose an option: ")
            if choice == "1":
                start_date = input("Start date (YYYY-MM-DD): ")
                end_date = input("End date (YYYY-MM-DD): ")
                summary = report_manager.sales_summary(start_date, end_date)
                print(summary)
            elif choice == "2":
                start_date = input("Start date (YYYY-MM-DD): ")
                end_date = input("End date (YYYY-MM-DD): ")
                limit = int(input("Number of products to show: "))
                products = report_manager.best_selling_products(start_date, end_date, limit)
                for row in products:
                    print(f"{row['id']}: {row['name']} sold {row['quantity_sold']}")
            elif choice == "3":
                valuation = report_manager.inventory_valuation()
                print(f"Inventory valuation: {valuation}")
            elif choice == "4":
                break
            else:
                print("Invalid option.")

    while True:
        print("\nMain Menu")
        print("1. Product Management")
        print("2. Sales")
        print("3. Reports")
        print("4. Exit")
        choice = input("Select an option: ")
        if choice == "1" and role in ("admin", "manager"):
            product_menu()
        elif choice == "2" and role in ("admin", "manager", "cashier"):
            sales_menu()
        elif choice == "3" and role in ("admin", "manager"):
            report_menu()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid selection or insufficient permissions.")


def main() -> None:
    db_path = os.environ.get("POS_DB", "pos.db")
    if tk is None:
        # run CLI fallback
        run_cli(db_path)
    else:
        # import GUI lazily
        try:
            from gui import POSApplication  # type: ignore
        except Exception as e:
            print("Failed to load GUI, falling back to CLI:\n", e)
            run_cli(db_path)
            return
        app = POSApplication(db_path=db_path)
        app.mainloop()


if __name__ == "__main__":
    main()
