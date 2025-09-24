import sqlite3
import json
from decimal import Decimal
from datetime import datetime
from typing import Tuple, Optional

DB_NAME = "payment_bot.db"


def get_conn():
    # Use check_same_thread=False if you plan to call DB from threads, but Pyrogram handlers are async tasks in same process.
    return sqlite3.connect(DB_NAME, isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        provider_txn_id TEXT NOT NULL,
        callsign TEXT NOT NULL,
        driver_profile_id TEXT DEFAULT '',
        amount TEXT NOT NULL,         -- store Decimal as string to preserve precision
        currency TEXT DEFAULT 'UZS',
        category_id TEXT NOT NULL,
        status TEXT DEFAULT 'created',
        raw_payload TEXT,
        park_group_id TEXT,   
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        performed_at TEXT,
        UNIQUE(provider, provider_txn_id)
    )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_provider_txn_id ON payments (provider, provider_txn_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_callsign ON payments (callsign)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_status ON payments (status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_park_group ON payments (park_group_id)")

    conn.commit()
    conn.close()


def save_payment(provider: str, provider_txn_id: str, callsign: str, amount: Decimal,
                 category_id: str, raw_payload: dict, status: str = "created",
                 driver_profile_id: str = "", performed_at: Optional[str] = None,
                 park_group_id: Optional[int] = None) -> Tuple[bool, dict, str]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        cur.execute(
            "SELECT id, status FROM payments WHERE provider = ? AND provider_txn_id = ?",
            (provider, provider_txn_id)
        )
        existing = cur.fetchone()
        if existing:
            payment_id, existing_status = existing
            if existing_status == "performed":
                cur.execute("COMMIT")
                return False, {"id": payment_id, "status": existing_status}, "already performed"
        else:
            payment_id = None

        raw_payload_str = json.dumps(raw_payload, ensure_ascii=False) if raw_payload else "{}"
        amount_str = str(amount)

        if existing:
            cur.execute("""
                UPDATE payments
                SET callsign = ?, amount = ?, currency = ?, category_id = ?, status = ?,
                    raw_payload = ?, driver_profile_id = ?, performed_at = ?, park_group_id = ?
                WHERE id = ?
            """, (callsign, amount_str, "UZS", category_id, status,
                  raw_payload_str, driver_profile_id, performed_at, park_group_id, payment_id))
        else:
            cur.execute("""
                INSERT INTO payments
                (provider, provider_txn_id, callsign, amount, currency, category_id,
                 status, raw_payload, driver_profile_id, performed_at, park_group_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (provider, provider_txn_id, callsign, amount_str, "UZS", category_id,
                  status, raw_payload_str, driver_profile_id, performed_at, park_group_id))
            payment_id = cur.lastrowid

        cur.execute("COMMIT")

        cur.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        columns = [c[0] for c in cur.description]
        row = cur.fetchone()
        payment_data = dict(zip(columns, row))
        return True, payment_data, "ok"

    except Exception as e:
        try:
            cur.execute("ROLLBACK")
        except Exception:
            pass
        return False, {}, f"db error: {e}"
    finally:
        conn.close()


def update_payment_status(payment_id: int, status: str,
                          driver_profile_id: str = None,
                          performed_at: str = None) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    try:
        if not performed_at and status == "performed":
            performed_at = datetime.utcnow().isoformat(timespec="seconds")
        if driver_profile_id and performed_at:
            cur.execute(
                "UPDATE payments SET status = ?, driver_profile_id = ?, performed_at = ? WHERE id = ?",
                (status, driver_profile_id, performed_at, payment_id)
            )
        elif performed_at:
            cur.execute(
                "UPDATE payments SET status = ?, performed_at = ? WHERE id = ?",
                (status, performed_at, payment_id)
            )
        else:
            cur.execute(
                "UPDATE payments SET status = ? WHERE id = ?",
                (status, payment_id)
            )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()
