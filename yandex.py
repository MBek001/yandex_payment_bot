import uuid
import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class YandexTaxiAPI:
    def __init__(self, park_id: str, clid: str, api_key: str):
        self.park_id = park_id
        self.clid = clid
        self.api_key = api_key

        self.driver_api_url = "https://fleet-api.taxi.yandex.net/v1/parks/driver-profiles/list"
        self.topup_api_url = "https://fleet-api.taxi.yandex.net/v2/parks/driver-profiles/transactions"

        self.base_fields = {
            "driver_profile": ["id", "first_name", "last_name", "phones", "work_status"],
            "car": ["brand", "model", "number", "color", "callsign", "category", "status", "year"],
            "accounts": ["balance", "currency", "id"],
            "current_status": ["status"],
        }

    def _make_api_request(self, url: str, body: dict, headers: dict = None, retries: int = 3):
        headers = headers or {}
        for attempt in range(retries):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=30)
                if not resp.ok:
                    logger.warning("Yandex API returned %s: %s", resp.status_code, resp.text)
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                logger.warning("Attempt %d Yandex request failed: %s", attempt + 1, e)
                if attempt == retries - 1:
                    raise
        return None

    def get_driver_by_callsign(self, callsign: str):
        if not callsign:
            return None
        body = {
            "fields": self.base_fields,
            "query": {"park": {"id": self.park_id}, "text": callsign},
            "limit": 50,
        }
        headers = {
            "X-API-Key": self.api_key,
            "X-Client-ID": self.clid,
            "Content-Type": "application/json",
        }
        try:
            resp = self._make_api_request(self.driver_api_url, body, headers=headers)
            if not resp:
                return None
            data = resp.json()
            drivers = data.get("driver_profiles", []) or []
            # prefer exact matching callsign in car
            for d in drivers:
                car = d.get("car") or {}
                if (car.get("callsign") or "").strip().upper() == callsign.upper():
                    return d
            return drivers[0] if drivers else None
        except Exception as e:
            logger.error("get_driver_by_callsign error: %s", e)
            return None

    def topup_balance(self, driver_id: str, category_id: str, amount: float) -> bool:
        headers = {
            "X-API-Key": self.api_key,
            "X-Client-ID": self.clid,
            "X-Idempotency-Token": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }
        body = {
            "park_id": self.park_id,
            "driver_profile_id": driver_id,
            "category_id": category_id,
            "amount": f"{amount:.2f}",
            "currency": "UZS",
            "event_at": datetime.utcnow().isoformat() + "Z",
            "description": "Пополнение баланса через систему",
        }
        try:
            resp = self._make_api_request(self.topup_api_url, body, headers=headers)
            return bool(resp and resp.status_code == 200)
        except Exception as e:
            logger.error("topup_balance error: %s", e)
            return False
