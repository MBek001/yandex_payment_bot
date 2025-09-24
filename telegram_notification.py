import requests
from html import escape
from decimal import Decimal, ROUND_HALF_UP
from telegram.constants import ParseMode
import config


def _post(url: str, payload: dict) -> None:
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print("Telegram error:", e, payload)


def send_html(bot_token: str, chat_id: str, html: str) -> None:
    if not bot_token or not chat_id:
        return
    _post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        {
            "chat_id": chat_id,
            "text": html,
            "parse_mode": ParseMode.HTML,
            "disable_web_page_preview": True,
        },
    )


def _kv(key: str, val) -> str:
    return f"<b>{escape(str(key))}:</b> {escape(str(val))}"


def _format_amount(amount) -> str:
    if amount is None:
        return ""
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = f"{amount:.2f}"
    int_part, frac = s.split(".")
    int_part_with_sep = format(int(int_part), ",").replace(",", " ")
    return f"{int_part_with_sep}.{frac}"


def notify_payment_success(park, *, provider: str, callsign: str, original_amount, topup_amount, driver_id: str | None,
                           provider_txn_id: str | None):
    if not getattr(config, "TELEGRAM_ENABLED", True):
        return
    bot = config.BOT_TOKEN
    chat = getattr(park, "notification_chat_id", "") or getattr(config, "TELEGRAM_CHAT_ID", "")
    if not bot or not chat:
        return
    rows = [
        f"✅ <b>To‘lov qabul qilindi ({park.name})</b>",
        _kv("Provider", provider),
        _kv("Pazivnoy", callsign),
        _kv("📥 Qabul qilingan summa", f"{_format_amount(original_amount)} UZS"),
        _kv("💳 To'langan summa", f"{_format_amount(topup_amount)} UZS"),
    ]
    if provider_txn_id:
        rows.append(_kv("To'lov ID", provider_txn_id))
    if driver_id:
        rows.append(_kv("Haydovchi ID", driver_id))
    send_html(bot, chat, "\n".join(rows))


def notify_payment_error(park, *, title: str, error_msg: str, provider: str | None = None, callsign: str | None = None,
                         amount_uzs=None, provider_txn_id: str | None = None, context: str | None = None,
                         payload_excerpt: str | None = None):
    if not getattr(config, "TELEGRAM_ENABLED", True):
        return
    bot = config.BOT_TOKEN
    chat = getattr(park, "notification_chat_id", "") or getattr(config, "TELEGRAM_CHAT_ID", "")
    if not bot or not chat:
        return
    rows = [
        f"❌ <b>{escape(title)}</b>",
        _kv("Xato", error_msg),
    ]
    if provider:
        rows.append(_kv("Provider", provider))
    if callsign:
        rows.append(_kv("Pazivnoy", callsign))
    if amount_uzs is not None:
        rows.append(_kv("Summa", f"{_format_amount(amount_uzs)} UZS"))
    if provider_txn_id:
        rows.append(_kv("To'lov ID", provider_txn_id))
    if context:
        rows.append(_kv("Context", context))
    send_html(bot, chat, "\n".join(rows))
