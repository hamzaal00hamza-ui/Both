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
    url = "https://apisyria.com/api/v1"
    headers = {
        "X-Api-Key": config.SHAMCASH_TOKEN,
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

    # API SYRIA response format: {success, data, message}
    if not body.get("success"):
        code = body.get("code", "API_ERROR")
        message = body.get("message", "")
        data = body.get("data")
        logger.warning(f"ShamCash error {code}: {message}")
        raise ShamCashError(code, message, data)

    return body.get("data")


def list_accounts() -> List[Dict[str, Any]]:
    """يرجع لائحة الحسابات المربوطة بهذا التوكن."""
    data = _request("GET", "/accounts", params={"resource": "accounts", "action": "list"})
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
    return _request("GET", "/balance", params={"resource": "shamcash", "action": "balance", "account_address": account_id})


def list_transactions(account_id: str,
                       start_at: Optional[str] = None,
                       end_at: Optional[str] = None,
                       coin_id = None,
                       limit: int = 50) -> List[Dict[str, Any]]:
    """يرجع المعاملات الواردة للحساب — عبر API SYRIA."""
    data = _request("GET", "/logs", params={
        "resource": "shamcash",
        "action": "logs",
        "account_address": account_id,
    })
    if not data:
        return []
    return data.get("items", []) or []


def find_matching_transaction(account_id: str,
                                expected_amount: float,
                                window_minutes: int = 30,
                                coin_id = COIN_SYP,
                                tolerance: float = 0.01) -> Optional[Dict[str, Any]]:
    """
    يبحث عن معاملة واردة بنفس المبلغ خلال آخر window_minutes دقيقة.
    يرجع المعاملة (dict) أو None.
    """
    # API SYRIA: استخدم find_tx للبحث المباشر
    try:
        data = _request("GET", "/find_tx", params={
            "resource": "shamcash",
            "action": "find_tx",
            "tx": str(account_id),
            "account_address": config.SHAMCASH_WALLET_CODE,
        })
    except ShamCashError:
        return None

    if not data or not data.get("found"):
        return None

    tx = data.get("transaction", {})
    try:
        amount = float(tx.get("amount", 0))
    except (TypeError, ValueError):
        return None

    if abs(amount - float(expected_amount)) <= tolerance:
        return tx
    return None


def is_enabled() -> bool:
    return _enabled()
