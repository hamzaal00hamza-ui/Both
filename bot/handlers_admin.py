"""
لوحة الأدمن
"""
import logging
import asyncio
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from . import config, database as db, keyboards as kb, fastcard
from .jobs import (
    build_today_report,
    build_price_check_report,
    compute_price_check_data,
    format_price_check_report,
    apply_price_fix,
)
from . import notify

logger = logging.getLogger(__name__)

(
    ADMIN_SEARCH_USER,
    ADMIN_EDIT_BALANCE_ID,
    ADMIN_EDIT_BALANCE_AMOUNT,
    ADMIN_TOGGLE_BAN_ID,
    ADMIN_BROADCAST_TEXT,
    ADMIN_CODES_INPUT,
    ADMIN_RATES_SET_OFFERS,
    ADMIN_RATES_SET_RECHARGE,
    ADMIN_COUPON_CODE,
    ADMIN_COUPON_VALUE,
    ADMIN_COUPON_MIN_ORDER,
    ADMIN_COUPON_MAX_USES,
    ADMIN_CHANNEL_INPUT,
    ADMIN_PRICE_INPUT,
    ADMIN_RATES_SET_USDT_WALLET,
    ADMIN_PROFIT_MARGIN_SET,
) = range(100, 116)


def is_admin(update: Update) -> bool:
    return config.ADMIN_ID and update.effective_user.id == config.ADMIN_ID


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ هذا الأمر للأدمن فقط.")
        return
    if not config.ADMIN_ID:
        await update.message.reply_text("⚠️ ADMIN_ID غير مضبوط في الإعدادات.")
        return
    await update.message.reply_text(
        "🛠️ *لوحة الأدمن*\n\nاختر إجراءً:",
        reply_markup=kb.admin_panel(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cb_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(update):
        return ConversationHandler.END

    data = q.data

    if data == "admin:stats":
        s = db.get_stats()
        text = (
            "📊 *إحصائيات*\n\n"
            f"• المستخدمين: {s['users']}\n"
            f"• الطلبات: {s['orders']}\n"
            f"• طلبات الشحن: {s['recharges']}\n"
            f"• إجمالي الشحن المقبول: {s['total_recharged']:.0f} ل.س\n"
            f"• إجمالي المبيعات: {s['total_sold']:.0f} ل.س"
        )
        await q.edit_message_text(text, reply_markup=kb.admin_panel(), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    if data == "admin:pending":
        rch = db.get_pending_recharges(10)
        ords = db.get_pending_orders(10)
        lines = ["⏳ *الطلبات المعلقة*\n"]
        if rch:
            lines.append("*طلبات شحن:*")
            for r in rch:
                lines.append(f"  #{r['id']} | {r['method']} | {r['amount']:.0f} ل.س | uid={r['user_id']}")
        else:
            lines.append("لا توجد طلبات شحن معلقة.")
        lines.append("")
        if ords:
            lines.append("*طلبات شراء:*")
            for o in ords:
                lines.append(f"  #{o['id']} | {o['game']} | {o['item']} | {o['price']:.0f} ل.س | uid={o['user_id']}")
        else:
            lines.append("لا توجد طلبات شراء معلقة.")
        await q.edit_message_text("\n".join(lines), reply_markup=kb.admin_panel(), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    if data == "admin:panel":
        await q.edit_message_text(
            "🛠️ *لوحة الأدمن*\n\nاختر إجراءً:",
            reply_markup=kb.admin_panel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    if data == "admin:search_user":
        await q.edit_message_text("🔍 أرسل آيدي المستخدم:", reply_markup=kb.back_to_admin())
        return ADMIN_SEARCH_USER

    if data == "admin:edit_balance":
        await q.edit_message_text("✏️ أرسل آيدي المستخدم لتعديل رصيده:", reply_markup=kb.back_to_admin())
        return ADMIN_EDIT_BALANCE_ID

    if data == "admin:toggle_ban":
        await q.edit_message_text("🚫 أرسل آيدي المستخدم لحظره/فك حظره:", reply_markup=kb.back_to_admin())
        return ADMIN_TOGGLE_BAN_ID

    if data == "admin:broadcast":
        await q.edit_message_text("📢 أرسل نص الإشعار لإرساله لجميع المستخدمين:", reply_markup=kb.back_to_admin())
        return ADMIN_BROADCAST_TEXT

    if data == "admin:price_check":
        await q.edit_message_text(
            "🔍 جاري فحص أسعار Fastcard بدقّة...\n\n_قد يستغرق 10-30 ثانية._",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            check_data = await compute_price_check_data()
            report = format_price_check_report(check_data)
        except Exception as e:
            logger.exception("price_check failed: %s", e)
            check_data = {"ok": False, "error": str(e)}
            report = f"❌ فشل الفحص: {e}"

        # نخزّن البيانات لاستخدامها بعدين في الإصلاح التلقائي
        context.user_data["price_check_data"] = check_data
        has_fixable = bool(check_data.get("ok") and (check_data.get("loss") or check_data.get("thin")))

        # قص الرسالة إذا تجاوزت حد تيليغرام (4096)
        if len(report) > 3900:
            cut = report.rfind("\n", 0, 3900)
            report = report[: cut if cut > 0 else 3900] + "\n\n_... (تم اقتطاع التقرير لطوله)_"

        markup = kb.admin_price_check_actions(has_fixable)
        try:
            await q.edit_message_text(report, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await q.edit_message_text(report, reply_markup=markup)

        # نسخة لقناة التوثيق
        try:
            await notify.notify_channel_only(context.bot, report)
        except Exception:
            pass
        return ConversationHandler.END

    if data == "admin:price_check:fix":
        # شاشة تأكيد قبل تطبيق الأسعار المقترحة
        check_data = context.user_data.get("price_check_data") or {}
        loss_n = len(check_data.get("loss", []))
        thin_n = len(check_data.get("thin", []))
        total = loss_n + thin_n
        if total == 0:
            await q.answer("لا يوجد منتجات تحتاج إصلاح.", show_alert=True)
            return ConversationHandler.END
        await q.edit_message_text(
            "🛠️ *تأكيد تطبيق الأسعار المقترحة*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"🆘 منتجات خاسرة: *{loss_n}*\n"
            f"⚠️ منتجات بربح ضعيف: *{thin_n}*\n"
            f"📦 الإجمالي: *{total}* منتج\n\n"
            "البوت رح يضبط لكل منتج سعر يدوي يحقق هامش ربح *12%* "
            "بناءً على التكلفة الجديدة من Fastcard.\n\n"
            "_السعر اليدوي بصير له الأولوية على الحساب التلقائي._\n"
            "_تقدر ترجع لأي منتج لاحقاً وتعيده للحساب التلقائي._",
            reply_markup=kb.admin_price_check_fix_confirm(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    if data == "admin:price_check:fix:yes":
        check_data = context.user_data.get("price_check_data") or {}
        if not check_data.get("ok"):
            await q.answer("البيانات منتهية الصلاحية. شغّل فحص جديد.", show_alert=True)
            return ConversationHandler.END
        await q.edit_message_text("⏳ جاري تطبيق الأسعار المقترحة...")
        try:
            result = await apply_price_fix(check_data)
        except Exception as e:
            logger.exception("apply_price_fix failed: %s", e)
            await q.edit_message_text(
                f"❌ فشل التطبيق: {e}",
                reply_markup=kb.back_to_admin(),
            )
            return ConversationHandler.END

        applied = result["applied"]
        skipped = result["skipped"]
        details = result["details"]

        lines = [
            "✅ *تم تطبيق الأسعار المقترحة*",
            "━━━━━━━━━━━━━━━━━",
            f"📌 منتجات تم تعديلها: *{applied}*",
        ]
        if skipped:
            lines.append(f"⏭️ متخطّاة: {skipped}")
        if details:
            lines.append("\n*أبرز التغييرات:*")
            for d in details[:12]:
                old_s = f"{d['old']:,}".replace(",", "،")
                new_s = f"{d['new']:,}".replace(",", "،")
                lab = d['label'][:35]
                lines.append(f"• {lab}\n  {old_s} → *{new_s}* ل.س")
            if len(details) > 12:
                lines.append(f"_... و {len(details) - 12} منتج إضافي._")
        lines.append("\n_التغييرات سارية فوراً للزبائن._")

        # نمسح الكاش بعد التطبيق
        context.user_data.pop("price_check_data", None)

        text = "\n".join(lines)
        try:
            await q.edit_message_text(text, reply_markup=kb.back_to_admin(), parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await q.edit_message_text(text, reply_markup=kb.back_to_admin())
        try:
            await notify.notify_channel_only(context.bot, text)
        except Exception:
            pass
        return ConversationHandler.END

    if data == "admin:channel":
        cur = notify.get_admin_channel() or "—"
        await q.edit_message_text(
            "📡 *قناة توثيق الطلبات*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"القناة الحالية: `{cur}`\n\n"
            "📥 *لربط قناة جديدة:*\n"
            "1) أنشئ قناة على تيليغرام (خاصة أو عامة).\n"
            "2) أضف هذا البوت كأدمن في القناة (مع صلاحية إرسال رسائل).\n"
            "3) أرسل هنا أحد الصيغتين:\n"
            "   • `@username` للقناة العامة\n"
            "   • `-100xxxxxxxxxx` (ID رقمي) للقناة الخاصة\n\n"
            "❌ لإلغاء الربط أرسل: `off`\n\n"
            "_بعد الربط، كل إشعارات الطلبات (تأكيد/رفض/شحن/تقييم) تنسخ تلقائياً للقناة._",
            reply_markup=kb.back_to_admin(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_CHANNEL_INPUT

    if data == "admin:rates":
        await _show_rates_panel(q)
        return ConversationHandler.END

    if data == "admin:rates:fetch":
        await q.edit_message_text(
            "⏳ جاري جلب السعر من قناة @SaymouaaExchange...",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            from . import exchange_rate as _er
            ch = await asyncio.to_thread(_er._fetch_rate_from_channel)
            buy = ch["buy"]
            sell = ch["sell"]
            avg = ch["avg"]
            cur_rate = config.get_syp_per_usd()
            diff = avg - cur_rate
            diff_str = f"+{diff:,.0f}" if diff >= 0 else f"{diff:,.0f}"
            text = (
                "🌐 *سعر الدولار من @SaymouaaExchange*\n"
                "━━━━━━━━━━━━━━━━━\n\n"
                f"🛒 *شراء:* `{buy:,.0f} ل.س/$`\n"
                f"💵 *بيع:*   `{sell:,.0f} ل.س/$`\n"
                f"📊 *متوسط:* `{avg:,.0f} ل.س/$`\n\n"
                f"💾 *السعر المحفوظ حالياً:* `{cur_rate:,.0f} ل.س/$`\n"
                f"📈 *الفرق:* `{diff_str} ل.س`\n\n"
                "هل تريد تطبيق *المتوسط* كسعر تسعير العروض؟"
            )
            await q.edit_message_text(
                text,
                reply_markup=kb.admin_rates_apply_fetched(avg),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await q.edit_message_text(
                f"❌ *فشل جلب السعر من القناة*\n\n`{e}`\n\nتحقق من الاتصال أو حاول لاحقاً.",
                reply_markup=kb.admin_rates_panel(),
                parse_mode=ParseMode.MARKDOWN,
            )
        return ConversationHandler.END

    if data.startswith("admin:rates:apply:"):
        try:
            new_rate = int(data.split(":")[3])
            if 1000 <= new_rate <= 500_000:
                db.set_setting("syp_per_usd", str(new_rate))
                await q.edit_message_text(
                    f"✅ *تم تحديث سعر تسعير العروض إلى {new_rate:,} ل.س/$*".replace(",", "،"),
                    reply_markup=kb.admin_rates_panel(),
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await q.edit_message_text(
                    "❌ السعر خارج النطاق المسموح.",
                    reply_markup=kb.admin_rates_panel(),
                    parse_mode=ParseMode.MARKDOWN,
                )
        except Exception as e:
            await q.edit_message_text(
                f"❌ خطأ: {e}",
                reply_markup=kb.admin_rates_panel(),
                parse_mode=ParseMode.MARKDOWN,
            )
        return ConversationHandler.END

    if data == "admin:profit_margin":
        cur_margin = config.get_profit_margin()
        await q.edit_message_text(
            "📊 *إدارة هامش الربح*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"الهامش الحالي: *{cur_margin * 100:.1f}%*\n\n"
            "📝 أرسل النسبة الجديدة كرقم بين `0` و `100`\n"
            "_(مثال: أرسل `10` لهامش ربح 10%)_\n\n"
            "⚠️ سيطبَّق على كل العروض المسعَّرة بالدولار فوراً.",
            reply_markup=kb.admin_rates_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_PROFIT_MARGIN_SET

    if data == "admin:rates:set_offers":
        cur_rate = config.get_syp_per_usd()
        await q.edit_message_text(
            "💱 *تعديل سعر تسعير العروض*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"السعر الحالي: *{cur_rate:,.0f} ل.س / 1 $*\n\n"
            "📝 أرسل السعر الجديد (مثال: `15500`).\n\n"
            "_ملاحظة: التغيير سيطبّق فوراً على كل عروض المتجر التي لها تكلفة بالدولار._",
            reply_markup=kb.admin_rates_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_RATES_SET_OFFERS

    if data == "admin:rates:set_recharge":
        cur_rate = config.get_usd_to_syp()
        await q.edit_message_text(
            "💱 *تعديل سعر شحن الدولار*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"السعر الحالي: *{cur_rate:,.0f} ل.س / 1 $*\n\n"
            "📝 أرسل السعر الجديد (مثال: `15000`).\n\n"
            "_هذا السعر يُستخدم لتحويل مبالغ شحن \"شام كاش دولار\" إلى رصيد ل.س للزبائن._",
            reply_markup=kb.admin_rates_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_RATES_SET_RECHARGE

    if data == "admin:rates:set_usdt_wallet":
        cur_wallet = config.USDT_WALLET_BEP20 or db.get_setting("usdt_wallet_bep20") or "—"
        await q.edit_message_text(
            "💎 *ضبط محفظة USDT (BEP20 / BSC)*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"العنوان الحالي:\n`{cur_wallet}`\n\n"
            "📝 أرسل عنوان المحفظة الجديد (BEP20).\n"
            "أو أرسل `-` لتعطيل خيار USDT.",
            reply_markup=kb.admin_rates_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_RATES_SET_USDT_WALLET

    # ===== تعديل أسعار المنتجات =====
    if data == "admin:prices":
        try:
            overrides_count = len(db.list_price_overrides())
        except Exception:
            overrides_count = 0
        await q.edit_message_text(
            "💲 *تعديل أسعار المنتجات*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"📊 عدد المنتجات بسعر يدوي: *{overrides_count}*\n\n"
            "اختر القسم اللي بدّك تعدّل أسعاره:\n\n"
            "_ملاحظة: السعر اليدوي له الأولوية على الحساب التلقائي بسعر الصرف._",
            reply_markup=kb.admin_price_categories(0),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    if data.startswith("admin:prices:page:"):
        try:
            page = int(data.split(":")[3])
        except (ValueError, IndexError):
            page = 0
        try:
            overrides_count = len(db.list_price_overrides())
        except Exception:
            overrides_count = 0
        await q.edit_message_text(
            "💲 *تعديل أسعار المنتجات*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"📊 عدد المنتجات بسعر يدوي: *{overrides_count}*\n\n"
            "اختر القسم اللي بدّك تعدّل أسعاره:",
            reply_markup=kb.admin_price_categories(page),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    if data.startswith("admin:prices:cat:"):
        cat_key = data.split(":", 3)[3]
        title = config.get_price_edit_title(cat_key)
        offers = config.get_price_edit_offers(cat_key)
        if not offers:
            await q.edit_message_text(
                f"⚠️ القسم *{title}* فارغ.",
                reply_markup=kb.admin_price_categories(0),
                parse_mode=ParseMode.MARKDOWN,
            )
            return ConversationHandler.END
        await q.edit_message_text(
            f"💲 *{title}*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"📦 عدد العروض: *{len(offers)}*\n\n"
            "اضغط على المنتج اللي بدّك تعدّل سعره.\n"
            "_العروض المعلّمة بـ ✏️ عندها سعر يدوي._",
            reply_markup=kb.admin_price_offers(cat_key, 0),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    if data.startswith("admin:prices:catpg:"):
        parts = data.split(":")
        try:
            cat_key = parts[3]
            page = int(parts[4])
        except (ValueError, IndexError):
            return ConversationHandler.END
        title = config.get_price_edit_title(cat_key)
        offers = config.get_price_edit_offers(cat_key)
        await q.edit_message_text(
            f"💲 *{title}*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"📦 عدد العروض: *{len(offers)}*\n\n"
            "اضغط على المنتج اللي بدّك تعدّل سعره.\n"
            "_العروض المعلّمة بـ ✏️ عندها سعر يدوي._",
            reply_markup=kb.admin_price_offers(cat_key, page),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    if data.startswith("admin:prices:offer:"):
        parts = data.split(":", 4)
        if len(parts) < 5:
            return ConversationHandler.END
        cat_key = parts[3]
        offer_id = parts[4]
        offers = config.get_price_edit_offers(cat_key)
        offer = next((o for o in offers if o.get("id") == offer_id), None)
        if not offer:
            await q.edit_message_text(
                "⚠️ العرض غير موجود.",
                reply_markup=kb.admin_price_categories(0),
                parse_mode=ParseMode.MARKDOWN,
            )
            return ConversationHandler.END
        ov = db.get_price_override(offer_id)
        cur_price = config.get_offer_price(offer)
        base_price = int(offer.get("price", 0) or 0)
        cost_usd = offer.get("cost_usd")
        # حساب السعر التلقائي (بدون override) للعرض
        auto_price = base_price
        if cost_usd:
            rate = config.get_syp_per_usd()
            if rate != config.PRICING_BASE_RATE:
                auto_price = config.round_up_to_500(base_price * (rate / config.PRICING_BASE_RATE))

        lines = [
            f"💲 *{offer.get('label', offer_id)}*",
            "━━━━━━━━━━━━━━━━━",
            "",
            f"🆔 معرّف العرض: `{offer_id}`",
            f"💰 السعر الحالي: *{cur_price:,} ل.س*".replace(",", "،"),
            f"⚙️ السعر التلقائي: {auto_price:,} ل.س".replace(",", "،"),
        ]
        if cost_usd:
            lines.append(f"💵 التكلفة: ${cost_usd}")
        if ov is not None:
            lines.append(f"✏️ سعر يدوي مفعّل: *{ov:,} ل.س*".replace(",", "،"))
        else:
            lines.append("⚙️ يستخدم الحساب التلقائي حالياً")
        lines.append("")
        lines.append("📝 *أرسل السعر الجديد بالليرة السورية* (مثال: `25000`):")

        # خزن المفاتيح للاستخدام عند استقبال الرسالة
        context.user_data["price_edit_cat"] = cat_key
        context.user_data["price_edit_offer"] = offer_id

        await q.edit_message_text(
            "\n".join(lines),
            reply_markup=kb.admin_price_cancel(cat_key, offer_id),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_PRICE_INPUT

    if data.startswith("admin:prices:reset:"):
        parts = data.split(":", 4)
        if len(parts) < 5:
            return ConversationHandler.END
        cat_key = parts[3]
        offer_id = parts[4]
        try:
            db.delete_price_override(offer_id)
        except Exception as e:
            logger.warning("delete_price_override failed: %s", e)
        offers = config.get_price_edit_offers(cat_key)
        offer = next((o for o in offers if o.get("id") == offer_id), None)
        new_price = config.get_offer_price(offer) if offer else 0
        title = config.get_price_edit_title(cat_key)
        await q.edit_message_text(
            f"✅ *تم إرجاع الحساب التلقائي*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"📦 المنتج: {offer.get('label', offer_id) if offer else offer_id}\n"
            f"💰 السعر الجديد: *{new_price:,} ل.س*\n\n".replace(",", "،") +
            f"العرض رجع للحساب التلقائي بسعر الصرف.",
            reply_markup=kb.admin_price_offers(cat_key, 0),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    if data == "admin:today_report":
        try:
            text = await build_today_report()
        except Exception as e:
            logger.warning("today_report failed: %s", e)
            text = "❌ تعذّر توليد التقرير. حاول لاحقاً."
        await q.edit_message_text(text, reply_markup=kb.back_to_admin(), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    if data == "admin:profit":
        await _show_profit_panel(q)
        return ConversationHandler.END

    if data == "admin:top_users":
        try:
            top = await asyncio.to_thread(db.get_top_spenders, 10)
        except Exception as e:
            logger.warning("get_top_spenders failed: %s", e)
            top = []

        lines = ["🏆 *أفضل 10 زبائن إنفاقاً*", "━━━━━━━━━━━━━━━━━", ""]
        if not top:
            lines.append("_ما في زبائن مسجّل لهم طلبات أو شحنات بعد._")
        else:
            medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
            for i, u in enumerate(top):
                medal = medals[i] if i < len(medals) else "🔹"
                name = u.get("first_name") or u.get("username") or f"User {u['user_id']}"
                username = f"@{u['username']}" if u.get("username") else ""
                spent = float(u.get("total_spent_syp") or 0)
                recharged = float(u.get("total_recharged") or 0)
                count = int(u.get("orders_count") or 0)
                level = u.get("level") or "-"
                lines.append(
                    f"{medal} *{name}* {username}\n"
                    f"   🆔 `{u['user_id']}`  |  {level}\n"
                    f"   💰 إنفاق: *{spent:,.0f} ل.س* ({count} طلب)\n"
                    f"   📥 شحنات: {recharged:,.0f} ل.س\n"
                )

        text = "\n".join(lines)
        await q.edit_message_text(text, reply_markup=kb.back_to_admin(), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    if data == "admin:coupons":
        try:
            coupons = await asyncio.to_thread(db.list_coupons, False, 30)
        except Exception as e:
            logger.warning("list_coupons failed: %s", e)
            coupons = []
        lines = ["🎟 *إدارة الكوبونات*", "━━━━━━━━━━━━━━━━━", ""]
        if not coupons:
            lines.append("_ما في كوبونات حالياً. اضغط «إنشاء كوبون جديد» للبدء._")
        else:
            for c in coupons[:15]:
                active = int(c.get("active") or 0)
                status = "✅ فعّال" if active else "🚫 معطّل"
                if c["discount_type"] == "percent":
                    val_txt = f"{c['discount_value']:.0f}%"
                else:
                    val_txt = f"{c['discount_value']:,.0f} ل.س".replace(",", "،")
                used = int(c.get("used_count") or 0)
                max_uses = int(c.get("max_uses") or 0)
                uses_txt = f"{used}/{max_uses}" if max_uses > 0 else f"{used}/∞"
                min_o = float(c.get("min_order") or 0)
                min_txt = f" | حد أدنى: {min_o:,.0f}".replace(",", "،") if min_o > 0 else ""
                lines.append(f"`{c['code']}` — {val_txt} — {uses_txt}{min_txt}\n   {status}")
        text = "\n".join(lines)
        await q.edit_message_text(text, reply_markup=kb.admin_coupons_panel(coupons), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    if data == "admin:coupon:new":
        await q.edit_message_text(
            "➕ *إنشاء كوبون جديد*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "أدخل بيانات الكوبون بهذه الصيغة:\n\n"
            "`الكود | النوع | القيمة | حد_أدنى | عدد_استخدامات`\n\n"
            "*أمثلة:*\n"
            "• `WELCOME10 | percent | 10 | 50000 | 10`\n"
            "  (خصم 10% على طلب 50 ألف، لـ 10 زبائن)\n"
            "• `BONUS5K | fixed | 5000 | 0 | 10`\n"
            "  (5000 ل.س مجاناً، لـ 10 زبائن)\n\n"
            "📌 *النوع:* `percent` (نسبة %) أو `fixed` (مبلغ ثابت)\n"
            "📌 *حد_أدنى:* لازم للنسبة، اختياري للثابت (0 = بلا حد)\n"
            "📌 *عدد_استخدامات:* عادةً 10 — اكتب 0 للتوزيع غير المحدود\n\n"
            f"💡 _الكوبونات التلقائية تتولّد كل {config.AUTO_COUPON_INTERVAL_DAYS} يوم "
            f"بقيمة {config.AUTO_COUPON_VALUE_SYP:,} ل.س لـ {config.AUTO_COUPON_MAX_USES} زبائن._".replace(",", "،"),
            reply_markup=kb.admin_coupon_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_COUPON_CODE

    if data.startswith("admin:coupon:disable:"):
        try:
            cid = int(data.split(":")[3])
            ok = await asyncio.to_thread(db.deactivate_coupon, cid)
            await q.answer("✅ تم التعطيل" if ok else "⚠️ فشل التعطيل", show_alert=False)
        except Exception:
            await q.answer("⚠️ خطأ", show_alert=False)
        # إعادة عرض القائمة
        coupons = await asyncio.to_thread(db.list_coupons, False, 30)
        lines = ["🎟 *إدارة الكوبونات*", "━━━━━━━━━━━━━━━━━", ""]
        if not coupons:
            lines.append("_ما في كوبونات._")
        else:
            for c in coupons[:15]:
                active = int(c.get("active") or 0)
                status = "✅ فعّال" if active else "🚫 معطّل"
                if c["discount_type"] == "percent":
                    val_txt = f"{c['discount_value']:.0f}%"
                else:
                    val_txt = f"{c['discount_value']:,.0f} ل.س".replace(",", "،")
                used = int(c.get("used_count") or 0)
                max_uses = int(c.get("max_uses") or 0)
                uses_txt = f"{used}/{max_uses}" if max_uses > 0 else f"{used}/∞"
                lines.append(f"`{c['code']}` — {val_txt} — {uses_txt}\n   {status}")
        text = "\n".join(lines)
        await q.edit_message_text(text, reply_markup=kb.admin_coupons_panel(coupons), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    if data == "admin:ratings":
        try:
            summary = await asyncio.to_thread(db.get_ratings_summary)
            recent = await asyncio.to_thread(db.get_recent_ratings, 15)
        except Exception as e:
            logger.warning("ratings fetch failed: %s", e)
            summary = {"count": 0, "avg": 0.0, "distribution": {}}
            recent = []

        count = int(summary.get("count") or 0)
        avg = float(summary.get("avg") or 0)
        dist = summary.get("distribution") or {}

        lines = ["⭐ *تقييمات الزبائن*", "━━━━━━━━━━━━━━━━━", ""]
        if count == 0:
            lines.append("_ما في تقييمات بعد. سيظهر هنا أول تقييم بعد إكمال أول طلب._")
        else:
            stars_avg = "⭐" * int(round(avg))
            lines.append(f"📊 المتوسط: *{avg:.2f}* {stars_avg}")
            lines.append(f"📝 إجمالي التقييمات: *{count}*")
            lines.append("")
            lines.append("*توزيع النجوم:*")
            for s in [5, 4, 3, 2, 1]:
                c = int(dist.get(s, 0))
                pct = (c / count * 100) if count else 0
                bar = "█" * int(pct / 5) if pct > 0 else ""
                lines.append(f"{'⭐' * s}  {c:>3}  {bar} {pct:.0f}%")
            lines.append("")
            lines.append("━━━━━━━━━━━━━━━━━")
            lines.append("*آخر التقييمات:*")
            lines.append("")
            for r in recent[:10]:
                stars_r = "⭐" * int(r.get("stars") or 0)
                name = r.get("first_name") or r.get("username") or f"User {r.get('user_id')}"
                item = (r.get("order_item") or "—")
                if len(item) > 40:
                    item = item[:37] + "..."
                lines.append(
                    f"{stars_r}  *{name}*\n"
                    f"   📋 #{r['order_id']} — _{item}_"
                )
        text = "\n".join(lines)
        await q.edit_message_text(text, reply_markup=kb.back_to_admin(), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    if data == "admin:chart":
        text = (
            "📈 *الرسم البياني للأرباح*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "اختر فترة لعرض الرسم البياني:\n\n"
            "• المبيعات والتكلفة كأعمدة يومية\n"
            "• الربح الصافي كخط منحنى\n"
            "• إجماليات الفترة في العنوان\n\n"
            "_التوليد قد يأخذ ثانيتين..._"
        )
        await q.edit_message_text(text, reply_markup=kb.admin_chart_panel(), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    if data.startswith("admin:chart:"):
        try:
            days = int(data.split(":")[2])
        except (ValueError, IndexError):
            days = 30
        days = max(1, min(days, 365))
        await q.edit_message_text(
            f"⏳ جاري توليد الرسم البياني لآخر {days} يوم...",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            from .chart import build_profit_chart_png
            png_bytes = await asyncio.to_thread(build_profit_chart_png, days)
            if not png_bytes:
                await q.edit_message_text(
                    "❌ تعذّر توليد الرسم البياني.",
                    reply_markup=kb.admin_chart_panel(),
                )
                return ConversationHandler.END
            from io import BytesIO
            buf = BytesIO(png_bytes)
            buf.name = f"profit_{days}d.png"
            await context.bot.send_photo(
                chat_id=q.message.chat_id,
                photo=buf,
                caption=f"📈 رسم بياني للأرباح — آخر {days} يوم",
                reply_markup=kb.admin_chart_panel(),
            )
            try:
                await q.delete_message()
            except Exception:
                pass
        except Exception as e:
            logger.warning("chart generation failed: %s", e)
            await q.edit_message_text(
                f"❌ خطأ بتوليد الرسم: {e}",
                reply_markup=kb.admin_chart_panel(),
            )
        return ConversationHandler.END

    if data.startswith("admin:profit:"):
        period = data.split(":")[2]
        try:
            from .jobs import (
                build_profit_today,
                build_profit_week,
                build_profit_month,
                build_profit_all_time,
            )
            builders = {
                "today": build_profit_today,
                "week": build_profit_week,
                "month": build_profit_month,
                "all": build_profit_all_time,
            }
            builder = builders.get(period)
            if builder is None:
                text = "❌ فترة غير معروفة."
            else:
                text = await builder()
        except Exception as e:
            logger.warning("profit_report failed: %s", e)
            text = "❌ تعذّر توليد تقرير الأرباح. حاول لاحقاً."
        await q.edit_message_text(text, reply_markup=kb.admin_profit_back(), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    if data == "admin:syriatel_balance":
        from . import syriatel_cash
        if not syriatel_cash.is_enabled():
            await q.edit_message_text(
                "⚠️ *سرياتيل كاش (التحقق التلقائي) غير مفعّل*\n\n"
                "ضع `SYRIATEL_CASH_TOKEN` في الـ Secrets ثم أعد تشغيل البوت.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.back_to_admin(),
            )
            return ConversationHandler.END
        try:
            balance = await asyncio.to_thread(syriatel_cash.get_balance)
            await q.edit_message_text(
                f"📱 *رصيد محفظة سرياتيل كاش*\n\n"
                f"📞 الرقم: `{config.SYRIATEL_CASH_NUMBER}`\n"
                f"💵 الرصيد الحالي: *{balance:,.2f}* ل.س",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.back_to_admin(),
            )
        except syriatel_cash.SyriatelCashError as e:
            await q.edit_message_text(
                f"❌ تعذّر جلب الرصيد:\n`{e.code}` — {e.message}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.back_to_admin(),
            )
        except Exception as e:
            await q.edit_message_text(
                f"❌ خطأ غير متوقّع: {e}",
                reply_markup=kb.back_to_admin(),
            )
        return ConversationHandler.END

    if data == "admin:shamcash_balance":
        from . import shamcash
        if not config.SHAMCASH_TOKEN or config.SHAMCASH_TOKEN in ("", "ضع_التوكن_هنا"):
            await q.edit_message_text(
                "⚠️ *شام كاش غير مفعّل*\n\n"
                "ضع `SHAMCASH_TOKEN` في الـ Secrets ثم أعد تشغيل البوت.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.back_to_admin(),
            )
            return ConversationHandler.END
        try:
            account_id = await asyncio.to_thread(shamcash.get_active_account_id)
            if not account_id:
                await q.edit_message_text(
                    "❌ لم يُعثر على حساب شام كاش نشط.",
                    reply_markup=kb.back_to_admin(),
                )
                return ConversationHandler.END
            balances_data = await asyncio.to_thread(shamcash.get_balances, account_id)
            coin_names = {1: "USD 💵", 2: "SYP 🇸🇾", 3: "EUR 💶"}
            lines = ["💰 *رصيد محفظة شام كاش*\n", f"🆔 الحساب: `{account_id}`\n"]

            # normalize: قد يرجع list أو dict فيه "balances"/"data"، أو dict مفاتيحه عملات
            if isinstance(balances_data, list):
                items = balances_data
            elif isinstance(balances_data, dict):
                items = (
                    balances_data.get("balances")
                    or balances_data.get("data")
                    or None
                )
                if items is None:
                    # dict مباشر: {"USD": 100, "SYP": 5000, ...}
                    items = [{"coin": k, "amount": v} for k, v in balances_data.items()]
            else:
                items = []

            if not items:
                lines.append("⚠️ لا توجد بيانات رصيد.")

            coin_str_map = {"USD": "USD 💵", "SYP": "SYP 🇸🇾", "EUR": "EUR 💶",
                            "usd": "USD 💵", "syp": "SYP 🇸🇾", "eur": "EUR 💶"}

            for item in items:
                if not isinstance(item, dict):
                    lines.append(f"• {item}")
                    continue
                # coin: يمكن coin_id (int)، أو coin (str)، أو name، أو currency
                raw_coin = (item.get("coin_id") or item.get("coinId") or
                            item.get("coin") or item.get("name") or
                            item.get("currency") or "")
                # amount: يمكن amount، أو balance، أو value
                raw_amount = item.get("amount")
                if raw_amount is None:
                    raw_amount = item.get("balance")
                if raw_amount is None:
                    raw_amount = item.get("value", 0)

                # label
                if isinstance(raw_coin, int):
                    coin_label = coin_names.get(raw_coin, f"عملة {raw_coin}")
                else:
                    coin_label = coin_str_map.get(str(raw_coin), str(raw_coin)) or "—"
                try:
                    amt = float(raw_amount)
                except (ValueError, TypeError):
                    amt = 0.0
                lines.append(f"• {coin_label}: *{amt:,.2f}*")

            await q.edit_message_text(
                "\n".join(lines),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.back_to_admin(),
            )
        except shamcash.ShamCashError as e:
            await q.edit_message_text(
                f"❌ تعذّر جلب الرصيد:\n`{e.code}` — {e.message}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.back_to_admin(),
            )
        except Exception as e:
            await q.edit_message_text(
                f"❌ خطأ غير متوقّع: {e}",
                reply_markup=kb.back_to_admin(),
            )
        return ConversationHandler.END

    if data == "admin:stock" or data.startswith("admin:stock:"):
        return await _handle_stock(q, data)

    if data == "admin:supplier":
        if not fastcard.is_enabled():
            await q.edit_message_text(
                "⚠️ *المتجر (Fastcard) غير مفعّل*\n\n"
                "ضع المتغيّر `FASTCARD_TOKEN` في إعدادات الـ Secrets ثم أعد تشغيل البوت.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.back_to_admin(),
            )
            return ConversationHandler.END
        try:
            profile = await asyncio.to_thread(fastcard.get_profile)
            balance_usd = float(profile.get("balance") or 0)
            email = profile.get("email") or "—"

            # جلب بيانات المنتجات لببجي S1
            all_pubg_ids = [o["product_id"] for o in config.PUBG_UC_OFFERS if o.get("product_id")]
            try:
                products_raw = await asyncio.to_thread(fastcard.get_products, all_pubg_ids)
                products_map = {
                    int(p["id"]): p
                    for p in products_raw
                    if isinstance(p, dict) and p.get("id")
                }
            except Exception:
                products_map = {}

            def fmt_offer(o):
                pid = o.get("product_id")
                p = products_map.get(pid)
                if not p:
                    icon = "❓"
                    note = "غير موجود"
                elif not p.get("available", True):
                    icon = "🔴"
                    note = "غير متاح"
                else:
                    icon = "🟢"
                    raw_params = p.get("params") or []
                    if isinstance(raw_params, list) and raw_params:
                        keys = [
                            str(x.get("key") or x.get("name") or x) if isinstance(x, dict) else str(x)
                            for x in raw_params if x
                        ]
                        note = "حقول: " + ", ".join(keys)
                    else:
                        note = "متاح"
                label = o.get("label", "")
                return f"{icon} {label} | ID={pid} | {note}"

            s1_lines = "\n".join(fmt_offer(o) for o in config.PUBG_UC_OFFERS if o.get("product_id"))

            msg = (
                f"💼 حالة المتجر (Fastcard API)\n\n"
                f"📧 الحساب: {email}\n"
                f"💵 الرصيد: {balance_usd:.4f} $\n\n"
                f"🪙 ببجي سيرفر 1:\n{s1_lines or '—'}\n\n"
                f"❓=غير موجود 🔴=موقوف"
            )
            await q.edit_message_text(msg, reply_markup=kb.back_to_admin())
        except fastcard.FastcardError as e:
            await q.edit_message_text(
                f"❌ خطأ Fastcard:\n{e.message}",
                reply_markup=kb.back_to_admin(),
            )
        except Exception as e:
            await q.edit_message_text(
                f"❌ خطأ غير متوقع:\n{type(e).__name__}: {e}",
                reply_markup=kb.back_to_admin(),
            )
        return ConversationHandler.END


async def _handle_stock(q, data: str):
    """عرض/إيقاف/تشغيل المنتجات. data إما 'admin:stock' أو
    'admin:stock:disable:<pid>' أو 'admin:stock:enable:<pid>' أو 'admin:stock:refresh'."""
    if not fastcard.is_enabled():
        await q.edit_message_text(
            "⚠️ التكامل مع Fastcard غير مفعّل.",
            reply_markup=kb.back_to_admin(),
        )
        return ConversationHandler.END

    # تبديل حالة منتج
    parts = data.split(":")
    if len(parts) >= 4 and parts[2] in ("disable", "enable"):
        try:
            pid = int(parts[3])
        except ValueError:
            await q.answer("ID غير صالح", show_alert=True)
            return ConversationHandler.END
        if parts[2] == "disable":
            db.disable_product(pid, reason="manual")
            await q.answer("تم إيقاف المنتج")
        else:
            db.enable_product(pid)
            await q.answer("تم تشغيل المنتج")
        # نكمّل لعرض القائمة المحدّثة

    await q.edit_message_text("⏳ جاري فحص المخزون من Fastcard...")

    offers = config.collect_priced_offers()
    pids = sorted({o["product_id"] for o in offers if o.get("product_id")})
    try:
        stock_map = await asyncio.to_thread(fastcard.check_stock, pids)
    except Exception as e:
        await q.edit_message_text(
            f"❌ فشل جلب المخزون: {e}",
            reply_markup=kb.back_to_admin(),
        )
        return ConversationHandler.END

    disabled = set(db.list_disabled_products())
    # مفقود من المتجر = ما رجع له Fastcard
    out_of_stock_pids = []
    missing_pids = []
    for o in offers:
        pid = o["product_id"]
        if pid not in stock_map:
            missing_pids.append(pid)
        elif stock_map.get(pid) is False:
            out_of_stock_pids.append(pid)

    # خرائط للعرض
    by_pid = {o["product_id"]: o for o in offers}

    rows = []
    lines = ["📦 *المنتجات غير المتوفرة / الموقوفة*\n"]

    def _short(label: str, n: int = 28) -> str:
        return label if len(label) <= n else label[: n - 1] + "…"

    section_added = False
    if out_of_stock_pids:
        section_added = True
        lines.append("\n🔴 *غير متوفرة على فاست كارد:*")
        for pid in out_of_stock_pids:
            o = by_pid[pid]
            mark = "⛔" if pid in disabled else "✅"
            lines.append(f"  • {_short(o['label'])} | #{pid} {mark}")
            btn_label = "تشغيل" if pid in disabled else "إيقاف"
            action = "enable" if pid in disabled else "disable"
            rows.append([InlineKeyboardButton(
                f"{mark} {_short(o['label'], 22)} — {btn_label}",
                callback_data=f"admin:stock:{action}:{pid}",
            )])

    if missing_pids:
        section_added = True
        lines.append("\n❓ *غير موجودة في فاست كارد:*")
        for pid in missing_pids[:20]:
            o = by_pid[pid]
            mark = "⛔" if pid in disabled else "✅"
            lines.append(f"  • {_short(o['label'])} | #{pid} {mark}")

    # المنتجات الموقوفة يدوياً (حتى لو متوفرة)
    manual_only = [pid for pid in disabled if pid not in out_of_stock_pids and pid in stock_map]
    if manual_only:
        section_added = True
        lines.append("\n⛔ *موقوفة يدوياً (متوفرة على المتجر):*")
        for pid in manual_only:
            o = by_pid.get(pid)
            label = o["label"] if o else f"#{pid}"
            lines.append(f"  • {_short(label)} | #{pid}")
            rows.append([InlineKeyboardButton(
                f"✅ تشغيل {_short(label, 22)}",
                callback_data=f"admin:stock:enable:{pid}",
            )])

    if not section_added:
        lines.append("\n✅ كل المنتجات متوفرة ومفعّلة.")

    rows.append([InlineKeyboardButton("🔄 تحديث", callback_data="admin:stock:refresh")])
    rows.append([InlineKeyboardButton("⬅️ رجوع للوحة الأدمن", callback_data="admin:panel")])

    text = "\n".join(lines)
    if len(text) > 3900:
        text = text[:3900] + "\n…"
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


async def msg_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    try:
        uid = int((update.message.text or "").strip())
    except ValueError:
        await update.message.reply_text("⚠️ آيدي غير صالح.", reply_markup=kb.admin_panel())
        return ConversationHandler.END
    user = db.get_user(uid)
    if not user:
        await update.message.reply_text("❌ مستخدم غير موجود.", reply_markup=kb.admin_panel())
        return ConversationHandler.END
    text = (
        f"👤 *مستخدم* {uid}\n"
        f"• الاسم: {user.get('username') or user.get('first_name') or '—'}\n"
        f"• الرصيد: {user['balance']:.0f} ل.س\n"
        f"• المستوى: {user['level']}\n"
        f"• إجمالي الشحن: {user['total_recharged']:.0f} ل.س\n"
        f"• محظور: {'نعم' if user['is_banned'] else 'لا'}"
    )
    await update.message.reply_text(text, reply_markup=kb.admin_panel(), parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


async def msg_edit_balance_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    try:
        uid = int((update.message.text or "").strip())
    except ValueError:
        await update.message.reply_text("⚠️ آيدي غير صالح.", reply_markup=kb.admin_panel())
        return ConversationHandler.END
    if not db.get_user(uid):
        await update.message.reply_text("❌ مستخدم غير موجود.", reply_markup=kb.admin_panel())
        return ConversationHandler.END
    context.user_data["edit_balance_uid"] = uid
    await update.message.reply_text(
        f"أرسل المبلغ الجديد للرصيد للمستخدم {uid} (يستبدل الرصيد الحالي):",
        reply_markup=kb.back_to_admin(),
    )
    return ADMIN_EDIT_BALANCE_AMOUNT


async def msg_edit_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    try:
        amount = float((update.message.text or "").strip())
    except ValueError:
        await update.message.reply_text("⚠️ مبلغ غير صالح.", reply_markup=kb.admin_panel())
        return ConversationHandler.END
    uid = context.user_data.pop("edit_balance_uid", None)
    if not uid:
        return ConversationHandler.END
    db.set_balance(uid, amount)
    await update.message.reply_text(
        f"✅ تم تعديل رصيد المستخدم {uid} إلى {amount:.0f} ل.س",
        reply_markup=kb.admin_panel(),
    )
    return ConversationHandler.END


async def msg_toggle_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    try:
        uid = int((update.message.text or "").strip())
    except ValueError:
        await update.message.reply_text("⚠️ آيدي غير صالح.", reply_markup=kb.admin_panel())
        return ConversationHandler.END
    user = db.get_user(uid)
    if not user:
        await update.message.reply_text("❌ مستخدم غير موجود.", reply_markup=kb.admin_panel())
        return ConversationHandler.END
    new_state = not bool(user["is_banned"])
    db.set_banned(uid, new_state)
    await update.message.reply_text(
        f"✅ تم {'حظر' if new_state else 'فك حظر'} المستخدم {uid}.",
        reply_markup=kb.admin_panel(),
    )
    return ConversationHandler.END


async def msg_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    text = update.message.text or ""
    user_ids = db.all_user_ids()
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, f"📢 *إشعار من الإدارة*\n\n{text}", parse_mode=ParseMode.MARKDOWN)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await update.message.reply_text(
        f"📢 تم الإرسال لـ {sent} | فشل: {failed}",
        reply_markup=kb.admin_panel(),
    )
    return ConversationHandler.END


async def msg_admin_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل @username أو -100xxxxx أو 'off' لضبط/إلغاء قناة التوثيق."""
    if not is_admin(update):
        return ConversationHandler.END
    raw = (update.message.text or "").strip()

    if raw.lower() in ("off", "إلغاء", "الغاء", "-", "/off"):
        notify.set_admin_channel("")
        await update.message.reply_text(
            "✅ تم إلغاء ربط قناة التوثيق.",
            reply_markup=kb.admin_panel(),
        )
        return ConversationHandler.END

    # تحقق من الصيغة
    val = raw
    if not (val.startswith("@") or val.lstrip("-").isdigit()):
        await update.message.reply_text(
            "❌ الصيغة غير صحيحة.\n\n"
            "الصيغ المقبولة:\n"
            "• `@channel_username`\n"
            "• `-1001234567890` (chat_id رقمي)\n"
            "• `off` لإلغاء الربط",
            reply_markup=kb.back_to_admin(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_CHANNEL_INPUT

    # اختبر الإرسال قبل الحفظ
    try:
        chat_id = int(val) if val.lstrip("-").isdigit() else val
        test_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="✅ *تم ربط قناة توثيق الطلبات بنجاح*\n\nستصلك من الآن نسخة من كل إشعارات البوت هنا.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        err = str(e)[:200]
        await update.message.reply_text(
            f"❌ *فشل الإرسال للقناة:*\n`{err}`\n\n"
            "تأكد من:\n"
            "• البوت أدمن في القناة\n"
            "• صلاحية إرسال الرسائل مفعلة\n"
            "• الاسم/المعرّف صحيح",
            reply_markup=kb.back_to_admin(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_CHANNEL_INPUT

    notify.set_admin_channel(val)
    await update.message.reply_text(
        f"✅ تم ربط قناة التوثيق بنجاح!\n\nالقناة: `{val}`",
        reply_markup=kb.admin_panel(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


# ============= Decision callbacks =============
async def cb_admin_recharge_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(update):
        return
    parts = q.data.split(":")
    action = parts[1]
    req_id = int(parts[2])
    req = db.get_recharge_request(req_id)
    if not req:
        await q.edit_message_caption("⚠️ الطلب غير موجود.") if q.message.photo else await q.edit_message_text("⚠️ الطلب غير موجود.")
        return
    if req["status"] != "pending":
        msg = f"⚠️ الطلب تم التعامل معه مسبقاً ({req['status']})."
        if q.message.photo:
            await q.edit_message_caption(msg)
        else:
            await q.edit_message_text(msg)
        return

    if action == "approve":
        db.update_recharge_status(req_id, "approved")
        # تحويل العملة إذا كانت الطريقة "شام كاش دولار"
        is_usd = req.get("method") == "shamcash_usd"
        if is_usd:
            credit_syp = float(req["amount"]) * config.get_usd_to_syp()
            user_msg_amount = f"*{req['amount']:.2f} $* (≈ {credit_syp:,.0f} ل.س)"
            caption_amount = f"{req['amount']:.2f} $ ≈ {credit_syp:,.0f} ل.س"
        else:
            credit_syp = float(req["amount"])
            user_msg_amount = f"*{credit_syp:.0f}* ل.س"
            caption_amount = f"{credit_syp:.0f} ل.س"
        result = db.update_balance(req["user_id"], credit_syp, count_as_recharge=True)
        try:
            await context.bot.send_message(
                req["user_id"],
                f"✅ تم قبول طلب الشحن #{req_id}\n"
                f"تمت إضافة {user_msg_amount} لرصيدك.\n"
                f"رصيدك الحالي: {result['balance']:,.0f} ل.س\n"
                f"مستواك: 🏅 {result['level']}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"notify user failed: {e}")
        # عمولة الإحالة (8%) إذا للمستخدم محيل
        try:
            from .handlers_user import apply_referral_commission
            await apply_referral_commission(
                context.bot, int(req["user_id"]), float(credit_syp),
                result.get("referrer_id") if result else None,
            )
        except Exception as e:
            logger.error(f"referral commission failed: {e}")
        # إشعار ترقية المستوى إذا انتقل لمستوى أعلى
        try:
            from .handlers_user import notify_level_up
            await notify_level_up(context.bot, int(req["user_id"]), result)
        except Exception as e:
            logger.error(f"level up notify failed: {e}")
        new_caption = f"✅ *تم القبول* — #{req_id} — {caption_amount}"

        # إشعار قناة التوثيق
        try:
            user_info = db.get_user(int(req["user_id"])) or {}
            uname = f"@{user_info['username']}" if user_info.get("username") else user_info.get("first_name", "—")
            method_labels = {
                "syriatel": "سيرياتيل كاش",
                "shamcash": "شام كاش",
                "shamcash_usd": "شام كاش دولار",
                "usdt": "USDT (BEP20 / BSC)",
                "manual": "يدوي",
            }
            method_ar = method_labels.get(req.get("method", ""), req.get("method", "—"))
            channel_text = (
                f"✅ *طلب شحن مقبول — #{req_id}*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 المستخدم: {uname} `({req['user_id']})`\n"
                f"💳 طريقة الدفع: {method_ar}\n"
                f"💰 المبلغ المضاف: *{caption_amount}*\n"
                f"🏦 الرصيد الجديد: *{result['balance']:,.0f} ل.س*\n"
                f"🏅 المستوى: {result['level']}"
            )
            await notify.notify_channel_only(context.bot, channel_text)
        except Exception as _e:
            logger.warning("channel notify recharge failed: %s", _e)

    else:
        db.update_recharge_status(req_id, "rejected")
        try:
            await context.bot.send_message(
                req["user_id"],
                f"❌ تم رفض طلب الشحن #{req_id}.\nللاستفسار: {config.SUPPORT_USERNAME}",
            )
        except Exception:
            pass
        new_caption = f"❌ *تم الرفض* — #{req_id}"

    try:
        if q.message.photo:
            await q.edit_message_caption(new_caption, parse_mode=ParseMode.MARKDOWN)
        else:
            await q.edit_message_text(new_caption, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        pass


async def cb_admin_order_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(update):
        return
    parts = q.data.split(":")
    action = parts[1]
    order_id = int(parts[2])
    order = db.get_order(order_id)
    if not order:
        await q.edit_message_text("⚠️ الطلب غير موجود.")
        return
    if order["status"] != "pending":
        await q.edit_message_text(f"⚠️ الطلب تم التعامل معه مسبقاً ({order['status']}).")
        return

    if action == "approve":
        db.update_order_status(order_id, "completed")
        try:
            await context.bot.send_message(
                order["user_id"],
                f"✅ تم تنفيذ طلبك #{order_id}\n"
                f"اللعبة: {order['game']}\n"
                f"العرض: {order['item']}\n"
                f"ID اللاعب: {order['player_id']}",
            )
        except Exception:
            pass
        # منح نقاط الولاء + طلب تقييم
        try:
            from . import handlers_user as hu
            await hu.grant_loyalty_for_order(context.bot, order["user_id"], float(order.get("price") or 0))
            await hu.send_rating_prompt(context.bot, order["user_id"], order_id, order.get("item", ""))
        except Exception:
            pass
        # إشعار قناة التوثيق
        try:
            user_info = db.get_user(int(order["user_id"])) or {}
            uname = f"@{user_info['username']}" if user_info.get("username") else user_info.get("first_name", "—")
            channel_text = (
                f"✅ *طلب شراء منفّذ — #{order_id}*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 المستخدم: {uname} `({order['user_id']})`\n"
                f"🎮 اللعبة: {order['game']}\n"
                f"🎁 العرض: {order['item']}\n"
                f"🆔 ID اللاعب: `{order['player_id']}`\n"
                f"💰 المبلغ: *{float(order.get('price',0)):,.0f} ل.س*"
            )
            await notify.notify_channel_only(context.bot, channel_text)
        except Exception as _e:
            logger.warning("channel notify order failed: %s", _e)

        await q.edit_message_text(f"✅ *تم التنفيذ* — #{order_id}", parse_mode=ParseMode.MARKDOWN)
    else:
        db.update_order_status(order_id, "rejected")
        db.update_balance(order["user_id"], float(order["price"]))
        try:
            await context.bot.send_message(
                order["user_id"],
                f"❌ تم رفض طلب #{order_id} وتم إرجاع المبلغ {order['price']:.0f} ل.س لرصيدك.",
            )
        except Exception:
            pass
        await q.edit_message_text(f"❌ *تم الرفض واسترجاع المبلغ* — #{order_id}", parse_mode=ParseMode.MARKDOWN)


async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء.", reply_markup=kb.admin_panel())
    return ConversationHandler.END


async def cb_admin_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعامل مع أزرار قائمة الأكواد: add / clear_menu / clear / إلخ."""
    q = update.callback_query
    await q.answer()
    if not is_admin(update):
        return ConversationHandler.END

    parts = q.data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "add" and len(parts) > 2:
        offer_id = parts[2]
        offer = next((o for o in config.PUBG_UC_OFFERS if o["id"] == offer_id), None)
        if not offer:
            return ConversationHandler.END
        context.user_data["codes_offer_id"] = offer_id
        avail = db.count_available_codes(offer_id)
        await q.edit_message_text(
            f"📥 *إضافة أكواد {offer['label']}*\n\n"
            f"المتوفر حالياً: {avail}\n\n"
            "ابعت الأكواد، كل كود بسطر منفصل (أو افصلهم بفاصلة).\n"
            "بسحب المكرر تلقائياً.",
            reply_markup=kb.back_to_admin(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_CODES_INPUT

    if action == "clear_menu":
        await q.edit_message_text(
            "🗑️ *تفريغ المخزون*\n\nاختر الباقة لحذف الأكواد المتوفرة فيها (المباعة لا تُمس):",
            reply_markup=kb.admin_codes_clear_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    if action == "clear" and len(parts) > 2:
        offer_id = parts[2]
        offer = next((o for o in config.PUBG_UC_OFFERS if o["id"] == offer_id), None)
        if not offer:
            return ConversationHandler.END
        deleted = db.clear_available_codes(offer_id)
        inv = db.codes_inventory()
        await q.edit_message_text(
            f"✅ تم حذف *{deleted}* كود من *{offer['label']}*.",
            reply_markup=kb.admin_codes_menu(inv),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END


async def msg_admin_codes_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END

    offer_id = context.user_data.get("codes_offer_id")
    offer = next((o for o in config.PUBG_UC_OFFERS if o["id"] == offer_id), None) if offer_id else None
    if not offer:
        await update.message.reply_text("⚠️ خطأ، أعد البدء من قائمة الأكواد.", reply_markup=kb.admin_panel())
        return ConversationHandler.END

    raw = update.message.text or ""
    # split على السطور أو الفواصل
    tokens = []
    for line in raw.replace(",", "\n").splitlines():
        t = line.strip()
        if t:
            tokens.append(t)

    if not tokens:
        await update.message.reply_text(
            "⚠️ ما لقيت أي كود بالنص. أعد الإرسال:",
            reply_markup=kb.back_to_admin(),
        )
        return ADMIN_CODES_INPUT

    added = db.add_uc_codes(offer_id, tokens)
    skipped = len(tokens) - added
    inv = db.codes_inventory()

    await update.message.reply_text(
        f"✅ *تمت الإضافة*\n\n"
        f"الباقة: {offer['label']}\n"
        f"تمت إضافة: *{added}* كود جديد\n"
        f"تم تجاهل: {skipped} (مكرر/فارغ)\n"
        f"المخزون الكلي للباقة: *{inv.get(offer_id, 0)}*",
        reply_markup=kb.admin_codes_menu(inv),
        parse_mode=ParseMode.MARKDOWN,
    )
    context.user_data.pop("codes_offer_id", None)
    return ConversationHandler.END


async def _show_profit_panel(q) -> None:
    """يعرض قائمة فترات الأرباح."""
    text = (
        "💵 *تقارير الأرباح*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "اختر الفترة لعرض الربح الصافي:\n\n"
        "📅 *اليوم* — منذ منتصف الليل (UTC)\n"
        "📆 *آخر 7 أيام* — أسبوع كامل\n"
        "🗓 *آخر 30 يوم* — شهر كامل\n"
        "🏆 *كل الفترة* — منذ بداية تشغيل البوت\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "_التقرير يحسب: المبيعات − (التكلفة بالدولار × سعر شحن الدولار)._"
    )
    await q.edit_message_text(text, reply_markup=kb.admin_profit_panel(), parse_mode=ParseMode.MARKDOWN)


async def _show_rates_panel(q) -> None:
    """يعرض شاشة سعر الصرف الحالي مع أزرار التعديل."""
    syp_per_usd = config.get_syp_per_usd()
    usd_to_syp = config.get_usd_to_syp()
    text = (
        "💱 *إدارة سعر الصرف*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"📊 *سعر تسعير العروض:*\n"
        f"   `1 $ = {syp_per_usd:,.0f} ل.س`\n"
        "   _يُستخدم لحساب أسعار كل عروض المتجر تلقائياً._\n\n"
        f"💵 *سعر شحن الدولار:*\n"
        f"   `1 $ = {usd_to_syp:,.0f} ل.س`\n"
        "   _يُستخدم لتحويل مبالغ شام كاش دولار إلى رصيد._\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "💡 *نصيحة:* اضبط سعر تسعير العروض أعلى من سعر شحن الدولار "
        "لتحقق هامش ربح على كل عملية بيع."
    )
    await q.edit_message_text(text, reply_markup=kb.admin_rates_panel(), parse_mode=ParseMode.MARKDOWN)


def _parse_rate(text: str) -> Optional[int]:
    """يحلل سعر صرف من نص. يقبل أرقام عادية، فواصل، إلخ. يرجع None لو غير صالح."""
    if not text:
        return None
    cleaned = text.strip().replace(",", "").replace("،", "").replace(" ", "")
    try:
        val = int(float(cleaned))
        if val < 1000 or val > 1_000_000:
            return None
        return val
    except (ValueError, TypeError):
        return None


async def msg_set_rate_offers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    new_rate = _parse_rate(update.message.text)
    if new_rate is None:
        await update.message.reply_text(
            "⚠️ سعر غير صالح. أرسل رقم بين 1,000 و 1,000,000 (مثل `15500`):",
            reply_markup=kb.admin_rates_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_RATES_SET_OFFERS
    old_rate = config.get_syp_per_usd()
    db.set_setting("syp_per_usd", str(new_rate))
    await update.message.reply_text(
        "✅ *تم تحديث سعر تسعير العروض*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"السعر السابق: {old_rate:,.0f} ل.س\n"
        f"السعر الجديد: *{new_rate:,} ل.س*\n\n"
        "🔄 جميع أسعار العروض في المتجر تم تحديثها تلقائياً.",
        reply_markup=kb.back_to_admin(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


def _parse_price(text: str) -> Optional[int]:
    """يحلل سعر بالليرة من نص. يقبل أرقام عربية، فواصل، إلخ."""
    if not text:
        return None
    cleaned = text.strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩،", "0123456789,"))
    cleaned = cleaned.replace(",", "").replace(" ", "").replace("ل.س", "").replace("ل.س.", "")
    cleaned = cleaned.replace("ليرة", "").strip()
    try:
        val = int(float(cleaned))
        if val < 1 or val > 100_000_000:
            return None
        return val
    except (ValueError, TypeError):
        return None


async def msg_set_offer_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل السعر اليدوي الجديد لمنتج معين ويحفظه."""
    if not is_admin(update):
        return ConversationHandler.END
    cat_key = context.user_data.get("price_edit_cat")
    offer_id = context.user_data.get("price_edit_offer")
    if not cat_key or not offer_id:
        await update.message.reply_text(
            "⚠️ انتهت الجلسة. ابدأ من جديد من لوحة الأدمن.",
            reply_markup=kb.back_to_admin(),
        )
        return ConversationHandler.END

    new_price = _parse_price(update.message.text)
    if new_price is None:
        await update.message.reply_text(
            "⚠️ سعر غير صالح. أرسل رقم صحيح بالليرة (مثال: `25000`):",
            reply_markup=kb.admin_price_cancel(cat_key, offer_id),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_PRICE_INPUT

    offers = config.get_price_edit_offers(cat_key)
    offer = next((o for o in offers if o.get("id") == offer_id), None)
    if not offer:
        await update.message.reply_text(
            "⚠️ العرض غير موجود.",
            reply_markup=kb.back_to_admin(),
        )
        return ConversationHandler.END

    old_price = config.get_offer_price(offer)
    try:
        db.set_price_override(offer_id, new_price)
    except Exception as e:
        logger.warning("set_price_override failed: %s", e)
        await update.message.reply_text(
            "❌ تعذّر حفظ السعر. حاول مرة ثانية.",
            reply_markup=kb.admin_price_offers(cat_key, 0),
        )
        return ConversationHandler.END

    context.user_data.pop("price_edit_cat", None)
    context.user_data.pop("price_edit_offer", None)

    await update.message.reply_text(
        "✅ *تم تحديث السعر*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"📦 المنتج: {offer.get('label', offer_id)}\n"
        f"💰 السعر القديم: {old_price:,} ل.س\n".replace(",", "،") +
        f"💰 السعر الجديد: *{new_price:,} ل.س* ✏️\n\n".replace(",", "،") +
        "🔄 السعر الجديد سيظهر للزبائن فوراً.",
        reply_markup=kb.admin_price_offers(cat_key, 0),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def msg_set_rate_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    new_rate = _parse_rate(update.message.text)
    if new_rate is None:
        await update.message.reply_text(
            "⚠️ سعر غير صالح. أرسل رقم بين 1,000 و 1,000,000 (مثل `15000`):",
            reply_markup=kb.admin_rates_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_RATES_SET_RECHARGE
    old_rate = config.get_usd_to_syp()
    db.set_setting("usd_to_syp", str(new_rate))
    await update.message.reply_text(
        "✅ *تم تحديث سعر شحن الدولار*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"السعر السابق: {old_rate:,.0f} ل.س\n"
        f"السعر الجديد: *{new_rate:,} ل.س*\n\n"
        "🔄 سيُطبّق على شحنات شام كاش دولار من الآن.",
        reply_markup=kb.back_to_admin(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def msg_set_usdt_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    addr = (update.message.text or "").strip()
    if addr == "-":
        db.set_setting("usdt_wallet_bep20", "")
        await update.message.reply_text(
            "✅ تم تعطيل خيار USDT. لن يظهر للمستخدمين حتى تضبط محفظة صالحة.",
            reply_markup=kb.back_to_admin(),
        )
        return ConversationHandler.END
    if len(addr) < 20:
        await update.message.reply_text(
            "⚠️ العنوان يبدو قصيراً جداً. أعد إرسال عنوان BEP20 الصحيح:",
            reply_markup=kb.admin_rates_cancel(),
        )
        return ADMIN_RATES_SET_USDT_WALLET
    db.set_setting("usdt_wallet_bep20", addr)
    await update.message.reply_text(
        "✅ *تم حفظ محفظة USDT*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"العنوان الجديد:\n`{addr}`\n\n"
        "💎 سيظهر خيار USDT الآن في صفحة الشحن للمستخدمين.",
        reply_markup=kb.back_to_admin(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def msg_set_profit_margin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    raw = (update.message.text or "").strip().replace(",", "").replace("،", "").replace("%", "")
    try:
        pct = float(raw)
        if not (0 <= pct <= 100):
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ نسبة غير صالحة. أرسل رقم بين `0` و `100` (مثال: `12`):",
            reply_markup=kb.admin_rates_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_PROFIT_MARGIN_SET
    old_margin = config.get_profit_margin()
    db.set_setting("profit_margin", str(pct / 100))
    await update.message.reply_text(
        "✅ *تم تحديث هامش الربح*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"الهامش السابق: *{old_margin * 100:.1f}%*\n"
        f"الهامش الجديد: *{pct:.1f}%*\n\n"
        "🔄 جميع أسعار العروض المسعَّرة بالدولار تم تحديثها تلقائياً.",
        reply_markup=kb.back_to_admin(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def msg_admin_create_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    txt = (update.message.text or "").strip()
    txt = txt.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩،", "0123456789,"))
    parts = [p.strip() for p in txt.split("|")]
    if len(parts) < 3:
        await update.message.reply_text(
            "⚠️ الصيغة غير صحيحة.\n"
            "الصيغة: `الكود | النوع | القيمة | حد_أدنى | عدد_استخدامات`\n"
            "مثال: `WELCOME10 | percent | 10 | 50000 | 100`",
            reply_markup=kb.admin_coupon_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_COUPON_CODE
    code = parts[0].upper().replace(" ", "")
    dtype = parts[1].lower()
    if dtype not in ("percent", "fixed"):
        await update.message.reply_text(
            "⚠️ النوع لازم يكون `percent` أو `fixed`.",
            reply_markup=kb.admin_coupon_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_COUPON_CODE
    try:
        value = float(parts[2])
        if value <= 0:
            raise ValueError
        if dtype == "percent" and value > 100:
            raise ValueError
    except (ValueError, TypeError):
        await update.message.reply_text(
            "⚠️ القيمة غير صالحة (للنسبة من 1 إلى 100، للثابت > 0).",
            reply_markup=kb.admin_coupon_cancel(),
        )
        return ADMIN_COUPON_CODE
    try:
        min_order = float(parts[3]) if len(parts) > 3 and parts[3] else 0
        if min_order < 0:
            min_order = 0
    except (ValueError, TypeError):
        min_order = 0
    if dtype == "percent" and min_order <= 0:
        await update.message.reply_text(
            "⚠️ كوبون النسبة لازم له «حد أدنى» للطلب (> 0).",
            reply_markup=kb.admin_coupon_cancel(),
        )
        return ADMIN_COUPON_CODE
    try:
        max_uses = int(float(parts[4])) if len(parts) > 4 and parts[4] else 0
        if max_uses < 0:
            max_uses = 0
    except (ValueError, TypeError):
        max_uses = 0

    # تحقق من تكرار الكود
    existing = await asyncio.to_thread(db.get_coupon_by_code, code)
    if existing:
        await update.message.reply_text(
            f"⚠️ الكود `{code}` موجود مسبقاً. اختر كود آخر.",
            reply_markup=kb.admin_coupon_cancel(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_COUPON_CODE

    try:
        cid = await asyncio.to_thread(
            db.create_coupon, code, dtype, value, min_order, max_uses, None
        )
    except Exception as e:
        logger.warning("create_coupon failed: %s", e)
        await update.message.reply_text(
            f"⚠️ فشل الحفظ: {e}",
            reply_markup=kb.admin_coupon_cancel(),
        )
        return ADMIN_COUPON_CODE

    if dtype == "percent":
        val_txt = f"{value:.0f}%"
    else:
        val_txt = f"{value:,.0f} ل.س".replace(",", "،")
    uses_txt = f"{max_uses}" if max_uses > 0 else "غير محدود"
    min_txt = f"{min_order:,.0f} ل.س".replace(",", "،") if min_order > 0 else "بلا حد"

    await update.message.reply_text(
        f"✅ *تم إنشاء الكوبون!*\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🎟 الكود: `{code}`\n"
        f"💸 الخصم: {val_txt}\n"
        f"🛒 الحد الأدنى: {min_txt}\n"
        f"♾️ الاستخدامات: {uses_txt}",
        reply_markup=kb.back_to_admin(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def cb_back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(update):
        return ConversationHandler.END
    await q.edit_message_text(
        "🛠️ *لوحة الأدمن*\n\nاختر إجراءً:",
        reply_markup=kb.admin_panel(),
        parse_mode=ParseMode.MARKDOWN,
    )
    context.user_data.pop("edit_balance_uid", None)
    return ConversationHandler.END


async def cmd_fcprod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تشخيص: /fcprod 6949 → يرجع تفاصيل المنتج من Fastcard (params, qty_values, type...)"""
    if not is_admin(update):
        return
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("الاستخدام: `/fcprod <product_id>`\nمثال: `/fcprod 6949`",
                                        parse_mode=ParseMode.MARKDOWN)
        return
    pid = int(args[0])
    try:
        prods = await asyncio.to_thread(fastcard.get_products, [pid])
    except Exception as e:
        await update.message.reply_text(f"❌ فشل: `{e}`", parse_mode=ParseMode.MARKDOWN)
        return
    if not prods:
        await update.message.reply_text(f"⚠️ لا منتج بالـ ID {pid}")
        return
    import json as _json
    txt = _json.dumps(prods[0], ensure_ascii=False, indent=2)[:3500]
    await update.message.reply_text(f"📦 منتج {pid}:\n```\n{txt}\n```",
                                    parse_mode=ParseMode.MARKDOWN)


async def cmd_fcfind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تشخيص: /fcfind 60 UC → يبحث في كل منتجات Fastcard عن اسم يطابق ويرجع IDs."""
    if not is_admin(update):
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("الاستخدام: `/fcfind <نص>`\nمثال: `/fcfind 60 UC`",
                                        parse_mode=ParseMode.MARKDOWN)
        return
    needle = " ".join(args).strip().lower()
    try:
        prods = await asyncio.to_thread(fastcard.get_products, None, True)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل: `{e}`", parse_mode=ParseMode.MARKDOWN)
        return
    matches = [p for p in prods if needle in (p.get("name") or "").lower()]
    if not matches:
        await update.message.reply_text(f"⚠️ ما لقيت شي يطابق `{needle}`", parse_mode=ParseMode.MARKDOWN)
        return
    lines = [f"`{p.get('id')}` — {p.get('name')}" for p in matches[:50]]
    await update.message.reply_text(
        f"🔎 *نتائج البحث* ({len(matches)}):\n" + "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_fcrefund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يدوي: /fcrefund <order_id> → يرجّع رصيد الزبون ويعلّم الطلب مسترجَع."""
    if not is_admin(update):
        return
    args = context.args or []
    if not args or not args[0].lstrip("#").isdigit():
        await update.message.reply_text(
            "الاستخدام: `/fcrefund <رقم_الطلب>`\nمثال: `/fcrefund 123`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    order_id = int(args[0].lstrip("#"))
    order = db.get_order(order_id)
    if not order:
        await update.message.reply_text(f"⚠️ طلب #{order_id} غير موجود.")
        return
    status = (order.get("status") or "").lower()
    if status in ("refunded", "refund", "rejected", "reject", "canceled", "cancelled"):
        await update.message.reply_text(f"⚠️ الطلب #{order_id} مسترجَع/مرفوض مسبقاً (الحالة: {status}).")
        return
    if status in ("accept", "accepted", "completed", "done", "success"):
        await update.message.reply_text(
            f"⚠️ الطلب #{order_id} مقبول/منفّذ. لو متأكد بدك ترجّعه استخدم `/fcrefund_force {order_id}`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    user_id = int(order["user_id"])
    price = float(order.get("price") or 0)
    item = order.get("item") or ""
    try:
        db.update_balance(user_id, price)
        db.update_order_status(order_id, "refunded")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل الاسترجاع: `{e}`", parse_mode=ParseMode.MARKDOWN)
        return

    await update.message.reply_text(
        f"✅ تم استرجاع *{price:.0f} ل.س* للمستخدم `{user_id}` وتعليم الطلب #{order_id} كـ refunded.",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        await context.bot.send_message(
            user_id,
            f"↩️ *تم استرجاع المبلغ كاملاً لرصيدك.*\n\n"
            f"📋 رقم الطلب: #{order_id}\n💎 {item}\n💰 المبلغ: {price:,.0f} ل.س".replace(",", "،"),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        pass


async def cmd_fcrefund_force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نسخة force: ترجّع حتى لو الطلب علامته accepted."""
    if not is_admin(update):
        return
    args = context.args or []
    if not args or not args[0].lstrip("#").isdigit():
        await update.message.reply_text("الاستخدام: `/fcrefund_force <رقم_الطلب>`", parse_mode=ParseMode.MARKDOWN)
        return
    order_id = int(args[0].lstrip("#"))
    order = db.get_order(order_id)
    if not order:
        await update.message.reply_text(f"⚠️ طلب #{order_id} غير موجود.")
        return
    user_id = int(order["user_id"])
    price = float(order.get("price") or 0)
    item = order.get("item") or ""
    try:
        db.update_balance(user_id, price)
        db.update_order_status(order_id, "refunded")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل: `{e}`", parse_mode=ParseMode.MARKDOWN)
        return
    await update.message.reply_text(
        f"✅ تم استرجاع *{price:.0f} ل.س* (force) للمستخدم `{user_id}` وطلب #{order_id} → refunded.",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        await context.bot.send_message(
            user_id,
            f"↩️ *تم استرجاع المبلغ كاملاً لرصيدك.*\n\n"
            f"📋 رقم الطلب: #{order_id}\n💎 {item}\n💰 المبلغ: {price:,.0f} ل.س".replace(",", "،"),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        pass


def register_admin_handlers(app):
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("fcprod", cmd_fcprod))
    app.add_handler(CommandHandler("fcfind", cmd_fcfind))
    app.add_handler(CommandHandler("fcrefund", cmd_fcrefund))
    app.add_handler(CommandHandler("fcrefund_force", cmd_fcrefund_force))

    back_handler = CallbackQueryHandler(cb_back_to_admin, pattern=r"^admin:panel$")

    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_admin_panel, pattern=r"^admin:")],
        states={
            ADMIN_SEARCH_USER: [
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_search_user),
            ],
            ADMIN_EDIT_BALANCE_ID: [
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_edit_balance_id),
            ],
            ADMIN_EDIT_BALANCE_AMOUNT: [
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_edit_balance_amount),
            ],
            ADMIN_TOGGLE_BAN_ID: [
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_toggle_ban),
            ],
            ADMIN_BROADCAST_TEXT: [
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_broadcast),
            ],
            ADMIN_CHANNEL_INPUT: [
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_admin_channel),
            ],
            ADMIN_CODES_INPUT: [
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_admin_codes_input),
            ],
            ADMIN_RATES_SET_OFFERS: [
                CallbackQueryHandler(cb_admin_panel, pattern=r"^admin:rates$"),
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_set_rate_offers),
            ],
            ADMIN_RATES_SET_RECHARGE: [
                CallbackQueryHandler(cb_admin_panel, pattern=r"^admin:rates$"),
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_set_rate_recharge),
            ],
            ADMIN_RATES_SET_USDT_WALLET: [
                CallbackQueryHandler(cb_admin_panel, pattern=r"^admin:rates$"),
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_set_usdt_wallet),
            ],
            ADMIN_PROFIT_MARGIN_SET: [
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_set_profit_margin),
            ],
            ADMIN_COUPON_CODE: [
                CallbackQueryHandler(cb_admin_panel, pattern=r"^admin:coupons$"),
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_admin_create_coupon),
            ],
            ADMIN_PRICE_INPUT: [
                CallbackQueryHandler(cb_admin_panel, pattern=r"^admin:prices"),
                back_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_set_offer_price),
            ],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel), CommandHandler("admin", admin_cancel)],
        per_message=False,
    )
    app.add_handler(admin_conv)

    codes_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_admin_codes, pattern=r"^admin_codes:")],
        states={
            ADMIN_CODES_INPUT: [
                CallbackQueryHandler(cb_back_to_admin, pattern=r"^admin:panel$"),
                CallbackQueryHandler(cb_admin_codes, pattern=r"^admin_codes:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_admin_codes_input),
            ],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel), CommandHandler("admin", admin_cancel)],
        per_message=False,
    )
    app.add_handler(codes_conv)

    app.add_handler(CallbackQueryHandler(cb_admin_recharge_decision, pattern=r"^adm_rch:"))
    app.add_handler(CallbackQueryHandler(cb_admin_order_decision, pattern=r"^adm_ord:"))
