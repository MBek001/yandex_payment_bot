import os
from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=False)

def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "y", "on")

@dataclass(frozen=True)
class Config:
    API_KEY: str = os.getenv("API_KEY")
    CLID: str = os.getenv("CLID")
    PARK_ID: str = os.getenv("PARK_ID")

    #telegram api configurations
    APP_TITLE= os.getenv("APP_TITLE")
    APP_ID= os.getenv("APP_ID")
    APP_SECRET = os.getenv("APP_SECRET")

    #talegran transaction notification groups ids
    BRO_TAXI = int(os.getenv("BRO_TAXI"))
    ALLOWED_USERS = int(os.getenv("ALLOWED_USERS"))

    PROVIDER_PAYME: str = os.getenv("PROVIDER_PAYME")
    PROVIDER_CLICK: str = os.getenv("PROVIDER_CLICK")
    DASHBOARD_SECRET: str = os.getenv("DASHBOARD_SECRET")

    # Telegram
    TELEGRAM_ENABLED: bool = env_bool("TELEGRAM_ENABLED", True)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID")
    TELEGRAM_STICKER_SUCCESS: str = os.getenv("TELEGRAM_STICKER_SUCCESS")
    TELEGRAM_STICKER_ERROR: str = os.getenv("TELEGRAM_STICKER_ERROR")

config = Config()



