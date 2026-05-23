"""
عميل API لمتجر Fastcard / Ahminix.
وثائق: https://store.ahminix.com/api-docs/
"""
import logging
import uuid
from typing import Optional, Dict, Any, List

import requests

from . import config

logger = logging.getLogger(__name__)


class FastcardError(Exception):
    def __init__(self, message: str, code: Optional[int] = None, debug: str = ""):
        super().__init__(message)
        self.message = message
        self.code = code
        self.debug = debug  # تفاصيل RAW/SENT — للأدمن/اللوغ فقط، مش للزبون


# رسائل عربية مفهومة لأكواد Fastcard/Ahminix الرسمية
# المرجع: https://store.ahminix.com/api-docs/
_CODE_MESSAGES = {
    100: "رصيد المتجر غير كافٍ مؤقتاً — تواصل مع الدعم.",  # Insufficient balance (متجر Fastcard)
    105: "هذا العرض غير متوفر حالياً عند المتجر — جرّب عرض تاني.",  # Quantity not available
    106: "الكمية المطلوبة غير مسموحة لهذا العرض.",  # Quantity not allowed
    110: "هذا العرض غير متوفر حالياً عند المتجر — جرّب عرض تاني.",  # Fastcard custom: Product not available
    111: "هذا العرض غير متوفر حالياً عند المتجر — جرّب عرض تاني.",  # Fastcard custom
    112: "الكمية صغيرة جداً.",  # Quantity too small
    113: "الكمية أكبر من المسموح.",  # Quantity too large
    114: "بيانات الطلب غير صحيحة — تأكد من Player ID وأعد المحاولة.",  # Unknown/Invalid parameter
    120: "خلل بالتكامل مع المتجر — تواصل مع الدعم.",  # Api Token required (config issue)
    121: "خلل بالتكامل مع المتجر — تواصل مع الدعم.",  # Token error
    122: "خلل بالتكامل مع المتجر — تواصل مع الدعم.",  # Not allowed to use API
    123: "خلل بالتكامل مع المتجر — تواصل مع الدعم.",  # IP not allowed
    130: "المتجر بصيانة حالياً — جرّب بعد فترة.",  # Maintenance
    500: "خطأ مؤقت من المتجر — جرّب بعد دقيقة.",  # Unknown error
}


def _friendly(msg: str, code) -> str:
    """يحوّل رسالة المتجر الإنكليزية لرسالة عربية مفهومة حسب الكود."""
    try:
        c = int(code) if code is not None else None
    except (TypeError, ValueError):
        c = None
    if c in _CODE_MESSAGES:
        return _CODE_MESSAGES[c]
    return msg or "خطأ غير معروف من المتجر."


def is_enabled() -> bool:
    return bool(config.FASTCARD_TOKEN and config.FASTCARD_BASE)


def _headers() -> Dict[str, str]:
    return {"api-token": config.FASTCARD_TOKEN, "Accept": "application/json"}


def _url(path: str) -> str:
    base = config.FASTCARD_BASE.rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _request(method: str, path: str, *, params=None, data=None, timeout: int = 25) -> Any:
    if not is_enabled():
        raise FastcardError("Fastcard API غير مفعّل (FASTCARD_TOKEN فاضي)")
    try:
        r = requests.request(
            method,
            _url(path),
            headers=_headers(),
            params=params,
            data=data,
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise FastcardError(f"تعذّر الاتصال بالمتجر: {e}") from e

    if r.status_code in (401, 403):
        raise FastcardError(f"التوكن غير صحيح أو محظور (HTTP {r.status_code})", code=r.status_code)

    try:
        body = r.json()
    except ValueError:
        raise FastcardError(f"رد غير متوقع من المتجر (HTTP {r.status_code})", code=r.status_code)

    # شكل الخطأ النموذجي: {"status":"ERROR","code":100,"message":"..."}
    if isinstance(body, dict) and body.get("status") and body["status"] != "OK":
        msg = body.get("message") or body.get("error") or "خطأ غير معروف"
        code_raw = body.get("code")
        try:
            code = int(code_raw) if code_raw is not None else None
        except (TypeError, ValueError):
            code = code_raw
        # للتشخيص: نخزّن الـ RAW/SENT بحقل debug منفصل (للأدمن/اللوغ فقط، مش للزبون)
        import json as _json
        debug_str = ""
        try:
            debug_str = f"RAW={_json.dumps(body, ensure_ascii=False)[:300]}"
            if data:
                safe_sent = {k: ("***" if k.lower() in ("playerid", "player id") else v) for k, v in data.items()}
                debug_str += f" | SENT={_json.dumps(safe_sent, ensure_ascii=False)[:200]}"
        except Exception:
            pass
        logger.error(f"Fastcard error: msg={msg} code={code} body={body} sent={data}")
        # رسالة عربية مفهومة للزبون + debug منفصل
        friendly = _friendly(msg, code)
        raise FastcardError(friendly, code=code, debug=debug_str)

    return body


def get_profile() -> Dict[str, Any]:
    """يرجع رصيد المتجر والإيميل."""
    return _request("GET", "profile")


def get_products(product_ids: Optional[List[int]] = None, base_only: bool = False) -> List[Dict[str, Any]]:
    """يرجع قائمة منتجات Fastcard وأسعارها بالدولار.

    - product_ids: لو محدد، يرجع فقط هذه الـ IDs (لتقليل الحجم).
    - base_only: لو True، يرجع فقط id+name (سريع جداً).
    رد كل منتج: {id, name, price, params, category_name, available, qty_values, product_type, parent_id}
    """
    params: Dict[str, Any] = {}
    if product_ids:
        params["products_id"] = ",".join(str(int(p)) for p in product_ids)
    if base_only:
        params["base"] = "1"
    body = _request("GET", "products", params=params, timeout=40)
    if isinstance(body, list):
        return body
    return []


def new_order(product_id: int, *, player_id: Optional[str] = None, order_uuid: Optional[str] = None,
              qty=1, extra: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    ينشئ طلب جديد. idempotent عبر order_uuid.
    player_id اختياري (لمنتجات الستوك/الأكواد ما بنبعث playerId).
    qty يقبل int/float/str (لأن بعض منتجات Fastcard تستخدم قيم كسرية).
    رد نموذجي:
    {
      "status": "OK",
      "data": {
        "order_id": "ID_12345",
        "status": "processing"|"accept"|"reject"|...,
        "price": 0.9,
        "data": {"playerId": "..."},
        "replay_api": ["CODE_IF_ANY"]
      }
    }
    """
    if not order_uuid:
        order_uuid = str(uuid.uuid4())

    try:
        qty_num = float(qty)
        if qty_num <= 0 or qty_num != qty_num or qty_num == float("inf"):
            raise FastcardError("قيمة الكمية غير صالحة")
    except (TypeError, ValueError):
        raise FastcardError("قيمة الكمية غير صالحة")
    qty_str = str(int(qty_num)) if qty_num.is_integer() else str(qty)

    payload = {
        "qty": qty_str,
        "order_uuid": order_uuid,
    }
    if player_id:
        payload["playerId"] = player_id
    if extra:
        for k, v in extra.items():
            payload[k] = str(v)

    # التوثيق الرسمي بيستخدم query string (?qty=...&playerId=...&order_uuid=...)
    # مش form body — منتجات Server 2 صارمة وبتطلب query string فقط.
    try:
        body = _request("POST", f"newOrder/{int(product_id)}/params", params=payload)
    except FastcardError as e:
        # بعض منتجات "package" بترفض qty → نعيد المحاولة بدون qty
        if e.code == 500:
            payload_no_qty = {k: v for k, v in payload.items() if k != "qty"}
            new_uuid = str(uuid.uuid4())
            payload_no_qty["order_uuid"] = new_uuid
            try:
                body = _request("POST", f"newOrder/{int(product_id)}/params", params=payload_no_qty)
                order_uuid = new_uuid
            except FastcardError:
                # المحاولة 3: endpoint بدون /params
                new_uuid2 = str(uuid.uuid4())
                payload["order_uuid"] = new_uuid2
                body = _request("POST", f"newOrder/{int(product_id)}", params=payload)
                order_uuid = new_uuid2
        else:
            raise

    out = body.get("data") if isinstance(body, dict) else None
    if not isinstance(out, dict):
        raise FastcardError("رد غير متوقع من newOrder")
    out.setdefault("order_uuid", order_uuid)
    return out


def check_order(uuid_or_id: str, *, by_uuid: bool = True) -> Optional[Dict[str, Any]]:
    """
    يفحص حالة طلب. by_uuid=True للـ UUID، False للـ numeric id.
    يرجع الطلب أو None لو ما لقيناه.
    """
    if by_uuid:
        params = {"orders": f'["{uuid_or_id}"]', "uuid": "1"}
    else:
        params = {"orders": f"[{uuid_or_id}]"}

    body = _request("GET", "check", params=params)
    items = body.get("data") if isinstance(body, dict) else None
    if not items:
        return None
    return items[0]
