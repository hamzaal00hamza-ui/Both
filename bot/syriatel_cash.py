"""
Syriatel Cash API — عبر منصة API SYRIA
التوثيق: https://apisyria.com/api/docs

Endpoints:
  GET  resource=syriatel&action=balance      → رصيد الحساب
  GET  resource=syriatel&action=history      → سجل العمليات (period: 7|30|all)
  GET  resource=syriatel&action=find_tx      → البحث برقم العملية
  POST resource=syriatel&action=transfer_cash → تحويل كاش

المصادقة: Header "X-Api-Key: TOKEN"
"""
import hashlib
import logging
import time
from typing import Optional, Dict, Any, List

import requests

from . import config

logger = logging.getLogger(__name__)

API_BASE         = "https://apisyria.com/api/v1"
REQUEST_TIMEOUT  = 15
MAX_RETRIES      = 3
RETRY_BACKOFF    = 1.5
BALANCE_CACHE_TTL = 60

SYRIATEL_NAMESPACE_PREFIX = 10 ** 17

_balance_cache: Optional[tuple] = None


class SyriatelCashError(Exception):
    def __init__(self, code: str, message: str, data: Any = None):
        super().__init__(f"{code}: {message}")
        self.code    = code
        self.message = message
        self.data    = data


def _get_token() -> str:
    return getattr(config, "SYRIATEL_CASH_TOKEN", "")


def _get_number() -> str:
    return getattr(config, "SYRIATEL_CASH_NUMBER", "")


def is_enabled() -> bool:
    return (
        bool(getattr(config, "SYRIATEL_CASH_AUTO_VERIFY", False))
        and bool(_get_token())
        and _get_token() not in ("", "ضع_التوكن_هنا")
    )


def _request(params: Dict[str, Any]) -> Dict[str, Any]:
    """يرسل GET لـ API SYRIA مع إعادة محاولة تلقائية."""
    token = _get_token()
    if not token:
        raise SyriatelCashError("AUTH_MISSING", "SYRIATEL_CASH_TOKEN غير مضبوط")

    headers = {
        "X-Api-Key": token,
        "Accept":    "application/json",
    }

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(
                API_BASE,
                headers=headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.Timeout:
            last_err = SyriatelCashError("SERVICE_DOWN", "خدمة سيرياتيل كاش لا تستجيب")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF)
                continue
            raise last_err
        except requests.RequestException as e:
            last_err = SyriatelCashError("NETWORK", str(e))
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF)
                continue
            raise last_err

        if resp.status_code >= 500:
            last_err = SyriatelCashError("SERVICE_DOWN", f"HTTP {resp.status_code}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF)
                continue
            raise last_err

        break

    try:
        body = resp.json()
    except ValueError:
        raise SyriatelCashError("INVALID_JSON", f"Non-JSON (HTTP {resp.status_code})")

    if not body.get("success"):
        msg  = body.get("message", "")
        code = body.get("code", "API_ERROR")
        logger.warning(f"API SYRIA Syriatel error: {code} — {msg}")
        raise SyriatelCashError(code, msg or code, body.get("data"))

    return body.get("data") or {}


def _post(params: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """يرسل POST لـ API SYRIA."""
    token = _get_token()
    if not token:
        raise SyriatelCashError("AUTH_MISSING", "SYRIATEL_CASH_TOKEN غير مضبوط")

    headers = {
        "X-Api-Key":   token,
        "Accept":      "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        resp = requests.post(
            API_BASE,
            headers=headers,
            params=params,
            data=body,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        raise SyriatelCashError("NETWORK", str(e))

    try:
        result = resp.json()
    except ValueError:
        raise SyriatelCashError("INVALID_JSON", f"Non-JSON (HTTP {resp.status_code})")

    if not result.get("success"):
        msg  = result.get("message", "")
        code = result.get("code", "API_ERROR")
        raise SyriatelCashError(code, msg or code, result.get("data"))

    return result.get("data") or {}


# ─────────────────────────────────────────
# Balance
# ─────────────────────────────────────────
def get_balance(gsm: Optional[str] = None, use_cache: bool = True) -> float:
    """رصيد حساب Syriatel Cash بالليرة السورية."""
    global _balance_cache
    if use_cache and _balance_cache is not None:
        ts, cached = _balance_cache
        if time.time() - ts < BALANCE_CACHE_TTL:
            return cached

    q = gsm or _get_number()
    data = _request({
        "resource": "syriatel",
        "action":   "balance",
        "gsm":      q,
    })
    try:
        balance = float(data.get("balance", 0))
    except (TypeError, ValueError):
        balance = 0.0
    _balance_cache = (time.time(), balance)
    return balance


# ─────────────────────────────────────────
# History
# ─────────────────────────────────────────
def list_incoming(gsm: Optional[str] = None,
                   status: str = "success",
                   page: int = 1,
                   period: str = "7") -> List[Dict[str, Any]]:
    """
    يرجع سجل عمليات Syriatel Cash.
    period: '7' | '30' | 'all'
    """
    q = gsm or _get_number()
    data = _request({
        "resource": "syriatel",
        "action":   "history",
        "gsm":      q,
        "period":   period,
    })
    return data.get("items", []) or []


# ─────────────────────────────────────────
# Find transaction
# ─────────────────────────────────────────
def find_matching_transaction(tx_code: str,
                               expected_amount: float,
                               query: Optional[str] = None,
                               tolerance: float = 0.5,
                               period: str = "7",
                               max_pages: int = 3) -> Optional[Dict[str, Any]]:
    """
    يبحث عن عملية واردة برقم العملية tx_code ومبلغ متقارب.
    يرجع dict العملية أو None.
    """
    target = (tx_code or "").strip()
    if not target:
        return None

    q = query or _get_number()

    try:
        data = _request({
            "resource": "syriatel",
            "action":   "find_tx",
            "tx":       target,
            "gsm":      q,
            "period":   period,
        })
    except SyriatelCashError as e:
        logger.warning(f"find_tx error: {e}")
        return None

    logger.info(f"find_tx response: found={data.get('found')} data_keys={list(data.keys())}")

    if not data.get("found"):
        logger.info(f"Syriatel tx {target} NOT FOUND → رفض")
        return None

    tx = data.get("transaction", {})
    try:
        amount = float(tx.get("amount", 0))
    except (TypeError, ValueError):
        logger.warning(f"Syriatel tx {target} bad amount field: {tx.get('amount')}")
        return None

    if abs(amount - float(expected_amount)) > tolerance:
        logger.warning(
            f"Syriatel tx {target} amount mismatch: "
            f"got {amount} vs expected {expected_amount} → رفض"
        )
        return None

    logger.info(f"Syriatel tx {target} matched ✅ amount={amount}")
    return tx


# ─────────────────────────────────────────
# Transfer Cash
# ─────────────────────────────────────────
def transfer_cash(to_gsm: str,
                  amount: float,
                  pin_code: str,
                  gsm: Optional[str] = None) -> Dict[str, Any]:
    """يحوّل مبلغ من حساب Syriatel Cash المصدر إلى رقم مستفيد."""
    src = gsm or _get_number()
    return _post(
        params={"resource": "syriatel", "action": "transfer_cash"},
        body={
            "gsm":      src,
            "to_gsm":   to_gsm,
            "amount":   str(int(amount)),
            "pin_code": pin_code,
        },
    )


# ─────────────────────────────────────────
# Stable TX ID
# ─────────────────────────────────────────
def stable_tx_id(transaction_no: str) -> int:
    """يحوّل transaction_no لرقم 64-bit ثابت للحفظ في DB."""
    s = (transaction_no or "").strip().encode("utf-8")
    h = hashlib.sha256(s).digest()
    base = int.from_bytes(h[:7], "big")
    return SYRIATEL_NAMESPACE_PREFIX + base
