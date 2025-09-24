import re
from decimal import Decimal, InvalidOperation

AMOUNT_RE = re.compile(r"🇺🇿\s*([^\n]+)")
TXN_RE = re.compile(r"🆔\s*([0-9a-fA-F]+)|🧾\s*(\d+)")
PAYMENT_ID_RE = re.compile(r"🧾\s*(\d+)")
DRIVER_RE_VARIANTS = [
    re.compile(r"🔸\s*Id водителя:\s*([0-9A-Za-z\-]+)", re.IGNORECASE),
    re.compile(r"🔸\s*ID водителя:\s*([0-9A-Za-z\-]+)", re.IGNORECASE),
    re.compile(r"🔸\s*Позывной водителя:\s*([0-9A-Za-z\-]+)", re.IGNORECASE),
    re.compile(r"🔸\s*Позывной:\s*([0-9A-Za-z\-]+)", re.IGNORECASE),
    re.compile(r"ID водителя:\s*([0-9A-Za-z\-]+)", re.IGNORECASE),
    re.compile(r"Позывной водителя:\s*([0-9A-Za-z\-]+)", re.IGNORECASE),
]


def parse_amount(text: str) -> Decimal:
    if not text:
        return Decimal("0")
    m = AMOUNT_RE.search(text)
    if not m:
        return Decimal("0")
    raw = m.group(1)
    # Remove non-digit except comma/dot
    clean = re.sub(r"[^\d,\.]", "", raw).replace(",", ".")
    try:
        return Decimal(clean)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def parse_provider_txn_id(text: str) -> str | None:
    # Prefer 🧾 numeric id as provider transaction id (payment receipt)
    m = PAYMENT_ID_RE.search(text)
    if m:
        return m.group(1)
    # fallback to 🆔 alphanumeric id
    m2 = re.search(r"🆔\s*([0-9a-fA-F]+)", text)
    if m2:
        return m2.group(1)
    return None


def parse_callsign(text: str) -> str | None:
    if not text:
        return None
    for rx in DRIVER_RE_VARIANTS:
        m = rx.search(text)
        if m:
            return m.group(1).strip()
    return None


def is_successful_payment(text: str) -> bool:
    if not text:
        return False
    return "Успешно оплачен" in text or "Успешно" in text and "оплачен" in text
