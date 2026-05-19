"""
عميل ShamCash API (https://api.shamcash-api.com/v1)
حسب التوثيق الرسمي على https://shamcash-api.com/docs
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import requests

from . import config

logger = logging.getLogger(__name__)

DAMASCUS_TZ = timezone(timedelta(hours=3))

COIN_USD = 1
COIN_SYP = 2
COIN_EUR = 3


class ShamCashError(Exception):
    def __init__(self, code: str, message: str, data: Any = None):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.data = data


def _enabled() -> bool:
    return bool(config.SHAMCASH_AUTO_VERIFY) and bool(config.SHAMCASH_TOKEN) \
        and config.SHAMCASH_TOKEN not in ("", "ضع_التوكن_هنا")


def _request(method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not config.SHAMCASH_TOKEN or config.SHAMCASH_TOKEN == "ضع_التوكن_هنا":
        raise ShamCashError("AUTH_MISSING", "SHAMCASH_TOKEN غير مضبوط")
    url = f"{config.SHAMCASH_API_URL.rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {config.SHAMCASH_TOKEN}",
        "Accept": "application/json",
    }
    try:
        resp = requests.request(method, url, headers=headers, params=params, timeout=20)
    except requests.RequestException as e:
        logger.error(f"ShamCash request error: {e}")
        raise ShamCashError("NETWORK", str(e))

    try:
        body = resp.json()
    except ValueError:
        raise ShamCashError("INVALID_JSON", f"Non-JSON response (HTTP {resp.status_code})")

    status = body.get("status")
    code = body.get("code", "UNKNOWN")
    message = body.get("message", "")
    data = body.get("data")

    if status != "success":
        logger.warning(f"ShamCash error {code}: {message}")
        raise ShamCashError(code, message, data)

    return data


def list_accounts() -> List[Dict[str, Any]]:
    """يرجع لائحة الحسابات المربوطة بهذا التوكن."""
    data = _request("GET", "/accounts")
    return data or []


def get_active_account_id() -> Optional[str]:
    """
    إذا الـ SHAMCASH_ACCOUNT_ID مضبوط ينستخدم،
    وإلا بنجيب أول حساب active من /accounts.
    """
    if config.SHAMCASH_ACCOUNT_ID and config.SHAMCASH_ACCOUNT_ID not in ("", "ضع_رقم_التاجر_هنا"):
        return config.SHAMCASH_ACCOUNT_ID
    try:
        accounts = list_accounts()
    except ShamCashError as e:
        logger.error(f"Cannot list accounts: {e}")
        return None
    for acc in accounts:
        if acc.get("status") == "active":
            return acc.get("id")
    return accounts[0].get("id") if accounts else None


def get_balances(account_id: str) -> Dict[str, Any]:
    return _request("GET", "/balances", params={"account_id": account_id})


def list_transactions(account_id: str,
                       start_at: Optional[str] = None,
                       end_at: Optional[str] = None,
                       coin_id: Optional[int] = None,
                       limit: int = 50) -> List[Dict[str, Any]]:
    """يرجع المعاملات الواردة للحساب."""
    params: Dict[str, Any] = {"account_id": account_id, "limit": limit}
    if start_at:
        params["start_at"] = start_at
    if end_at:
        params["end_at"] = end_at
    if coin_id is not None:
        params["coin_id"] = coin_id
    data = _request("GET", "/transactions", params=params)
    if not data:
        return []
    return data.get("transactions", []) or []


def find_matching_transaction(account_id: str,
                                expected_amount: float,
                                window_minutes: int = 30,
                                coin_id: int = COIN_SYP,
                                tolerance: float = 0.01) -> Optional[Dict[str, Any]]:
    """
    يبحث عن معاملة واردة بنفس المبلغ خلال آخر window_minutes دقيقة.
    يرجع المعاملة (dict) أو None.
    """
    now_dam = datetime.now(DAMASCUS_TZ)
    start = (now_dam - timedelta(minutes=window_minutes)).strftime("%Y-%m-%dT%H:%M:%S%z")
    end = now_dam.strftime("%Y-%m-%dT%H:%M:%S%z")
    start = start[:-2] + ":" + start[-2:]
    end = end[:-2] + ":" + end[-2:]

    txs = list_transactions(account_id, start_at=start, end_at=end, coin_id=coin_id, limit=100)
    for tx in txs:
        try:
            amount = float(tx.get("amount", 0))
        except (TypeError, ValueError):
            continue
        if abs(amount - float(expected_amount)) <= tolerance:
            return tx
    return None


def is_enabled() -> bool:
    return _enabled()
