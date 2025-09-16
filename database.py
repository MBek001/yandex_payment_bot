import sqlite3
from decimal import Decimal
from datetime import datetime

# Database file
DB_NAME = "payment_bot.db"


def init_db():
    """Initialize the SQLite database and create the payments table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create payments table (equivalent to Django Payment model)
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS payments
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       provider
                       TEXT
                       NOT
                       NULL,
                       provider_txn_id
                       TEXT
                       NOT
                       NULL,
                       callsign
                       TEXT
                       NOT
                       NULL,
                       driver_profile_id
                       TEXT
                       DEFAULT
                       '',
                       amount
                       DECIMAL
                       NOT
                       NULL,
                       currency
                       TEXT
                       DEFAULT
                       'UZS',
                       category_id
                       TEXT
                       NOT
                       NULL,
                       status
                       TEXT
                       DEFAULT
                       'created',
                       raw_payload
                       TEXT,
                       created_at
                       TEXT
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       performed_at
                       TEXT,
                       UNIQUE
                   (
                       provider,
                       provider_txn_id
                   )
                       )
                   """)

    # Create indexes for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_provider_txn_id ON payments (provider, provider_txn_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_callsign ON payments (callsign)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON payments (status)")

    conn.commit()
    conn.close()


def save_payment(provider: str, provider_txn_id: str, callsign: str, amount: Decimal,
                 category_id: str, raw_payload: dict, status: str = "created",
                 driver_profile_id: str = "", performed_at: str = None) -> tuple[bool, dict, str]:
    """Save a payment to the database and return (success, payment_data, message)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Check if payment already exists
    cursor.execute(
        "SELECT id, status FROM payments WHERE provider = ? AND provider_txn_id = ?",
        (provider, provider_txn_id)
    )
    existing = cursor.fetchone()

    if existing:
        payment_id, existing_status = existing
        if existing_status == "performed":
            conn.close()
            return False, {"id": payment_id, "status": existing_status}, "already performed"

    # Convert raw_payload to string (since SQLite doesn't have a JSON type)
    raw_payload_str = str(raw_payload) if raw_payload else "{}"

    # Insert or update payment
    if existing:
        cursor.execute(
            """
            UPDATE payments
            SET callsign          = ?,
                amount            = ?,
                currency          = ?,
                category_id       = ?,
                status            = ?,
                raw_payload       = ?,
                driver_profile_id = ?,
                performed_at      = ?
            WHERE id = ?
            """,
            (callsign, str(amount), "UZS", category_id, status, raw_payload_str,
             driver_profile_id, performed_at, payment_id)
        )
    else:
        cursor.execute(
            """
            INSERT INTO payments
            (provider, provider_txn_id, callsign, amount, currency, category_id,
             status, raw_payload, driver_profile_id, performed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (provider, provider_txn_id, callsign, str(amount), "UZS", category_id,
             status, raw_payload_str, driver_profile_id, performed_at)
        )
        payment_id = cursor.lastrowid

    conn.commit()

    # Fetch the saved payment
    cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    columns = [col[0] for col in cursor.description]
    payment_data = dict(zip(columns, cursor.fetchone()))

    conn.close()
    return True, payment_data, "ok"


def update_payment_status(payment_id: int, status: str, driver_profile_id: str = None,
                          performed_at: str = None) -> bool:
    """Update the status and optional fields of a payment."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if driver_profile_id and performed_at:
        cursor.execute(
            "UPDATE payments SET status = ?, driver_profile_id = ?, performed_at = ? WHERE id = ?",
            (status, driver_profile_id, performed_at, payment_id)
        )
    else:
        cursor.execute(
            "UPDATE payments SET status = ? WHERE id = ?",
            (status, payment_id)
        )

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success