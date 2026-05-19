"""
إرسال إشعارات الأدمن — ترسل لـ ADMIN_ID و(اختيارياً) لقناة توثيق الطلبات.

قناة التوثيق:
- مصدرها الأساسي: db.get_setting("admin_channel") — يضبطها الأدمن من اللوحة.
- Fallback: متغير البيئة ADMIN_CHANNEL (اختياري، للنشر الأولي).
- القيمة المقبولة: @username أو -100xxxxxxxxxx (chat_id).

الدالة الرئيسية: notify_admin(bot, text, **kwargs)
- ترسل للأدمن DM دائماً (لو ADMIN_ID مضبوط).
- ترسل لقناة التوثيق إن وُجدت.
- تقمع الأخطاء حتى لا تعطّل تدفق الطلب الأساسي.
"""
import logging
from typing import Any, Optional

from telegram import Bot
from telegram.constants import ParseMode

from . import config, database as db

logger = logging.getLogger(__name__)


def get_admin_channel() -> str:
    """قناة التوثيق الحالية: DB أولاً ثم ENV var."""
    val = db.get_setting("admin_channel")
    if val:
        return val.strip()
    return (config.ADMIN_CHANNEL or "").strip()


def set_admin_channel(value: Optional[str]) -> None:
    """ضبط/إلغاء قناة التوثيق. قيمة فاضية = إلغاء."""
    db.set_setting("admin_channel", (value or "").strip())


def _channel_to_chat_id(channel: str) -> Any:
    """يحوّل @username يبقى نص، -100xxx يحوّل لـ int."""
    channel = channel.strip()
    if channel.lstrip("-").isdigit():
        return int(channel)
    return channel


async def notify_admin(bot: Bot, text: str, **kwargs: Any) -> None:
    """يرسل text للأدمن DM ولقناة التوثيق (لو موجودة).

    kwargs تُمرر كما هي لـ bot.send_message (parse_mode, reply_markup, ...).
    أي خطأ يُسجّل بدون رفع استثناء.
    """
    if "parse_mode" not in kwargs:
        kwargs["parse_mode"] = ParseMode.MARKDOWN

    if config.ADMIN_ID:
        try:
            await bot.send_message(chat_id=config.ADMIN_ID, text=text, **kwargs)
        except Exception as e:
            logger.error(f"notify_admin DM failed: {e}")

    channel = get_admin_channel()
    if channel:
        ch_kwargs = dict(kwargs)
        # الأزرار التفاعلية للأدمن لا معنى لها على قناة عامة — نحذفها
        ch_kwargs.pop("reply_markup", None)
        try:
            await bot.send_message(
                chat_id=_channel_to_chat_id(channel),
                text=text,
                **ch_kwargs,
            )
        except Exception as e:
            logger.error(f"notify_admin channel ({channel}) failed: {e}")


async def notify_channel_only(bot: Bot, text: str, **kwargs: Any) -> None:
    """يرسل لقناة التوثيق فقط (للتوثيق العام، بدون إزعاج الأدمن DM)."""
    if "parse_mode" not in kwargs:
        kwargs["parse_mode"] = ParseMode.MARKDOWN

    channel = get_admin_channel()
    if not channel:
        return
    ch_kwargs = dict(kwargs)
    ch_kwargs.pop("reply_markup", None)
    try:
        await bot.send_message(
            chat_id=_channel_to_chat_id(channel),
            text=text,
            **ch_kwargs,
        )
    except Exception as e:
        logger.error(f"notify_channel ({channel}) failed: {e}")
