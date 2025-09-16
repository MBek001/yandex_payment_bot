import os
import re
from decimal import Decimal, InvalidOperation
from pyrogram import Client, filters

from database import init_db
from utils import save_payment_and_topup
from config import config

# Initialize the database
init_db()

# Pyrogram configuration
api_id = config.APP_ID
api_hash = config.APP_SECRET
app_title = config.APP_TITLE
app = Client(app_title, api_id=api_id, api_hash=api_hash)

BRO_TAXI = config.BRO_TAXI
ALLOWED_USERS = config.ALLOWED_USERS

def parse_amount(amount_text: str) -> Decimal:
    clean = re.sub(r"[^\d,\.]", "", amount_text)
    clean = clean.replace(",", ".")
    try:
        return Decimal(clean)
    except InvalidOperation:
        print(f"⚠️ Decimal error, clean string: {clean!r}")
        return Decimal("0")

@app.on_message(filters.chat(BRO_TAXI) & filters.user(ALLOWED_USERS))
async def get_messages(client, message):
    try:
        text = message.text or message.caption

        if "✅" not in text or "Успешно оплачен" not in text:
            print("ℹ️ Bu xabar bekor qilingan yoki muvaffaqiyatsiz, saqlanmaydi")
            return

        payment_id_match = re.search(r"🧾\s*(\d+)", text)
        provider_txn_id = payment_id_match.group(1) if payment_id_match else None

        callsign_match = re.search(r"Id водителя:\s*(\d+)", text)
        callsign = callsign_match.group(1) if callsign_match else None

        amount_match = re.search(r"🇺🇿\s*([^\n]+)", text)
        amount_uzs = parse_amount(amount_match.group(1)) if amount_match else Decimal("0")

        if provider_txn_id and callsign and amount_uzs > 0:
            ok, payment, msg = save_payment_and_topup(
                provider="payme",
                provider_txn_id=provider_txn_id,
                callsign=callsign,
                amount_uzs=amount_uzs,
                raw_payload={"raw_text": text},
            )
            print("💾 Natija:", ok, msg)
        else:
            print("⚠️ Xabardan kerakli maydonlarni ajratib bo‘lmadi")

    except Exception as e:
        print("⚠️ Xatolik:", e)
        print("To‘liq obyekt:", message)

if __name__ == "__main__":
    print("📌 Userbot ishga tushyapti...")
    app.run()