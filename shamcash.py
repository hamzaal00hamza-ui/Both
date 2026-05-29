"""
عميل ShamCash API — عبر منصة API SYRIA
التوثيق: https://apisyria.com/api/docs

نقاط النهاية المستخدمة:
  GET resource=shamcash&action=balance   → رصيد الحساب
  GET resource=shamcash&action=logs      → سجل التحويلات
  GET resource=shamcash&action=find_tx   → البحث برقم العملية

المصادقة: Header "X-Api-Key: YOUR_KEY"
"""
import logging
from typing import Optional, Dict, Any, List

import requests

from . import config


# ─────────────────────────────────────────
# Constants — متوافقة مع الكود القديم
# ─────────────────────────────────────────
COIN_SYP = "SYP"
COIN_USD = "USD"
COIN_EUR = "EUR"


logger = logging.getLogger(__name__)

API_BASE        = "https://apisyria.com/api/v1"
REQUEST_TIMEOUT = 20


class ShamCashError(Exception):
    def __init__(self, code: str, message: str, data: Any = None):
        super().__init__(f"{code}: {message}")
        self.code    = code
        self.message = message
        self.data    = data


def _enabled() -> bool:
    return (
        bool(config.SHAMCASH_AUTO_VERIFY)
        and bool(config.SHAMCASH_TOKEN)
        and config.SHAMCASH_TOKEN not in ("", "ضع_التوكن_هنا")
    )


def is_enabled() -> bool:
    return _enabled()


def _request(params: Dict[str, Any]) -> Dict[str, Any]:
    """يرسل GET لـ API SYRIA ويرجع data أو يرفع ShamCashError."""
    if not config.SHAMCASH_TOKEN:
        raise ShamCashError("AUTH_MISSING", "SHAMCASH_TOKEN غير مضبوط")

    headers = {
        "X-Api-Key": config.SHAMCASH_TOKEN,
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
    """
    يرجع قائمة أرصدة حساب ShamCash.
    كل عنصر: {currency, balance}
    """
    addr = account_address or config.SHAMCASH_WALLET_CODE
    data = _request({
        "resource":        "shamcash",
        "action":          "balance",
        "account_address": addr,
    })
    return data.get("balances", []) or []


def get_syp_balance(account_address: Optional[str] = None) -> float:
    """يرجع رصيد الليرة السورية فقط."""
    balances = get_balances(account_address)
    for b in balances:
        if b.get("currency") == "SYP":
            try:
                return float(b.get("balance", 0))
            except (TypeError, ValueError):
                return 0.0
    return 0.0


# ─────────────────────────────────────────
# Logs (سجل التحويلات)
# ─────────────────────────────────────────
def list_transactions(account_address: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    يرجع سجل تحويلات ShamCash.
    كل عنصر: {tran_id, from_name, to_name, currency, amount, datetime, account, note}
    """
    addr = account_address or config.SHAMCASH_WALLET_CODE
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
                               # معاملات قديمة للتوافق مع الكود السابق
                               window_minutes: int = 30,
                               coin_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    يبحث عن عملية ShamCash برقم العملية tran_id ومبلغ متقارب.
    account_id: رقم العملية كما يظهر في تطبيق شام كاش.
    window_minutes: مُهمَل في API الجديد (محفوظ للتوافق).
    coin_id: عملة البحث — COIN_SYP أو COIN_USD (للتوافق، لا يؤثر حالياً).
    يرجع dict العملية أو None.
    """
    target = str(account_id or "").strip()
    if not target:
        return None

    addr = account_address or config.SHAMCASH_WALLET_CODE

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

    # التحقق من العملة — نقبل SYP فقط
    currency = str(tx.get("currency", "")).upper()
    if currency and currency != "SYP":
        logger.warning(f"ShamCash tx {target}: unexpected currency {currency}")
        return None

    if abs(amount - float(expected_amount)) > tolerance:
        logger.warning(
            f"ShamCash tx {target} found but amount mismatch: "
            f"got {amount} vs expected {expected_amount}"
        )
        return None

    return tx


# Backward compat — الكود القديم كان يستدعي list_transactions بـ account_id
def list_accounts() -> List[Dict[str, Any]]:
    """يرجع لائحة حسابات ShamCash المرتبطة (من resource=accounts)."""
    if not config.SHAMCASH_TOKEN:
        return []
    try:
        headers = {
            "X-Api-Key": config.SHAMCASH_TOKEN,
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
    if config.SHAMCASH_WALLET_CODE and config.SHAMCASH_WALLET_CODE not in ("", "ضع_رقم_التاجر_هنا"):
        return config.SHAMCASH_WALLET_CODE
    accounts = list_accounts()
    if accounts:
        return accounts[0].get("account_address")
    return None
