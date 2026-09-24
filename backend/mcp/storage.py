"""Local demo records. Identity is selected in the UI, so these are not real employee records."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_records.sqlite3"


def connect(path: Path = DB_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000")
    db.execute("""CREATE TABLE IF NOT EXISTS employees (
        employee_id TEXT PRIMARY KEY,
        casual INTEGER NOT NULL,
        sick INTEGER NOT NULL
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS claims (
        claim_id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL,
        status TEXT NOT NULL
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS tickets (
        number INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT NOT NULL,
        issue TEXT NOT NULL,
        status TEXT NOT NULL
    )""")
    db.executemany("INSERT OR IGNORE INTO employees VALUES (?, ?, ?)", [
        ("EMP001", 5, 7), ("EMP002", 2, 4),
    ])
    db.execute("INSERT OR IGNORE INTO claims VALUES ('CLM100', 'EMP001', 'Under review')")
    db.execute(
        "INSERT OR IGNORE INTO tickets (number, employee_id, issue, status) "
        "VALUES (100, 'EMP001', 'Example VPN issue', 'Open')"
    )
    db.commit()
    return db


def require_employee(db, employee_id: str):
    if db.execute("SELECT 1 FROM employees WHERE employee_id=?", (employee_id,)).fetchone() is None:
        raise ValueError("Unknown demo employee")


def leave_balance(employee_id: str, path: Path = DB_PATH) -> dict:
    with connect(path) as db:
        require_employee(db, employee_id)
        row = db.execute(
            "SELECT casual, sick FROM employees WHERE employee_id=?", (employee_id,)
        ).fetchone()
        return {"casual": row["casual"], "sick": row["sick"]}


def claim_status(employee_id: str, claim_id: str, path: Path = DB_PATH) -> str:
    with connect(path) as db:
        require_employee(db, employee_id)
        row = db.execute(
            "SELECT status FROM claims WHERE employee_id=? AND claim_id=?",
            (employee_id, claim_id.upper()),
        ).fetchone()
        return row["status"] if row else "No claim found for your account"


def ticket_status(employee_id: str, ticket_id: str, path: Path = DB_PATH) -> str:
    with connect(path) as db:
        require_employee(db, employee_id)
        number = int(ticket_id[2:]) if ticket_id.upper().startswith("IT") and ticket_id[2:].isdigit() else -1
        row = db.execute(
            "SELECT status FROM tickets WHERE employee_id=? AND number=?",
            (employee_id, number),
        ).fetchone()
        return row["status"] if row else "No ticket found for your account"


def create_ticket(employee_id: str, issue: str, path: Path = DB_PATH) -> str:
    if len(issue.strip()) < 8:
        raise ValueError("Please describe the issue in at least eight characters")
    with connect(path) as db:
        require_employee(db, employee_id)
        row = db.execute(
            "INSERT INTO tickets(employee_id, issue, status) VALUES (?, ?, 'Open')",
            (employee_id, issue.strip()),
        )
        return f"IT{row.lastrowid}"
