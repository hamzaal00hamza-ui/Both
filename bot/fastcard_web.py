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
