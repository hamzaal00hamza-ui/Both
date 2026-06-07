"""
Binance Pay — نظام إيداع USDT أوتوماتيكي
التوثيق: https://developers.binance.com/docs/binance-pay

الاستخدام:
  1. أضف للـ config.py:
       BINANCE_API_KEY    = os.environ.get("BINANCE_API_KEY", "")
       BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")
       BINANCE_PAY_AUTO   = os.environ.get("BINANCE_PAY_AUTO", "1") == "1"

  2. في handlers_user.py أضف:
       from .binance_pay import create_order, query_order, is_enabled as binance_enabled

  3. Webhook route في main.py أو webhook handler:
       POST /webhook/binance  →  handle_webhook(request)
"""
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Optional, Dict, Any

import requests

from . import config

logger = logging.getLogger(__name__)

BINANCE_PAY_BASE = "https://bpay.binanceapi.com"
REQUEST_TIMEOUT  = 15


class BinancePayError(Exception):
    def __init__(self, code: str, message: str, data: Any = None):
        super().__init__(f"{code}: {message}")
        self.code    = code
        self.message = message
        self.data    = data


def is_enabled() -> bool:
    return (
        getattr(config, "BINANCE_PAY_AUTO", False)
        and bool(getattr(config, "BINANCE_API_KEY", ""))
        and bool(getattr(config, "BINANCE_SECRET_KEY", ""))
    )


# ─────────────────────────────────────────
# Signature — HMAC-SHA512
# ─────────────────────────────────────────
def _sign(payload: str, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest().upper()


def _nonce() -> str:
    return uuid.uuid4().hex


# ─────────────────────────────────────────
# HTTP Helper
# ─────────────────────────────────────────
def _request(method: str, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    api_key    = getattr(config, "BINANCE_API_KEY", "")
    secret_key = getattr(config, "BINANCE_SECRET_KEY", "")

    if not api_key or not secret_key:
        raise BinancePayError("AUTH_MISSING", "BINANCE_API_KEY أو BINANCE_SECRET_KEY غير مضبوط")

    timestamp  = str(int(time.time() * 1000))
    nonce      = _nonce()
    body_str   = json.dumps(body, separators=(",", ":"))
    payload    = f"{timestamp}\n{nonce}\n{body_str}\n"
    signature  = _sign(payload, secret_key)

    headers = {
        "Content-Type":          "application/json",
        "BinancePay-Timestamp":  timestamp,
        "BinancePay-Nonce":      nonce,
        "BinancePay-Certificate-SN": api_key,
        "BinancePay-Signature":  signature,
    }

    url = BINANCE_PAY_BASE + path
    try:
        resp = requests.request(
            method, url,
            headers=headers,
            data=body_str,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        raise BinancePayError("NETWORK", str(e))

    try:
        data = resp.json()
    except ValueError:
        raise BinancePayError("INVALID_JSON", f"HTTP {resp.status_code}")

    status = data.get("status")
    code   = data.get("code", "UNKNOWN")

    if status != "SUCCESS":
        msg = data.get("errorMessage", code)
        logger.warning(f"Binance Pay error {code}: {msg}")
        raise BinancePayError(code, msg, data.get("data"))

    return data.get("data") or {}


# ─────────────────────────────────────────
# Create Order — إنشاء طلب دفع
# ─────────────────────────────────────────
def create_order(amount_usdt: float,
                 merchant_trade_no: Optional[str] = None,
                 description: str = "إيداع رصيد GameZone",
                 buyer_id: Optional[str] = None) -> Dict[str, Any]:
    """
    ينشئ طلب دفع Binance Pay ويرجع:
      - prepayId:    معرّف الطلب للتتبع
      - checkoutUrl: رابط الدفع (يفتحه المستخدم)
      - qrcodeLink:  QR Code للدفع
      - expireTime:  وقت انتهاء الطلب (milliseconds)

    amount_usdt: المبلغ بالدولار (USDT)
    merchant_trade_no: رقم فريد للطلب (يتولد تلقائياً لو فارغ)
    buyer_id: معرّف المشتري (اختياري — Telegram user_id مثلاً)
    """
    trade_no = merchant_trade_no or uuid.uuid4().hex[:32]

    body: Dict[str, Any] = {
        "env":             {"terminalType": "APP"},
        "merchantTradeNo": trade_no,
        "orderAmount":     round(float(amount_usdt), 8),
        "currency":        "USDT",
        "description":     description,
        "goodsDetails": [{
            "goodsType":        "01",
            "goodsCategory":    "D000",
            "referenceGoodsId": trade_no,
            "goodsName":        description,
        }],
    }

    if buyer_id:
        body["buyer"] = {"referenceBuyerId": str(buyer_id)}

    data = _request("POST", "/binancepay/openapi/v3/order", body)
    data["merchantTradeNo"] = trade_no
    logger.info(f"Binance Pay order created: {trade_no} — ${amount_usdt} USDT")
    return data


# ─────────────────────────────────────────
# Query Order — استعلام عن حالة الطلب
# ─────────────────────────────────────────
def query_order(merchant_trade_no: str) -> Dict[str, Any]:
    """
    يسأل عن حالة طلب بـ merchantTradeNo.
    الحالات الممكنة:
      INITIAL     → في الانتظار
      PENDING     → بدأ الدفع
      PAID        → ✅ تم الدفع
      CANCELED    → ملغي
      ERROR       → خطأ
      REFUNDING   → استرداد
      REFUNDED    → مسترد
    """
    data = _request("POST", "/binancepay/openapi/v3/order/query", {
        "merchantTradeNo": merchant_trade_no,
    })
    return data


def is_paid(merchant_trade_no: str) -> bool:
    """يرجع True لو الطلب مدفوع."""
    try:
        data = query_order(merchant_trade_no)
        return data.get("status") == "PAID"
    except BinancePayError:
        return False


# ─────────────────────────────────────────
# Close Order — إلغاء طلب
# ─────────────────────────────────────────
def close_order(merchant_trade_no: str) -> bool:
    """يلغي طلب دفع لم يُنفَّذ بعد."""
    try:
        _request("POST", "/binancepay/openapi/v3/order/close", {
            "merchantTradeNo": merchant_trade_no,
        })
        return True
    except BinancePayError as e:
        logger.warning(f"Close order failed: {e}")
        return False


# ─────────────────────────────────────────
# Webhook Verification — التحقق من الإشعار
# ─────────────────────────────────────────
def verify_webhook(payload: str, timestamp: str, nonce: str, signature: str) -> bool:
    """
    يتحقق من صحة Webhook القادم من Binance Pay.
    استدعه قبل معالجة أي إشعار.

    payload:   نص الـ body كاملاً
    timestamp: من header BinancePay-Timestamp
    nonce:     من header BinancePay-Nonce
    signature: من header BinancePay-Signature
    """
    secret_key = getattr(config, "BINANCE_SECRET_KEY", "")
    if not secret_key:
        logger.error("BINANCE_SECRET_KEY غير مضبوط — لا يمكن التحقق من Webhook")
        return False

    expected = f"{timestamp}\n{nonce}\n{payload}\n"
    expected_sig = _sign(expected, secret_key)
    return hmac.compare_digest(expected_sig, signature.upper())


def parse_webhook(body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    يحلّل body الـ Webhook ويرجع بيانات الدفع أو None.

    يرجع dict يحتوي:
      merchantTradeNo, totalFee, currency, transactionId, status
    """
    biz_type   = body.get("bizType", "")
    biz_status = body.get("bizStatus", "")

    if biz_type != "PAY" or biz_status != "PAY_SUCCESS":
        return None

    try:
        data = json.loads(body.get("data", "{}"))
    except (json.JSONDecodeError, TypeError):
        return None

    return {
        "merchantTradeNo": data.get("merchantTradeNo"),
        "totalFee":        float(data.get("totalFee", 0)),
        "currency":        data.get("currency", "USDT"),
        "transactionId":   data.get("transactionId"),
        "status":          "PAID",
    }


# ─────────────────────────────────────────
# Poll Order (بديل Webhook للسيرفرات بدون endpoint)
# ─────────────────────────────────────────
def poll_until_paid(merchant_trade_no: str,
                    timeout_seconds: int = 600,
                    interval_seconds: int = 5) -> bool:
    """
    يستعلم عن الطلب كل interval_seconds حتى يُدفع أو ينتهي الوقت.
    استخدمه في thread منفصل أو asyncio.to_thread.
    يرجع True لو دُفع، False لو انتهى الوقت.
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            if is_paid(merchant_trade_no):
                logger.info(f"Binance Pay order PAID: {merchant_trade_no}")
                return True
        except BinancePayError as e:
            logger.warning(f"Poll error: {e}")
        time.sleep(interval_seconds)
    logger.info(f"Binance Pay order timeout: {merchant_trade_no}")
    return False
