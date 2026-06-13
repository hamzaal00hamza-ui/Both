"""
نقطة HTTP بسيطة للتحقق من اسم اللاعب — يناديها الموقع.
منفصلة تماماً عن منطق البوت (polling/handlers) حتى لا تؤثر عليه.
تشتغل بنفس الـ thread تبع health server.
"""
import json
import logging
import os
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)

CHECK_API_SECRET = os.environ.get("CHECK_API_SECRET", "")


def handle_check_player(query_string: str):
    """
    يعالج طلب التحقق. يرجّع (status_code, dict).
    query_string: جزء الـ query بعد ? (مثل: player=123&product=456&secret=xxx)
    """
    q = parse_qs(query_string or "")
    secret = (q.get("secret", [""])[0]).strip()
    player = (q.get("player", [""])[0]).strip()
    product = q.get("product", ["0"])[0]
    debug = q.get("debug", [""])[0] == "1"

    expected = (CHECK_API_SECRET or "").strip()

    if debug:
        return 200, {
            "secret_len_url": len(secret),
            "secret_expected_len": len(expected),
            "match": secret == expected,
            "expected_is_set": bool(expected),
        }

    if expected and secret != expected:
        return 403, {"ok": False, "msg": "unauthorized"}

    if not player:
        return 200, {"ok": False, "msg": "أدخل ID اللاعب أولاً"}

    try:
        product_id = int(product) if str(product).isdigit() else 0
    except Exception:
        product_id = 0

    try:
        from .fastcard_web import check_player
        res = check_player(player, product_id or 7816)
        name = res.get("player_name") or res.get("name") or res.get("username")
        valid = res.get("valid")
        success = res.get("success")
        valid_str = str(valid).lower()
        is_valid = (success is True or valid is True or valid == 1
                    or valid_str in ("true", "1", "valid") or bool(name))
        if is_valid and name:
            return 200, {"ok": True, "name": name}
        return 200, {"ok": False, "msg": "ID غير صحيح أو لم يتم العثور على اللاعب"}
    except Exception as e:
        logger.warning(f"check-player api error: {e}")
        return 200, {"ok": False, "soft": True, "msg": "تعذّر التحقق حالياً"}
