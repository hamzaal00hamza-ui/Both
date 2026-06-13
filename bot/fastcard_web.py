import os
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
import re as _re2

from . import config



def _totp_now(secret: str) -> str:
    """يولّد كود 2FA (TOTP) من الـ secret بدون مكتبات خارجية."""
    import hmac, hashlib, struct, time, base64
    secret = (secret or "").upper().replace(" ", "")
    if not secret:
        return ""
    missing = len(secret) % 8
    if missing:
        secret += "=" * (8 - missing)
    try:
        key = base64.b32decode(secret)
    except Exception:
        return ""
    counter = int(time.time()) // 30
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF
    return str(code % 1000000).zfill(6)


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


def _get_csrf_token(s: requests.Session) -> str:
    """يجلب CSRF token من صفحة الموقع (من meta tag أو cookie)."""
    base = config.FASTCARD_WEB_BASE.rstrip("/")
    import re as _re
    # نجرب صفحات فيها form التحقق (الببجي/فري فاير فيها الـ token)
    pages = [
        "/index?page=products&cat=440",  # ببجي
        "/index?page=products",
        "/index",
    ]
    try:
        for page in pages:
            try:
                r = s.get(base + page, timeout=15)
            except Exception:
                continue
            html = r.text or ""
            # طريقة 0 (الأهم): window.PLAYER_CHECK_CSRF
            m = _re.search(r'PLAYER_CHECK_CSRF\s*=\s*["\']([a-f0-9]{20,})["\']', html, _re.I)
            if m:
                return m.group(1)
        # html هي آخر صفحة جُلبت
        # طريقة 1: meta tag
        m = _re.search(r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']', html)
        if m:
            return m.group(1)
        # طريقة 2: csrf_token في JS
        m = _re.search(r'csrf[_-]?token["\']?\s*[:=]\s*["\']([a-f0-9]{32,})["\']', html, _re.I)
        if m:
            return m.group(1)
        # طريقة 3: input hidden
        m = _re.search(r'name=["\']_token["\']\s+value=["\']([^"\']+)["\']', html)
        if m:
            return m.group(1)
        # طريقة 4: من cookie
        for c in s.cookies:
            if "csrf" in c.name.lower() or "xsrf" in c.name.lower():
                return c.value
    except Exception as e:
        logger.warning(f"_get_csrf_token failed: {e}")
    return ""


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
    cookies_names = [c.name for c in s.cookies]
    logger.info(f"_login: status={r.status_code} final_url={r.url} cookies={cookies_names}")
    
    # لو وصلنا لصفحة المصادقة الثنائية (2FA / twofactor)
    if "twofactor" in r.url.lower() or "two-factor" in r.url.lower() or "2fa" in r.url.lower():
        secret = getattr(config, "FASTCARD_2FA_SECRET", "") or os.environ.get("FASTCARD_2FA_SECRET", "")
        if not secret:
            raise FastcardWebError("الحساب يتطلب 2FA لكن FASTCARD_2FA_SECRET غير موجود")
        
        code = _totp_now(secret)
        logger.info(f"_login: 2FA required, generated code={code}")
        
        # نجيب CSRF token من صفحة twofactor
        import re as _re
        twofa_html = r.text or ""
        csrf = ""
        m = _re.search(r'name=["\']?_token["\']?\s+value=["\']([^"\']+)["\']', twofa_html)
        if m:
            csrf = m.group(1)
        else:
            m = _re.search(r'csrf[_-]?token["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']', twofa_html, _re.I)
            if m:
                csrf = m.group(1)
        
        twofa_url = base + "/twofactor"
        # نجرّب أسماء حقول شائعة للكود
        for field in ("code", "otp", "two_factor_code", "token", "2fa_code", "authenticator_code", "pin"):
            payload = {field: code}
            if csrf:
                payload["_token"] = csrf
                payload["csrf_token"] = csrf
            try:
                r2 = s.post(twofa_url, data=payload, allow_redirects=True, timeout=20,
                            headers={"X-Requested-With": "XMLHttpRequest", "Referer": twofa_url})
            except Exception:
                continue
            # نجحنا لو خرجنا من صفحة twofactor
            if "twofactor" not in r2.url.lower():
                logger.info(f"_login: 2FA success with field '{field}' → {r2.url}")
                return
        logger.warning("_login: 2FA failed with all field names")
        raise FastcardWebError("فشل إدخال رمز المصادقة الثنائية")
    
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
    """يرجّع dict فيه success/valid/player_name. data بتحتوي اسم اللاعب لو success=True."""
    if not is_enabled():
        raise FastcardWebError("تحقق الاسم غير مفعّل (مفاتيح الموقع ناقصة)")

    # الرابط الصح: /ajax/player-id-check
    base = config.FASTCARD_WEB_BASE.rstrip("/")
    url = base + "/ajax/player-id-check"
    
    # الـ parameters الجديدة: user_id بدل player_id
    # نفس ترتيب الموقع الأصلي: product_id أولاً ثم user_id
    payload = {"product_id": int(product_id), "user_id": str(player_id)}

    for attempt in (1, 2):
        s = _get_session(force_relogin=(attempt == 2))
        # نجيب CSRF token (ضروري للـ endpoint الجديد)
        csrf = _get_csrf_token(s)
        logger.info(f"check_player CSRF token = '{csrf[:20]}...' (len={len(csrf)})")
        try:
            # POST request مطابق لملف player-id-check.js الأصلي حرف بحرف
            # المهم: X-CSRF-Token (مش X-CSRF-TOKEN) + الترتيب product_id ثم user_id
            r = s.post(url, data=payload, timeout=25,
                       headers={"Accept": "application/json",
                                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                                "X-Requested-With": "XMLHttpRequest",
                                "X-CSRF-Token": csrf,
                                "Origin": base,
                                "Referer": base + "/index?page=products&cat=440"})
        except Exception as e:
            if attempt == 2:
                raise FastcardWebError(f"تعذّر الاتصال بالموقع: {e}")
            continue

        # logging مفصّل للتشخيص
        raw_text = (r.text or "")
        logger.info(f"check_player status={r.status_code} url={r.url} body={raw_text[:300]}")

        try:
            data = r.json()
        except Exception:
            # لو مش JSON — يمكن صفحة login (session منتهية)
            low = raw_text.lower()
            if attempt == 1 and ("login" in low or "تسجيل الدخول" in raw_text or "<!doctype" in low):
                logger.info("check_player: session expired, re-login...")
                continue
            if attempt == 2:
                raise FastcardWebError(f"رد غير متوقع من الموقع: {raw_text[:150]}")
            continue

        # نقرأ الحقول
        success = data.get("success")
        valid = data.get("valid")
        player_name = data.get("player_name") or data.get("name") or data.get("username")

        # نجاح: valid=True وفي اسم
        if valid and player_name:
            return {
                "success": True,
                "message": player_name,
                "data": player_name,
            }
        
        # لو success=False وفي رسالة login → أعِد المحاولة
        msg = str(data.get("message") or data.get("error") or "")
        if attempt == 1 and ("login" in msg.lower() or "تسجيل" in msg or not success):
            logger.info(f"check_player: retry (success={success}, msg={msg})")
            continue
        
        # فشل حقيقي
        return {
            "success": False,
            "message": "ID غير صحيح أو لم يتم العثور على اللاعب",
            "data": None,
        }

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
        # نطبع الرد كامل بدون HTML tags للتشخيص
        import re as _re
        _clean = _re.sub(r"<[^>]+>", " ", raw)
        _clean = _re.sub(r"\s+", " ", _clean).strip()
        logger.info(f"fastcard_web.place_order status={r.status_code} clean_text={_clean[:800]}")

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
        success_kw = ["نجح", "تم تنفيذ", "بنجاح", "تمت", "قيد التنفيذ", "success", "delivered", "completed", "approved", "processing", "pending"]
        # كلمات فشل صريحة فقط (تجنب "رصيد" لأنها قد تظهر بسياق عادي)
        fail_kw_ar = ["فشل الطلب", "حدث خطأ", "ID غير صحيح", "رصيد غير كاف", "رصيدك غير", "غير متوفر", "تم رفض", "رفض طلب", "تعذر تنفيذ", "تعذّر تنفيذ", "مرفوض", "لم يتم"]
        fail_kw_en = ["failed", "insufficient", "not enough", "invalid player", "out of stock"]

        is_success = any(k in raw for k in success_kw[:6]) or any(k in low for k in success_kw[6:])
        is_fail = any(k in raw for k in fail_kw_ar) or any(k in low for k in fail_kw_en)

        # الفشل له الأولوية المطلقة — لو فيه أي كلمة رفض/فشل → فاشل
        # النجاح لازم يكون صريح (مش بس وجود order-result)
        # ملخص نصّي مختصر
        import re
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()[:300]

        # حالة "قيد التنفيذ" — لا قبول صريح ولا رفض → نتابعه لاحقاً
        pending_kw = ["قيد التنفيذ", "قيد المعالجة", "جاري", "pending", "processing", "in progress"]
        is_pending = any(k in raw for k in pending_kw[:3]) or any(k in low for k in pending_kw[3:])

        # القرار النهائي:
        # - فشل صريح → فاشل
        # - نجاح صريح وما فيه فشل → ناجح
        # - لا هذا ولا ذاك (قيد التنفيذ) → معلّق للمتابعة
        final_success = bool(is_success and not is_fail)
        order_pending = bool((is_pending or (r.status_code == 200 and "order-result" in low)) and not is_fail and not is_success)

        # رسالة نظيفة ثابتة (بدون كود HTML/CSS)
        if final_success:
            clean_msg = "تم تنفيذ الطلب بنجاح"
        elif order_pending:
            clean_msg = "طلبك قيد التنفيذ"
        else:
            clean_msg = "تعذّر تنفيذ طلبك"

        # استخراج رقم الطلب من الرد (order.php?id=58828 أو id=58828)
        web_order_id = None
        _id_match = _re2.search(r"order\.php\?id=(\d+)", raw) or _re2.search(r'data-order-id="(\d+)"', raw) or _re2.search(r'"order_id"\s*:\s*"?(\d+)', raw) or _re2.search(r'id=(\d{4,})', raw)
        if _id_match:
            web_order_id = _id_match.group(1)

        return {
            "success": final_success,
            "pending": order_pending,
            "message": clean_msg,
            "order_id": web_order_id,
            "_html": True,
        }

    raise FastcardWebError("فشل الاتصال بعد محاولتين")


def check_order_status(order_id: str) -> Optional[Dict[str, Any]]:
    """
    يفحص حالة طلب من صفحة الموقع order.php?id=ORDER_ID.
    يقرأ badge-state ويرجّع الحالة: accept / processing / reject.
    """
    if not order_id:
        return None
    base = config.FASTCARD_WEB_BASE.rstrip("/")
    url = base + "/api/order.php?id=" + str(order_id)

    for attempt in (1, 2):
        s = _get_session(force_relogin=(attempt == 2))
        try:
            r = s.get(url, timeout=30, headers={"X-Requested-With": "XMLHttpRequest"})
        except Exception:
            if attempt == 2:
                return None
            continue

        raw = (r.text or "")
        low = raw.lower()

        # لو رجعنا لصفحة تسجيل الدخول → أعد المحاولة
        if "login" in r.url.lower() and attempt == 1:
            continue

        # نقرأ badge-state من الـ HTML
        # completed → مقبول/منفّذ | pending → قيد التنفيذ | rejected → مرفوض
        status = "processing"
        if "badge-state completed" in low or "مقبول" in raw or "تم التنفيذ" in raw or "منفذ" in raw or "منفّذ" in raw:
            status = "accept"
        elif "badge-state rejected" in low or "مرفوض" in raw or "تم الرفض" in raw or "فشل" in raw:
            status = "reject"
        elif "badge-state pending" in low or "قيد التنفيذ" in raw or "قيد المعالجة" in raw or "بانتظار" in raw:
            status = "processing"

        # نستخرج رد المتجر/الكود لو موجود
        replay = []
        _code = _re2.search(r"الاستجابة[:\s]*([^<\n]{1,60})", raw)
        if _code:
            replay = [_code.group(1).strip()]

        return {
            "order_id": str(order_id),
            "status": status,
            "replay_api": replay,
            "_html": True,
        }

    return None


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
