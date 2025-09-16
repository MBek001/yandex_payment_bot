from decimal import Decimal
from datetime import datetime
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


def save_payment_and_topup(provider: str, provider_txn_id: str, callsign: str,
                           amount_uzs: Decimal, raw_payload: dict) -> tuple[bool, dict, str]:
    if provider == "payme":
        category_id = config.PROVIDER_PAYME
    elif provider == "click":
        category_id = config.PROVIDER_CLICK
    else:
        raise Exception("Unknown provider")

    # Save payment to database
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

    # Resolve driver ID
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

    # Perform top-up
    ok = taxi_api.topup_balance(driver_id=driver_id, category_id=category_id, amount=float(amount_uzs))
    if not ok:
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
            context=f"category_id={category_id}, driver_id={driver_id}",
            payload_excerpt=str(raw_payload)[:500],
        )
        return False, payment, "yandex topup failed"

    # Update payment as performed
    update_payment_status(
        payment_id=payment["id"],
        status="performed",
        driver_profile_id=driver_id,
        performed_at=datetime.utcnow().isoformat()
    )

    notify_payment_success(
        config,
        provider=provider,
        callsign=callsign,
        amount_uzs=amount_uzs,
        driver_id=driver_id,
        provider_txn_id=provider_txn_id,
    )
    return True, payment, "ok"
