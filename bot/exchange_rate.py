"""
جلب سعر صرف الدولار مقابل الليرة السورية من قناة تيليغرام @SaymouaaExchange.
يُحدَّث كل ساعة ويُحفظ في DB.
"""
import logging
import re
import asyncio
import requests

from . import config, database as db

logger = logging.getLogger(__name__)

CHANNEL_URL = "https://t.me/s/SaymouaaExchange"
CHANNEL_NAME = "@SaymouaaExchange"
REQUEST_TIMEOUT = 15


def _fetch_rate_from_channel() -> dict:
    """
    يجلب أحدث سعر صرف من قناة تيليغرام @SaymouaaExchange.
    يرجع {"buy": float, "sell": float, "avg": float}
    """
    resp = requests.get(CHANNEL_URL, timeout=REQUEST_TIMEOUT, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    resp.raise_for_status()
    html = resp.text

    # استخرج كل نصوص الرسائل
    msg_blocks = re.findall(
        r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
        html,
        re.DOTALL,
    )

    # ابحث في آخر الرسائل عن رسالة تحتوي على سعرين (شراء وبيع)
    for block in reversed(msg_blocks):
        text = re.sub(r"<[^>]+>", "", block).strip()
        nums = re.findall(r"(\d{2,3},\d{3})", text)
        if len(nums) >= 2:
            buy = float(nums[0].replace(",", ""))
            sell = float(nums[1].replace(",", ""))
            avg = round((buy + sell) / 2)
            if 1000 <= buy <= 500_000 and 1000 <= sell <= 500_000:
                return {"buy": buy, "sell": sell, "avg": avg}

    raise ValueError("لم يتم العثور على سعر صرف في آخر رسائل القناة")


async def update_rate_from_channel() -> dict:
    """
    يجلب السعر من القناة ويحفظه في DB.
    يرجع: {"buy": float, "sell": float, "avg": float, "changed": bool, "old_rate": float}
    """
    old_rate = config.get_syp_per_usd()

    data = await asyncio.to_thread(_fetch_rate_from_channel)

    new_rate = data["avg"]
    changed = abs(new_rate - old_rate) >= 1.0
    if changed:
        db.set_setting("syp_per_usd", str(new_rate))
        logger.info("تم تحديث سعر الصرف: %.0f → %.0f", old_rate, new_rate)
    else:
        logger.info("سعر الصرف لم يتغير: %.0f", new_rate)

    return {**data, "changed": changed, "old_rate": old_rate}
