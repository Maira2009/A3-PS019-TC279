from __future__ import annotations

import sqlite3
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1] / "data" / "demo"
TARGET = DEMO / "support.db"


def main() -> None:
    TARGET.unlink(missing_ok=True)
    with sqlite3.connect(TARGET) as con:
        con.execute(
            """CREATE TABLE tickets (
                ticket_id TEXT PRIMARY KEY,
                customer_id TEXT,
                customer_name TEXT,
                mobile TEXT,
                contact_email TEXT,
                address TEXT,
                issue_category TEXT,
                retry_count INTEGER,
                transaction_amount REAL
            )"""
        )
        con.executemany(
            "INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("TKT-001", "CUS-2001", "Aarav Demo", "+91-98765-43210", "aarav.demo@example.com", "12 Sample Road Pune", "Login help", 1, 0.0),
                ("TKT-002", "CUS-2002", "Ishita Example", "+91-92222-33333", "ishita.example@example.com", "9 Mock Crescent Bengaluru", "Billing question", 2, 1499.0),
                ("TKT-003", "CUS-2003", "Diya Example", "+91-91234-56789", "diya.example@example.com", "8 Test Avenue Mumbai", "Account help", 0, 0.0),
                ("TKT-004", "CUS-2004", "Reyansh Sample", "+91-96666-77777", "reyansh.sample@example.com", "21 Demo Park Hyderabad", "Product query", 1, 799.0),
            ],
        )
        con.execute("CREATE TABLE empty_reference (code TEXT, description TEXT)")
    print(TARGET)


if __name__ == "__main__":
    main()
