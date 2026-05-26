"""
Fastcard Website Client (لتحقق من اسم اللاعب)

seller API ما بتدعم redeemtech_check_player. هاد الموديول بيعمل تسجيل دخول
عادي بالاسم وكلمة السر ويستعمل الـ session cookie ليستدعي:
    POST /api/redeemtech_check_player.php
    body: player_id=<id>&product_id=<pid>
    response: {"success": bool, "message": str, "data": {...}}
"""
import logging
import threading
from typing import Optional, Dict, Any

import requests

from . import config

logger = logging.getLogger(__name__)

_session: Optional[requests.Session] = None
_lock = threading.Lock()
_UA = ("Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36")


class FastcardWebError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def is_enabled() -> bool:
    return bool(config.FASTCARD_WEB_USERNAME and config.FASTCARD_WEB_PASSWORD)


def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": _UA,
        "Accept-Language": "ar,en;q=0.9",
        "Referer": config.FASTCARD_WEB_BASE + "/",
    })
    return s


def _login(s: requests.Session) -> None:
    base = config.FASTCARD_WEB_BASE.rstrip("/")
    # نزور صفحة login لجلب PHPSESSID
    try:
        s.get(base + "/login", timeout=15)
    except Exception as e:
        raise FastcardWebError(f"web login GET failed: {e}")
    try:
        r = s.post(
            base + "/login",
            data={"username": config.FASTCARD_WEB_USERNAME,
                  "password": config.FASTCARD_WEB_PASSWORD},
            allow_redirects=True,
            timeout=20,
        )
    except Exception as e:
        raise FastcardWebError(f"web login POST failed: {e}")
    # بنجاح الدخول الموقع غالباً يحوّل لـ home. بنتأكد بزيارة صفحة محمية.
    if r.status_code >= 500:
        raise FastcardWebError(f"web login server error {r.status_code}")
    body = (r.text or "").lower()
    if "login" in r.url.lower() and ("name=\"password\"" in body or "كلمة" in (r.text or "")):
        raise FastcardWebError("بيانات تسجيل الدخول إلى موقع فاست كارد غير صحيحة")


def _get_session(force_relogin: bool = False) -> requests.Session:
    global _session
    with _lock:
        if force_relogin or _session is None:
            _session = _new_session()
            _login(_session)
        return _session


def check_player(player_id: str, product_id: int) -> Dict[str, Any]:
    """يرجّع dict فيه success/message/data. data بتحتوي اسم اللاعب لو success=True."""
    if not is_enabled():
        raise FastcardWebError("تحقق الاسم غير مفعّل (مفاتيح الموقع ناقصة)")

    url = config.FASTCARD_WEB_BASE.rstrip("/") + "/api/redeemtech_check_player.php"
    payload = {"player_id": str(player_id), "product_id": int(product_id)}

    for attempt in (1, 2):
        s = _get_session(force_relogin=(attempt == 2))
        try:
            r = s.post(url, data=payload, timeout=25,
                       headers={"X-Requested-With": "XMLHttpRequest"})
        except Exception as e:
            if attempt == 2:
                raise FastcardWebError(f"تعذّر الاتصال بالموقع: {e}")
            continue

        try:
            data = r.json()
        except Exception:
            text = (r.text or "")[:200]
            if attempt == 2:
                raise FastcardWebError(f"رد غير متوقع من الموقع: {text}")
            continue

        msg = str(data.get("message") or "")
        if not data.get("success") and ("تسجيل الدخول" in msg or "login" in msg.lower()):
            # session منتهية → أعِد المحاولة بعد إعادة الدخول
            if attempt == 1:
                continue
        return data

    raise FastcardWebError("فشل الاتصال بعد محاولتين")


def place_order(product_id: int, player_id: str, quantity: int = 1) -> Dict[str, Any]:
    """
    ينفّذ الطلب عبر endpoint الموقع نفسه (وليس seller API).
    هاد الـ endpoint هو اللي بيستعملو الموقع وبيوصل تلقائي خلال ثوانٍ.
        POST /api/order-handler.php
        body: product_id, quantity, player_id
    """
    if not is_enabled():
        raise FastcardWebError("الطلب عبر الموقع غير مفعّل (مفاتيح الموقع ناقصة)")

    # حظر يدوي من الأدمن لهذا المنتج
    try:
        from . import database as _db
        if _db.is_product_disabled(int(product_id)):
            raise FastcardWebError("هذا المنتج موقوف مؤقتاً — جرّب لاحقاً أو تواصل مع الدعم.")
    except FastcardWebError:
        raise
    except Exception:
        pass

    url = config.FASTCARD_WEB_BASE.rstrip("/") + "/api/order-handler.php"
    payload = {
        "product_id": int(product_id),
        "quantity": int(quantity),
        "player_id": str(player_id),
    }

    for attempt in (1, 2):
        s = _get_session(force_relogin=(attempt == 2))
        try:
            r = s.post(url, data=payload, timeout=60,
                       headers={"X-Requested-With": "XMLHttpRequest"})
        except Exception as e:
            if attempt == 2:
                raise FastcardWebError(f"تعذّر الاتصال بالموقع: {e}")
            continue

        raw = (r.text or "")
        logger.info(f"fastcard_web.place_order status={r.status_code} body={raw[:500]}")

        # محاولة قراءة JSON أولاً
        try:
            data = r.json()
            msg = str(data.get("message") or "")
            if not data.get("success") and ("تسجيل الدخول" in msg or "login" in msg.lower()):
                if attempt == 1:
                    continue
            return data
        except Exception:
            pass

        # الرد HTML — نحلّلو بكلمات مفتاحية
        low = raw.lower()
        # علامات تسجيل خروج → أعد المحاولة مع تسجيل دخول جديد
        if attempt == 1 and ("login" in low or "تسجيل الدخول" in raw) and "order-result" not in low:
            continue

        # كلمات نجاح بالعربي/الإنجليزي
        success_kw = ["نجح", "تم تنفيذ", "بنجاح", "تمت", "success", "delivered", "completed", "approved"]
        fail_kw = ["فشل", "خطأ", "غير صحيح", "غير كاف", "رصيد", "failed", "error", "invalid", "insufficient"]

        is_success = any(k in raw for k in success_kw[:4]) or any(k in low for k in success_kw[4:])
        is_fail = any(k in raw for k in fail_kw[:5]) or any(k in low for k in fail_kw[5:])

        # افتراضياً: لو الـ HTTP 200 وفي order-result بدون كلمات فشل صريحة → اعتبرو ناجح
        if r.status_code == 200 and not is_fail:
            is_success = True

        # ملخص نصّي مختصر
        import re
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()[:300]

        return {
            "success": bool(is_success and not is_fail),
            "message": text or ("تم بنجاح" if is_success else "فشل"),
            "_html": True,
        }

    raise FastcardWebError("فشل الاتصال بعد محاولتين")


def extract_player_name(resp: Dict[str, Any]) -> Optional[str]:
    """يحاول يستخرج اسم اللاعب من الرد بعدة مفاتيح شائعة."""
    if not resp or not resp.get("success"):
        return None
    data = resp.get("data") or {}
    if isinstance(data, str):
        return data.strip() or None
    if isinstance(data, dict):
        for k in ("name", "player_name", "nickname", "username", "playerName", "nick"):
            v = data.get(k)
            if v:
                return str(v).strip()
        # لو الرد فيه مفتاح واحد فقط بقيمة نصية
        if len(data) == 1:
            v = next(iter(data.values()))
            if isinstance(v, str) and v.strip():
                return v.strip()
    msg = resp.get("message")
    if isinstance(msg, str) and msg.strip():
        return msg.strip()
    return None
