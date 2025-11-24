from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime
from typing import Tuple

import config
from yandex import YandexTaxiAPI
from database import save_payment, update_payment_status
from telegram_notification import notify_payment_success, notify_payment_error


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


def _apply_provider_fee(provider: str, amount: Decimal, park) -> Decimal:
    raw_fee = getattr(park, "payment_fee", None) or getattr(config, "PAYMENT_FEE", 0)
    fee_fraction = _normalize_fee_value(raw_fee)
    fee_fraction = max(min(fee_fraction, Decimal("1")), Decimal("0"))
    multiplier = Decimal("1") - fee_fraction
    return (amount * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def save_payment_and_topup(provider: str, provider_txn_id: str, callsign: str,
                           amount_uzs: Decimal, raw_payload: dict, park) -> Tuple[bool, dict, str]:

    category_id = _get_category_id(provider, park)

    ok, payment, msg = save_payment(
        provider=provider,
        provider_txn_id=provider_txn_id,
        callsign=callsign,
        amount=amount_uzs,
        category_id=category_id,
        raw_payload=raw_payload,
        status="created",
        park_group_id=park.name,
    )
    if not ok:
        return False, payment, msg

    payment_id = int(payment["id"])

    # 2. Resolve driver by callsign within this park
    api = YandexTaxiAPI(park.park_id, park.clid, park.api_key)
    driver = api.get_driver_by_callsign(callsign)
    driver_id = None
    if driver:
        driver_profile = driver.get("driver_profile") or {}
        driver_id = driver_profile.get("id") or driver.get("id")

    if not driver_id:
        update_payment_status(payment_id=payment_id, status="failed")
        # notify park
        try:
            notify_payment_error(
                park,
                title=f"Haydovchi topilmadi #{park.name}",
                error_msg=f"Haydovchi topilmadi",
                provider=provider,
                callsign=callsign,
                amount_uzs=amount_uzs,
                provider_txn_id=provider_txn_id,
                context=f"park={park.park_id}",
                payload_excerpt=str(raw_payload)[:500],
            )
        except Exception:
            pass
        return False, payment, "driver not found in park"

    # 3. Compute topup after provider fee
    topup_amount = _apply_provider_fee(provider, amount_uzs, park)

    ok_topup = False
    try:
        ok_topup = api.topup_balance(driver_id=driver_id, category_id=provider, amount=float(topup_amount))
    except Exception:
        ok_topup = False

    if not ok_topup:
        update_payment_status(payment_id=payment_id, status="failed")
        try:
            notify_payment_error(
                park,
                title="Yandex top-up xatosi",
                error_msg="Yandex topup failed",
                provider=provider,
                callsign=callsign,
                amount_uzs=amount_uzs,
                provider_txn_id=provider_txn_id,
                context=f"park={park.park_id}, driver_id={driver_id}, topup_amount={topup_amount}",
                payload_excerpt=str(raw_payload)[:500],
            )
        except Exception:
            pass
        return False, payment, "yandex topup failed"

    update_payment_status(payment_id=payment_id, status="performed", driver_profile_id=driver_id,
                          performed_at=datetime.utcnow().isoformat())

    if ok_topup:
        try:
            notify_payment_success(
                park,
                provider=category_id,
                callsign=callsign,
                original_amount=amount_uzs,
                topup_amount=topup_amount,
                driver_id=driver_id,
                provider_txn_id=provider_txn_id,
            )
            print("sent notif ", category_id)
        except Exception:
            return

    return True, payment, "ok"


def _get_category_id(provider: str, park) -> str:
    suffix = (park.name or "").rsplit("_", 1)[-1].lower()

    if suffix == "click":
        return config.PROVIDER_CLICK
    if suffix == "payme":
        return config.PROVIDER_PAYME

    # Agar park.name dan aniqlanmasa, provider parametri bo'yicha
    if provider == "click":
        return config.PROVIDER_CLICK
    if provider == "payme":
        return config.PROVIDER_PAYME

    # Oxirgi variant: park.provider yoki default PAYME
    if getattr(park, "provider", None):
        return park.provider

    return config.PROVIDER_PAYME
