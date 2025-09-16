import uuid
import requests
from datetime import datetime
from config import config
import logging

logger = logging.getLogger(__name__)

class YandexTaxiAPI:
    def __init__(self):
        self.driver_api_url = "https://fleet-api.taxi.yandex.net/v1/parks/driver-profiles/list"
        self.topup_api_url = "https://fleet-api.taxi.yandex.net/v2/parks/driver-profiles/transactions"
        self.categories_api_url = "https://fleet-api.taxi.yandex.net/v2/parks/transactions/categories/list"
        self.headers = {
            "X-API-Key": config.API_KEY,
            "X-Client-ID": config.CLID,
            "Content-Type": "application/json",
            "Accept-Language": "ru-RU",
        }
        self.base_query = {
            "fields": {
                "driver_profile": ["id", "first_name", "last_name", "phones", "work_status"],
                "car": ["brand", "model", "number", "color", "callsign", "category", "status", "year"],
                "accounts": ["balance", "currency", "id"],
                "current_status": ["status"],
            },
            "query": {"park": {"id": config.PARK_ID}},
        }

    def _make_api_request(self, url: str, body: dict, retries: int = 3):
        headers = self.headers.copy()
        if url == self.topup_api_url:
            headers["X-Idempotency-Token"] = str(uuid.uuid4())
        for attempt in range(retries):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=30)
                if not resp.ok:
                    logger.error("Yandex API %s: %s", resp.status_code, resp.text)
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                if attempt == retries - 1:
                    raise
        return None

    def get_driver_by_callsign(self, callsign: str):
        callsign = (callsign or "").strip()
        if not callsign:
            return None
        body = {"fields": self.base_query["fields"], "query": {"park": {"id": config.PARK_ID}, "text": callsign}, "limit": 50}
        try:
            resp = self._make_api_request(self.driver_api_url, body)
            if not resp or resp.status_code != 200:
                return None
            drivers = (resp.json().get("driver_profiles", []) or [])
            for d in drivers:
                car = (d.get("car") or {})
                if (car.get("callsign") or "").strip().upper() == callsign.upper():
                    return d
            return drivers[0] if drivers else None
        except Exception:
            return None

    def topup_balance(self, driver_id: str, category_id: str, amount: float) -> bool:
        try:
            body = {
                "park_id": config.PARK_ID,
                "driver_profile_id": driver_id,
                "category_id": category_id,
                "amount": f"{amount:.2f}",
                "currency": "UZS",
                "event_at": datetime.utcnow().isoformat() + "Z",
                "description": "Авто пополнение баланса через систему",
            }
            resp = self._make_api_request(self.topup_api_url, body)
            return bool(resp and resp.status_code == 200)
        except Exception:
            return False

taxi_api = YandexTaxiAPI()
