"""
gui.py

Contains the Tkinter based user interface for the POS system. The GUI
is organized into several frames for different sections of the
application. These classes should only be imported when Tkinter is
available, otherwise the CLI fallback will be used.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import tkinter as tk  # type: ignore
from tkinter import ttk, messagebox, filedialog, simpledialog  # type: ignore

from db import Database
from user import UserManager
from product import ProductManager
from sales import SalesManager
from report import ReportManager


class POSApplication(tk.Tk):
    """Main Tkinter application for the POS system."""

    def __init__(self, db_path: str = "pos.db") -> None:
        super().__init__()
        self.title("Point of Sale System")
        self.geometry("1024x600")
        self.resizable(True, True)
        # Initialize database and managers
        self.db = Database(db_path)
        self.db.init_db()
        self.user_manager = UserManager(self.db)
        self.product_manager = ProductManager(self.db)
        self.sales_manager = SalesManager(self.db, tax_rate=0.07)
        self.report_manager = ReportManager(self.db)
        # Ensure at least one admin user exists
        self._ensure_admin_user()
        # Current logged in user info
        self.user_id: Optional[int] = None
        self.user_role: Optional[str] = None
        # Container for frames
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        # Frames dictionary
        self.frames = {}
        for F in (LoginFrame, MainMenuFrame, ProductFrame, SalesFrame, ReportFrame, UserFrame):
            frame = F(parent=self.container, controller=self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame(LoginFrame)

    def _ensure_admin_user(self) -> None:
        """Create a default admin user if no users exist."""
        if not self.user_manager.list_users():
            try:
                self.user_manager.create_user("admin", "admin", "admin")
            except Exception:
                pass

    def show_frame(self, frame_class) -> None:
        frame = self.frames[frame_class]
        frame.tkraise()
        if hasattr(frame, 'on_show'):
            frame.on_show()


class LoginFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Login", font=("Arial", 20)).pack(pady=20)
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        ttk.Label(self, text="Username").pack()
        ttk.Entry(self, textvariable=self.username_var).pack(pady=5)
        ttk.Label(self, text="Password").pack()
        ttk.Entry(self, textvariable=self.password_var, show="*").pack(pady=5)
        ttk.Button(self, text="Login", command=self.login).pack(pady=10)
        self.msg_label = ttk.Label(self, text="")
        self.msg_label.pack()

    def login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        auth = self.controller.user_manager.authenticate(username, password)
        if auth:
            self.controller.user_id, self.controller.user_role = auth
            self.username_var.set("")
            self.password_var.set("")
            self.msg_label.config(text="")
            self.controller.show_frame(MainMenuFrame)
        else:
            self.msg_label.config(text="Invalid credentials", foreground="red")


class MainMenuFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Main Menu", font=("Arial", 18)).pack(pady=20)
        self.buttons_frame = ttk.Frame(self)
        self.buttons_frame.pack(pady=10)
        self.product_btn = ttk.Button(
            self.buttons_frame, text="Product Management", command=lambda: controller.show_frame(ProductFrame)
        )
        self.sales_btn = ttk.Button(
            self.buttons_frame, text="Sales", command=lambda: controller.show_frame(SalesFrame)
        )
        self.report_btn = ttk.Button(
            self.buttons_frame, text="Reports", command=lambda: controller.show_frame(ReportFrame)
        )
        self.user_btn = ttk.Button(
            self.buttons_frame, text="User Management", command=lambda: controller.show_frame(UserFrame)
        )
        self.logout_btn = ttk.Button(
            self, text="Logout", command=self.logout
        )
        # layout buttons in a grid
        self.product_btn.grid(row=0, column=0, padx=10, pady=10)
        self.sales_btn.grid(row=0, column=1, padx=10, pady=10)
        self.report_btn.grid(row=1, column=0, padx=10, pady=10)
        self.user_btn.grid(row=1, column=1, padx=10, pady=10)
        self.logout_btn.pack(pady=20)

    def on_show(self):
        role = self.controller.user_role
        # show/hide buttons based on role
        self.product_btn.state(["!disabled"] if role in ("admin", "manager") else ["disabled"])
        self.sales_btn.state(["!disabled"] if role in ("admin", "manager", "cashier") else ["disabled"])
        self.report_btn.state(["!disabled"] if role in ("admin", "manager") else ["disabled"])
        self.user_btn.state(["!disabled"] if role == "admin" else ["disabled"])

    def logout(self):
        self.controller.user_id = None
        self.controller.user_role = None
        self.controller.show_frame(LoginFrame)


class ProductFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Product Management", font=("Arial", 16)).pack(pady=10)
        # search bar
        search_frame = ttk.Frame(self)
        search_frame.pack(pady=5, fill="x")
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.bind("<Return>", lambda e: self.refresh_products())
        ttk.Button(search_frame, text="Search", command=self.refresh_products).pack(side="left")
        # treeview for products
        columns = ("ID", "Name", "SKU", "Price", "Stock")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, minwidth=50, width=100)
        self.tree.pack(fill="both", expand=True, pady=5)
        # control buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Add", command=self.add_product_dialog).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_selected).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Import CSV", command=self.import_csv).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Export CSV", command=self.export_csv).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Back", command=lambda: controller.show_frame(MainMenuFrame)).pack(side="left", padx=5)
        self.refresh_products()

    def refresh_products(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        query = self.search_var.get().strip()
        results = self.controller.product_manager.search_products(query)
        for row in results:
            self.tree.insert("", "end", values=(row["id"], row["name"], row["sku"], row["selling_price"], row["stock"]))

    def add_product_dialog(self):
        ProductDialog(self, self.controller, mode="add")

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "No product selected")
            return
        item = self.tree.item(selected[0])
        pid = item["values"][0]
        ProductDialog(self, self.controller, mode="edit", product_id=pid)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "No product selected")
            return
        pid = self.tree.item(selected[0])["values"][0]
        if messagebox.askyesno("Delete", "Are you sure you want to delete this product?"):
            self.controller.product_manager.delete_product(pid)
            self.refresh_products()

    def import_csv(self):
        path = filedialog.askopenfilename(title="Import CSV", filetypes=[("CSV Files", "*.csv")])
        if path:
            count = self.controller.product_manager.import_from_csv(path)
            messagebox.showinfo("Import", f"Imported {count} products")
            self.refresh_products()

    def export_csv(self):
        path = filedialog.asksaveasfilename(title="Export CSV", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if path:
            count = self.controller.product_manager.export_to_csv(path)
            messagebox.showinfo("Export", f"Exported {count} products")


class ProductDialog(tk.Toplevel):
    def __init__(self, parent: ProductFrame, controller: POSApplication, mode: str, product_id: Optional[int] = None):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.mode = mode
        self.product_id = product_id
        self.title("Add Product" if mode == "add" else "Edit Product")
        self.grab_set()
        # form variables
        self.name_var = tk.StringVar()
        self.sku_var = tk.StringVar()
        self.purchase_price_var = tk.StringVar()
        self.selling_price_var = tk.StringVar()
        self.stock_var = tk.StringVar()
        # populate fields if editing
        if mode == "edit" and product_id is not None:
            rows = self.controller.product_manager.search_products("")
            product = None
            for r in rows:
                if r["id"] == product_id:
                    product = r
                    break
            if product:
                self.name_var.set(product["name"])
                self.sku_var.set(product["sku"])
                self.purchase_price_var.set(str(product["purchase_price"]))
                self.selling_price_var.set(str(product["selling_price"]))
                self.stock_var.set(str(product["stock"]))
        # create form
        ttk.Label(self, text="Name").grid(row=0, column=0, sticky="e", pady=2)
        ttk.Entry(self, textvariable=self.name_var).grid(row=0, column=1, pady=2)
        ttk.Label(self, text="SKU").grid(row=1, column=0, sticky="e", pady=2)
        ttk.Entry(self, textvariable=self.sku_var).grid(row=1, column=1, pady=2)
        ttk.Label(self, text="Purchase Price").grid(row=2, column=0, sticky="e", pady=2)
        ttk.Entry(self, textvariable=self.purchase_price_var).grid(row=2, column=1, pady=2)
        ttk.Label(self, text="Selling Price").grid(row=3, column=0, sticky="e", pady=2)
        ttk.Entry(self, textvariable=self.selling_price_var).grid(row=3, column=1, pady=2)
        ttk.Label(self, text="Stock").grid(row=4, column=0, sticky="e", pady=2)
        ttk.Entry(self, textvariable=self.stock_var).grid(row=4, column=1, pady=2)
        ttk.Button(self, text="Save", command=self.save).grid(row=5, column=0, columnspan=2, pady=10)

    def save(self):
        name = self.name_var.get().strip()
        sku = self.sku_var.get().strip()
        try:
            purchase_price = float(self.purchase_price_var.get() or 0)
            selling_price = float(self.selling_price_var.get() or 0)
            stock = int(self.stock_var.get() or 0)
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values")
            return
        if not name or not sku:
            messagebox.showerror("Error", "Name and SKU are required")
            return
        try:
            if self.mode == "add":
                self.controller.product_manager.add_product(
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
            else:
                self.controller.product_manager.update_product(
                    self.product_id,
                    name=name,
                    sku=sku,
                    purchase_price=purchase_price,
                    selling_price=selling_price,
                    stock=stock,
                )
            self.parent.refresh_products()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))


class SalesFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Sales", font=("Arial", 16)).pack(pady=10)
        # search bar
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Search").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.bind("<Return>", lambda e: self.search_products())
        ttk.Button(search_frame, text="Search", command=self.search_products).pack(side="left")
        # product list
        columns = ("ID", "Name", "Price", "Stock")
        self.product_tree = ttk.Treeview(self, columns=columns, show="headings", height=8)
        for col in columns:
            self.product_tree.heading(col, text=col)
            self.product_tree.column(col, minwidth=50, width=120)
        self.product_tree.pack(pady=5)
        # cart list
        ttk.Label(self, text="Cart").pack()
        cart_columns = ("ID", "Name", "Qty", "Unit Price", "Subtotal")
        self.cart_tree = ttk.Treeview(self, columns=cart_columns, show="headings", height=8)
        for col in cart_columns:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, minwidth=50, width=100)
        self.cart_tree.pack(pady=5)
        # totals
        self.total_var = tk.StringVar(value="Total: $0.00")
        ttk.Label(self, textvariable=self.total_var, font=("Arial", 14)).pack()
        # controls
        control_frame = ttk.Frame(self)
        control_frame.pack(pady=5)
        ttk.Button(control_frame, text="Add to Cart", command=self.add_to_cart).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Remove from Cart", command=self.remove_from_cart).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Discount", command=self.apply_discount_dialog).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Finalize Sale", command=self.finalize_sale_dialog).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Clear Cart", command=self.clear_cart).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Back", command=lambda: controller.show_frame(MainMenuFrame)).pack(side="left", padx=5)
        self.refresh_cart()

    def search_products(self):
        query = self.search_var.get().strip()
        results = self.controller.product_manager.search_products(query)
        for i in self.product_tree.get_children():
            self.product_tree.delete(i)
        for row in results:
            self.product_tree.insert("", "end", values=(row["id"], row["name"], row["selling_price"], row["stock"]))

    def add_to_cart(self):
        selected = self.product_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a product to add")
            return
        item = self.product_tree.item(selected[0])
        pid, name, price, stock = item["values"]
        if stock < 1:
            messagebox.showerror("Error", "This product is out of stock")
            return
        qty = simpledialog.askinteger("Quantity", "Enter quantity", initialvalue=1, minvalue=1)
        if qty:
            self.controller.sales_manager.add_item(product_id=pid, name=name, price=price, quantity=qty)
            self.refresh_cart()

    def remove_from_cart(self):
        selected = self.cart_tree.selection()
        if not selected:
            return
        item = self.cart_tree.item(selected[0])
        pid = item["values"][0]
        self.controller.sales_manager.remove_item(pid)
        self.refresh_cart()

    def refresh_cart(self):
        for i in self.cart_tree.get_children():
            self.cart_tree.delete(i)
        for item in self.controller.sales_manager.cart:
            self.cart_tree.insert(
                "",
                "end",
                values=(
                    item.product_id,
                    item.name,
                    item.quantity,
                    item.unit_price,
                    item.subtotal(),
                ),
            )
        self.total_var.set(f"Total: ${self.controller.sales_manager.total():.2f}")

    def apply_discount_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Apply Discount")
        ttk.Label(dlg, text="Discount percent (leave blank for none)").grid(row=0, column=0)
        percent_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=percent_var).grid(row=0, column=1)
        ttk.Label(dlg, text="Discount amount").grid(row=1, column=0)
        amount_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=amount_var).grid(row=1, column=1)
        def apply():
            try:
                pct = float(percent_var.get()) if percent_var.get() else 0.0
                amt = float(amount_var.get()) if amount_var.get() else 0.0
                self.controller.sales_manager.set_discount(amount=amt, percent=pct)
                dlg.destroy()
                self.refresh_cart()
            except ValueError:
                messagebox.showerror("Error", "Invalid discount values")
        ttk.Button(dlg, text="Apply", command=apply).grid(row=2, column=0, columnspan=2, pady=5)

    def finalize_sale_dialog(self):
        if not self.controller.sales_manager.cart:
            messagebox.showerror("Error", "Cart is empty")
            return
        dlg = tk.Toplevel(self)
        dlg.title("Finalize Sale")
        ttk.Label(dlg, text=f"Total: ${self.controller.sales_manager.total():.2f}").pack(pady=5)
        ttk.Label(dlg, text="Payment Method").pack()
        method_var = tk.StringVar(value="cash")
        ttk.Combobox(dlg, textvariable=method_var, values=["cash", "card", "mobile"]).pack(pady=5)
        def finalize():
            sale_id = self.controller.sales_manager.finalize_sale(
                payment_method=method_var.get(), user_id=self.controller.user_id
            )
            messagebox.showinfo("Sale", f"Sale completed. ID: {sale_id}")
            dlg.destroy()
            self.refresh_cart()
        ttk.Button(dlg, text="Complete", command=finalize).pack(pady=5)

    def clear_cart(self):
        self.controller.sales_manager.clear_cart()
        self.refresh_cart()


class ReportFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Reports", font=("Arial", 16)).pack(pady=10)
        # date range
        date_frame = ttk.Frame(self)
        date_frame.pack(pady=5)
        ttk.Label(date_frame, text="Start Date (YYYY-MM-DD)").grid(row=0, column=0)
        ttk.Label(date_frame, text="End Date (YYYY-MM-DD)").grid(row=1, column=0)
        self.start_var = tk.StringVar(value=str(date.today()))
        self.end_var = tk.StringVar(value=str(date.today()))
        ttk.Entry(date_frame, textvariable=self.start_var).grid(row=0, column=1)
        ttk.Entry(date_frame, textvariable=self.end_var).grid(row=1, column=1)
        # summary section
        ttk.Button(self, text="Generate Summary", command=self.show_summary).pack(pady=5)
        self.summary_text = tk.Text(self, height=5, width=60)
        self.summary_text.pack(pady=5)
        # best selling section
        ttk.Button(self, text="Best Selling Products", command=self.show_best_sellers).pack(pady=5)
        self.best_tree = ttk.Treeview(self, columns=("ID", "Name", "Quantity"), show="headings", height=10)
        for col in ("ID", "Name", "Quantity"):
            self.best_tree.heading(col, text=col)
            self.best_tree.column(col, width=150)
        self.best_tree.pack(pady=5)
        # inventory valuation
        ttk.Button(self, text="Inventory Valuation", command=self.show_valuation).pack(pady=5)
        self.valuation_var = tk.StringVar(value="Inventory valuation: $0.00")
        ttk.Label(self, textvariable=self.valuation_var, font=("Arial", 14)).pack(pady=5)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame(MainMenuFrame)).pack(pady=10)

    def show_summary(self):
        start = self.start_var.get()
        end = self.end_var.get()
        summary = self.controller.report_manager.sales_summary(start, end)
        self.summary_text.delete("1.0", tk.END)
        for k, v in summary.items():
            self.summary_text.insert(tk.END, f"{k.replace('_',' ').title()}: {v}\n")

    def show_best_sellers(self):
        start = self.start_var.get()
        end = self.end_var.get()
        products = self.controller.report_manager.best_selling_products(start, end)
        for i in self.best_tree.get_children():
            self.best_tree.delete(i)
        for row in products:
            self.best_tree.insert("", "end", values=(row["id"], row["name"], row["quantity_sold"]))

    def show_valuation(self):
        value = self.controller.report_manager.inventory_valuation()
        self.valuation_var.set(f"Inventory valuation: ${value:.2f}")


class UserFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="User Management", font=("Arial", 16)).pack(pady=10)
        # treeview for users
        self.tree = ttk.Treeview(self, columns=("ID", "Username", "Role", "Created At"), show="headings")
        for col in ("ID", "Username", "Role", "Created At"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        self.tree.pack(fill="both", expand=True, pady=5)
        # controls
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Add User", command=self.add_user_dialog).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete User", command=self.delete_selected).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Back", command=lambda: controller.show_frame(MainMenuFrame)).pack(side="left", padx=5)
        self.refresh_users()

    def refresh_users(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        users = self.controller.user_manager.list_users()
        for u in users:
            self.tree.insert("", "end", values=(u["id"], u["username"], u["role"], u["created_at"]))

    def add_user_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Add User")
        ttk.Label(dlg, text="Username").grid(row=0, column=0)
        username_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=username_var).grid(row=0, column=1)
        ttk.Label(dlg, text="Password").grid(row=1, column=0)
        password_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=password_var, show="*").grid(row=1, column=1)
        ttk.Label(dlg, text="Role").grid(row=2, column=0)
        role_var = tk.StringVar(value="cashier")
        ttk.Combobox(dlg, textvariable=role_var, values=["admin", "manager", "cashier"]).grid(row=2, column=1)
        def add():
            username = username_var.get().strip()
            password = password_var.get().strip()
            role = role_var.get()
            if not username or not password:
                messagebox.showerror("Error", "Username and password required")
                return
            try:
                self.controller.user_manager.create_user(username, password, role)
                messagebox.showinfo("User", "User created")
                dlg.destroy()
                self.refresh_users()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        ttk.Button(dlg, text="Create", command=add).grid(row=3, column=0, columnspan=2, pady=5)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a user to delete")
            return
        user_id = self.tree.item(selected[0])["values"][0]
        if user_id == self.controller.user_id:
            messagebox.showerror("Error", "You cannot delete yourself")
            return
        if messagebox.askyesno("Delete", "Are you sure?"):
            self.controller.user_manager.delete_user(user_id)
            self.refresh_users()
