import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# === GLOBAL SETTINGS ===
APP_TITLE = os.getenv("APP_TITLE", "YandexTaxi")
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DASHBOARD_SECRET = os.getenv("DASHBOARD_SECRET")
PROVIDER_PAYME = os.getenv("PROVIDER_PAYME")
PROVIDER_CLICK = os.getenv("PROVIDER_CLICK")


# === HELPERS ===
def parse_list(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# === LOAD PARKS ===
class Park:
    def __init__(self, name, api_key, clid, park_id, telegram_groups, notification_chat_id,
                 allowed_users, payment_fee, sticker_success, sticker_error, provider):
        self.name = name
        self.api_key = api_key
        self.clid = clid
        self.park_id = park_id
        self.telegram_groups = telegram_groups
        self.notification_chat_id = notification_chat_id
        self.allowed_users = allowed_users
        self.payment_fee = payment_fee
        self.sticker_success = sticker_success
        self.sticker_error = sticker_error
        self.provider = provider


def load_parks_from_env():
    parks = {}
    idx = 1

    while True:
        if not os.getenv(f"PARK{idx}_NAME"):
            break

        parks[f"PARK{idx}"] = Park(
            name=os.getenv(f"PARK{idx}_NAME"),
            api_key=os.getenv(f"PARK{idx}_API_KEY"),
            clid=os.getenv(f"PARK{idx}_CLID"),
            park_id=os.getenv(f"PARK{idx}_PARK_ID"),
            telegram_groups=parse_list(os.getenv(f"PARK{idx}_TELEGRAM_GROUPS", "")),
            notification_chat_id=os.getenv(f"PARK{idx}_NOTIFICATION_CHAT_ID"),
            allowed_users=parse_list(os.getenv(f"PARK{idx}_ALLOWED_USERS", "")),
            payment_fee=int(os.getenv(f"PARK{idx}_PAYMENT_FEE", 0)),
            sticker_success=os.getenv(f"PARK{idx}_STICKER_SUCCESS", "✅"),
            sticker_error=os.getenv(f"PARK{idx}_STICKER_ERROR", "❌"),
            provider=os.getenv(f"PARK{idx}_PROVIDER"),
        )
        idx += 1

    return parks


# === READY PARKS CONFIG ===
PARKS = load_parks_from_env()
