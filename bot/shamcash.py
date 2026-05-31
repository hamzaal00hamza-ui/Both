"""
ShamCash API — عبر منصة API SYRIA
التوثيق: https://apisyria.com/api/docs

Endpoints:
  GET  resource=shamcash&action=balance    → رصيد الحساب
  GET  resource=shamcash&action=logs       → سجل التحويلات
  GET  resource=shamcash&action=find_tx   → البحث برقم العملية

المصادقة: Header "X-Api-Key: TOKEN"
"""
import logging
from typing import Optional, Dict, Any, List

import requests

from . import config

logger = logging.getLogger(__name__)

API_BASE        = "https://apisyria.com/api/v1"
REQUEST_TIMEOUT = 20

# ── Constants (backward compat) ─────────────────────────
COIN_USD = 1
COIN_SYP = 2
COIN_EUR = 3


class ShamCashError(Exception):
    def __init__(self, code: str, message: str, data: Any = None):
        super().__init__(f"{code}: {message}")
        self.code    = code
        self.message = message
        self.data    = data


def is_enabled() -> bool:
    return (
        bool(getattr(config, "SHAMCASH_AUTO_VERIFY", False))
        and bool(getattr(config, "SHAMCASH_TOKEN", ""))
        and config.SHAMCASH_TOKEN not in ("", "ضع_التوكن_هنا")
    )


def _get_token() -> str:
    return getattr(config, "SHAMCASH_TOKEN", "")


def _get_address() -> str:
    return getattr(config, "SHAMCASH_WALLET_CODE", "")


def _request(params: Dict[str, Any]) -> Dict[str, Any]:
    """يرسل GET لـ API SYRIA ويرجع data أو يرفع ShamCashError."""
    token = _get_token()
    if not token:
        raise ShamCashError("AUTH_MISSING", "SHAMCASH_TOKEN غير مضبوط")

    headers = {
        "X-Api-Key": token,
        "Accept":    "application/json",
    }

    try:
        resp = requests.get(
            API_BASE,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        logger.error(f"ShamCash request error: {e}")
        raise ShamCashError("NETWORK", str(e))

    try:
        body = resp.json()
    except ValueError:
        raise ShamCashError("INVALID_JSON", f"Non-JSON response (HTTP {resp.status_code})")

    if not body.get("success"):
        msg  = body.get("message", "")
        code = body.get("code", "API_ERROR")
        logger.warning(f"API SYRIA ShamCash error: {code} — {msg}")
        raise ShamCashError(code, msg or code, body.get("data"))

    return body.get("data") or {}


# ─────────────────────────────────────────
# Balance
# ─────────────────────────────────────────
def get_balances(account_address: Optional[str] = None) -> List[Dict[str, Any]]:
    """يرجع قائمة أرصدة حساب ShamCash."""
    addr = account_address or _get_address()
    data = _request({
        "resource":        "shamcash",
        "action":          "balance",
        "account_address": addr,
    })
    return data.get("balances", []) or []


def get_syp_balance(account_address: Optional[str] = None) -> float:
    """يرجع رصيد الليرة السورية فقط."""
    for b in get_balances(account_address):
        if b.get("currency") == "SYP":
            try:
                return float(b.get("balance", 0))
            except (TypeError, ValueError):
                return 0.0
    return 0.0


# ─────────────────────────────────────────
# Logs (سجل التحويلات)
# ─────────────────────────────────────────
def list_transactions(account_address: Optional[str] = None,
                       start_at: Optional[str] = None,
                       end_at: Optional[str] = None,
                       coin_id=None,
                       limit: int = 50) -> List[Dict[str, Any]]:
    """
    يرجع سجل تحويلات ShamCash.
    كل عنصر: {tran_id, from_name, to_name, currency, amount, datetime, account, note}
    """
    addr = account_address or _get_address()
    data = _request({
        "resource":        "shamcash",
        "action":          "logs",
        "account_address": addr,
    })
    return data.get("items", []) or []


# ─────────────────────────────────────────
# Find transaction
# ─────────────────────────────────────────
def find_matching_transaction(account_id: str,
                               expected_amount: float,
                               account_address: Optional[str] = None,
                               tolerance: float = 0.01,
                               window_minutes: int = 30,
                               coin_id=None) -> Optional[Dict[str, Any]]:
    """
    يبحث عن عملية ShamCash برقم العملية tran_id ومبلغ متقارب.
    account_id: رقم العملية كما يظهر في تطبيق شام كاش.
    يرجع dict العملية أو None.
    """
    target = str(account_id or "").strip()
    if not target:
        return None

    addr = account_address or _get_address()

    try:
        data = _request({
            "resource":        "shamcash",
            "action":          "find_tx",
            "tx":              target,
            "account_address": addr,
        })
    except ShamCashError as e:
        logger.warning(f"ShamCash find_tx error: {e}")
        return None

    if not data.get("found"):
        return None

    tx = data.get("transaction", {})
    try:
        amount = float(tx.get("amount", 0))
    except (TypeError, ValueError):
        return None

    # التحقق من العملة
    currency = str(tx.get("currency", "")).upper()
    if currency and currency != "SYP":
        logger.warning(f"ShamCash tx {target}: unexpected currency {currency}")
        return None

    if abs(amount - float(expected_amount)) > tolerance:
        logger.warning(
            f"ShamCash tx {target} amount mismatch: "
            f"got {amount} vs expected {expected_amount}"
        )
        return None

    return tx


# ─────────────────────────────────────────
# Accounts (backward compat)
# ─────────────────────────────────────────
def list_accounts() -> List[Dict[str, Any]]:
    """يرجع لائحة حسابات ShamCash المرتبطة."""
    try:
        headers = {
            "X-Api-Key": _get_token(),
            "Accept":    "application/json",
        }
        resp = requests.get(
            API_BASE,
            headers=headers,
            params={"resource": "accounts", "action": "list"},
            timeout=REQUEST_TIMEOUT,
        )
        body = resp.json()
        if body.get("success"):
            return body.get("data", {}).get("shamcash", [])
    except Exception as e:
        logger.error(f"ShamCash list_accounts error: {e}")
    return []


def get_active_account_id() -> Optional[str]:
    """يرجع account_address أول حساب ShamCash نشط."""
    addr = _get_address()
    if addr and addr not in ("", "ضع_رقم_التاجر_هنا"):
        return addr
    accounts = list_accounts()
    if accounts:
        return accounts[0].get("account_address")
    return None
