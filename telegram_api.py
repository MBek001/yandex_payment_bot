import asyncio
from decimal import Decimal
from pyrogram import Client, filters

import config
from config import PARKS
from parser import parse_amount, parse_callsign, parse_provider_txn_id, is_successful_payment
from utils import save_payment_and_topup
from database import init_db

# initialize DB
init_db()

# Pyrogram configuration
api_id = config.APP_ID
api_hash = config.APP_SECRET
app_title = config.APP_TITLE
app = Client(app_title, api_id=api_id, api_hash=api_hash)


def safe_text(msg):
    return (msg or "") if isinstance(msg, str) else str(msg)


def get_park_by_group_id(group_id: int):
    """Telegram group_id orqali tegishli parkni topadi"""
    for park in PARKS.values():
        if str(group_id) in park.telegram_groups:
            return park
    return None


@app.on_message(filters.group)
async def handle_message(client, message):
    try:
        text = safe_text(message.text or message.caption or "")
        chat = message.chat
        group_id = str(chat.id)

        # Parkni topamiz
        park = get_park_by_group_id(group_id)
        if not park:
            print(f"❌ Unknown park for group {group_id}")
            return

        # To'lov xabari ekanligini tekshirish
        if not is_successful_payment(text):
            print("⚠️ Not a successful payment message, skipping.")
            return

        # Ma'lumotlarni parse qilish
        provider_txn_id = parse_provider_txn_id(text)
        callsign = parse_callsign(text)
        amount = parse_amount(text)

        if not provider_txn_id or not callsign or amount <= Decimal("0"):
            print(
                f"⚠️ Missing fields in message from {group_id}: txn={provider_txn_id}, callsign={callsign}, amount={amount}"
            )
            return

        raw_payload = {
            "raw_text": text,
            "group_id": group_id,
            "group_title": getattr(chat, "title", None),
        }

        # Asosiy ishlovchi task
        async def _process():
            ok, payment, msg = save_payment_and_topup(
                provider=park.provider,
                provider_txn_id=provider_txn_id,
                callsign=callsign,
                amount_uzs=amount,
                raw_payload=raw_payload,
                park=park,
            )
            print(f"✅ Processed txn {provider_txn_id} for park {park.name}: ok={ok}, msg={msg}")

        asyncio.create_task(_process())

    except Exception as e:
        print("🔥 Error in handle_message:", e)


if __name__ == "__main__":
    print("🚀 Bot starting...")
    app.run()
