# POS Application

This repository contains a self‑contained Point of Sale (POS) system written
in Python. The goal of the project is to provide a fully functional,
offline capable POS solution that can run on a typical desktop computer
without requiring any external services. It uses SQLite for local data
storage and comes with a graphical user interface (GUI) built using
Tkinter. For environments where Tkinter is not available (for example
when running on a minimal Linux server), a text based command line
interface (CLI) fallback is provided.

## Features

- **Product Management**
  - Add, edit and delete products with SKU, price and stock levels
  - Import products from CSV files
  - Export the product catalogue to CSV
  - Search products by name or SKU
- **Sales Processing**
  - Build a shopping cart, adjust quantities and remove items
  - Apply percentage or fixed discounts
  - Calculate tax and totals automatically
  - Finalize sales with different payment methods
  - Stock levels are reduced when a sale is completed
- **Reporting**
  - Sales summary for arbitrary date ranges
  - List best selling products
  - Inventory valuation based on purchase price
- **User Management**
  - Support for multiple users with roles (admin, manager, cashier)
  - Admins can create and delete users
- **Inventory History**
  - Automatic logging of inventory changes
- **Cross Platform**
  - Pure Python solution: should work on Windows, macOS and most Linux
    distributions with Python 3 installed

## Requirements

The application targets Python 3.7 or higher. It relies only on the
standard library, particularly `sqlite3` and `tkinter`. On most
systems, Tkinter is included by default. If Tkinter is not installed
the application will fall back to a simple CLI.

No third party libraries are required. For printing receipts, exporting
PDFs or generating barcodes, you could integrate libraries such as
`reportlab` or `python‑barcode`, but these are not included here to
keep the dependencies minimal.

## Getting Started

Clone the repository (or copy the `pos_app` folder) and navigate into
it:

```bash
cd pos_app
```

To run the application with the GUI (recommended):

```bash
python main.py
```

If Tkinter is unavailable on your system you will automatically be
dropped into a text based interface instead.

The application creates a SQLite database file named `pos.db` in the
current working directory by default. You can override this using
the `POS_DB` environment variable:

```bash
POS_DB=/path/to/mydata.db python main.py
```

On the first run a default administrative user is created with the
credentials `admin` / `admin`. Please login with these credentials
immediately and create additional users with appropriate roles, then
delete or change the password for the default admin account.

## CSV Import/Export

CSV files used for import/export follow these columns:

```
name,sku,purchase_price,selling_price,stock,category,supplier,description,image_path,min_stock
```

During import unknown categories are created automatically. Suppliers
are not yet implemented and can be left blank. Only the `name`, `sku`,
`purchase_price` and `selling_price` columns are mandatory.

## Limitations and Future Work

This project was implemented in a constrained environment and is
intended primarily as a starting point for a more comprehensive POS
system. Several advanced features mentioned in the original
specification have not been implemented, including but not limited to:

- Barcode scanning support
- Printing and emailing of receipts
- Supplier management
- Backup and restore functionality
- Visual charts in the reports
- Multi‑language support
- Loyalty program integration
- Automatic software updates

These features can be added incrementally. The existing modular
architecture should make it straightforward to extend the system. For
example, to implement receipt printing you could integrate the
`reportlab` library and generate PDF receipts for each sale.

## Contributing

Pull requests are welcome. When adding features, please keep the code
well organised and modular, and avoid adding unnecessary dependencies.
