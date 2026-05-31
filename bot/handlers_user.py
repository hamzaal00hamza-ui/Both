import json
"""
معالجات أوامر وأزرار المستخدمين العاديين
"""
import asyncio
import logging
import re
import time
import uuid
from typing import Optional, Dict, Any

from telegram import Update, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from . import config, database as db, keyboards as kb, fastcard, fastcard_web
from . import notify
from .shamcash import (
    is_enabled as shamcash_enabled,
    get_active_account_id,
    find_matching_transaction,
    ShamCashError,
    COIN_SYP,
    COIN_USD,
)
from . import syriatel_cash
from .syriatel_cash import SyriatelCashError

logger = logging.getLogger(__name__)

(
    SYRIATEL_TX_CODE,
    SYRIATEL_AMOUNT,
    SHAMCASH_AMOUNT,
    SHAMCASH_PHOTO,
    PUBG_PLAYER_ID,
    SHAMCASH_USD_AMOUNT,
    FREEFIRE_PLAYER_ID,
    FASTCARD_PLAYER_ID,
    LOYALTY_REDEEM_AMOUNT,
    COUPON_CODE_INPUT,
    FASTCARD_CUSTOM_AMOUNT,
    USDT_AMOUNT_USD,
    USDT_TX_HASH,
) = range(13)


WELCOME = (
    "🎮 *GameZone — متجرك للألعاب الرقمية*\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "⚡ شحن فوري · 🔒 آمن 100% · 💬 دعم 24/7\n\n"
    "👇 اختر من القائمة:"
)


async def ensure_user(update: Update) -> dict:
    u = update.effective_user
    return db.get_or_create_user(u.id, u.username, u.first_name)


async def is_banned(update: Update) -> bool:
    user = await ensure_user(update)
    return bool(user.get("is_banned"))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = await ensure_user(update)
    except Exception as _e:
        import traceback as _tb
        _tb_str = _tb.format_exc()[-1500:]
        try:
            await update.message.reply_text(f"❌ DB ERROR:\n{_e}\n\n{_tb_str}")
        except Exception:
            pass
        return
    if user.get("is_banned"):
        await update.message.reply_text("🚫 تم حظرك من استخدام البوت. تواصل مع الدعم: " + config.SUPPORT_USERNAME)
        return

    # ========== معالجة رابط الإحالة /start ref_<id> ==========
    bonus_msg = ""
    if user.get("is_new") and context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            try:
                referrer_id = int(arg[4:])
            except ValueError:
                referrer_id = 0
            if referrer_id > 0:
                applied = db.attach_referrer(
                    user_id=update.effective_user.id,
                    referrer_id=referrer_id,
                    signup_bonus=float(config.REFERRAL_SIGNUP_BONUS),
                )
                if applied:
                    bonus_msg = (
                        f"\n\n🎁 *مبروك!* استلمت مكافأة الانضمام: "
                        f"*{int(applied['bonus_amount'])} ل.س* — رصيدك الآن: {int(applied['new_balance'])} ل.س"
                    )
                    # إشعار المُحيل
                    try:
                        new_user = update.effective_user
                        new_label = (f"@{new_user.username}" if new_user.username
                                     else (new_user.first_name or str(new_user.id)))
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=(
                                "👥 *إحالة جديدة!*\n\n"
                                f"انضم إلى البوت عن طريق رابطك: {new_label}\n\n"
                                f"💰 ستحصل على *{config.REFERRAL_COMMISSION_PERCENT}%* مكافأة من كل عملية شحن يقوم بها."
                            ),
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    except Exception:
                        pass

    from datetime import datetime, timezone, timedelta
    _syria = timezone(timedelta(hours=3))
    _hour = datetime.now(_syria).hour
    if 5 <= _hour < 12:
        _greeting = "🌅 *GOOD MORNING* 🌅"
    elif 12 <= _hour < 17:
        _greeting = "☀️ *GOOD AFTERNOON* ☀️"
    elif 17 <= _hour < 21:
        _greeting = "🌆 *GOOD EVENING* 🌆"
    else:
        _greeting = "🌙 *GOOD NIGHT* 🌙"

    name = update.effective_user.first_name or "صديقنا"
    welcome_caption = (
        f"{_greeting}\n"
        f"👋 *أهلاً {name}!*\n\n"
        "🎮 *GameZone* — شحن العاب رقمية فوري وآمن\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ تسليم فوري · 🛡 100% آمن · 🌟 دعم 24/7"
        + bonus_msg
    )
    try:
        await update.message.reply_photo(
            photo=config.START_BANNER_URL,
            caption=welcome_caption,
            reply_markup=kb.user_reply_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        await update.message.reply_text(
            welcome_caption,
            reply_markup=kb.user_reply_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )


async def notify_level_up(bot, user_id: int, recharge_state: Optional[Dict[str, Any]]) -> None:
    """يرسل إشعار للمستخدم عند ترقية مستواه. يُستدعى بعد كل عملية شحن.
    آمن للاستدعاء حتى لو الـ state فاضي أو ما في ترقية."""
    if not recharge_state or not recharge_state.get("level_changed"):
        return
    new_level = recharge_state.get("level") or ""
    prev_level = recharge_state.get("previous_level") or ""
    total = float(recharge_state.get("total_recharged") or 0)
    try:
        await bot.send_message(
            chat_id=int(user_id),
            text=(
                "🎉 *مبروك! تمّت ترقيتك إلى مستوى جديد* 🎉\n"
                "━━━━━━━━━━━━━━━━━\n\n"
                f"📈 من: {prev_level}\n"
                f"🆕 إلى: *{new_level}*\n\n"
                f"📊 إجمالي شحنك: *{total:,.0f} ل.س*\n\n"
                "✨ شكراً لثقتك بنا — كل ما زاد شحنك زاد مستواك!"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        pass


async def send_rating_prompt(bot, user_id: int, order_id: int, item_label: str = "") -> None:
    """يرسل رسالة طلب تقييم للزبون بعد إكمال طلب. آمن: يتجاهل أي خطأ."""
    try:
        if db.has_rated(int(order_id)):
            return
        item_line = f"\n💎 المنتج: {item_label}" if item_label else ""
        await bot.send_message(
            chat_id=int(user_id),
            text=(
                "⭐ *قيّم تجربتك معنا*\n"
                "━━━━━━━━━━━━━━━━━\n"
                f"📋 رقم الطلب: #{order_id}{item_line}\n\n"
                "كيف كانت تجربتك؟ تقييمك بساعدنا نحسّن خدمتنا 🙏"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.rating_keyboard(int(order_id)),
        )
    except Exception as e:
        logger.warning(f"send_rating_prompt failed: {e}")


async def cb_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل تقييم الزبون. callback_data: rate:<order_id>:<stars>  (stars=0 = تخطّي)"""
    q = update.callback_query
    await q.answer()
    parts = (q.data or "").split(":")
    if len(parts) != 3:
        return
    try:
        order_id = int(parts[1])
        stars = int(parts[2])
    except ValueError:
        return

    user_id = q.from_user.id
    if stars == 0:
        try:
            await q.edit_message_text("شكراً لك 🙏 يمكنك تقييم طلباتك في أي وقت لاحقاً.")
        except Exception:
            pass
        return

    saved = await asyncio.to_thread(db.add_rating, order_id, user_id, stars, "")
    if not saved:
        try:
            await q.edit_message_text("✅ سبق وقيّمت هذا الطلب — شكراً لك!")
        except Exception:
            pass
        return

    stars_str = "⭐" * stars
    try:
        await q.edit_message_text(
            f"✅ *تم استلام تقييمك*\n\n"
            f"📋 الطلب: #{order_id}\n"
            f"التقييم: {stars_str}\n\n"
            "شكراً لمساعدتنا في تحسين الخدمة 🙏❤️",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        pass

    # إشعار الأدمن لو التقييم منخفض (1-2 نجوم) ليتدخّل
    if stars <= 2 and config.ADMIN_ID:
        try:
            user = db.get_user(user_id) or {}
            uname = user.get("username") or user.get("first_name") or str(user_id)
            await notify.notify_admin(
                context.bot,
                f"⚠️ *تقييم منخفض*\n\n"
                f"المستخدم: @{uname} ({user_id})\n"
                f"الطلب: #{order_id}\n"
                f"التقييم: {stars_str}\n\n"
                "_يستحسن التواصل مع الزبون لمعرفة المشكلة._",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass


async def _show_loyalty_panel(q, user_id: int) -> None:
    """يعرض شاشة نقاط الولاء للمستخدم."""
    pts = await asyncio.to_thread(db.get_loyalty_points, user_id)
    user = db.get_user(user_id) or {}
    min_redeem = config.LOYALTY_MIN_REDEEM
    rate = config.LOYALTY_REDEEM_RATE
    earn_pct = config.LOYALTY_EARN_PERCENT
    can_redeem = pts >= min_redeem
    syp_value = pts * rate

    text = (
        "💎 *نقاط الولاء*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 رصيد نقاطك: *{pts:,}* نقطة\n"
        f"💰 قيمتها: *{syp_value:,.0f} ل.س*\n\n".replace(",", "،") +
        "📋 *كيف تكسب النقاط؟*\n"
        f"• كل طلب ناجح يكسبك *{earn_pct:.0f}%* من قيمته نقاط\n"
        f"• كل نقطة = *{rate}* ل.س\n"
        f"• الحد الأدنى للاستبدال: *{min_redeem:,}* نقطة\n\n".replace(",", "،") +
        "💡 _ما عليك إلا الشراء — والنقاط تنحسب لك تلقائياً!_"
    )
    if not can_redeem:
        remaining = max(0, min_redeem - pts)
        if remaining > 0:
            text += f"\n\n⏳ تحتاج *{remaining:,}* نقطة إضافية للاستبدال.".replace(",", "،")

    await q.edit_message_text(
        text,
        reply_markup=kb.loyalty_menu(can_redeem=can_redeem, suggested_redeem=pts if can_redeem else 0),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cb_loyalty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يتعامل مع أزرار شاشة الولاء: استبدال الكل، أو طلب مبلغ مخصص."""
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        await q.edit_message_text("🚫 تم حظرك من استخدام البوت.")
        return ConversationHandler.END

    user_id = q.from_user.id
    data = q.data or ""

    if data == "loyalty:redeem_all":
        pts = await asyncio.to_thread(db.get_loyalty_points, user_id)
        if pts < config.LOYALTY_MIN_REDEEM:
            await q.edit_message_text(
                "⚠️ نقاطك أقل من الحد الأدنى للاستبدال.",
                reply_markup=kb.back_to_main(),
            )
            return ConversationHandler.END
        result = await asyncio.to_thread(db.redeem_loyalty_points, user_id, pts, config.LOYALTY_REDEEM_RATE)
        if not result:
            await q.edit_message_text(
                "⚠️ صار خطأ أثناء الاستبدال — جرّب مرة ثانية.",
                reply_markup=kb.back_to_main(),
            )
            return ConversationHandler.END
        await q.edit_message_text(
            "✅ *تم الاستبدال بنجاح!*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"💎 نقاط مستبدلة: *{result['points_used']:,}*\n".replace(",", "،") +
            f"💰 رصيد مضاف: *{result['syp_added']:,.0f} ل.س*\n".replace(",", "،") +
            f"💼 رصيدك الجديد: *{result['new_balance']:,.0f} ل.س*\n".replace(",", "،") +
            f"🎯 نقاطك المتبقية: *{result['new_points']:,}*".replace(",", "،"),
            reply_markup=kb.back_to_main(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    if data == "loyalty:redeem_custom":
        pts = await asyncio.to_thread(db.get_loyalty_points, user_id)
        if pts < config.LOYALTY_MIN_REDEEM:
            await q.edit_message_text(
                "⚠️ نقاطك أقل من الحد الأدنى للاستبدال.",
                reply_markup=kb.back_to_main(),
            )
            return ConversationHandler.END
        await q.edit_message_text(
            "✏️ *استبدال مبلغ مخصص*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 رصيدك الحالي: *{pts:,}* نقطة\n".replace(",", "،") +
            f"📝 أدخل عدد النقاط اللي تبي تستبدلها\n"
            f"(الحد الأدنى: *{config.LOYALTY_MIN_REDEEM:,}*)".replace(",", "،"),
            reply_markup=kb.loyalty_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return LOYALTY_REDEEM_AMOUNT

    return ConversationHandler.END


async def loyalty_redeem_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل عدد النقاط المراد استبدالها (نص)."""
    txt = (update.message.text or "").strip()
    # تنقية أرقام عربية / فواصل
    txt_clean = txt.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")).replace(",", "").replace("،", "").replace(" ", "")
    if not txt_clean.isdigit():
        await update.message.reply_text("⚠️ أدخل رقم صحيح فقط.", reply_markup=kb.loyalty_cancel())
        return LOYALTY_REDEEM_AMOUNT
    points = int(txt_clean)
    user_id = update.effective_user.id

    if points < config.LOYALTY_MIN_REDEEM:
        await update.message.reply_text(
            f"⚠️ الحد الأدنى للاستبدال *{config.LOYALTY_MIN_REDEEM:,}* نقطة.".replace(",", "،"),
            reply_markup=kb.loyalty_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return LOYALTY_REDEEM_AMOUNT

    current = await asyncio.to_thread(db.get_loyalty_points, user_id)
    if points > current:
        await update.message.reply_text(
            f"⚠️ نقاطك ({current:,}) أقل من العدد المطلوب.".replace(",", "،"),
            reply_markup=kb.loyalty_cancel(),
        )
        return LOYALTY_REDEEM_AMOUNT

    result = await asyncio.to_thread(db.redeem_loyalty_points, user_id, points, config.LOYALTY_REDEEM_RATE)
    if not result:
        await update.message.reply_text(
            "⚠️ تعذّر إتمام الاستبدال — جرّب مرة ثانية.",
            reply_markup=kb.back_to_main(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "✅ *تم الاستبدال بنجاح!*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"💎 نقاط مستبدلة: *{result['points_used']:,}*\n".replace(",", "،") +
        f"💰 رصيد مضاف: *{result['syp_added']:,.0f} ل.س*\n".replace(",", "،") +
        f"💼 رصيدك الجديد: *{result['new_balance']:,.0f} ل.س*\n".replace(",", "،") +
        f"🎯 نقاطك المتبقية: *{result['new_points']:,}*".replace(",", "،"),
        reply_markup=kb.back_to_main(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def cb_coupon_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يبدأ إدخال كود الخصم."""
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        await q.edit_message_text("🚫 تم حظرك من استخدام البوت.")
        return ConversationHandler.END
    await q.edit_message_text(
        "🎟 *كود الخصم*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "أدخل كود الخصم اللي عندك 👇\n\n"
        "💡 _الكود يضيف رصيد مباشرة لحسابك تستخدمه بأي طلب._",
        reply_markup=kb.coupon_cancel(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return COUPON_CODE_INPUT


async def msg_coupon_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل كود الخصم من الزبون ويطبّقه (يضاف للرصيد مباشرة)."""
    code = (update.message.text or "").strip().upper()
    if not code or len(code) > 50:
        await update.message.reply_text("⚠️ أدخل كود صحيح.", reply_markup=kb.coupon_cancel())
        return COUPON_CODE_INPUT

    user_id = update.effective_user.id
    coupon = await asyncio.to_thread(db.get_coupon_by_code, code)
    if not coupon:
        await update.message.reply_text(
            "❌ الكود غير صحيح أو غير موجود.",
            reply_markup=kb.coupon_cancel(),
        )
        return COUPON_CODE_INPUT
    if not int(coupon.get("active") or 0):
        await update.message.reply_text("❌ هذا الكود معطّل.", reply_markup=kb.back_to_main())
        return ConversationHandler.END

    # تحقق صلاحية + تكرار + سقف الاستخدام
    # نستخدم order_amount = min_order أو 1 (لتجاوز فحص الحد الأدنى) لأن الخصم سيضاف للرصيد مباشرة
    base_amount = float(coupon.get("min_order") or 0) or 100000  # افتراضي 100k لحساب الـ percent
    result = await asyncio.to_thread(db.validate_coupon_for_user, code, user_id, base_amount)
    if not result["ok"]:
        await update.message.reply_text(
            result["error"] or "❌ تعذّر تطبيق الكود.",
            reply_markup=kb.back_to_main(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    # احتساب الخصم النهائي
    coupon = result["coupon"]
    discount = float(result["discount"])
    if coupon["discount_type"] == "percent":
        # في وضع "إضافة للرصيد"، الـ percent يُحسب على min_order (لو محدد) فقط لتجنب الاستغلال
        if float(coupon.get("min_order") or 0) <= 0:
            await update.message.reply_text(
                "❌ هذا الكود لا يمكن استخدامه حالياً (يحتاج إعداد إضافي من الإدارة).",
                reply_markup=kb.back_to_main(),
            )
            return ConversationHandler.END
        discount = round(float(coupon["min_order"]) * float(coupon["discount_value"]) / 100.0 / 100) * 100
        if discount <= 0:
            await update.message.reply_text("❌ قيمة الكود غير صالحة.", reply_markup=kb.back_to_main())
            return ConversationHandler.END

    # سجّل استخدام الكوبون + أضف للرصيد بـ atomic operations
    consumed = await asyncio.to_thread(db.consume_coupon, int(coupon["id"]), user_id, None, discount)
    if not consumed:
        await update.message.reply_text(
            "⚠️ تعذّر إتمام التطبيق — جرّب مرة ثانية.",
            reply_markup=kb.back_to_main(),
        )
        return ConversationHandler.END

    state = await asyncio.to_thread(db.update_balance, user_id, float(discount), False)
    new_balance = float(state.get("balance") or 0) if state else 0

    await update.message.reply_text(
        "🎉 *تم تطبيق الكود بنجاح!*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"🎟 الكود: `{coupon['code']}`\n"
        f"💰 رصيد مضاف: *{discount:,.0f} ل.س*\n".replace(",", "،") +
        f"💼 رصيدك الجديد: *{new_balance:,.0f} ل.س*\n\n".replace(",", "،") +
        "✨ يمكنك الآن استخدام رصيدك في المتجر!",
        reply_markup=kb.back_to_main(),
        parse_mode=ParseMode.MARKDOWN,
    )

    # إشعار الأدمن
    if config.ADMIN_ID:
        try:
            user = db.get_user(user_id) or {}
            uname = user.get("username") or user.get("first_name") or "—"
            await notify.notify_admin(
                context.bot,
                f"🎟 *استخدام كوبون*\n\n"
                f"الكود: `{coupon['code']}`\n"
                f"المستخدم: @{uname} ({user_id})\n"
                f"الخصم المضاف: *{discount:,.0f} ل.س*".replace(",", "،"),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass

    return ConversationHandler.END


async def grant_loyalty_for_order(bot, user_id: int, order_price_syp: float) -> int:
    """يمنح نقاط ولاء للزبون عند نجاح طلب. يرجع عدد النقاط المضافة (قد يكون 0)."""
    try:
        if order_price_syp <= 0:
            return 0
        pct = float(config.LOYALTY_EARN_PERCENT) / 100.0
        points = int(round(float(order_price_syp) * pct))
        if points <= 0:
            return 0
        new_total = await asyncio.to_thread(db.add_loyalty_points, user_id, points)
        # إشعار لطيف للزبون
        try:
            await bot.send_message(
                chat_id=int(user_id),
                text=(
                    f"💎 *كسبت {points:,} نقطة ولاء!*\n".replace(",", "،") +
                    f"🎯 رصيدك: *{new_total:,} نقطة*".replace(",", "،") +
                    "\n\n_استبدلها برصيد من زر «💎 نقاطي» في القائمة الرئيسية._"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
        return points
    except Exception as e:
        logger.warning(f"grant_loyalty_for_order failed: {e}")
        return 0


async def apply_referral_commission(bot, recharger_user_id: int, recharge_amount: float,
                                     referrer_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """عند اعتماد شحن، إذا للمستخدم محيل، يضيف له 8% عمولة ويرسل إشعار.
    `referrer_id` هو الـ referrer للمستخدم الذي شحن (يأتي من نتيجة update_balance)."""
    if not referrer_id or recharge_amount <= 0:
        return None
    # لا تُدفع عمولة لمحيل محظور
    ref_user = db.get_user(int(referrer_id))
    if not ref_user or int(ref_user.get("is_banned") or 0) == 1:
        return None
    pct = float(config.REFERRAL_COMMISSION_PERCENT) / 100.0
    commission = round(recharge_amount * pct)
    if commission <= 0:
        return None
    # إضافة للرصيد بدون احتسابها كشحن (لا ترفع المستوى)
    ref_state = db.update_balance(int(referrer_id), float(commission), count_as_recharge=False)
    if not ref_state:
        return None
    db.record_referral_commission(
        referrer_id=int(referrer_id),
        referred_user_id=int(recharger_user_id),
        recharge_amount=float(recharge_amount),
        commission=float(commission),
    )
    # إشعار المُحيل
    try:
        ru = db.get_user(recharger_user_id) or {}
        label = ru.get("username") or ru.get("first_name") or str(recharger_user_id)
        await bot.send_message(
            chat_id=int(referrer_id),
            text=(
                "💎 *مكافأة إحالة جديدة!*\n\n"
                f"صديقك {label} قام بشحن *{int(recharge_amount)} ل.س*.\n"
                f"حصلت على *{int(commission)} ل.س* "
                f"({config.REFERRAL_COMMISSION_PERCENT}%)\n\n"
                f"💰 رصيدك الآن: *{int(ref_state['balance'])} ل.س*"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        pass
    return {"commission": commission, "referrer_balance": ref_state["balance"]}


async def _build_referral_screen(user_id: int, bot) -> tuple:
    """يبني نص + كيبورد شاشة الإحالة."""
    me = await bot.get_me()
    bot_username = me.username or "bot"
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    stats = db.get_referral_stats(user_id)
    text = (
        "👥 *دعوة الأصدقاء*\n\n"
        f"🎁 كل صديق ينضم عن طريق رابطك يحصل على *{int(config.REFERRAL_SIGNUP_BONUS)} ل.س* مكافأة انضمام.\n"
        f"💰 وأنت تحصل على مكافأة *{config.REFERRAL_COMMISSION_PERCENT}%* من كل عملية شحن يقوم بها — مدى الحياة!\n\n"
        f"🔗 *رابط الدعوة الخاص بك:*\n`{link}`\n\n"
        "📊 *إحصائياتك:*\n"
        f"• عدد الأصدقاء المُحالين: *{stats['invited_count']}*\n"
        f"• عدد عمليات المكافأة: *{stats['commission_orders']}*\n"
        f"• إجمالي مكافآتك من الإحالات: *{int(stats['commission_total'])} ل.س*\n\n"
        "📤 اضغط الزر بالأسفل لمشاركة الرابط مع أصدقائك."
    )
    share_text = (
        f"🎮 انضم لبوت شحن الألعاب واحصل على {int(config.REFERRAL_SIGNUP_BONUS)} ل.س هدية! 🎁"
    )
    return text, kb.referral_menu(link, share_text)


async def cmd_reply_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعالج أزرار لوحة المفاتيح الثابتة في الأسفل (Reply Keyboard)."""
    if await is_banned(update):
        return
    text = (update.message.text or "").strip()

    async def send(msg, markup):
        await update.message.reply_text(msg, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


    if text in ["🔥 الألعاب 🎮", "🎮 الألعاب 🔥", "🎮 قسم الألعاب"]:
        await update.message.reply_text(
            "🎮 *قسم الألعاب* 🔥\n""━━━━━━━━━━━━━━━━━\n\n""🏆 PUBG · Free Fire · COD · وأكثر\n""⚡ شحن فوري أوتوماتيكي 100%\n\n""👇 اختر اللعبة:",
            reply_markup=kb.games_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )

    elif text in ["💫 التطبيقات 📱", "📱 التطبيقات ✨", "📱 قسم التطبيقات"]:
        await send(
            "📱 *التطبيقات والاشتراكات* ✨\n""━━━━━━━━━━━━━━━━━\n\n""🎵 Spotify · Netflix · Shahid · وأكثر\n""💎 أسعار منافسة وتسليم فوري\n\n""👇 اختر التطبيق:",
            kb.subs_menu(),
        )

    elif text in ["💳 بطاقات وأكواد 🃏", "🃏 بطاقات وأكواد 💳", "🃏 قسم البطاقات والأكواد"]:
        await send("🃏 *بطاقات هدايا وأكواد* 💳\n""━━━━━━━━━━━━━━━━━\n\n""🍎 iTunes · 🎮 PSN · Steam · Xbox\n""✅ أكواد أصلية مضمونة 100%\n\n""👇 اختر المنصة:", kb.cards_menu())

    elif text in ["⚡ الرشق 📈", "📈 الرشق ⚡", "📈 قسم الرشق"]:
        await send(
            "📈 *خدمات الرشق* ⚡\n""━━━━━━━━━━━━━━━━━\n\n""📸 Instagram · TikTok · YouTube · وأكثر\n""🚀 نمو حقيقي وسريع\n\n""👇 اختر المنصة:",
            kb.smm_menu(),
        )

    elif text in ["🌐 الأرقام 📲", "📲 أرقام 🌐", "📲 قسم الأرقام"]:
        await send("📲 *الأرقام والأرصدة* 🌐\n""━━━━━━━━━━━━━━━━━\n\n""📱 أرقام واتساب · تيليغرام · وأكثر\n""⚡ تسليم فوري وآمن\n\n""👇 اختر الخدمة:", kb.balance_menu())

    elif text in ["💰 شحن الرصيد ⚡", "💰 شحن الرصيد ⚡", "💰 شحن رصيد الحساب"]:
        await send(
            "💰 *شحن رصيد الحساب* ⚡\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "🔄 التحقق التلقائي يضيف الرصيد فوراً\n"
            "🔒 آمن 100% · دعم 24/7\n\n"
            "👇 اختر طريقة الشحن:",
            kb.recharge_methods(),
        )

    elif text in ["📊 حسابي 👤", "👤 حسابي 📊", "👤 معلومات حسابي"]:
        user = db.get_user(update.effective_user.id)
        orders_count = db.count_user_orders(update.effective_user.id)
        loyalty_pts = int(user.get("loyalty_points") or 0)
        username = user.get("username") or user.get("first_name") or "—"
        await update.message.reply_text(
            "👤 *الملف الشخصي*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"🪪 الاسم: `{username}`\n"
            f"🆔 المعرّف: `{user['user_id']}`\n\n"
            f"💰 الرصيد الحالي: *{user['balance']:,.0f} ل.س*\n".replace(",", "،") +
            f"💎 نقاط الولاء: *{loyalty_pts:,}* نقطة\n".replace(",", "،") +
            f"🏅 المستوى: *{user['level']}*\n\n"
            f"📊 إجمالي الشحن: *{user['total_recharged']:,.0f} ل.س*\n".replace(",", "،") +
            f"📦 عدد الطلبات: *{orders_count}*\n"
            "━━━━━━━━━━━━━━━━━",
            reply_markup=kb.back_to_main(),
            parse_mode=ParseMode.MARKDOWN,
        )

    elif text in ["👑 نقاط الولاء 💎", "💎 نقاط الولاء 🏆", "💎 نقاط الولاء"]:
        user_id = update.effective_user.id
        pts = await asyncio.to_thread(db.get_loyalty_points, user_id)
        min_redeem = config.LOYALTY_MIN_REDEEM
        rate = config.LOYALTY_REDEEM_RATE
        earn_pct = config.LOYALTY_EARN_PERCENT
        can_redeem = pts >= min_redeem
        syp_value = pts * rate
        loyalty_text = (
            "💎 *نقاط الولاء*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 رصيد نقاطك: *{pts:,}* نقطة\n"
            f"💰 قيمتها: *{syp_value:,.0f} ل.س*\n\n".replace(",", "،") +
            "📋 *كيف تكسب النقاط؟*\n"
            f"• كل طلب ناجح يكسبك *{earn_pct:.0f}%* من قيمته نقاط\n"
            f"• كل نقطة = *{rate}* ل.س\n"
            f"• الحد الأدنى للاستبدال: *{min_redeem:,}* نقطة\n\n".replace(",", "،") +
            "💡 _ما عليك إلا الشراء — والنقاط تنحسب لك تلقائياً!_"
        )
        if not can_redeem:
            remaining = max(0, min_redeem - pts)
            if remaining > 0:
                loyalty_text += f"\n\n⏳ تحتاج *{remaining:,}* نقطة إضافية للاستبدال.".replace(",", "،")
        await update.message.reply_text(
            loyalty_text,
            reply_markup=kb.loyalty_menu(can_redeem=can_redeem, suggested_redeem=pts if can_redeem else 0),
            parse_mode=ParseMode.MARKDOWN,
        )

    elif text in ["🎁 كود خصم 🎟", "🎟 كود خصم 🎁", "🎟 كود الخصم"]:
        await update.message.reply_text(
            "🎟 *كود الخصم*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "لديك كود خصم؟ اضغط الزر أدناه لإدخاله 👇",
            reply_markup=kb.coupon_entry_button(),
            parse_mode=ParseMode.MARKDOWN,
        )

    elif text in ["💬 الدعم 📞", "📞 الدعم 💬", "📞 التواصل مع الأدمن"]:
        await update.message.reply_text(
            "💬 *الدعم والمساعدة* 🌟\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "⚡ وقت الاستجابة: أقل من 5 دقائق\n"
            "🕐 متاح 24/7 طوال اليوم\n\n"
            "💬 فريقنا جاهز لمساعدتك على مدار الساعة.\n\n"
            f"📩 راسلنا الآن عبر: {config.SUPPORT_USERNAME}\n\n"
            "⏱️ متوسط الرد: أقل من 10 دقائق",
            reply_markup=kb.back_to_main(),
            parse_mode=ParseMode.MARKDOWN,
        )


async def cb_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        await q.edit_message_text("🚫 تم حظرك من استخدام البوت.")
        return
    data = q.data

    if data == "menu:main":
        await _safe_edit(q, "👇 اختر من القائمة أدناه:")

    elif data == "menu:account":
        user = db.get_user(update.effective_user.id)
        orders_count = db.count_user_orders(update.effective_user.id)
        loyalty_pts = int(user.get("loyalty_points") or 0)
        username = user.get("username") or user.get("first_name") or "—"
        text = (
            "👤 *الملف الشخصي*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"🪪 الاسم: `{username}`\n"
            f"🆔 المعرّف: `{user['user_id']}`\n\n"
            f"💰 الرصيد الحالي: *{user['balance']:,.0f} ل.س*\n"
            f"💎 نقاط الولاء: *{loyalty_pts:,}* نقطة\n"
            f"🏅 المستوى: *{user['level']}*\n\n"
            f"📊 إجمالي الشحن: *{user['total_recharged']:,.0f} ل.س*\n"
            f"📦 عدد الطلبات: *{orders_count}*\n"
            "━━━━━━━━━━━━━━━━━"
        )
        await _safe_edit(q, text, reply_markup=kb.back_to_main())

    elif data == "menu:recharge":
        await _safe_edit(
            q,
            "💰 *شحن رصيد الحساب*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "اختر طريقة الدفع المناسبة لك 👇\n\n"
            "⚡ التحقق التلقائي يضيف الرصيد فوراً\n"
            "🛡️ كل العمليات مشفّرة وآمنة",
            reply_markup=kb.recharge_methods(),
        )

    elif data == "menu:store":
        await _safe_edit(q, "👇 اختر من القائمة أدناه:")

    elif data == "menu:subs":
        await _safe_edit(
            q,
            "💎 *اشتراكات التطبيقات*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "اختر التطبيق اللي تبي تفعّل اشتراكه 👇",
            reply_markup=kb.subs_menu(),
        )

    elif data == "menu:smm":
        await _safe_edit(
            q,
            "📈 *خدمات الرشق*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "اختر الخدمة المناسبة لك 👇",
            reply_markup=kb.smm_menu(),
        )

    elif data == "menu:loyalty":
        await _show_loyalty_panel(q, update.effective_user.id)

    elif data == "menu:referral":
        text, markup = await _build_referral_screen(update.effective_user.id, context.bot)
        await _safe_edit(q, text, reply_markup=markup)

    elif data == "menu:support":
        await _safe_edit(
            q,
            "💬 *الدعم والمساعدة* 🌟\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "⚡ وقت الاستجابة: أقل من 5 دقائق\n"
            "🕐 متاح 24/7 طوال اليوم\n\n"
            "💬 فريقنا جاهز لمساعدتك على مدار الساعة.\n\n"
            f"📩 راسلنا الآن عبر: {config.SUPPORT_USERNAME}\n\n"
            "⏱️ متوسط الرد: أقل من 10 دقائق",
            reply_markup=kb.back_to_main(),
        )


# ============= Store callbacks =============
async def _safe_edit(q, text: str, reply_markup=None, parse_mode=ParseMode.MARKDOWN):
    """يعدّل الرسالة سواء كانت نصاً أو صورة (caption). يمنع الفشل الصامت."""
    try:
        await q.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:
        pass
    try:
        await q.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        pass

async def cb_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return
    data = q.data

    if data == "store:games":
        await _safe_edit(
            q,
            "🎮 *الألعاب*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "اختر اللعبة اللي تبي تشحنها 👇\n\n"
            "⚡ التسليم تلقائي خلال دقائق",
            reply_markup=kb.games_menu(),
        )
    elif data == "store:cards":
        await _safe_edit(
            q,
            "💳 *البطاقات الرقمية*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "اختر نوع البطاقة 👇\n\n"
            "📌 كل البطاقات أكواد جاهزة من المخزون\n"
            "⚡ يوصلك الكود فور تأكيد الطلب",
            reply_markup=kb.cards_menu(),
        )
    elif data == "store:subs":
        await _safe_edit(
            q,
            "💎 *اشتراكات التطبيقات*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "اختر التطبيق اللي تبي تشترك فيه 👇\n\n"
            "📩 يُفعَّل الاشتراك على إيميل/يوزر تدخله وقت الطلب\n"
            "⏱️ التفعيل خلال دقائق إلى ساعات حسب التطبيق",
            reply_markup=kb.subs_menu(),
        )
    elif data == "store:balance":
        await _safe_edit(
            q,
            "📱 *تعبئة الجوال*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "اختر شبكتك 👇\n\n"
            "⚡ التعبئة مباشرة على رقمك خلال دقائق\n"
            "📞 يُطلب رقم الجوال وقت الطلب",
            reply_markup=kb.balance_menu(),
        )
    elif data == "store:smm":
        await _safe_edit(
            q,
            "📈 *خدمات الرشق*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "متابعين • لايكات • مشاهدات\n\n"
            "اختر الخدمة 👇\n\n"
            "🔗 يُطلب رابط الحساب أو المنشور وقت الطلب\n"
            "⚡ معظم الخدمات تبدأ خلال 0-24 ساعة",
            reply_markup=kb.smm_menu(),
        )
    elif data == "store:pubg":
        await _safe_edit(
            q,
            "🎯 *PUBG MOBILE* 🏆\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "🥇 اللعبة الأكثر شعبية في العالم\n"
            "⚡ شحن فوري · 🔒 مضمون\n\n"
            "👇 اختر القسم:",
            reply_markup=kb.pubg_sections(),
        )
    elif data == "store:freefire":
        await _safe_edit(
            q,
            "🔥 *FREE FIRE* 💎\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "💫 شحن ماسات فوري وآمن\n"
            "⚡ تسليم خلال ثوانٍ معدودة\n\n"
            "👇 اختر القسم:",
            reply_markup=kb.freefire_sections(),
        )
    elif data == "store:supercell":
        await _safe_edit(
            q,
            "🏰 *ألعاب Supercell* ⚔️\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "🪄 Clash of Clans · Clash Royale · Brawl Stars\n"
            "📌 الشحن بإيميل Supercell ID\n\n"
            "👇 اختر اللعبة:",
            reply_markup=kb.supercell_sections(),
        )
    elif data == "store:cod":
        await _safe_edit(
            q,
            "🪖 *كول أوف ديوتي موبايل*\n\n"
            "اختر القسم 👇\n\n"
            "💎 *شدات:* Player ID + إيميل + واتساب\n"
            "🎫 *Battle Pass:* Player ID فقط",
            reply_markup=kb.cod_sections(),
        )
    elif data == "store:delta":
        await _send_fastcard_list(q, "df")
    elif data == "store:minecraft":
        await _send_fastcard_list(q, "mc")
    elif data == "store:fortnite":
        await _send_fastcard_list(q, "fn")
    elif data == "store:ludo":
        await _safe_edit(
            q,
            "🎲 *ألعاب لودو*\n\n"
            "اختر اللعبة 👇\n\n"
            "📌 الشحن مباشر بإدخال Player ID",
            reply_markup=kb.ludo_sections(),
        )


async def cb_pubg_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return
    data = q.data

    if data == "pubg:uc":
        await _safe_edit(
            q,
            "🎯 *PUBG MOBILE — شدات*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "⚡ شحن تلقائي فوري خلال ثوانٍ\n"
            "🔒 آمن 100% · مضمون أو يُرد المبلغ\n\n"
            "👇 اختر الباقة المناسبة:",
            reply_markup=kb.pubg_uc_offers(),
        )
    elif data == "pubg:membership":
        await _send_fastcard_list(q, "pm")
    elif data == "pubg:codes":
        await _send_fastcard_list(q, "pc")


async def _send_fastcard_list(q, prefix: str):
    cat = config.FASTCARD_CATEGORIES.get(prefix)
    if not cat:
        return
    fields = cat.get("input_fields", [])
    has_password = any(f.get("type") == "password" for f in fields)

    # ===== أقسام مفتوحة المبلغ (الزبون يكتب القيمة بنفسه) =====
    if cat.get("custom_amount"):
        min_a = int(cat.get("min_amount", 1000))
        max_a = int(cat.get("max_amount", 1000000))
        markup = int(cat.get("markup_pct", 10))
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        intro = (
            f"{cat['title']}\n\n"
            "💸 *اختار المبلغ يلي بدّك ياه بنفسك* — اكتبلي قديش بدّك بالليرة السورية وأنا "
            "بحسبلك السعر فوراً.\n\n"
            f"🔢 الحد الأدنى: {min_a:,} ل.س\n".replace(",", "،") +
            f"🔝 الحد الأعلى: {max_a:,} ل.س\n\n".replace(",", "،") +
            f"📊 *العمولة:* {markup}% فقط (بتنضاف على المبلغ).\n\n"
            "👇 اضغط الزر تحت لتبدا."
        )
        kb_amt = InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ اكتب المبلغ يلي بدّك", callback_data=f"fcamt:{prefix}")],
            [InlineKeyboardButton("⬅️ رجوع", callback_data=cat.get("back_callback", "menu:main"))],
        ])
        await _safe_edit(q, intro, reply_markup=kb_amt)
        return

    import sys
    offers = getattr(sys.modules["bot.config"], cat["offers_attr"], [])
    if not offers:
        await _safe_edit(
            q,
            f"{cat['title']}\n\n"
            "🔧 هذا القسم قيد التجهيز حالياً، رح تتوفر العروض قريباً جداً.\n"
            "شكراً لصبرك 🌷",
            reply_markup=kb.fastcard_offers_list(prefix),
        )
        return

    if not fields:
        intro = (
            f"{cat['title']}\n\n"
            "🔶 *اختر حزمة:* 👇\n\n"
            "_هذي أكواد جاهزة — بعد التأكيد يوصلك الكود فوراً 🎟️_"
        )
    elif has_password:
        intro = (
            f"{cat['title']}\n\n"
            "🔶 *اختر حزمة:* 👇\n\n"
            "📌 *كيف الشحن؟*\n"
            "1️⃣ تختار العرض\n"
            "2️⃣ تدخل إيميل وكلمة مرور حساب Supercell ID\n"
            "3️⃣ نشحن الجواهر مباشرة على حسابك بدقائق\n\n"
            "🔒 *تنبيه أمني:* بعد ما يوصلك الشحن، يفضّل تغيّر كلمة المرور وتفعّل الحماية الثنائية."
        )
    elif len(fields) == 1 and fields[0].get("type") == "id":
        intro = (
            f"{cat['title']}\n\n"
            "🔶 *اختر حزمة:* 👇\n\n"
            "_(اختر العرض، ادخل Player ID، وسيتم التنفيذ مباشرة خلال ثوانٍ ✨)_"
        )
    else:
        field_labels = " + ".join(f.get("label", f["key"]).split("(")[0].strip() for f in fields)
        intro = (
            f"{cat['title']}\n\n"
            "🔶 *اختر حزمة:* 👇\n\n"
            f"📌 *البيانات اللي بنحتاجها:* {field_labels}"
        )

    markup = kb.fastcard_offers_list(prefix)
    await _safe_edit(q, intro, reply_markup=markup)


async def cb_supercell_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يوجّه لأقسام Supercell الفرعية: Brawl Stars / CoC / CR / Hay Day."""
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return
    parts = q.data.split(":", 1)
    if len(parts) != 2:
        return
    prefix = parts[1]
    if prefix not in ("bs", "coc", "cr", "hd"):
        return
    await _send_fastcard_list(q, prefix)


async def cb_cod_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يوجّه لأقسام COD الفرعية: شدات (cod) / Battle Pass (cdbp)."""
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return
    parts = q.data.split(":", 1)
    if len(parts) != 2:
        return
    sub = parts[1]
    mapping = {"packs": "cod", "bp": "cdbp"}
    prefix = mapping.get(sub)
    if not prefix:
        return
    await _send_fastcard_list(q, prefix)


async def cb_ludo_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يوجّه لأقسام Ludo الفرعية: World / Club / Yalla."""
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return
    parts = q.data.split(":", 1)
    if len(parts) != 2:
        return
    prefix = parts[1]
    if prefix not in ("lw", "lc", "yl"):
        return
    await _send_fastcard_list(q, prefix)


async def cb_cards_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يوجّه قسم البطاقات: قائمة المنصة → دول → عروض."""
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return
    parts = q.data.split(":", 1)
    if len(parts) != 2:
        return
    sub = parts[1]

    if sub == "menu":
        await _safe_edit(
            q,
            "💳 *البطاقات*\n\n"
            "اختر نوع البطاقة 👇\n\n"
            "📌 كل البطاقات أكواد جاهزة من المخزون — يوصلك الكود فور التأكيد.",
            reply_markup=kb.cards_menu(),
        )
        return

    titles = {
        "psn":      ("🎮 *PlayStation (PSN)*", "اختر الدولة 👇"),
        "steam":    ("🚂 *Steam*", "اختر الدولة 👇"),
        "itunes":   ("🍎 *iTunes*", "اختر الدولة 👇"),
        "gplay":    ("📱 *Google Play*", "اختر الدولة 👇"),
        "xbox":     ("🎮 *Xbox*", "اختر الدولة 👇"),
        "razer":    ("🟢 *Razer Gold*", "اختر المنطقة 👇"),
        "roblox":   ("🎮 *Roblox*", "اختر المنطقة 👇"),
        "valorant": ("🔫 *Valorant*", "اختر المنطقة 👇"),
    }
    if sub not in titles:
        return
    title, hint = titles[sub]
    await _safe_edit(
        q,
        f"{title}\n\n{hint}",
        reply_markup=kb.cards_platform_menu(sub),
    )


# ============= PUBG UC purchase (auto via Fastcard API) =============
async def cb_pubg_uc_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يطلب Player ID قبل ما يدفع."""
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return ConversationHandler.END

    offer_id = q.data.split(":", 1)[1]
    offer = next((o for o in config.PUBG_UC_OFFERS if o["id"] == offer_id), None)
    if not offer:
        return ConversationHandler.END

    user = db.get_user(update.effective_user.id)
    if (user["balance"] or 0) < config.get_offer_price(offer):
        await _safe_edit(
            q,
            f"❌ رصيدك غير كافٍ.\n\nالعرض: *{offer['label']}*\n"
            f"السعر: {config.get_offer_price(offer)} ل.س\nرصيدك: {user['balance']:.0f} ل.س\n\n"
            "اشحن رصيدك أولاً.",
            reply_markup=kb.insufficient_balance(),
        )
        return ConversationHandler.END

    context.user_data["pubg_offer_id"] = offer_id
    await _safe_edit(
        q,
        f"💎 *{offer['label']} — {config.get_offer_price(offer)} ل.س*\n\n"
        f"رصيدك: {user['balance']:.0f} ل.س\n\n"
        "🎮 *أدخل Player ID*\n"
        "━━━━━━━━━━━━━\n\n"
        "📍 تجده في ببجي: الملف الشخصي → الزاوية اليسرى\n\n"
        "👇 أرسل الرقم الآن:",
        reply_markup=kb.cancel_inline(),
    )
    return PUBG_PLAYER_ID


async def msg_pubg_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text.isdigit() or not (5 <= len(text) <= 15):
        await update.message.reply_text(
            "⚠️ Player ID يجب يكون أرقام فقط (بين 5 و 15 خانة). جرّب مرة ثانية:",
            reply_markup=kb.cancel_inline(),
        )
        return PUBG_PLAYER_ID

    offer_id = context.user_data.get("pubg_offer_id")
    offer = next((o for o in config.PUBG_UC_OFFERS if o["id"] == offer_id), None) if offer_id else None
    if not offer:
        await update.message.reply_text(
            "⚠️ انتهت الجلسة، ارجع للمتجر وابدأ من جديد.",
            reply_markup=kb.back_to_main(),
        )
        return ConversationHandler.END

    context.user_data["pubg_player_id"] = text
    user = db.get_user(update.effective_user.id)

    # عروض تتطلب تحقق من اسم اللاعب قبل الشحن — لا يُسمح بالطلب بدون تحقق
    if offer.get("verify") and not fastcard_web.is_enabled():
        await update.message.reply_text(
            "⚠️ خدمة التحقق من الاسم لهذا العرض غير متاحة حالياً. اختر عرضاً آخر أو تواصل مع الدعم.",
            reply_markup=kb.back_to_main(),
        )
        return ConversationHandler.END

    if offer.get("verify") and fastcard_web.is_enabled():
        verify_cost_syp = round(config.FASTCARD_VERIFY_COST_USD * config.get_syp_per_usd())
        await update.message.reply_text(
            f"💎 *{offer['label']}*\n\n"
            f"🎮 Player ID: `{text}`\n"
            f"💰 سعر الشحن: {config.get_offer_price(offer)} ل.س\n"
            f"💼 رصيدك: {user['balance']:.0f} ل.س\n\n"
            f"⚠️ هاد العرض بدو *تحقق من اسم اللاعب* قبل الشراء.\n"
            f"رح يخصم من رصيدك {verify_cost_syp:.0f} ل.س لقاء التحقق "
            f"(غير قابل للاسترجاع حتى لو ألغيت الشحن).\n\n"
            "اضغط تحقق ليطلع لك اسم اللاعب وتأكدلو قبل الشحن.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.pubg_uc_verify(offer_id, verify_cost_syp),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"💎 *{offer['label']}*\n\n"
        f"🎮 Player ID: `{text}`\n"
        f"💰 السعر: {config.get_offer_price(offer)} ل.س\n"
        f"💼 رصيدك: {user['balance']:.0f} ل.س\n\n"
        "⚠️ تأكد من Player ID كويس. بعد التأكيد ما فينا نستردّ الطلب.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.pubg_uc_confirm(offer_id, config.get_offer_price(offer)),
    )
    return ConversationHandler.END


async def cb_pubg_uc_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحقق من اسم اللاعب عبر موقع فاست كارد قبل الشراء."""
    q = update.callback_query
    await q.answer("جاري التحقق...")
    if await is_banned(update):
        return

    offer_id = q.data.split(":", 1)[1]
    offer = next((o for o in config.PUBG_UC_OFFERS if o["id"] == offer_id), None)
    if not offer or not offer.get("verify"):
        return

    player_id = context.user_data.get("pubg_player_id")
    if not player_id:
        await _safe_edit(q, "⚠️ انتهت الجلسة. اضغط /start وابدأ من جديد.", reply_markup=kb.back_to_main())
        return

    if not fastcard_web.is_enabled():
        await _safe_edit(q, "⚠️ خدمة التحقق من الاسم غير مفعّلة حالياً. تواصل مع الدعم.", reply_markup=kb.back_to_main())
        return

    user_id = update.effective_user.id
    user = db.get_user(user_id)
    verify_cost_syp = round(config.FASTCARD_VERIFY_COST_USD * config.get_syp_per_usd())
    offer_price = config.get_offer_price(offer)

    if (user["balance"] or 0) < verify_cost_syp:
        await _safe_edit(
            q,
            f"❌ رصيدك غير كافٍ للتحقق.\n\nالتكلفة: {verify_cost_syp:.0f} ل.س\nرصيدك: {user['balance']:.0f} ل.س",
            reply_markup=kb.insufficient_balance(),
        )
        return

    # نخصم تكلفة التحقق فوراً (غير قابلة للاسترجاع)
    db.update_balance(user_id, -verify_cost_syp)

    await _safe_edit(
        q,
        f"⏳ جاري التحقق من Player ID: `{player_id}`...",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        resp = await asyncio.to_thread(fastcard_web.check_player, player_id, int(offer["product_id"]))
    except fastcard_web.FastcardWebError as e:
        # فشل اتصال → نرجّع تكلفة التحقق
        db.update_balance(user_id, verify_cost_syp)
        logger.warning("fastcard_web.check_player error: %s", e)
        await context.bot.send_message(
            user_id,
            f"❌ تعذّر التحقق من الاسم وتم استرجاع المبلغ.\nالسبب: {e.message}",
            reply_markup=kb.back_to_main(),
        )
        return

    if not resp.get("success"):
        # رد سلبي (مثلاً ID غير موجود) — التكلفة ما بترجع لأن الموقع خصمها فعلاً
        msg = str(resp.get("message") or "اللاعب غير موجود")
        await context.bot.send_message(
            user_id,
            f"❌ *لم يتم العثور على اللاعب.*\n\nPlayer ID: `{player_id}`\nرسالة الموقع: {msg}\n\n"
            "تأكد من الرقم وحاول مرة ثانية.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back_to_main(),
        )
        return

    name = fastcard_web.extract_player_name(resp) or "—"
    context.user_data["pubg_verified_name"] = name
    user2 = db.get_user(user_id)
    await context.bot.send_message(
        user_id,
        f"✅ *تم التحقق من الاسم بنجاح*\n\n"
        f"🎮 Player ID: `{player_id}`\n"
        f"👤 اسم اللاعب: *{name}*\n\n"
        f"💎 العرض: {offer['label']}\n"
        f"💰 السعر: {offer_price:.0f} ل.س\n"
        f"💼 رصيدك: {user2['balance']:.0f} ل.س\n\n"
        "⚠️ تأكد من الاسم. بعد التأكيد ما فينا نستردّ الطلب.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.pubg_uc_confirm(offer_id, offer_price),
    )


async def cb_pubg_uc_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنفيذ الطلب عبر Fastcard API."""
    q = update.callback_query
    await q.answer("جاري الإرسال للمتجر...")
    if await is_banned(update):
        return

    offer_id = q.data.split(":", 1)[1]
    offer = next((o for o in config.PUBG_UC_OFFERS if o["id"] == offer_id), None)
    if not offer:
        return

    player_id = context.user_data.get("pubg_player_id")
    if not player_id:
        await _safe_edit(q, "⚠️ انتهت الجلسة. اضغط /start وابدأ من جديد.", reply_markup=kb.back_to_main())
        return

    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if (user["balance"] or 0) < config.get_offer_price(offer):
        await _safe_edit(q, "❌ رصيدك غير كافٍ. اشحن أولاً.", reply_markup=kb.insufficient_balance())
        return

    if not fastcard.is_enabled():
        await _safe_edit(q, "⚠️ التكامل مع المتجر غير مفعّل حالياً. تواصل مع الدعم.", reply_markup=kb.back_to_main())
        return

    # خصم الرصيد فوراً + إنشاء سجل طلب + استدعاء API
    db.update_balance(user_id, -config.get_offer_price(offer))
    api_uuid = str(uuid.uuid4())
    order_id = db.create_order(
        user_id, "PUBG", offer["label"], config.get_offer_price(offer), player_id, api_uuid=api_uuid,
    )

    await _safe_edit(
        q,
        f"⏳ *جاري معالجة طلبك...*\n\n"
        f"💎 {offer['label']}\n"
        f"🎮 Player ID: `{player_id}`\n"
        f"📋 رقم الطلب: #{order_id}\n\n"
        "_بترجعلك النتيجة بعد ثوانٍ_",
    )

    _start_ts = time.time()
    # العروض اللي بدها تحقق (مثل uc_60v) منمرّرها عبر endpoint الموقع نفسه
    # (order-handler.php) لأن seller API ما بينفّذها تلقائياً.
    use_web = bool(offer.get("verify")) and fastcard_web.is_enabled()

    try:
        if use_web:
            web_resp = await asyncio.to_thread(
                fastcard_web.place_order,
                offer["product_id"],
                player_id=player_id,
                quantity=1,
            )
            # نلفّ الرد بشكل شبيه بـ seller API حتى يكمل بقية الكود
            success = bool(web_resp.get("success"))
            result = {
                "order_id": str(web_resp.get("order_id") or web_resp.get("id") or ""),
                "status": "accept" if success else "reject",
                "replay_api": [str(web_resp.get("message") or web_resp.get("data") or "")],
                "_raw": web_resp,
            }
            if not success:
                raise fastcard.FastcardError(str(web_resp.get("message") or "فشل الطلب عبر الموقع"))
        else:
            result = await asyncio.to_thread(
                fastcard.new_order,
                offer["product_id"],
                player_id=player_id,
                order_uuid=api_uuid,
            )
    except (fastcard.FastcardError, fastcard_web.FastcardWebError) as e:
        # فشل الإنشاء → استرجاع المبلغ
        db.update_balance(user_id, config.get_offer_price(offer))
        db.update_order_api(order_id, status="rejected", api_response=str(e))
        logger.error(f"new_order failed: {e}")
        await context.bot.send_message(
            user_id,
            f"❌ تعذّر تنفيذ الطلب وتم استرجاع المبلغ كاملاً لرصيدك.\n\n"
            f"السبب: {e.message}\n"
            f"رقم الطلب: #{order_id}",
            reply_markup=kb.back_to_main(),
        )
        if config.ADMIN_ID:
            try:
                await notify.notify_admin(
                    context.bot,
                    f"⚠️ *فشل طلب PUBG API* #{order_id}\nUser: {user_id}\n"
                    f"الخطأ: {e.message}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
        context.user_data.pop("pubg_offer_id", None)
        context.user_data.pop("pubg_player_id", None); context.user_data.pop("pubg_verified_name", None)
        return

    api_order_id = str(result.get("order_id") or "")
    final_status = (result.get("status") or "").lower()
    final_data = result
    db.update_order_api(order_id, api_order_id=api_order_id, api_response=config.sanitize_for_storage(result))

    # polling لو الحالة لسة بـ processing
    elapsed = 0
    while elapsed < config.FASTCARD_POLL_TIMEOUT and final_status in ("processing", "wait", "pending", ""):
        await asyncio.sleep(config.FASTCARD_POLL_INTERVAL)
        elapsed += config.FASTCARD_POLL_INTERVAL
        try:
            info = await asyncio.to_thread(fastcard.check_order, api_uuid, by_uuid=True)
            if info:
                final_data = info
                final_status = (info.get("status") or "").lower()
        except fastcard.FastcardError as e:
            logger.warning(f"poll attempt failed: {e}")
            continue

    db.update_order_api(order_id, status=final_status or "unknown", api_response=config.sanitize_for_storage(final_data))

    accepted = final_status in ("accept", "accepted", "completed", "done", "success")
    rejected = final_status in ("reject", "rejected", "fail", "failed", "refund", "refunded", "canceled", "cancelled")

    if accepted:
        took = max(0, int(round(time.time() - _start_ts)))
        new_user = db.get_user(user_id)
        await context.bot.send_message(
            user_id,
            f"✅ *تم تنفيذ طلبك بنجاح!*\n\n"
            f"💎 العرض: {offer['label']}\n"
            f"🎮 Player ID: `{player_id}`\n"
            f"💰 السعر: {config.get_offer_price(offer)} ل.س\n"
            f"📋 رقم الطلب: #{order_id}\n"
            f"💼 رصيدك الجديد: {new_user['balance']:.0f} ل.س\n"
            f"⏱ مدة التنفيذ: {took} ثانية\n\n"
            "✨ الشدات أُضيفت على حسابك ببجي مباشرة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back_to_main(),
        )
        await grant_loyalty_for_order(context.bot, user_id, float(config.get_offer_price(offer)))
        await send_rating_prompt(context.bot, user_id, order_id, offer.get("label", ""))
        if config.ADMIN_ID:
            try:
                uname = user.get("username") or user.get("first_name") or "—"
                await notify.notify_admin(
                    context.bot,
                    f"💰 *بيع تلقائي عبر API* #{order_id}\n\n"
                    f"المستخدم: @{uname} ({user_id})\n"
                    f"العرض: {offer['label']}\n"
                    f"Player ID: `{player_id}`\n"
                    f"السعر للزبون: {config.get_offer_price(offer)} ل.س\n"
                    f"API Order: `{api_order_id}`",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as e:
                logger.error(f"admin notify failed: {e}")
    elif rejected:
        # استرجاع المبلغ
        db.update_balance(user_id, config.get_offer_price(offer))
        await context.bot.send_message(
            user_id,
            f"❌ *المتجر رفض الطلب وتم استرجاع المبلغ كاملاً.*\n\n"
            f"📋 رقم الطلب: #{order_id}\n"
            f"الحالة: {final_status}\n\n"
            "تأكد من Player ID وجرّب مرة ثانية، أو تواصل مع الدعم.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back_to_main(),
        )
        if config.ADMIN_ID:
            try:
                await notify.notify_admin(
                    context.bot,
                    f"⚠️ *طلب مرفوض* #{order_id}\nUser: {user_id}\nPlayer ID: `{player_id}`\nالحالة: {final_status}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
    else:
        # ما زال processing بعد التايم آوت — لا نسترجع، ولا نزعج المستخدم أو الأدمن
        pass

    context.user_data.pop("pubg_offer_id", None)
    context.user_data.pop("pubg_player_id", None); context.user_data.pop("pubg_verified_name", None)


# ============= Free Fire =============
async def cb_freefire_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return
    data = q.data

    if data == "ff:diamonds":
        await _safe_edit(
            q,
            "💎 *جواهر فري فاير — شحن تلقائي مباشر*\n\n"
            "اختر الباقة، ثم ادخل Player ID وستصلك الجواهر على حسابك خلال ثوانٍ:",
            reply_markup=kb.freefire_diamond_offers(),
        )
    elif data == "ff:membership":
        await _send_fastcard_list(q, "fm")
    elif data == "ff:codes":
        await _send_fastcard_list(q, "fc")


# ============= Free Fire diamonds purchase (auto via Fastcard API) =============
async def cb_freefire_diamond_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return ConversationHandler.END

    offer_id = q.data.split(":", 1)[1]
    offer = next((o for o in config.FREEFIRE_DIAMOND_OFFERS if o["id"] == offer_id), None)
    if not offer:
        return ConversationHandler.END

    user = db.get_user(update.effective_user.id)
    if (user["balance"] or 0) < config.get_offer_price(offer):
        await _safe_edit(
            q,
            f"❌ رصيدك غير كافٍ.\n\nالعرض: *{offer['label']}*\n"
            f"السعر: {config.get_offer_price(offer)} ل.س\nرصيدك: {user['balance']:.0f} ل.س\n\n"
            "اشحن رصيدك أولاً.",
            reply_markup=kb.insufficient_balance(),
        )
        return ConversationHandler.END

    context.user_data["ff_offer_id"] = offer_id
    await _safe_edit(
        q,
        f"💎 *{offer['label']} — {config.get_offer_price(offer)} ل.س*\n\n"
        f"رصيدك: {user['balance']:.0f} ل.س\n\n"
        "📝 ابعت الـ *Player ID* تبعك (الرقم الموجود بحسابك فري فاير):",
        reply_markup=kb.cancel_inline(),
    )
    return FREEFIRE_PLAYER_ID


async def msg_freefire_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text.isdigit() or not (5 <= len(text) <= 15):
        await update.message.reply_text(
            "⚠️ Player ID يجب يكون أرقام فقط (بين 5 و 15 خانة). جرّب مرة ثانية:",
            reply_markup=kb.cancel_inline(),
        )
        return FREEFIRE_PLAYER_ID

    offer_id = context.user_data.get("ff_offer_id")
    offer = next((o for o in config.FREEFIRE_DIAMOND_OFFERS if o["id"] == offer_id), None) if offer_id else None
    if not offer:
        await update.message.reply_text(
            "⚠️ انتهت الجلسة، ارجع للمتجر وابدأ من جديد.",
            reply_markup=kb.back_to_main(),
        )
        return ConversationHandler.END

    context.user_data["ff_player_id"] = text
    user = db.get_user(update.effective_user.id)
    await update.message.reply_text(
        f"💎 *{offer['label']}*\n\n"
        f"🎮 Player ID: `{text}`\n"
        f"💰 السعر: {config.get_offer_price(offer)} ل.س\n"
        f"💼 رصيدك: {user['balance']:.0f} ل.س\n\n"
        "⚠️ تأكد من Player ID كويس. بعد التأكيد ما فينا نستردّ الطلب.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.freefire_diamond_confirm(offer_id, config.get_offer_price(offer)),
    )
    return ConversationHandler.END


async def cb_freefire_diamond_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنفيذ طلب جواهر فري فاير عبر Fastcard API."""
    q = update.callback_query
    await q.answer("جاري الإرسال للمتجر...")
    if await is_banned(update):
        return

    offer_id = q.data.split(":", 1)[1]
    offer = next((o for o in config.FREEFIRE_DIAMOND_OFFERS if o["id"] == offer_id), None)
    if not offer:
        return

    player_id = context.user_data.get("ff_player_id")
    if not player_id:
        await q.edit_message_text(
            "⚠️ انتهت الجلسة. اضغط /start وابدأ من جديد.",
            reply_markup=kb.back_to_main(),
        )
        return

    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if (user["balance"] or 0) < config.get_offer_price(offer):
        await q.edit_message_text(
            "❌ رصيدك غير كافٍ. اشحن أولاً.",
            reply_markup=kb.insufficient_balance(),
        )
        return

    if not fastcard.is_enabled():
        await q.edit_message_text(
            "⚠️ التكامل مع المتجر غير مفعّل حالياً. تواصل مع الدعم.",
            reply_markup=kb.back_to_main(),
        )
        return

    db.update_balance(user_id, -config.get_offer_price(offer))
    api_uuid = str(uuid.uuid4())
    order_id = db.create_order(
        user_id, "FREEFIRE", offer["label"], config.get_offer_price(offer), player_id, api_uuid=api_uuid,
    )

    await q.edit_message_text(
        f"⏳ *جاري معالجة طلبك...*\n\n"
        f"💎 {offer['label']}\n"
        f"🎮 Player ID: `{player_id}`\n"
        f"📋 رقم الطلب: #{order_id}\n\n"
        "_بترجعلك النتيجة بعد ثوانٍ_",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        result = await asyncio.to_thread(
            fastcard.new_order,
            offer["product_id"],
            player_id=player_id,
            order_uuid=api_uuid,
        )
    except fastcard.FastcardError as e:
        db.update_balance(user_id, config.get_offer_price(offer))
        db.update_order_api(order_id, status="rejected", api_response=str(e))
        logger.error(f"FF new_order failed: {e}")
        await context.bot.send_message(
            user_id,
            f"❌ تعذّر تنفيذ الطلب وتم استرجاع المبلغ كاملاً لرصيدك.\n\n"
            f"السبب: {e.message}\n"
            f"رقم الطلب: #{order_id}",
            reply_markup=kb.back_to_main(),
        )
        if config.ADMIN_ID:
            try:
                await notify.notify_admin(
                    context.bot,
                    f"⚠️ *فشل طلب فري فاير API* #{order_id}\nUser: {user_id}\n"
                    f"الخطأ: {e.message}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
        context.user_data.pop("ff_offer_id", None)
        context.user_data.pop("ff_player_id", None)
        return

    api_order_id = str(result.get("order_id") or "")
    final_status = (result.get("status") or "").lower()
    final_data = result
    db.update_order_api(order_id, api_order_id=api_order_id, api_response=config.sanitize_for_storage(result))

    elapsed = 0
    while elapsed < config.FASTCARD_POLL_TIMEOUT and final_status in ("processing", "wait", "pending", ""):
        await asyncio.sleep(config.FASTCARD_POLL_INTERVAL)
        elapsed += config.FASTCARD_POLL_INTERVAL
        try:
            info = await asyncio.to_thread(fastcard.check_order, api_uuid, by_uuid=True)
            if info:
                final_data = info
                final_status = (info.get("status") or "").lower()
        except fastcard.FastcardError as e:
            logger.warning(f"FF poll attempt failed: {e}")
            continue

    db.update_order_api(order_id, status=final_status or "unknown", api_response=config.sanitize_for_storage(final_data))

    accepted = final_status in ("accept", "accepted", "completed", "done", "success")
    rejected = final_status in ("reject", "rejected", "fail", "failed", "refund", "refunded", "canceled", "cancelled")

    if accepted:
        replay = final_data.get("replay_api") or []
        extra = ""
        if isinstance(replay, list) and replay:
            val = str(replay[0]).strip()
            if val:
                extra = f"\n📩 رد المتجر: `{val}`"
        new_user = db.get_user(user_id)
        await context.bot.send_message(
            user_id,
            f"✅ *تم تنفيذ طلبك بنجاح!*\n\n"
            f"💎 العرض: {offer['label']}\n"
            f"🎮 Player ID: `{player_id}`\n"
            f"💰 السعر: {config.get_offer_price(offer)} ل.س\n"
            f"📋 رقم الطلب: #{order_id}\n"
            f"💼 رصيدك الجديد: {new_user['balance']:.0f} ل.س"
            f"{extra}\n\n"
            "✨ الجواهر أُضيفت على حسابك فري فاير مباشرة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back_to_main(),
        )
        await grant_loyalty_for_order(context.bot, user_id, float(config.get_offer_price(offer)))
        await send_rating_prompt(context.bot, user_id, order_id, offer.get("label", ""))
        if config.ADMIN_ID:
            try:
                uname = user.get("username") or user.get("first_name") or "—"
                await notify.notify_admin(
                    context.bot,
                    f"💰 *بيع تلقائي عبر API (فري فاير)* #{order_id}\n\n"
                    f"المستخدم: @{uname} ({user_id})\n"
                    f"العرض: {offer['label']}\n"
                    f"Player ID: `{player_id}`\n"
                    f"السعر للزبون: {config.get_offer_price(offer)} ل.س\n"
                    f"API Order: `{api_order_id}`",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as e:
                logger.error(f"admin notify failed: {e}")
    elif rejected:
        db.update_balance(user_id, config.get_offer_price(offer))
        await context.bot.send_message(
            user_id,
            f"❌ *المتجر رفض الطلب وتم استرجاع المبلغ كاملاً.*\n\n"
            f"📋 رقم الطلب: #{order_id}\n"
            f"الحالة: {final_status}\n\n"
            "تأكد من Player ID وجرّب مرة ثانية، أو تواصل مع الدعم.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back_to_main(),
        )
        if config.ADMIN_ID:
            try:
                await notify.notify_admin(
                    context.bot,
                    f"⚠️ *طلب فري فاير مرفوض* #{order_id}\nUser: {user_id}\nPlayer ID: `{player_id}`\nالحالة: {final_status}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
    else:
        # ما زال processing بعد التايم آوت — لا نزعج المستخدم أو الأدمن
        pass

    context.user_data.pop("ff_offer_id", None)
    context.user_data.pop("ff_player_id", None)


# ============= Generic Fastcard auto-delivery (memberships + codes) =============
async def cb_fastcard_list_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رجوع لقائمة قسم تلقائي (مثلاً من شاشة التأكيد)."""
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return
    parts = q.data.split(":", 1)
    if len(parts) != 2:
        return
    prefix = parts[1]
    await _send_fastcard_list(q, prefix)


async def cb_fastcard_sold_out(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("🔴 نفد المخزون حالياً، جرّب لاحقاً", show_alert=True)


async def cb_fastcard_amount_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نقطة دخول لقسم رصيد مفتوح المبلغ. يطلب من الزبون كتابة المبلغ."""
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return ConversationHandler.END
    parts = q.data.split(":", 1)  # fcamt:<prefix>
    if len(parts) != 2:
        return ConversationHandler.END
    prefix = parts[1]
    cat = config.FASTCARD_CATEGORIES.get(prefix)
    if not cat or not cat.get("custom_amount"):
        return ConversationHandler.END

    user = db.get_user(update.effective_user.id)
    min_a = int(cat.get("min_amount", 1000))
    max_a = int(cat.get("max_amount", 1000000))
    markup = int(cat.get("markup_pct", 10))

    context.user_data["fc_prefix"] = prefix
    context.user_data["fc_fields"] = {}
    context.user_data["fc_field_idx"] = 0
    context.user_data.pop("fc_custom_offer", None)
    context.user_data.pop("fc_offer_id", None)

    await _safe_edit(
        q,
        f"{cat['title']}\n\n"
        f"💼 رصيدك الحالي: {user['balance']:,.0f} ل.س\n\n".replace(",", "،") +
        "✍️ *اكتب المبلغ يلي بدّك* بالليرة السورية (أرقام فقط):\n"
        f"_مثال: 10000 يعني تشحن 10,000 ل.س_\n\n".replace(",", "،") +
        f"🔢 الحد الأدنى: {min_a:,} ل.س\n".replace(",", "،") +
        f"🔝 الحد الأعلى: {max_a:,} ل.س\n".replace(",", "،") +
        f"📊 العمولة: {markup}%",
        reply_markup=kb.cancel_inline(),
    )
    return FASTCARD_CUSTOM_AMOUNT


async def msg_fastcard_custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل المبلغ من الزبون، يبني عرض ديناميكي، ويطلب رقم الجوال."""
    text = (update.message.text or "").strip()
    # تنظيف: شيل الفواصل والنقاط والرموز العربية
    cleaned = (
        text.replace(",", "")
            .replace("،", "")
            .replace(".", "")
            .replace(" ", "")
            .replace("ل.س", "")
            .replace("ل.س.", "")
            .replace("ليرة", "")
            .strip()
    )
    # حول الأرقام العربية لأرقام لاتينية
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for i, d in enumerate(arabic_digits):
        cleaned = cleaned.replace(d, str(i))

    prefix = context.user_data.get("fc_prefix")
    cat = config.FASTCARD_CATEGORIES.get(prefix) if prefix else None
    if not cat or not cat.get("custom_amount"):
        await update.message.reply_text(
            "⚠️ انتهت الجلسة، ارجع للمتجر وابدأ من جديد.",
            reply_markup=kb.back_to_main(),
        )
        return ConversationHandler.END

    if not cleaned.isdigit():
        await update.message.reply_text(
            "⚠️ المبلغ لازم يكون أرقام فقط. مثال: `10000`\nأعد الإدخال:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.cancel_inline(),
        )
        return FASTCARD_CUSTOM_AMOUNT

    amount = int(cleaned)
    min_a = int(cat.get("min_amount", 1000))
    max_a = int(cat.get("max_amount", 1000000))

    if amount < min_a:
        await update.message.reply_text(
            f"⚠️ الحد الأدنى هو {min_a:,} ل.س.\nأعد الإدخال:".replace(",", "،"),
            reply_markup=kb.cancel_inline(),
        )
        return FASTCARD_CUSTOM_AMOUNT
    if amount > max_a:
        await update.message.reply_text(
            f"⚠️ الحد الأعلى هو {max_a:,} ل.س.\nأعد الإدخال:".replace(",", "،"),
            reply_markup=kb.cancel_inline(),
        )
        return FASTCARD_CUSTOM_AMOUNT

    offer, _ = config.build_custom_balance_offer(prefix, amount)
    if not offer:
        await update.message.reply_text(
            "⚠️ ما قدرت أحسب السعر. تأكد من المبلغ وحاول مرة ثانية.",
            reply_markup=kb.cancel_inline(),
        )
        return FASTCARD_CUSTOM_AMOUNT

    user = db.get_user(update.effective_user.id)
    price = offer["price"]

    if (user["balance"] or 0) < price:
        await update.message.reply_text(
            f"❌ رصيدك غير كافٍ.\n\n"
            f"📦 المبلغ المطلوب: {amount:,} ل.س\n".replace(",", "،") +
            f"💰 السعر (مع العمولة): {price:,} ل.س\n".replace(",", "،") +
            f"💼 رصيدك: {user['balance']:,.0f} ل.س\n\n".replace(",", "،") +
            "اشحن رصيدك أو خفّف المبلغ.",
            reply_markup=kb.insufficient_balance(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    # خزّن العرض الديناميكي
    context.user_data["fc_custom_offer"] = offer
    context.user_data["fc_offer_id"] = offer["id"]
    context.user_data["fc_fields"] = {}
    context.user_data["fc_field_idx"] = 0

    fields = cat.get("input_fields", [])
    if not fields:
        # روح مباشرة للتأكيد (نظري — كل أقسام الرصيد عندها رقم جوال)
        await context.bot.send_message(
            update.effective_chat.id,
            f"{cat['title']}\n\n"
            f"📦 المبلغ: {amount:,} ل.س\n".replace(",", "،") +
            f"💰 السعر النهائي: {price:,} ل.س\n".replace(",", "،") +
            f"💼 رصيدك: {user['balance']:,.0f} ل.س\n\n".replace(",", "،") +
            "اضغط تأكيد للتنفيذ.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.fastcard_confirm(prefix, offer["id"], price),
        )
        return ConversationHandler.END

    # في رقم جوال (أو أكثر) → اعرض ملخص ثم اطلب أول حقل
    await context.bot.send_message(
        update.effective_chat.id,
        f"✅ تم تحديد المبلغ\n\n"
        f"📦 المبلغ: {amount:,} ل.س\n".replace(",", "،") +
        f"💰 السعر النهائي (مع {int(cat.get('markup_pct', 10))}% عمولة): {price:,} ل.س".replace(",", "،"),
        parse_mode=ParseMode.MARKDOWN,
    )
    await _ask_field(update.message, context, offer, cat, fields, 0, user_balance=user["balance"], first=True)
    return FASTCARD_PLAYER_ID


async def cb_fastcard_buy_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يبدأ الشراء: حسب عدد الحقول بالقسم بيسأل واحد/أكثر، أو بيروح مباشرة للتأكيد."""
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return ConversationHandler.END

    parts = q.data.split(":", 2)  # fcbuy:<prefix>:<offer_id>
    if len(parts) != 3:
        return ConversationHandler.END
    prefix, offer_id = parts[1], parts[2]
    offer, cat = config.get_fastcard_offer(prefix, offer_id)
    if not offer or not cat:
        return ConversationHandler.END
    if not offer.get("enabled", True):
        await q.answer("🔴 نفد المخزون حالياً", show_alert=True)
        return ConversationHandler.END

    user = db.get_user(update.effective_user.id)
    if (user["balance"] or 0) < config.get_offer_price(offer):
        await _safe_edit(
            q,
            f"❌ رصيدك غير كافٍ.\n\n"
            f"العرض: *{offer['label']}*\n"
            f"السعر: {config.get_offer_price(offer):,} ل.س\n".replace(",", "،") +
            f"رصيدك: {user['balance']:,.0f} ل.س\n\n".replace(",", "،") +
            "اشحن رصيدك أولاً.",
            reply_markup=kb.insufficient_balance(),
        )
        return ConversationHandler.END

    # تهيئة الجلسة
    context.user_data["fc_prefix"] = prefix
    context.user_data["fc_offer_id"] = offer_id
    context.user_data["fc_fields"] = {}
    context.user_data["fc_field_idx"] = 0
    context.user_data.pop("fc_custom_offer", None)  # هذا مسار العروض الجاهزة

    fields = cat.get("input_fields", [])

    # لا توجد حقول → روح مباشرة لشاشة التأكيد
    if not fields:
        price_fmt = f"{config.get_offer_price(offer):,}".replace(",", "،")
        bal_fmt   = f"{user['balance']:,.0f}".replace(",", "،")
        await _safe_edit(
            q,
            f"{cat['title']}\n\n"
            f"🔷 *الحزمة:* {offer['label']}\n"
            f"🔷 *السعر:* {price_fmt} ل.س\n"
            f"🔷 *رصيدك:* {bal_fmt} ل.س\n\n"
            "⚠️ بعد التأكيد ينزل الكود مباشرة. ما فينا نسترجع الكود بعد الشراء.",
            reply_markup=kb.fastcard_confirm(prefix, offer_id, config.get_offer_price(offer)),
        )
        return ConversationHandler.END

    # في حقل أو أكثر → اطلب أول حقل
    await _ask_field(q, context, offer, cat, fields, 0, user_balance=user["balance"], first=True)
    return FASTCARD_PLAYER_ID


def _field_prompt_text(offer, cat, fields, idx, user_balance, first=False):
    """يبني نص الطلب لحقل معيّن."""
    field = fields[idx]
    total = len(fields)
    header = f"{cat['title']}\n\n"
    if first:
        header += (
            f"*{offer['label']}* — {config.get_offer_price(offer):,} ل.س\n".replace(",", "،") +
            f"💼 رصيدك: {user_balance:,.0f} ل.س\n\n".replace(",", "،")
        )
    progress = f"📝 الخطوة {idx+1} من {total}\n" if total > 1 else ""
    body = f"{progress}ابعت *{field['label']}*:"
    # تنبيه أمني خاص بالباسورد
    if field.get("type") == "password":
        body += (
            "\n\n🔒 *تنبيه أمني مهم:*\n"
            "• هاد كلمة مرور حساب Supercell ID تبعك (مو إيميل Gmail).\n"
            "• ما منستخدمها إلا لشحن طلبك ومنحذفها بعد التنفيذ.\n"
            "• يفضّل تغيّرها بعد ما يوصلك الشحن لأقصى أمان."
        )
    return header + body


async def _ask_field(q_or_msg, context, offer, cat, fields, idx, user_balance, first=False):
    """يعرض رسالة طلب الحقل. يدعم CallbackQuery (edit) أو Message (send في نفس الشات)."""
    text = _field_prompt_text(offer, cat, fields, idx, user_balance, first=first)
    if hasattr(q_or_msg, "edit_message_text"):
        await _safe_edit(q_or_msg, text, reply_markup=kb.cancel_inline())
    else:
        # نستخدم send_message على chat_id لأن الرسالة الأصلية ربما انحذفت (لو حقل حساس)
        await context.bot.send_message(
            q_or_msg.chat_id, text,
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.cancel_inline(),
        )


async def _show_confirm(message, context, offer, cat, fields, user):
    """يعرض شاشة التأكيد بكل القيم المُجمَّعة (مع إخفاء الحساس)."""
    fc_fields = context.user_data.get("fc_fields", {})
    lines = [f"{cat['title']}", "", f"🔷 *الحزمة:* {offer['label']}"]
    for f in fields:
        v = fc_fields.get(f["key"], "")
        masked = config.mask_field_value(f, v)
        # نعرض القيم بصيغة آمنة
        if f.get("type") == "password":
            lines.append(f"🔷 {f['label']}: `{masked}`")
        elif f.get("type") == "email":
            lines.append(f"🔷 {f['label']}: `{v}`")
        elif f.get("type") == "phone":
            lines.append(f"🔷 {f['label']}: `{v}`")
        elif f.get("type") == "id":
            lines.append(f"🔷 {f['label']}: `{v}`")
        else:
            lines.append(f"🔷 {f['label']}: `{v}`")
    price_fmt = f"{config.get_offer_price(offer):,}".replace(",", "،")
    bal_fmt   = f"{user['balance']:,.0f}".replace(",", "،")
    lines += [
        f"🔷 *السعر:* {price_fmt} ل.س",
        f"🔷 *رصيدك:* {bal_fmt} ل.س",
        "",
        "⚠️ تأكد من البيانات كويس قبل التأكيد. بعد التأكيد ما فينا نسترجع الطلب.",
    ]
    prefix = context.user_data["fc_prefix"]
    offer_id = context.user_data["fc_offer_id"]
    # send_message على chat_id لأن الرسالة الأصلية ربما انحذفت (لو الحقل الأخير كان الباسورد)
    await context.bot.send_message(
        message.chat_id,
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.fastcard_confirm(prefix, offer_id, config.get_offer_price(offer)),
    )


async def msg_fastcard_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج عام لإدخالات حقول Fastcard المتعددة. يتقدم سلسلة الحقول حسب fc_field_idx."""
    text = (update.message.text or "").strip()

    prefix = context.user_data.get("fc_prefix")
    offer_id = context.user_data.get("fc_offer_id")
    custom_offer = context.user_data.get("fc_custom_offer")
    offer, cat = config.get_fastcard_offer(prefix, offer_id, custom_offer=custom_offer) if (prefix and offer_id) else (None, None)
    if not offer or not cat:
        await update.message.reply_text(
            "⚠️ انتهت الجلسة، ارجع للمتجر وابدأ من جديد.",
            reply_markup=kb.back_to_main(),
        )
        return ConversationHandler.END

    fields = cat.get("input_fields", [])
    idx = context.user_data.get("fc_field_idx", 0)
    if idx >= len(fields):
        # ما في حقول إضافية — هذا غير متوقع
        return ConversationHandler.END

    field = fields[idx]
    is_sensitive = field.get("type") == "password" or field.get("sensitive")

    # احذف رسالة المستخدم فوراً لو حساسة (قبل التحقق وقبل أي رد)
    if is_sensitive:
        try:
            await update.message.delete()
        except Exception:
            pass

    validator, err_msg = config.FIELD_VALIDATORS.get(field.get("type", "text"), (lambda v: True, "⚠️ غير صحيح"))

    if not validator(text):
        # نستخدم send_message بدل reply_text لأن الرسالة الأصلية ربما انحذفت
        await context.bot.send_message(
            update.effective_chat.id,
            f"{err_msg}\n\nأعد إدخال *{field['label']}*:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.cancel_inline(),
        )
        return FASTCARD_PLAYER_ID

    context.user_data["fc_fields"][field["key"]] = text

    next_idx = idx + 1
    context.user_data["fc_field_idx"] = next_idx

    user = db.get_user(update.effective_user.id)

    if next_idx < len(fields):
        # في حقول أكثر → اطلب التالي
        await _ask_field(update.message, context, offer, cat, fields, next_idx, user_balance=user["balance"])
        return FASTCARD_PLAYER_ID

    # كل الحقول جُمعت → اعرض شاشة التأكيد
    await _show_confirm(update.message, context, offer, cat, fields, user)
    return ConversationHandler.END


async def cb_fastcard_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التنفيذ النهائي للطلب عبر Fastcard لأي قسم تلقائي."""
    q = update.callback_query
    await q.answer("جاري الإرسال للمتجر...")
    if await is_banned(update):
        return

    parts = q.data.split(":", 2)  # fcconf:<prefix>:<offer_id>
    if len(parts) != 3:
        return
    prefix, offer_id = parts[1], parts[2]
    custom_offer = context.user_data.get("fc_custom_offer")
    offer, cat = config.get_fastcard_offer(prefix, offer_id, custom_offer=custom_offer)
    if not offer or not cat:
        await q.edit_message_text(
            "⚠️ انتهت الجلسة. اضغط /start وابدأ من جديد.",
            reply_markup=kb.back_to_main(),
        )
        return

    user_id = update.effective_user.id
    user = db.get_user(user_id)

    fields = cat.get("input_fields", [])
    fc_fields = context.user_data.get("fc_fields", {}) or {}

    # تحقق من تجميع كل الحقول المطلوبة
    missing = [f for f in fields if not fc_fields.get(f["key"])]
    if missing:
        await q.edit_message_text(
            "⚠️ انتهت الجلسة. اضغط /start وابدأ من جديد.",
            reply_markup=kb.back_to_main(),
        )
        return

    # افصل playerId عن باقي الحقول (بتُمرَّر بـ extra)
    player_id = fc_fields.get("playerId")
    extra = {k: v for k, v in fc_fields.items() if k != "playerId"}

    # قيم حساسة لازم تنحذف من أي شي بينحفظ بقاعدة البيانات (الباسورد بشكل خاص)
    _sensitive_vals = [
        fc_fields.get(f["key"], "") for f in fields
        if f.get("sensitive") or f.get("type") == "password"
    ]

    if (user["balance"] or 0) < config.get_offer_price(offer):
        await q.edit_message_text(
            "❌ رصيدك غير كافٍ. اشحن أولاً.",
            reply_markup=kb.insufficient_balance(),
        )
        return

    if not fastcard.is_enabled():
        await q.edit_message_text(
            "⚠️ التكامل مع المتجر غير مفعّل حالياً. تواصل مع الدعم.",
            reply_markup=kb.back_to_main(),
        )
        return

    db.update_balance(user_id, -config.get_offer_price(offer))
    api_uuid = str(uuid.uuid4())
    # نخزن في عمود player_id ملخّصاً آمناً (بدون الباسورد)
    summary = config.summarize_fields_for_db(fields, fc_fields) if fields else "—"
    order_id = db.create_order(
        user_id, cat["game"], offer["label"], config.get_offer_price(offer),
        summary, api_uuid=api_uuid,
    )

    # ملخّص الحقول لشاشة المعالجة (مع إخفاء الحساس)
    proc_lines = []
    for f in fields:
        v = fc_fields.get(f["key"], "")
        if not v:
            continue
        masked = config.mask_field_value(f, v)
        if f.get("type") == "id":
            proc_lines.append(f"🎮 {f['label']}: `{v}`")
        elif f.get("type") == "email":
            proc_lines.append(f"📧 `{v}`")
        elif f.get("type") == "phone":
            proc_lines.append(f"📱 `{v}`")
        elif f.get("type") == "password":
            proc_lines.append(f"🔑 `{masked}`")

    await q.edit_message_text(
        f"⏳ *جاري معالجة طلبك...*\n\n"
        f"{cat['title']}\n"
        f"العرض: {offer['label']}\n" +
        ("\n".join(proc_lines) + "\n" if proc_lines else "") +
        f"📋 رقم الطلب: #{order_id}\n\n"
        "_بترجعلك النتيجة بعد ثوانٍ_",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        result = await asyncio.to_thread(
            fastcard.new_order,
            offer["product_id"],
            player_id=player_id,
            order_uuid=api_uuid,
            qty=offer.get("qty", 1),
            extra=extra if extra else None,
        )
    except fastcard.FastcardError as e:
        db.update_balance(user_id, config.get_offer_price(offer))
        db.update_order_api(
            order_id, status="rejected",
            api_response=config.sanitize_for_storage(str(e), extra_redact_values=_sensitive_vals),
        )
        logger.error(f"Fastcard generic ({prefix}/{offer_id}) new_order failed: <redacted error>")
        await context.bot.send_message(
            user_id,
            f"❌ تعذّر تنفيذ الطلب وتم استرجاع المبلغ كاملاً لرصيدك.\n\n"
            f"السبب: {e.message}\n"
            f"رقم الطلب: #{order_id}",
            reply_markup=kb.back_to_main(),
        )
        if config.ADMIN_ID:
            try:
                await notify.notify_admin(
                    context.bot,
                    f"⚠️ فشل طلب تلقائي #{order_id}\n"
                    f"User: {user_id}\nالقسم: {cat['title']}\nالعرض: {offer['label']}\n"
                    f"الخطأ: {e.message}",
                )
            except Exception:
                pass
        for k in ("fc_prefix", "fc_offer_id", "fc_player_id", "fc_fields", "fc_field_idx", "fc_custom_offer"):
            context.user_data.pop(k, None)
        return

    api_order_id = str(result.get("order_id") or "")
    final_status = (result.get("status") or "").lower()
    final_data = result
    db.update_order_api(
        order_id, api_order_id=api_order_id,
        api_response=config.sanitize_for_storage(result, extra_redact_values=_sensitive_vals),
    )

    elapsed = 0
    while elapsed < config.FASTCARD_POLL_TIMEOUT and final_status in ("processing", "wait", "pending", ""):
        await asyncio.sleep(config.FASTCARD_POLL_INTERVAL)
        elapsed += config.FASTCARD_POLL_INTERVAL
        try:
            info = await asyncio.to_thread(fastcard.check_order, api_uuid, by_uuid=True)
            if info:
                final_data = info
                final_status = (info.get("status") or "").lower()
        except fastcard.FastcardError:
            logger.warning("Fastcard generic poll failed: <redacted error>")
            continue

    db.update_order_api(
        order_id, status=final_status or "unknown",
        api_response=config.sanitize_for_storage(final_data, extra_redact_values=_sensitive_vals),
    )

    accepted = final_status in ("accept", "accepted", "completed", "done", "success")
    rejected = final_status in ("reject", "rejected", "fail", "failed", "refund", "refunded", "canceled", "cancelled")

    is_code_only = not fields  # ما في حقول → منتج كود/ستوك
    has_credentials = any(f.get("type") == "password" for f in fields)

    if accepted:
        replay = final_data.get("replay_api") or []
        extra_txt = ""
        if isinstance(replay, list) and replay:
            val = str(replay[0]).strip()
            if val:
                if is_code_only:
                    extra_txt = f"\n\n🎟️ *الكود تبعك:*\n`{val}`\n_(اضغط على الكود لنسخه)_"
                else:
                    extra_txt = f"\n📩 رد المتجر: `{val}`"
        new_user = db.get_user(user_id)
        # نص الإغلاق حسب نوع المنتج
        if is_code_only:
            closing = "✨ الكود في الأعلى."
        elif has_credentials:
            closing = (
                "✨ تم تنفيذ الشحن على حسابك مباشرة.\n"
                "🔒 *للحماية:* نوصيك تغيّر كلمة مرور Supercell ID وتفعّل الحماية الثنائية."
            )
        else:
            closing = "✨ تم التنفيذ على حسابك مباشرة."

        try:
            _balance = float((new_user or {}).get("balance") or 0)
            _msg = (
                f"✅ *تم تنفيذ طلبك بنجاح!*\n\n"
                f"{cat['title']}\n"
                f"العرض: {offer['label']}\n" +
                (f"📌 البيانات: `{summary}`\n" if summary and summary != "—" else "") +
                f"💰 السعر: {config.get_offer_price(offer):,} ل.س\n".replace(",", "،") +
                f"📋 رقم الطلب: #{order_id}\n"
                f"💼 رصيدك الجديد: {_balance:,.0f} ل.س".replace(",", "،") +
                f"{extra_txt}\n\n" +
                closing
            )
            await context.bot.send_message(
                user_id, _msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.back_to_main(),
            )
        except Exception as _send_err:
            try:
                await context.bot.send_message(
                    user_id,
                    f"✅ تم تنفيذ طلبك بنجاح!\nرقم الطلب: #{order_id}\n{offer.get('label','')}{extra_txt}",
                    reply_markup=kb.back_to_main(),
                )
            except Exception:
                pass
            if config.ADMIN_ID:
                try:
                    import traceback as _tb
                    await context.bot.send_message(
                        config.ADMIN_ID,
                        f"⚠️ فشل إرسال إشعار النجاح للمستخدم {user_id} على الطلب #{order_id}:\n{_send_err}\n\n{_tb.format_exc()[-800:]}",
                    )
                except Exception:
                    pass
        await grant_loyalty_for_order(context.bot, user_id, float(config.get_offer_price(offer)))
        await send_rating_prompt(context.bot, user_id, order_id, offer.get("label", ""))
        if config.ADMIN_ID:
            try:
                uname = user.get("username") or user.get("first_name") or "—"
                await notify.notify_admin(
                    context.bot,
                    f"💰 *بيع تلقائي عبر API* #{order_id}\n\n"
                    f"المستخدم: @{uname} ({user_id})\n"
                    f"القسم: {cat['title']}\n"
                    f"العرض: {offer['label']}\n" +
                    (f"البيانات: `{summary}`\n" if summary and summary != "—" else "") +
                    f"السعر للزبون: {config.get_offer_price(offer):,} ل.س\n".replace(",", "،") +
                    f"API Order: `{api_order_id}`",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as e:
                logger.error(f"admin notify failed: {e}")
    elif rejected:
        db.update_balance(user_id, config.get_offer_price(offer))
        if is_code_only:
            reject_hint = "غالباً المخزون نفد. جرّب لاحقاً أو اختر عرض ثاني."
        elif has_credentials:
            reject_hint = (
                "تأكد إن الإيميل وكلمة المرور صحيحين، وإن الحماية الثنائية مغلقة مؤقتاً، "
                "وجرّب مرة ثانية أو تواصل مع الدعم."
            )
        else:
            reject_hint = "تأكد من Player ID وجرّب مرة ثانية، أو تواصل مع الدعم."
        await context.bot.send_message(
            user_id,
            f"❌ *المتجر رفض الطلب وتم استرجاع المبلغ كاملاً.*\n\n"
            f"📋 رقم الطلب: #{order_id}\n"
            f"الحالة: {final_status}\n\n" +
            reject_hint,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back_to_main(),
        )
        if config.ADMIN_ID:
            try:
                await notify.notify_admin(
                    context.bot,
                    f"⚠️ *طلب تلقائي مرفوض* #{order_id}\n"
                    f"User: {user_id}\nالقسم: {cat['title']}\nالعرض: {offer['label']}\nالحالة: {final_status}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
    else:
        # ما زال processing بعد التايم آوت — لا نزعج المستخدم أو الأدمن
        pass

    for k in ("fc_prefix", "fc_offer_id", "fc_player_id", "fc_fields", "fc_field_idx", "fc_custom_offer"):
        context.user_data.pop(k, None)


# ============= Recharge: Syriatel =============
async def cb_syriatel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return ConversationHandler.END

    text = (
        "📱 *سيرياتيل كاش*\n\n"
        f"الرقم: `{config.SYRIATEL_CASH_NUMBER}`\n\n"
        "اشحن الرصيد المطلوب على الرقم التالي عبر التحويل اليدوي حصراً، "
        "ومن ثم أدخل رقم العملية (Transaction ID) من التطبيق."
    )
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.cancel_inline())
    return SYRIATEL_TX_CODE


async def msg_syriatel_tx_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = (update.message.text or "").strip()
    if len(code) < 4:
        await update.message.reply_text(
            "⚠️ رقم العملية قصير جداً. أعد المحاولة:",
            reply_markup=kb.cancel_inline(),
        )
        return SYRIATEL_TX_CODE
    context.user_data["syriatel_tx"] = code
    await update.message.reply_text(
        "أدخل المبلغ الذي تم تحويله (بالليرة السورية):",
        reply_markup=kb.cancel_inline(),
    )
    return SYRIATEL_AMOUNT


async def msg_syriatel_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "⚠️ المبلغ غير صالح. أدخل رقماً موجباً:",
            reply_markup=kb.cancel_inline(),
        )
        return SYRIATEL_AMOUNT

    user_id = update.effective_user.id
    tx = context.user_data.get("syriatel_tx", "")
    req_id = db.create_recharge_request(user_id, "syriatel", amount, transaction_code=tx)
    context.user_data["syriatel_req_id"] = req_id

    if syriatel_cash.is_enabled():
        msg = (
            f"📱 *طلب شحن سيرياتيل كاش*\n\n"
            f"💰 المبلغ: *{amount:,.0f}* ل.س\n"
            f"🔢 رقم العملية: `{tx}`\n"
            f"📞 الرقم المستلم: `{config.SYRIATEL_CASH_NUMBER}`\n\n"
            "✅ بعد إتمام التحويل اضغط *«تحقق تلقائي»* وسيُضاف الرصيد فوراً."
        )
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.syriatel_after_amount(req_id),
        )
    else:
        await update.message.reply_text(
            "✅ تم إرسال الطلب، سيتم التحقق منه قريباً.",
            reply_markup=kb.back_to_main(),
        )

    if config.ADMIN_ID:
        try:
            user = db.get_user(user_id)
            uname = user.get("username") or user.get("first_name") or "—"
            await notify.notify_admin(
                context.bot,
                f"🆕 *طلب شحن جديد* #{req_id}\n\n"
                f"المستخدم: @{uname} ({user_id})\n"
                f"الطريقة: سيرياتيل كاش 📱\n"
                f"المبلغ: *{amount:.0f}* ل.س\n"
                f"رقم العملية: `{tx}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.admin_recharge_decision(req_id),
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")

    context.user_data.pop("syriatel_tx", None)
    return ConversationHandler.END


async def cb_syriatel_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    # answer() مع تجاهل لو callback قديم
    try:
        await q.answer("جاري التحقق...", show_alert=False)
    except BadRequest:
        pass  # query too old — نُكمل بدون الـ pop-up
    
    if await is_banned(update):
        return

    try:
        req_id = int(q.data.split(":", 1)[1])
    except (ValueError, IndexError):
        return

    req = db.get_recharge_request(req_id)
    if not req or req["user_id"] != update.effective_user.id:
        await q.edit_message_text("⚠️ الطلب غير موجود.", reply_markup=kb.back_to_main())
        return

    if req["status"] == "approved":
        await q.edit_message_text("✅ هذا الطلب تم اعتماده مسبقاً.", reply_markup=kb.back_to_main())
        return

    if not syriatel_cash.is_enabled():
        await q.edit_message_text(
            "⚠️ التحقق التلقائي غير مفعل حالياً. سيتم مراجعة طلبك يدوياً.",
            reply_markup=kb.back_to_main(),
        )
        return

    expected_amount = float(req["amount"])
    user_id = req["user_id"]
    tx_code = (req.get("transaction_code") or "").strip()

    if not tx_code:
        await q.edit_message_text(
            "⚠️ لم يتم العثور على رقم العملية في الطلب. تواصل مع الدعم.",
            reply_markup=kb.back_to_main(),
        )
        return

    # رسالة feedback فورية — قد تستغرق العملية حتى 45 ثانية مع retry
    try:
        await q.edit_message_text(
            "🔄 *جاري التحقق من تحويلك...*\n\n"
            "_قد يستغرق هذا حتى دقيقة. لا تغلق هذه الرسالة._",
            parse_mode=ParseMode.MARKDOWN,
        )
    except BadRequest:
        pass

    try:
        tx = await asyncio.to_thread(
            syriatel_cash.find_matching_transaction,
            tx_code,
            expected_amount,
        )
    except SyriatelCashError as e:
        logger.error(f"Syriatel Cash transactions fetch failed: {e}")
        if e.code == "RATE_LIMIT_EXCEEDED":
            title = "🐢 *النظام مشغول حالياً*"
            friendly = "كثرة الطلبات على خدمة سرياتيل. انتظر *دقيقة* ثم اضغط «تحقق تلقائي» مرة أخرى."
        elif e.code == "RATE_LIMITED":
            title = "⏸ *التحقق التلقائي موقوف مؤقتاً*"
            friendly = (
                "تم تجاوز الحد اليومي لاستعلامات حسابنا لدى مزوّد الخدمة، "
                "وتم تعليق الحساب مؤقتاً.\n\n"
                "👈 اضغط *«اطلب مراجعة يدوية»* وسيتم اعتماد طلبك يدوياً خلال دقائق."
            )
        elif e.code == "SUBSCRIPTION_EXPIRED":
            title = "⛔ *الخدمة معطّلة مؤقتاً*"
            friendly = "اشتراك التحقق التلقائي منتهي. تواصل مع الدعم أو اطلب مراجعة يدوية."
        elif e.code == "SESSION_EXPIRED":
            title = "⛔ *الخدمة معطّلة مؤقتاً*"
            friendly = "انتهت جلسة الخدمة. تواصل مع الدعم أو اطلب مراجعة يدوية."
        elif e.code == "SERVICE_DOWN":
            title = "🛠 *خدمة سرياتيل معطّلة مؤقتاً*"
            friendly = (
                "خادم التحقق التلقائي لا يستجيب حالياً (المشكلة من مزوّد الخدمة، "
                "ليست من البوت).\n\n"
                "👈 اضغط *«اطلب مراجعة يدوية»* وسيتم اعتماد طلبك يدوياً خلال دقائق."
            )
        elif e.code == "TIMEOUT":
            title = "⏱ *اتصال بطيء*"
            friendly = "استجابة الخدمة بطيئة الآن. أعد المحاولة بعد قليل أو اطلب مراجعة يدوية."
        elif e.code in ("NETWORK", "FETCH_FAILED"):
            title = "📡 *تعذّر الاتصال*"
            friendly = "تعذّر الوصول لخدمة سرياتيل. أعد المحاولة بعد قليل أو اطلب مراجعة يدوية."
        else:
            title = "⚠️ *تعذّر التحقق الآن*"
            friendly = e.message or e.code
        try:
            await q.edit_message_text(
                f"{title}\n\n{friendly}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.syriatel_retry(req_id),
            )
        except BadRequest as edit_err:
            # تجاهل "Message is not modified" — يحصل لو ضغط الزر مرتين بنفس النتيجة
            if "not modified" not in str(edit_err).lower():
                raise
        return

    if not tx:
        await q.edit_message_text(
            f"❌ لم نعثر على تحويل برقم العملية `{tx_code}` بقيمة *{expected_amount:,.0f}* ل.س.\n\n"
            "تأكد من إتمام التحويل ومن صحة رقم العملية، ثم أعد المحاولة، "
            "أو اطلب مراجعة يدوية.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.syriatel_retry(req_id),
        )
        return

    tx_no = str(tx.get("transaction_no", "")).strip()
    tx_id = syriatel_cash.stable_tx_id(tx_no)

    if db.is_transaction_consumed(tx_id):
        await q.edit_message_text(
            "⚠️ هذا التحويل مستخدم مسبقاً. تواصل مع الدعم إذا كان خطأ.",
            reply_markup=kb.back_to_main(),
        )
        return

    claimed = db.consume_transaction(tx_id, user_id, expected_amount)
    if not claimed:
        await q.edit_message_text(
            "⚠️ هذا التحويل مستخدم مسبقاً.",
            reply_markup=kb.back_to_main(),
        )
        return

    try:
        new_state = db.update_balance(user_id, expected_amount, count_as_recharge=True)
        db.update_recharge_status(req_id, "approved")
    except Exception as credit_err:
        logger.exception(
            f"FATAL: tx {tx_no} consumed but balance credit failed for user {user_id}: {credit_err}"
        )
        if config.ADMIN_ID:
            try:
                await notify.notify_admin(
                    context.bot,
                    f"🚨 *خطأ حرج — Syriatel Cash* #{req_id}\n\n"
                    f"تم تأكيد العملية `{tx_no}` لكن فشل إضافة الرصيد!\n"
                    f"User: `{user_id}` | المبلغ: *{expected_amount:,.0f}* ل.س\n"
                    f"الخطأ: `{credit_err}`\n\n"
                    f"⚠️ راجع الرصيد يدوياً.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
        await q.edit_message_text(
            "⚠️ تم التأكد من العملية لكن حدث خطأ تقني عند إضافة الرصيد.\n"
            "تواصل مع الدعم وأرسل رقم الطلب: " + str(req_id),
            reply_markup=kb.back_to_main(),
        )
        return

    await apply_referral_commission(
        context.bot, user_id, float(expected_amount),
        new_state.get("referrer_id") if new_state else None,
    )
    await notify_level_up(context.bot, user_id, new_state)

    sender = tx.get("from_gsm") or "—"
    tx_date = tx.get("date") or "—"
    await q.edit_message_text(
        f"✅ *تم التحقق بنجاح!*\n\n"
        f"المبلغ: *{expected_amount:,.0f}* ل.س\n"
        f"المُرسِل: `{sender}`\n"
        f"رقم العملية: `{tx_no}`\n"
        f"التاريخ: {tx_date}\n\n"
        f"رصيدك الحالي: *{new_state['balance']:,.0f}* ل.س\n"
        f"مستواك: *{new_state['level']}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.back_to_main(),
    )

    if config.ADMIN_ID:
        try:
            user = db.get_user(user_id)
            uname = user.get("username") or user.get("first_name") or "—"
            await notify.notify_admin(
                context.bot,
                f"✅ *شحن تلقائي عبر سيرياتيل كاش* #{req_id}\n\n"
                f"المستخدم: @{uname} ({user_id})\n"
                f"المبلغ: {expected_amount:,.0f} ل.س\n"
                f"رقم العملية: `{tx_no}`\n"
                f"المُرسِل: `{sender}`",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"admin notify failed: {e}")


async def cb_syriatel_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return
    try:
        req_id = int(q.data.split(":", 1)[1])
    except (ValueError, IndexError):
        return
    req = db.get_recharge_request(req_id)
    if not req or req["user_id"] != update.effective_user.id:
        await q.edit_message_text("⚠️ الطلب غير موجود.", reply_markup=kb.back_to_main())
        return
    await q.edit_message_text(
        "✅ تم تحويل طلبك للمراجعة اليدوية.\nسيتم الرد عليك خلال دقائق من قبل الإدارة.",
        reply_markup=kb.back_to_main(),
    )


# ============= Recharge: Sham Cash =============
async def cb_shamcash_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return ConversationHandler.END

    text = (
        "💳 *شام كاش*\n\n"
        f"رمز التحويل: `{config.SHAMCASH_WALLET_CODE}`\n"
        f"اسم المحفظة: *{config.SHAMCASH_WALLET_NAME}*\n\n"
        "أدخل المبلغ الذي تريد شحنه (بالليرة السورية):"
    )
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.cancel_inline())
    return SHAMCASH_AMOUNT


async def msg_shamcash_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "⚠️ المبلغ غير صالح. أدخل رقماً موجباً:",
            reply_markup=kb.cancel_inline(),
        )
        return SHAMCASH_AMOUNT

    user_id = update.effective_user.id
    req_id = db.create_recharge_request(user_id, "shamcash", amount)
    context.user_data["shamcash_req_id"] = req_id
    context.user_data["shamcash_amount"] = amount

    if shamcash_enabled():
        msg = (
            f"💳 *المبلغ المطلوب: {amount:,.0f} ل.س*\n\n"
            "━━━━━━━━━━━━━━━━━\n"
            f"📍 حوّل المبلغ إلى محفظة شام كاش:\n\n"
            f"🔢 الرمز: `{config.SHAMCASH_WALLET_CODE}`\n"
            f"👤 الاسم: *{config.SHAMCASH_WALLET_NAME}*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "✅ بعد التحويل اضغط *«تحقق تلقائي»* وسيُضاف الرصيد فوراً.\n"
            "📸 أو ارسل صورة عملية التحويل لمراجعتها يدوياً."
        )
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.shamcash_after_amount(req_id),
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "بعد التحويل أرسل صورة عملية التحويل 📸",
            reply_markup=kb.cancel_inline(),
        )
        return SHAMCASH_PHOTO


async def cb_shamcash_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("جاري التحقق...", show_alert=False)
    if await is_banned(update):
        return

    try:
        req_id = int(q.data.split(":", 1)[1])
    except (ValueError, IndexError):
        return

    req = db.get_recharge_request(req_id)
    if not req or req["user_id"] != update.effective_user.id:
        await q.edit_message_text("⚠️ الطلب غير موجود.", reply_markup=kb.back_to_main())
        return

    if req["status"] == "approved":
        await q.edit_message_text("✅ هذا الطلب تم اعتماده مسبقاً.", reply_markup=kb.back_to_main())
        return

    if not shamcash_enabled():
        await q.edit_message_text(
            "⚠️ التحقق التلقائي غير مفعل حالياً. ارسل صورة العملية.",
            reply_markup=kb.shamcash_retry(req_id),
        )
        return

    expected_amount = float(req["amount"])
    user_id = req["user_id"]

    try:
        account_id = get_active_account_id()
    except ShamCashError as e:
        logger.error(f"Account fetch failed: {e}")
        await q.edit_message_text(
            f"⚠️ تعذّر الاتصال بشام كاش.\nالخطأ: {e.message}\nجرّب يدوي:",
            reply_markup=kb.shamcash_retry(req_id),
        )
        return

    if not account_id:
        await q.edit_message_text(
            "⚠️ لا يوجد حساب شام كاش مربوط. تواصل مع الدعم.",
            reply_markup=kb.shamcash_retry(req_id),
        )
        return

    try:
        tx = find_matching_transaction(
            account_id=account_id,
            expected_amount=expected_amount,
            window_minutes=config.SHAMCASH_VERIFY_WINDOW_MIN,
            coin_id=COIN_SYP,
        )
    except ShamCashError as e:
        logger.error(f"Transactions fetch failed: {e}")
        await q.edit_message_text(
            f"⚠️ تعذّر التحقق الآن.\n{e.message}",
            reply_markup=kb.shamcash_retry(req_id),
        )
        return

    if not tx:
        await q.edit_message_text(
            f"❌ لم نعثر على تحويل بقيمة *{expected_amount:.0f}* ل.س خلال آخر "
            f"{config.SHAMCASH_VERIFY_WINDOW_MIN} دقيقة.\n\n"
            "تأكد من إتمام التحويل ثم أعد المحاولة، أو أرسل صورة للمراجعة اليدوية.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.shamcash_retry(req_id),
        )
        return

    tx_id = int(tx["transaction_id"])
    if db.is_transaction_consumed(tx_id):
        await q.edit_message_text(
            "⚠️ هذا التحويل مستخدم مسبقاً. تواصل مع الدعم إذا كان خطأ.",
            reply_markup=kb.shamcash_retry(req_id),
        )
        return

    claimed = db.consume_transaction(tx_id, user_id, expected_amount)
    if not claimed:
        await q.edit_message_text(
            "⚠️ هذا التحويل مستخدم مسبقاً.",
            reply_markup=kb.shamcash_retry(req_id),
        )
        return

    db.update_recharge_status(req_id, "approved")
    new_state = db.update_balance(user_id, expected_amount, count_as_recharge=True)
    await apply_referral_commission(
        context.bot, user_id, float(expected_amount),
        new_state.get("referrer_id") if new_state else None,
    )
    await notify_level_up(context.bot, user_id, new_state)

    sender = tx.get("sender_name") or tx.get("sender_address") or "—"
    await q.edit_message_text(
        f"✅ *تم التحقق بنجاح!*\n\n"
        f"المبلغ: *{expected_amount:,.0f}* ل.س\n"
        f"المُرسِل: {sender}\n"
        f"رقم التحويل: `{tx_id}`\n\n"
        f"رصيدك الحالي: *{new_state['balance']:,.0f}* ل.س\n"
        f"مستواك: *{new_state['level']}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.back_to_main(),
    )

    if config.ADMIN_ID:
        try:
            user = db.get_user(user_id)
            uname = user.get("username") or user.get("first_name") or "—"
            await notify.notify_admin(
                context.bot,
                f"✅ *شحن تلقائي عبر شام كاش* #{req_id}\n\n"
                f"المستخدم: @{uname} ({user_id})\n"
                f"المبلغ: {expected_amount:.0f} ل.س\n"
                f"رقم التحويل: `{tx_id}`\n"
                f"المُرسِل: {sender}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"admin notify failed: {e}")


# ============= Recharge: Sham Cash USD =============
async def cb_shamcash_usd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return ConversationHandler.END

    text = (
        "💵 *شام كاش — دولار*\n\n"
        f"رمز التحويل: `{config.SHAMCASH_WALLET_CODE}`\n"
        f"اسم المحفظة: *{config.SHAMCASH_WALLET_NAME}*\n\n"
        f"📈 سعر الصرف: 1$ = {config.get_usd_to_syp():,.0f} ل.س\n\n"
        "أدخل المبلغ الذي تريد شحنه (بالدولار، مثلاً: 5):"
    )
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.cancel_inline())
    return SHAMCASH_USD_AMOUNT


async def msg_shamcash_usd_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    try:
        amount_usd = float(text)
        if amount_usd <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "⚠️ المبلغ غير صالح. أدخل رقماً موجباً بالدولار (مثلاً 5):",
            reply_markup=kb.cancel_inline(),
        )
        return SHAMCASH_USD_AMOUNT

    user_id = update.effective_user.id
    # نخزن المبلغ كـ USD في عمود amount مع method=shamcash_usd للتمييز
    req_id = db.create_recharge_request(user_id, "shamcash_usd", amount_usd)
    context.user_data["shamcash_req_id"] = req_id
    context.user_data["shamcash_amount"] = amount_usd
    context.user_data["shamcash_currency"] = "USD"

    syp_value = amount_usd * config.get_usd_to_syp()

    if shamcash_enabled():
        msg = (
            f"💵 *المبلغ المطلوب: {amount_usd:.2f} $*\n"
            f"_(يُضاف لرصيدك ما يعادل {syp_value:,.0f} ل.س)_\n\n"
            "━━━━━━━━━━━━━━━━━\n"
            "📍 حوّل المبلغ بالدولار إلى محفظة شام كاش:\n\n"
            f"🔢 الرمز: `{config.SHAMCASH_WALLET_CODE}`\n"
            f"👤 الاسم: *{config.SHAMCASH_WALLET_NAME}*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "✅ بعد التحويل اضغط *«تحقق تلقائي»* وسيُضاف الرصيد فوراً.\n"
            "📸 أو ارسل صورة عملية التحويل لمراجعتها يدوياً."
        )
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.shamcash_usd_after_amount(req_id),
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "بعد التحويل أرسل صورة عملية التحويل 📸",
            reply_markup=kb.cancel_inline(),
        )
        return SHAMCASH_PHOTO


async def cb_shamcash_usd_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("جاري التحقق...", show_alert=False)
    if await is_banned(update):
        return

    try:
        req_id = int(q.data.split(":", 1)[1])
    except (ValueError, IndexError):
        return

    req = db.get_recharge_request(req_id)
    if not req or req["user_id"] != update.effective_user.id:
        await q.edit_message_text("⚠️ الطلب غير موجود.", reply_markup=kb.back_to_main())
        return

    if req["status"] == "approved":
        await q.edit_message_text("✅ هذا الطلب تم اعتماده مسبقاً.", reply_markup=kb.back_to_main())
        return

    if not shamcash_enabled():
        await q.edit_message_text(
            "⚠️ التحقق التلقائي غير مفعل حالياً. ارسل صورة العملية.",
            reply_markup=kb.shamcash_usd_retry(req_id),
        )
        return

    expected_amount_usd = float(req["amount"])
    user_id = req["user_id"]

    try:
        account_id = get_active_account_id()
    except ShamCashError as e:
        logger.error(f"Account fetch failed: {e}")
        await q.edit_message_text(
            f"⚠️ تعذّر الاتصال بشام كاش.\nالخطأ: {e.message}\nجرّب يدوي:",
            reply_markup=kb.shamcash_usd_retry(req_id),
        )
        return

    if not account_id:
        await q.edit_message_text(
            "⚠️ لا يوجد حساب شام كاش مربوط. تواصل مع الدعم.",
            reply_markup=kb.shamcash_usd_retry(req_id),
        )
        return

    try:
        tx = find_matching_transaction(
            account_id=account_id,
            expected_amount=expected_amount_usd,
            window_minutes=config.SHAMCASH_VERIFY_WINDOW_MIN,
            coin_id=COIN_USD,
        )
    except ShamCashError as e:
        logger.error(f"Transactions fetch failed: {e}")
        await q.edit_message_text(
            f"⚠️ تعذّر التحقق الآن.\n{e.message}",
            reply_markup=kb.shamcash_usd_retry(req_id),
        )
        return

    if not tx:
        await q.edit_message_text(
            f"❌ لم نعثر على تحويل بقيمة *{expected_amount_usd:.2f} $* خلال آخر "
            f"{config.SHAMCASH_VERIFY_WINDOW_MIN} دقيقة.\n\n"
            "تأكد من إتمام التحويل ثم أعد المحاولة، أو أرسل صورة للمراجعة اليدوية.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.shamcash_usd_retry(req_id),
        )
        return

    tx_id = int(tx["transaction_id"])
    if db.is_transaction_consumed(tx_id):
        await q.edit_message_text(
            "⚠️ هذا التحويل مستخدم مسبقاً. تواصل مع الدعم إذا كان خطأ.",
            reply_markup=kb.shamcash_usd_retry(req_id),
        )
        return

    syp_credit = expected_amount_usd * config.get_usd_to_syp()
    claimed = db.consume_transaction(tx_id, user_id, syp_credit)
    if not claimed:
        await q.edit_message_text(
            "⚠️ هذا التحويل مستخدم مسبقاً.",
            reply_markup=kb.shamcash_usd_retry(req_id),
        )
        return

    db.update_recharge_status(req_id, "approved")
    new_state = db.update_balance(user_id, syp_credit, count_as_recharge=True)
    await apply_referral_commission(
        context.bot, user_id, float(syp_credit),
        new_state.get("referrer_id") if new_state else None,
    )
    await notify_level_up(context.bot, user_id, new_state)

    sender = tx.get("sender_name") or tx.get("sender_address") or "—"
    await q.edit_message_text(
        f"✅ *تم التحقق بنجاح!*\n\n"
        f"المبلغ: *{expected_amount_usd:.2f} $*\n"
        f"≈ *{syp_credit:,.0f}* ل.س على رصيدك\n"
        f"المُرسِل: {sender}\n"
        f"رقم التحويل: `{tx_id}`\n\n"
        f"رصيدك الحالي: *{new_state['balance']:,.0f}* ل.س\n"
        f"مستواك: *{new_state['level']}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.back_to_main(),
    )

    if config.ADMIN_ID:
        try:
            user = db.get_user(user_id)
            uname = user.get("username") or user.get("first_name") or "—"
            await notify.notify_admin(
                context.bot,
                f"✅ *شحن تلقائي عبر شام كاش (دولار)* #{req_id}\n\n"
                f"المستخدم: @{uname} ({user_id})\n"
                f"المبلغ: {expected_amount_usd:.2f} $ ≈ {syp_credit:,.0f} ل.س\n"
                f"رقم التحويل: `{tx_id}`\n"
                f"المُرسِل: {sender}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"admin notify failed: {e}")


async def cb_shamcash_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return ConversationHandler.END
    try:
        req_id = int(q.data.split(":", 1)[1])
    except (ValueError, IndexError):
        return ConversationHandler.END

    req = db.get_recharge_request(req_id)
    if not req or req["user_id"] != update.effective_user.id:
        await q.edit_message_text("⚠️ الطلب غير موجود.", reply_markup=kb.back_to_main())
        return ConversationHandler.END
    if req["status"] != "pending":
        await q.edit_message_text(
            f"⚠️ الطلب تم التعامل معه ({req['status']}).",
            reply_markup=kb.back_to_main(),
        )
        return ConversationHandler.END

    context.user_data["shamcash_req_id"] = req_id
    context.user_data["shamcash_amount"] = float(req["amount"])
    await q.edit_message_text(
        "📸 ارسل صورة عملية التحويل الآن:",
        reply_markup=kb.cancel_inline(),
    )
    return SHAMCASH_PHOTO


async def msg_shamcash_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ يرجى إرسال صورة فعلية لعملية التحويل.",
            reply_markup=kb.cancel_inline(),
        )
        return SHAMCASH_PHOTO

    photo_file_id = update.message.photo[-1].file_id
    amount = context.user_data.get("shamcash_amount", 0)
    req_id = context.user_data.get("shamcash_req_id")
    user_id = update.effective_user.id

    if not req_id:
        req_id = db.create_recharge_request(user_id, "shamcash", amount, photo_file_id=photo_file_id)
    else:
        # update existing pending request with the photo
        with db.get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE recharge_requests SET photo_file_id = ? WHERE id = ?",
                (photo_file_id, req_id),
            )
            conn.commit()

    await update.message.reply_text(
        "✅ تم إرسال الطلب، سيتم التحقق منه قريباً.",
        reply_markup=kb.back_to_main(),
    )

    if config.ADMIN_ID:
        try:
            user = db.get_user(user_id)
            uname = user.get("username") or user.get("first_name") or "—"
            req = db.get_recharge_request(req_id) if req_id else None
            method = (req or {}).get("method", "shamcash")
            if method == "shamcash_usd":
                amount_line = f"المبلغ: *{amount:.2f} $* (≈ {amount * config.get_usd_to_syp():,.0f} ل.س)"
                method_label = "شام كاش 💵 (دولار - يدوي)"
            else:
                amount_line = f"المبلغ: *{amount:.0f}* ل.س"
                method_label = "شام كاش 💳 (يدوي)"
            caption = (
                f"🆕 *طلب شحن جديد* #{req_id}\n\n"
                f"المستخدم: @{uname} ({user_id})\n"
                f"الطريقة: {method_label}\n"
                f"{amount_line}"
            )
            await context.bot.send_photo(
                config.ADMIN_ID,
                photo=photo_file_id,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.admin_recharge_decision(req_id),
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")

    context.user_data.pop("shamcash_amount", None)
    context.user_data.pop("shamcash_req_id", None)
    return ConversationHandler.END


# ============= USDT =============

async def cb_usdt_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_banned(update):
        return ConversationHandler.END

    # رمز المحفظة الثابت
    wallet = "0x9a8e639b26ee2a7796b6a2d81d2df0a74cb615d5"

    # زر Binance Pay أوتو إذا مفعّل
    from .binance_pay import is_enabled as bp_enabled
    bp_active = bp_enabled()

    text = (
        "💎 *إيداع USDT — BSC BEP20 فقط*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📤 *عنوان المحفظة:*\n"
        f"`{wallet}`\n\n"
        "⚠️ *تنبيه مهم:* التحويل يجب أن يكون حصراً على شبكة\n"
        "👉 *BSC (BEP20)* فقط — أي شبكة أخرى يضيع المبلغ\n\n"
        "━━━━━━━━━━━━━━━━━\n"
    )

    if bp_active:
        text += "✅ *الإيداع أوتوماتيكي عبر Binance Pay*\n"
        text += "اضغط الزر أدناه لإنشاء طلب دفع فوري من حساب Binance:"
        markup = kb.usdt_deposit_menu(binance_pay=True)
    else:
        text += "2️⃣ أرسل *المبلغ* الذي حوّلته (بالدولار $):"
        markup = kb.cancel_inline()

    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    return USDT_AMOUNT_USD


async def cb_usdt_binance_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يطلب المبلغ لإنشاء طلب Binance Pay."""
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting_binance_amount"] = True
    await q.edit_message_text(
        "⚡ *Binance Pay — إيداع أوتوماتيكي*\n\n"
        "أرسل المبلغ الذي تريد إيداعه بالدولار\n"
        "مثال: `10` أو `25` أو `50`:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.cancel_inline(),
    )
    return USDT_AMOUNT_USD


async def msg_usdt_binance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل المبلغ وينشئ طلب Binance Pay."""
    from .binance_pay import create_order, BinancePayError
    import asyncio

    if not context.user_data.get("awaiting_binance_amount"):
        return await msg_usdt_amount(update, context)

    text = (update.message.text or "").strip().replace(",", ".")
    try:
        amount = float(text)
        if amount < 1:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "⚠️ أدخل مبلغاً صحيحاً (الحد الأدنى 1$):",
            reply_markup=kb.cancel_inline(),
        )
        return USDT_AMOUNT_USD

    user_id = update.effective_user.id
    trade_no = f"GZ_{user_id}_{int(time.time())}"

    try:
        order = create_order(
            amount_usdt=amount,
            merchant_trade_no=trade_no,
            description=f"إيداع GameZone — {user_id}",
            buyer_id=str(user_id),
        )
    except BinancePayError as e:
        await update.message.reply_text(
            f"⚠️ تعذّر إنشاء طلب الدفع: {e.message}",
            reply_markup=kb.back_to_main(),
        )
        return ConversationHandler.END

    checkout_url = order.get("checkoutUrl", "")
    prepay_id    = order.get("prepayId", "")
    qr_link      = order.get("qrcodeLink", "")

    msg = await update.message.reply_text(
        f"✅ *تم إنشاء طلب الدفع*\n\n"
        f"💎 المبلغ: *{amount} USDT*\n"
        f"🔑 رقم الطلب: `{trade_no}`\n\n"
        f"👇 افتح الرابط وادفع من حساب Binance:\n{checkout_url}\n\n"
        f"⏳ الطلب صالح لمدة *15 دقيقة*\n"
        f"سيُضاف رصيدك تلقائياً فور الدفع ✅",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.back_to_main(),
    )

    # Poll في background
    context.user_data.pop("awaiting_binance_amount", None)

    # حفظ الطلب في DB لمراقبته عبر job دوري
    db.set_setting(f"binance_order_{trade_no}", json.dumps({
        "user_id":  user_id,
        "amount":   amount,
        "trade_no": trade_no,
        "prepay_id": prepay_id,
        "created":  time.time(),
    }))

    return ConversationHandler.END


async def cb_usdt_manual_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يطلب من المستخدم إدخال المبلغ للدفع اليدوي."""
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "💎 *إيداع USDT يدوي*\n\n"
        "أرسل المبلغ الذي حوّلته (بالدولار $):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.cancel_inline(),
    )
    return USDT_AMOUNT_USD


async def msg_usdt_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip().replace(",", ".")
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "⚠️ أدخل مبلغاً صحيحاً بالدولار (مثال: `10` أو `25.5`):",
            reply_markup=kb.cancel_inline(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return USDT_AMOUNT_USD

    # لو Binance Pay مختار
    if context.user_data.pop("awaiting_binance_amount", False):
        return await _process_binance_pay(update, context, amount)

    context.user_data["usdt_amount"] = amount
    await update.message.reply_text(
        f"✅ المبلغ: *{amount} $*\n\n"
        "3️⃣ الآن أرسل *Hash* (رقم) العملية من محفظتك:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.cancel_inline(),
    )
    return USDT_TX_HASH


async def _process_binance_pay(update, context, amount: float):
    """يطلب Hash العملية من المستخدم للتحقق أوتو عبر BscScan."""
    wallet = "0x9a8e639b26ee2a7796b6a2d81d2df0a74cb615d5"
    context.user_data["usdt_amount"] = amount
    await update.message.reply_text(
        f"💎 *إيداع USDT — BSC BEP20*\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📤 حوّل *{amount} USDT* على العنوان:\n"
        f"`{wallet}`\n\n"
        f"⚠️ *حصراً شبكة BSC (BEP20) فقط*\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"بعد التحويل أرسل *رقم العملية (Hash)*\n"
        f"مثال: `0x1234abcd...`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.cancel_inline(),
    )
    return USDT_TX_HASH


async def msg_usdt_tx_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tx_hash = (update.message.text or "").strip()
    if len(tx_hash) < 20:
        await update.message.reply_text(
            "⚠️ الـ Hash يبدو قصيراً. أعد إرساله:\nمثال: `0x1234abcd...`",
            reply_markup=kb.cancel_inline(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return USDT_TX_HASH

    user_id = update.effective_user.id
    amount  = context.user_data.get("usdt_amount", 0)

    # أرسل رسالة انتظار
    wait_msg = await update.message.reply_text(
        "🔍 جاري التحقق من العملية على البلوكتشين...",
    )

    # تحقق فوري عبر BscScan
    from .usdt_bsc import verify_deposit
    import json as _json, time as _time

    # تحقق من صحة الـ Hash أولاً
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        await wait_msg.edit_text(
            "❌ *الـ Hash غير صحيح*\n\n"
            "الـ Hash يجب أن يبدأ بـ `0x` ويتكون من 66 حرف\n"
            "مثال: `0x1234abcd...`\n\n"
            "تأكد من نسخه كاملاً من محفظتك وأعد الإرسال:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.cancel_inline(),
        )
        return USDT_TX_HASH

    verified = False
    verify_error = None
    try:
        from .usdt_bsc import verify_deposit, find_tx_by_hash
        # أولاً تحقق إن العملية موجودة أصلاً
        tx_data = find_tx_by_hash(tx_hash)
        if tx_data is None:
            verify_error = "not_found"
        else:
            verified = verify_deposit(tx_hash, amount)
            if not verified:
                verify_error = "wrong_amount"
    except Exception as e:
        logger.error(f"BscScan verify error: {e}")
        verify_error = "api_error"

    syp_per_usd = config.get_usd_to_syp()
    amount_syp  = amount * syp_per_usd

    if verified:
        # ✅ أضف الرصيد فوراً
        db.add_balance(user_id, amount_syp)
        req_id = db.create_recharge_request(
            user_id, "usdt", amount_syp, transaction_code=tx_hash
        )
        await wait_msg.edit_text(
            f"✅ *تم التحقق وإضافة الرصيد!*\n\n"
            f"💎 *{amount} USDT* أضيفت لرصيدك ⚡\n"
            f"💰 الرصيد المضاف: *{amount_syp:,.0f} ل.س*\n"
            f"🔑 رقم الطلب: `{req_id}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back_to_main(),
        )
        if config.ADMIN_ID:
            try:
                await notify.notify_admin(
                    context.bot,
                    f"✅ *إيداع USDT أوتو — #{req_id}*\n"
                    f"👤 `{user_id}`\n"
                    f"💎 {amount}$ — {amount_syp:,.0f} ل.س\n"
                    f"🔗 `{tx_hash}`",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass

    elif verify_error == "not_found":
        # ❌ العملية مش موجودة على BSC
        await wait_msg.edit_text(
            f"❌ *العملية غير موجودة على شبكة BSC*\n\n"
            f"🔗 Hash: `{tx_hash}`\n\n"
            "⚠️ *الأسباب المحتملة:*\n"
            "• العملية على شبكة أخرى (TRC20، ERC20، ...)\n"
            "• الـ Hash غير صحيح\n"
            "• العملية لم تُؤكَّد بعد (انتظر دقيقة وحاول ثانية)\n\n"
            "تأكد أن التحويل تم على شبكة *BSC (BEP20) فقط* ✅",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.usdt_retry_markup(amount),
        )
        context.user_data["usdt_amount"] = amount

    elif verify_error == "wrong_amount":
        # ❌ المبلغ غير مطابق
        await wait_msg.edit_text(
            f"⚠️ *المبلغ غير مطابق*\n\n"
            f"العملية موجودة لكن المبلغ المحوَّل لا يطابق *{amount} USDT*\n\n"
            f"تواصل مع الدعم إذا كنت متأكداً من التحويل.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back_to_main(),
        )

    else:
        # ⏳ خطأ في API — احفظ للفحص الدوري
        db.set_setting(f"usdt_pending_{tx_hash[:20]}", _json.dumps({
            "user_id":  user_id,
            "tx_hash":  tx_hash,
            "amount":   amount,
            "created":  _time.time(),
        }))
        req_id = db.create_recharge_request(
            user_id, "usdt", amount_syp, transaction_code=tx_hash
        )
        await wait_msg.edit_text(
            f"⏳ *جاري التحقق...*\n\n"
            f"💎 المبلغ: *{amount} USDT*\n"
            f"🔗 Hash: `{tx_hash}`\n\n"
            f"سيُضاف رصيدك تلقائياً فور تأكيد العملية ✅\n"
            f"عادةً خلال 1-3 دقائق",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back_to_main(),
        )
        if config.ADMIN_ID:
            try:
                user_obj = db.get_user(user_id) or {}
                uname = user_obj.get("username") or user_obj.get("first_name") or "—"
                await notify.notify_admin(
                    context.bot,
                    f"🆕 *طلب إيداع USDT — #{req_id}*\n"
                    f"👤 @{uname} `({user_id})`\n"
                    f"💎 {amount}$ — {amount_syp:,.0f} ل.س\n"
                    f"🔗 `{tx_hash}`\n"
                    f"🌐 BSC (BEP20) — جاري التحقق",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb.admin_recharge_decision(req_id),
                )
            except Exception:
                pass
        if config.ADMIN_ID:
            try:
                user = db.get_user(user_id) or {}
                uname = user.get("username") or user.get("first_name") or "—"
                await notify.notify_admin(
                    context.bot,
                    f"🆕 *طلب إيداع USDT — #{req_id}*\n"
                    f"👤 @{uname} `({user_id})`\n"
                    f"💎 {amount}$ — {amount_syp:,.0f} ل.س\n"
                    f"🔗 `{tx_hash}`\n"
                    f"🌐 BSC (BEP20) — جاري التحقق أوتو",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb.admin_recharge_decision(req_id),
                )
            except Exception:
                pass

    context.user_data.pop("usdt_amount", None)
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q:
        await q.answer()
        await q.edit_message_text(WELCOME, reply_markup=kb.main_menu(), parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


def register_user_handlers(app):
    app.add_handler(CommandHandler("start", cmd_start))

    syriatel_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cancel_conversation),CallbackQueryHandler(cb_syriatel_start, pattern=r"^recharge:syriatel$")],
        states={
            SYRIATEL_TX_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_syriatel_tx_code),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
            SYRIATEL_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_syriatel_amount),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
            CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|fclist:|order:|game:|menu:|back:)"),
        ],
        per_message=False,
        allow_reentry=True,
    )
    app.add_handler(syriatel_conv)

    app.add_handler(CallbackQueryHandler(cb_syriatel_verify, pattern=r"^syr_verify:"))
    app.add_handler(CallbackQueryHandler(cb_syriatel_manual, pattern=r"^syr_manual:"))

    usdt_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cancel_conversation),CallbackQueryHandler(cb_usdt_start, pattern=r"^recharge:usdt$")],
        states={
            USDT_AMOUNT_USD: [
                # زر Binance Pay الأوتو
                CallbackQueryHandler(cb_usdt_binance_pay, pattern=r"^usdt:binance_pay$"),
                # دفع يدوي
                CallbackQueryHandler(cb_usdt_manual_start, pattern=r"^usdt:manual$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_usdt_amount),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
            USDT_TX_HASH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_usdt_tx_hash),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
            CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|fclist:|order:|game:|menu:|back:)"),
        ],
        per_message=False,
        allow_reentry=True,
    )
    app.add_handler(usdt_conv)

    shamcash_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cancel_conversation),
            CallbackQueryHandler(cb_shamcash_start, pattern=r"^recharge:shamcash$"),
            CallbackQueryHandler(cb_shamcash_usd_start, pattern=r"^recharge:shamcash_usd$"),
            CallbackQueryHandler(cb_shamcash_manual, pattern=r"^sc_manual:"),
        ],
        states={
            SHAMCASH_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_shamcash_amount),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
            SHAMCASH_USD_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_shamcash_usd_amount),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
            SHAMCASH_PHOTO: [
                MessageHandler(filters.PHOTO, msg_shamcash_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_shamcash_photo),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
            CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|fclist:|order:|game:|menu:|back:)"),
        ],
        per_message=False,
        allow_reentry=True,
    )
    app.add_handler(shamcash_conv)

    app.add_handler(CallbackQueryHandler(cb_shamcash_verify, pattern=r"^sc_verify:"))
    app.add_handler(CallbackQueryHandler(cb_shamcash_usd_verify, pattern=r"^sc_verify_usd:"))

    pubg_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cancel_conversation),CallbackQueryHandler(cb_pubg_uc_select, pattern=r"^pubg_uc:")],
        states={
            PUBG_PLAYER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_pubg_player_id),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
            CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|fclist:|order:|game:|menu:|back:)"),
        ],
        per_message=False,
        allow_reentry=True,
    )
    app.add_handler(pubg_conv)

    app.add_handler(CallbackQueryHandler(cb_pubg_uc_confirm, pattern=r"^pubg_uc_confirm:"))
    app.add_handler(CallbackQueryHandler(cb_pubg_uc_verify, pattern=r"^pubg_uc_verify:"))

    freefire_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cancel_conversation),CallbackQueryHandler(cb_freefire_diamond_select, pattern=r"^ff_dia:")],
        states={
            FREEFIRE_PLAYER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_freefire_player_id),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
            CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|fclist:|order:|game:|menu:|back:)"),
        ],
        per_message=False,
        allow_reentry=True,
    )
    app.add_handler(freefire_conv)

    app.add_handler(CallbackQueryHandler(cb_freefire_diamond_confirm, pattern=r"^ff_dia_confirm:"))

    # ===== Generic Fastcard auto-delivery (memberships + codes + custom-amount balance) =====
    fastcard_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cancel_conversation),
            CallbackQueryHandler(cb_fastcard_buy_select, pattern=r"^fcbuy:"),
            CallbackQueryHandler(cb_fastcard_amount_start, pattern=r"^fcamt:"),
        ],
        states={
            FASTCARD_CUSTOM_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_fastcard_custom_amount),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^store:balance$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
            FASTCARD_PLAYER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_fastcard_player_id),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
            CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|fclist:|order:|game:|menu:|back:)"),
        ],
        per_message=False,
        allow_reentry=True,
    )
    app.add_handler(fastcard_conv)
    app.add_handler(CallbackQueryHandler(cb_fastcard_confirm, pattern=r"^fcconf:"))
    app.add_handler(CallbackQueryHandler(cb_fastcard_list_nav, pattern=r"^fclist:"))
    app.add_handler(CallbackQueryHandler(cb_fastcard_sold_out, pattern=r"^fcsold:"))

    # ===== Loyalty Points =====
    loyalty_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cancel_conversation),CallbackQueryHandler(cb_loyalty, pattern=r"^loyalty:redeem_custom$")],
        states={
            LOYALTY_REDEEM_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, loyalty_redeem_amount),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:loyalty$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
            CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|fclist:|order:|game:|menu:|back:)"),
        ],
        per_message=False,
        allow_reentry=True,
    )
    app.add_handler(loyalty_conv)
    app.add_handler(CallbackQueryHandler(cb_loyalty, pattern=r"^loyalty:redeem_all$"))

    # ===== Discount Coupon =====
    coupon_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cancel_conversation),CallbackQueryHandler(cb_coupon_entry, pattern=r"^menu:coupon$")],
        states={
            COUPON_CODE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_coupon_code),
                CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
                CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|pubg_uc:|ff_dia:|fcbuy:|loyalty:|menu:|back:|game_|fclist:)"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern=r"^menu:main$"),
            CallbackQueryHandler(cancel_conversation, pattern=r"^(recharge:|fclist:|order:|game:|menu:|back:)"),
        ],
        per_message=False,
        allow_reentry=True,
    )
    app.add_handler(coupon_conv)

    # Reply Keyboard nav — group=-1 يضمن الأولوية على ConversationHandlers
    _REPLY_KB_TEXTS = {
        "🔥 الألعاب 🎮", "💫 التطبيقات 📱",
        "💳 بطاقات وأكواد 🃏", "⚡ الرشق 📈", "🌐 الأرقام 📲",
        "💰 شحن الرصيد ⚡", "📊 حسابي 👤",
        "👑 نقاط الولاء 💎", "🎁 كود خصم 🎟", "💬 الدعم 📞",
        "🎮 قسم الألعاب", "📱 قسم التطبيقات", "🃏 قسم البطاقات والأكواد",
        "📈 قسم الرشق", "📲 قسم الأرقام",
        "💎 نقاط الولاء", "🎟 كود الخصم",
        "💰 شحن رصيد الحساب", "👤 معلومات حسابي", "📞 التواصل مع الأدمن",
    }
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(
            "^(" + "|".join(map(lambda s: s.replace("+", r"\+"), _REPLY_KB_TEXTS)) + ")$"
        ), cmd_reply_nav),
        group=-1,
    )

    app.add_handler(CallbackQueryHandler(cb_main_menu, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(cb_store, pattern=r"^store:"))
    app.add_handler(CallbackQueryHandler(cb_pubg_section, pattern=r"^pubg:"))
    app.add_handler(CallbackQueryHandler(cb_freefire_section, pattern=r"^ff:"))
    app.add_handler(CallbackQueryHandler(cb_supercell_section, pattern=r"^sc:"))
    app.add_handler(CallbackQueryHandler(cb_cod_section, pattern=r"^cdnav:"))
    app.add_handler(CallbackQueryHandler(cb_ludo_section, pattern=r"^lunav:"))
    app.add_handler(CallbackQueryHandler(cb_cards_section, pattern=r"^cards:"))
    app.add_handler(CallbackQueryHandler(cb_rating, pattern=r"^rate:"))
