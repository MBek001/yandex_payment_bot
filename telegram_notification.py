import requests
from html import escape
from decimal import Decimal, ROUND_HALF_UP

from telegram.constants import ParseMode


def _post(url: str, payload: dict) -> None:
    try:
        requests.post(url, json=payload, timeout=10).raise_for_status()
    except Exception:
        pass


def send_sticker(bot_token: str, chat_id: str, sticker: str) -> None:
    if sticker:
        _post(
            f"https://api.telegram.org/bot{bot_token}/sendSticker",
            {"chat_id": chat_id, "sticker": sticker},
        )


def send_html(bot_token: str, chat_id: str, html: str) -> None:
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
    """
    Format Decimal or numeric amount into '20 000.00' style:
    - space as thousand separator
    - two decimals
    """
    if amount is None:
        return ""
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    # Round to 2 decimals
    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = f"{amount:.2f}"  # Decimal supports f-format
    int_part, frac = s.split(".")
    int_part_with_sep = format(int(int_part), ",").replace(",", " ")
    return f"{int_part_with_sep}.{frac}"


def notify_payment_success(cfg,
                           *,
                           provider: str,
                           callsign: str,
                           original_amount,
                           topup_amount,
                           driver_id: str | None,
                           provider_txn_id: str | None) -> None:
    if not getattr(cfg, "TELEGRAM_ENABLED", False):
        return
    bot = getattr(cfg, "TELEGRAM_BOT_TOKEN", "")
    chat = getattr(cfg, "TELEGRAM_CHAT_ID", "")
    if not bot or not chat:
        return
    send_sticker(bot, chat, getattr(cfg, "TELEGRAM_STICKER_SUCCESS", ""))
    rows = [
        "✅ <b>To‘lov qabul qilindi</b>",
        _kv("📝 Provider", provider),
        _kv("🔸 Pazivnoy", callsign),
        _kv("🧾 Haydovchi tashladi", f"{_format_amount(original_amount)} UZS"),
        _kv("💳 Haydovchiga tashlandi", f"{_format_amount(topup_amount)} UZS"),
    ]
    if provider_txn_id:
        rows.append(_kv("🧾 To'lov IDsi", provider_txn_id))
    if driver_id:
        rows.append(_kv("🔍 Haydovchi IDsi", driver_id))
    send_html(bot, chat, "\n".join(rows))


def notify_payment_error(cfg,
                         *,
                         title: str,
                         error_msg: str,
                         provider: str | None = None,
                         callsign: str | None = None,
                         amount_uzs=None,
                         provider_txn_id: str | None = None,
                         context: str | None = None,
                         payload_excerpt: str | None = None) -> None:
    if not getattr(cfg, "TELEGRAM_ENABLED", False):
        return
    bot = getattr(cfg, "TELEGRAM_BOT_TOKEN", "")
    chat = getattr(cfg, "TELEGRAM_CHAT_ID", "")
    if not bot or not chat:
        return
    send_sticker(bot, chat, getattr(cfg, "TELEGRAM_STICKER_ERROR", ""))
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
        rows.append(_kv("To'lov IDsi", provider_txn_id))
    if context:
        rows.append(_kv("Context", context))
    if payload_excerpt:
        rows.append(_kv("Payload excerpt", payload_excerpt[:500]))
    send_html(bot, chat, "\n".join(rows))
