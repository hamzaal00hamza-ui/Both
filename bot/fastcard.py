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
    def __init__(self, message: str, code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.code = code


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
        code = body.get("code")
        raise FastcardError(f"خطأ من المتجر: {msg} (code={code})", code=code)

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

    body = _request("POST", f"newOrder/{int(product_id)}/params", data=payload)
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
