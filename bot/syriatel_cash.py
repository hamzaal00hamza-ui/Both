"""
عميل Syriatel Cash API (https://api.melchersman.com/syr-cash/v1)
حسب التوثيق الرسمي على https://api.melchersman.com/syr-cash/api-docs

نقاط مهمة:
- الـ Auth: Header `api-token: <TOKEN>`
- Rate limit: 2 طلبات/دقيقة لكل رقم
- /IncomingHistory يرجع المعاملات الواردة، نفلتر بـ transaction_no + amount + status="1"
- transaction_no نص (مثل "TXN123456") — نحوّله لرقم 64-bit عبر hash مستقر
  مع prefix لتفادي التصادم مع transaction_id العددي لـ ShamCash
- get_balance() محفوظ بـ cache 60 ثانية لتقليل استهلاك rate limit
"""
import hashlib
import logging
import time
from typing import Optional, Dict, Any, List, Tuple

import requests

from . import config

logger = logging.getLogger(__name__)

SYRIATEL_NAMESPACE_PREFIX = 10 ** 17
REQUEST_TIMEOUT = 15  # ثانية لكل محاولة — قصيرة لنعيد المحاولة بدلاً من الانتظار طويلاً
MAX_RETRIES = 3       # عدد المحاولات الإجمالي عند TIMEOUT/NETWORK
RETRY_BACKOFF = 1.5   # ثانية بين المحاولات
BALANCE_CACHE_TTL = 60  # ثانية — لتجنّب استهلاك rate limit عند زر الأدمن

_balance_cache: Optional[Tuple[float, float]] = None  # (timestamp, balance)


class SyriatelCashError(Exception):
    def __init__(self, code: str, message: str, data: Any = None):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.data = data


def _enabled() -> bool:
    return (
        bool(config.SYRIATEL_CASH_AUTO_VERIFY)
        and bool(config.SYRIATEL_CASH_TOKEN)
        and config.SYRIATEL_CASH_TOKEN not in ("", "ضع_التوكن_هنا")
    )


def is_enabled() -> bool:
    return _enabled()


def _request(method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    يطلب من API مع إعادة محاولة تلقائية عند TIMEOUT/NETWORK.
    لا يعيد المحاولة عند RATE_LIMIT أو SUBSCRIPTION_EXPIRED (لا فائدة).
    """
    if not config.SYRIATEL_CASH_TOKEN:
        raise SyriatelCashError("AUTH_MISSING", "SYRIATEL_CASH_TOKEN غير مضبوط")
    url = f"{config.SYRIATEL_CASH_API_URL.rstrip('/')}{path}"
    headers = {
        "api-token": config.SYRIATEL_CASH_TOKEN,
        "Accept": "application/json",
    }
    
    last_err: Optional[SyriatelCashError] = None
    resp = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        except requests.Timeout as e:
            last_err = SyriatelCashError("SERVICE_DOWN", "خدمة سرياتيل كاش لا تستجيب")
            logger.warning(f"Syriatel Cash timeout (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF)
                continue
            raise last_err
        except requests.RequestException as e:
            last_err = SyriatelCashError("NETWORK", str(e))
            logger.warning(f"Syriatel Cash network error (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF)
                continue
            raise last_err
        
        # تحقّق من 5xx (سيرفر API ساقط — مثل 502/503/504)
        if resp.status_code >= 500:
            last_err = SyriatelCashError(
                "SERVICE_DOWN",
                f"خادم سرياتيل كاش معطّل (HTTP {resp.status_code})"
            )
            logger.warning(
                f"Syriatel Cash server error {resp.status_code} (attempt {attempt}/{MAX_RETRIES})"
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF)
                continue
            raise last_err
        
        # نجح الاتصال — اخرج من اللوب
        break
    
    if resp is None:
        # نظرياً لا يحدث، لكن للسلامة
        raise last_err or SyriatelCashError("UNKNOWN", "خطأ غير معروف")
    
    try:
        body = resp.json()
    except ValueError:
        raise SyriatelCashError("INVALID_JSON", f"Non-JSON response (HTTP {resp.status_code})")

    success = body.get("success")
    code = body.get("code", "UNKNOWN")
    data = body.get("data") or {}
    message = data.get("message", "") if isinstance(data, dict) else ""

    if not success:
        logger.warning(f"Syriatel Cash error {code}: {message}")
        raise SyriatelCashError(code, message or code, data)

    return data if isinstance(data, dict) else {}


def get_balance(query: Optional[str] = None, use_cache: bool = True) -> float:
    """
    رصيد محفظة سرياتيل كاش الحالية.
    
    use_cache: لو True (الافتراضي)، يستخدم نتيجة محفوظة لمدة 60 ثانية لتجنّب
    استهلاك rate limit. مفيد لزر الأدمن لأن الرصيد لا يتغير بسرعة.
    """
    global _balance_cache
    if use_cache and _balance_cache is not None:
        ts, cached = _balance_cache
        if time.time() - ts < BALANCE_CACHE_TTL:
            return cached
    
    q = query or config.SYRIATEL_CASH_NUMBER
    data = _request("GET", "/Balance", params={"query": q})
    try:
        balance = float(data.get("balance", 0))
    except (TypeError, ValueError):
        balance = 0.0
    _balance_cache = (time.time(), balance)
    return balance


def list_incoming(query: Optional[str] = None,
                  status: str = "success",
                  page: int = 1) -> List[Dict[str, Any]]:
    """
    يرجع لائحة المعاملات الواردة (deposits) من Syriatel Cash.
    يتعامل مع FETCH_FAILED (no data found) كصفحة فارغة (سلوك طبيعي عند نهاية الصفحات).
    """
    q = query or config.SYRIATEL_CASH_NUMBER
    params: Dict[str, Any] = {"query": q, "status": status}
    if page and page > 1:
        params["page"] = page
    try:
        data = _request("GET", "/IncomingHistory", params=params)
    except SyriatelCashError as e:
        # FETCH_FAILED مع "no data" = نهاية الصفحات أو لا معاملات أصلاً، ليس خطأ
        if e.code == "FETCH_FAILED":
            return []
        raise
    txs = data.get("transactions") if isinstance(data, dict) else None
    return txs or []


def find_matching_transaction(tx_code: str,
                               expected_amount: float,
                               query: Optional[str] = None,
                               tolerance: float = 0.5,
                               max_pages: int = 3) -> Optional[Dict[str, Any]]:
    """
    يبحث عن معاملة واردة بنفس رقم العملية tx_code (transaction_no) ومبلغ مطابق
    عبر صفحات /IncomingHistory. يرجع المعاملة (dict) أو None.
    
    ملاحظة: لا نُنهي البحث عند أول mismatch لرقم مكرر — نُكمل لكل
    السجلات حتى الصفحة الأخيرة لتجنّب false-negatives.
    
    tolerance: فرق مسموح به بين amount المرسل والـ expected (نصف ل.س للأمان).
    """
    target = (tx_code or "").strip().upper()
    if not target:
        return None
    
    last_mismatch_log = None
    for page in range(1, max_pages + 1):
        try:
            txs = list_incoming(query=query, status="success", page=page)
        except SyriatelCashError:
            raise
        if not txs:
            break
        
        for tx in txs:
            tx_no = str(tx.get("transaction_no", "")).strip().upper()
            if tx_no != target:
                continue
            try:
                amount = float(tx.get("amount", 0))
            except (TypeError, ValueError):
                continue
            status = str(tx.get("status", "")).strip()
            if status != "1":
                last_mismatch_log = f"tx {tx_no} found but status={status}"
                continue
            if abs(amount - float(expected_amount)) > tolerance:
                last_mismatch_log = (
                    f"tx {tx_no} found but amount mismatch: "
                    f"got {amount} vs expected {expected_amount}"
                )
                continue
            return tx
        
        if len(txs) < 10:
            break
    
    if last_mismatch_log:
        logger.warning(f"Syriatel Cash search ended unmatched: {last_mismatch_log}")
    return None


def stable_tx_id(transaction_no: str) -> int:
    """
    يحوّل transaction_no النصي لرقم 64-bit ثابت لتخزينه في consumed_transactions
    (الجدول transaction_id INTEGER PRIMARY KEY).
    نضيف prefix لتجنب التصادم مع IDs العددية من شام كاش.
    """
    s = (transaction_no or "").strip().upper().encode("utf-8")
    h = hashlib.sha256(s).digest()
    base = int.from_bytes(h[:7], "big")
    return SYRIATEL_NAMESPACE_PREFIX + base
