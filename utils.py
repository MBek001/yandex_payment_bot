# utils.py
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime
from typing import Tuple

from config import config
from yandex import taxi_api
from database import save_payment, update_payment_status
from telegram_notification import notify_payment_success, notify_payment_error


def get_category_for_provider(provider: str) -> str:
    return provider


def resolve_driver_id_by_callsign(callsign: str) -> str | None:

    callsign = (callsign or "").strip()
    if not callsign:
        return None
    driver = taxi_api.get_driver_by_callsign(callsign)
    if not driver:
        return None
    dp = (driver.get("driver_profile") or {})
    return dp.get("id")


def _normalize_fee_value(raw_fee) -> Decimal:

    if raw_fee is None:
        return Decimal("0")
    try:
        fee_dec = Decimal(str(raw_fee))
    except (InvalidOperation, ValueError):
        return Decimal("0")
    if fee_dec > 1:
        try:
            return (fee_dec / Decimal("100")).quantize(Decimal("0.0000001"))
        except InvalidOperation:
            return Decimal("0")
    return fee_dec


def _apply_provider_fee(provider: str, amount: Decimal) -> Decimal:

    if amount is None:
        return Decimal("0.00")

    raw_fee = None
    try:
        raw_fee = config.PAYMENT_FEE
    except Exception:
        raw_fee = None

    if raw_fee is None:
        raw_fee = getattr(config, "PROVIDER_FEE_DEFAULT", 0)

    fee_fraction = _normalize_fee_value(raw_fee)

    if fee_fraction < 0:
        fee_fraction = Decimal("0")
    if fee_fraction > 1:
        fee_fraction = Decimal("1")

    multiplier = (Decimal("1") - fee_fraction)
    topup = (amount * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return topup


def save_payment_and_topup(provider: str, provider_txn_id: str, callsign: str,
                           amount_uzs: Decimal, raw_payload: dict) -> Tuple[bool, dict, str]:

    if provider == "payme":
        category_id = config.PROVIDER_PAYME
    elif provider == "click":
        category_id = config.PROVIDER_CLICK
    else:
        raise Exception("Unknown provider")

    ok, payment, msg = save_payment(
        provider=provider,
        provider_txn_id=provider_txn_id,
        callsign=callsign,
        amount=amount_uzs,
        category_id=category_id,
        raw_payload=raw_payload
    )

    if not ok:
        return False, payment, msg

    driver_id = resolve_driver_id_by_callsign(callsign)
    if not driver_id:
        update_payment_status(
            payment_id=payment["id"],
            status="failed"
        )
        notify_payment_error(
            config,
            title="Haydovchi topilmadi",
            error_msg="Bu Pazivnoyda haydovchi topilmadi",
            provider=provider,
            callsign=callsign,
            amount_uzs=amount_uzs,
            provider_txn_id=provider_txn_id,
            payload_excerpt=str(raw_payload)[:500],
        )
        return False, payment, "driver not found by callsign"

    topup_amount = _apply_provider_fee(provider, amount_uzs)

    try:
        ok_topup = taxi_api.topup_balance(driver_id=driver_id, category_id=category_id, amount=float(topup_amount))
    except Exception as e:
        ok_topup = False

    if not ok_topup:
        update_payment_status(
            payment_id=payment["id"],
            status="failed"
        )
        notify_payment_error(
            config,
            title="Yandex top-up xatosi",
            error_msg="yandex topup failed",
            provider=provider,
            callsign=callsign,
            amount_uzs=amount_uzs,
            provider_txn_id=provider_txn_id,
            context=f"category_id={category_id}, driver_id={driver_id}, topup_amount={topup_amount}",
            payload_excerpt=str(raw_payload)[:500],
        )
        return False, payment, "yandex topup failed"

    update_payment_status(
        payment_id=payment["id"],
        status="performed",
        driver_profile_id=driver_id,
        performed_at=datetime.utcnow().isoformat()
    )

    try:
        notify_payment_success(
            config,
            provider=provider,
            callsign=callsign,
            original_amount=amount_uzs,
            topup_amount=topup_amount,
            driver_id=driver_id,
            provider_txn_id=provider_txn_id,
        )
    except Exception:
        pass

    return True, payment, "ok"
