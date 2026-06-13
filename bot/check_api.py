"""
نقطة HTTP بسيطة للتحقق من اسم اللاعب — يناديها الموقع.
منفصلة تماماً عن منطق البوت (polling/handlers) حتى لا تؤثر عليه.
"""
import json
import logging
import os
import time
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)

CHECK_API_SECRET = os.environ.get("CHECK_API_SECRET", "")


def _try_check(player, product_id):
    """محاولة واحدة عبر check_player، ترجّع (name|None, raw_result)."""
    from .fastcard_web import check_player
    res = check_player(player, product_id)
    name = res.get("player_name") or res.get("name") or res.get("username") or res.get("message")
    valid = res.get("valid")
    success = res.get("success")
    valid_str = str(valid).lower()
    is_valid = (success is True or valid is True or valid == 1
                or valid_str in ("true", "1", "valid"))
    # message بترجع اسم اللاعب لما success=True (حسب منطق check_player)
    if success is True and name and name != "ID غير صحيح أو لم يتم العثور على اللاعب":
        return name, res
    if is_valid and name:
        return name, res
    return None, res


def handle_check_player(query_string: str):
    """
    يعالج طلب التحقق. يرجّع (status_code, dict).
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
    if not product_id:
        product_id = 7816  # منتج تحقق افتراضي

    # نعيد المحاولة حتى 3 مرات — يعالج حالة الجلسة الفاسدة المؤقتة
    last = None
    for i in range(3):
        try:
            # بعد فشل المحاولة الأولى، نجبر جلسة دخول نظيفة
            if i == 1:
                try:
                    from .fastcard_web import _get_session
                    _get_session(force_relogin=True)
                    logger.info("check-player: forced fresh login before retry")
                except Exception as e:
                    logger.warning(f"force relogin failed: {e}")
            name, raw = _try_check(player, product_id)
            last = raw
            if name:
                return 200, {"ok": True, "name": name}
        except Exception as e:
            logger.warning(f"check-player attempt {i+1} error: {e}")
            last = {"error": str(e)}
        time.sleep(0.6)

    return 200, {"ok": False, "msg": "ID غير صحيح أو لم يتم العثور على اللاعب"}
