"""
utils.py
This module hosts utility functions that are used across the POS system.
These include password hashing, CSV import/export helpers and other
reusable logic. Keeping these helpers separate improves modularity and
allows code reuse without cyclic dependencies.
"""

import csv
import hashlib
import os
from typing import List, Dict, Iterable


def hash_password(password: str) -> str:
    """Return a SHA256 hash of the given password.

    The password hashing used here is intentionally simple. In a real
    production environment you should use a library such as `passlib`
    (https://passlib.readthedocs.io/en/stable/) or `bcrypt` to hash
    passwords with a salt and a strong hashing function. For the purposes
    of this sample application and given the constraints of the
    environment, we will use SHA256 to avoid introducing third party
    dependencies. This is sufficient for demonstration but not adequate
    for secure password storage in real deployments.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify that a password matches the given hash."""
    return hash_password(password) == password_hash


def read_csv(file_path: str) -> List[Dict[str, str]]:
    """Read a CSV file and return a list of dictionaries.

    Each row becomes a dictionary where the keys are taken from the
    header row. If the file does not exist an empty list is returned.
    This helper is used when importing products from CSV files.
    """
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv(file_path: str, fieldnames: List[str], rows: Iterable[Dict[str, str]]) -> None:
    """Write an iterable of dictionaries to a CSV file.

    The order of keys in each row must match the provided fieldnames.
    """
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
