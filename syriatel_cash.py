"""
عميل Syriatel Cash API — عبر منصة API SYRIA
التوثيق: https://apisyria.com/api/docs

نقاط النهاية المستخدمة:
  GET  resource=syriatel&action=balance      → رصيد الحساب
  GET  resource=syriatel&action=history      → سجل العمليات
  GET  resource=syriatel&action=find_tx      → البحث برقم العملية
  POST resource=syriatel&action=transfer_cash → تحويل كاش
  POST resource=syriatel&action=mobile_recharge → شحن رصيد موبايل

المصادقة: Header "X-Api-Key: YOUR_KEY" أو query param api_key
"""
import hashlib
import logging
import time
from typing import Optional, Dict, Any, List

import requests

from . import config

logger = logging.getLogger(__name__)

# Namespace prefix لتمييز IDs سيرياتيل عن شام كاش في consumed_transactions
SYRIATEL_NAMESPACE_PREFIX = 10 ** 17

REQUEST_TIMEOUT  = 15
MAX_RETRIES      = 3
RETRY_BACKOFF    = 1.5
BALANCE_CACHE_TTL = 60  # ثانية

_balance_cache: Optional[tuple] = None  # (timestamp, balance)

API_BASE = "https://apisyria.com/api/v1"


class SyriatelCashError(Exception):
    def __init__(self, code: str, message: str, data: Any = None):
        super().__init__(f"{code}: {message}")
        self.code    = code
        self.message = message
        self.data    = data


def _enabled() -> bool:
    return (
        bool(config.SYRIATEL_CASH_AUTO_VERIFY)
        and bool(config.SYRIATEL_CASH_TOKEN)
        and config.SYRIATEL_CASH_TOKEN not in ("", "ضع_التوكن_هنا")
    )


def is_enabled() -> bool:
    return _enabled()


def _request(method: str,
             params: Optional[Dict[str, Any]] = None,
             data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    يرسل طلباً لـ API SYRIA مع إعادة محاولة تلقائية.
    - GET  → params في query string
    - POST → data في body (x-www-form-urlencoded)
    """
    if not config.SYRIATEL_CASH_TOKEN:
        raise SyriatelCashError("AUTH_MISSING", "SYRIATEL_CASH_TOKEN غير مضبوط")

    headers = {
        "X-Api-Key": config.SYRIATEL_CASH_TOKEN,
        "Accept":    "application/json",
    }

    last_err: Optional[SyriatelCashError] = None
    resp = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if method.upper() == "POST":
                resp = requests.post(
                    API_BASE,
                    headers=headers,
                    params=params,
                    data=data,
                    timeout=REQUEST_TIMEOUT,
                )
            else:
                resp = requests.get(
                    API_BASE,
                    headers=headers,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
        except requests.Timeout:
            last_err = SyriatelCashError("SERVICE_DOWN", "خدمة سيرياتيل كاش لا تستجيب")
            logger.warning(f"Syriatel timeout (attempt {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF)
                continue
            raise last_err
        except requests.RequestException as e:
            last_err = SyriatelCashError("NETWORK", str(e))
            logger.warning(f"Syriatel network error (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF)
                continue
            raise last_err

        if resp.status_code >= 500:
            last_err = SyriatelCashError(
                "SERVICE_DOWN",
                f"خادم API SYRIA معطّل (HTTP {resp.status_code})"
            )
            logger.warning(f"API SYRIA server error {resp.status_code} (attempt {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF)
                continue
            raise last_err

        break  # نجح الاتصال

    if resp is None:
        raise last_err or SyriatelCashError("UNKNOWN", "خطأ غير معروف")

    try:
        body = resp.json()
    except ValueError:
        raise SyriatelCashError("INVALID_JSON", f"Non-JSON response (HTTP {resp.status_code})")

    if not body.get("success"):
        msg  = body.get("message", "")
        code = body.get("code", "API_ERROR")
        logger.warning(f"API SYRIA Syriatel error: {code} — {msg}")
        raise SyriatelCashError(code, msg or code, body.get("data"))

    return body.get("data") or {}


# ─────────────────────────────────────────
# Balance
# ─────────────────────────────────────────
def get_balance(gsm: Optional[str] = None, use_cache: bool = True) -> float:
    """رصيد حساب Syriatel Cash (بالليرة السورية)."""
    global _balance_cache
    if use_cache and _balance_cache is not None:
        ts, cached = _balance_cache
        if time.time() - ts < BALANCE_CACHE_TTL:
            return cached

    q = gsm or config.SYRIATEL_CASH_NUMBER
    data = _request("GET", params={
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
def list_incoming(gsm: Optional[str] = None, period: str = "7") -> List[Dict[str, Any]]:
    """
    يرجع سجل عمليات Syriatel Cash.
    period: '7' | '30' | 'all'
    كل عنصر: {transaction_no, date, from, to, amount}
    """
    q = gsm or config.SYRIATEL_CASH_NUMBER
    data = _request("GET", params={
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
                               gsm: Optional[str] = None,
                               tolerance: float = 0.5,
                               period: str = "7") -> Optional[Dict[str, Any]]:
    """
    يبحث عن عملية واردة برقم العملية tx_code ومبلغ متقارب.
    يستخدم نقطة find_tx لبحث سريع ودقيق.
    يرجع dict العملية أو None.
    """
    target = (tx_code or "").strip()
    if not target:
        return None

    q = gsm or config.SYRIATEL_CASH_NUMBER

    try:
        data = _request("GET", params={
            "resource": "syriatel",
            "action":   "find_tx",
            "tx":       target,
            "gsm":      q,
            "period":   period,
        })
    except SyriatelCashError as e:
        logger.warning(f"find_tx error: {e}")
        return None

    if not data.get("found"):
        return None

    tx = data.get("transaction", {})
    try:
        amount = float(tx.get("amount", 0))
    except (TypeError, ValueError):
        return None

    if abs(amount - float(expected_amount)) > tolerance:
        logger.warning(
            f"Syriatel tx {target} found but amount mismatch: "
            f"got {amount} vs expected {expected_amount}"
        )
        return None

    return tx


# ─────────────────────────────────────────
# Transfer Cash (تحويل كاش)
# ─────────────────────────────────────────
def transfer_cash(to_gsm: str,
                  amount: float,
                  pin_code: str,
                  gsm: Optional[str] = None) -> Dict[str, Any]:
    """
    يحوّل مبلغ من حساب Syriatel Cash المصدر إلى رقم مستفيد.
    يرجع بيانات العملية أو يرفع SyriatelCashError.
    """
    src = gsm or config.SYRIATEL_CASH_NUMBER
    data = _request("POST",
        params={"resource": "syriatel", "action": "transfer_cash"},
        data={
            "gsm":      src,
            "to_gsm":   to_gsm,
            "amount":   str(int(amount)),
            "pin_code": pin_code,
        },
    )
    return data


# ─────────────────────────────────────────
# Mobile Recharge (شحن رصيد موبايل)
# ─────────────────────────────────────────
def mobile_recharge(target_gsm: str,
                    category: str,
                    pin_code: str,
                    gsm: Optional[str] = None) -> Dict[str, Any]:
    """
    يشحن رصيد موبايل Syriatel (مسبق الدفع).
    category: إحدى القيم المدعومة مثل '9.61', '20.19', ...
    """
    src = gsm or config.SYRIATEL_CASH_NUMBER
    data = _request("POST",
        params={"resource": "syriatel", "action": "mobile_recharge"},
        data={
            "gsm":        src,
            "target_gsm": target_gsm,
            "category":   category,
            "pin_code":   pin_code,
        },
    )
    return data


# ─────────────────────────────────────────
# Stable TX ID (للحفظ في DB)
# ─────────────────────────────────────────
def stable_tx_id(transaction_no: str) -> int:
    """
    يحوّل transaction_no النصي لرقم 64-bit ثابت
    لتخزينه في consumed_transactions.
    """
    s = (transaction_no or "").strip().encode("utf-8")
    h = hashlib.sha256(s).digest()
    base = int.from_bytes(h[:7], "big")
    return SYRIATEL_NAMESPACE_PREFIX + base
