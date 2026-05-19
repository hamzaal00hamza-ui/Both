"""
مهام مجدولة (JobQueue): تنبيه عند انخفاض رصيد المتجر، تقرير يومي.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes

from . import config, database as db, fastcard, exchange_rate

logger = logging.getLogger(__name__)


async def _send_admin(app: Application, text: str) -> None:
    """يرسل للأدمن DM ولقناة التوثيق (لو مربوطة)."""
    from . import notify
    await notify.notify_admin(app.bot, text)


async def _build_pubg_report(since_iso: str, title: str) -> str:
    stats = await asyncio.to_thread(db.get_pubg_stats_since, since_iso)

    lines = [
        f"📈 *{title}*",
        "",
        f"✅ طلبات منفّذة: *{stats['completed']}*",
    ]
    if stats["refunded"]:
        lines.append(f"↩️ مُسترَجَعة: {stats['refunded']}")
    if stats["pending"]:
        lines.append(f"⏳ قيد التنفيذ: {stats['pending']}")

    lines.append("")
    if stats["by_item"]:
        lines.append("*التفصيل:*")
        for item, count in stats["by_item"].items():
            lines.append(f"  • {item} × {count}")
        lines.append("")

    lines.append(f"💰 المبيعات (للزبائن): *{stats['total_revenue_syp']:,.0f} ل.س*")
    lines.append(f"💵 التكلفة (من المتجر): *{stats['total_cost_usd']:.2f} $*")

    # رصيد المتجر الحالي إن أمكن
    if fastcard.is_enabled():
        try:
            profile = await asyncio.to_thread(fastcard.get_profile)
            bal = float(profile.get("balance") or 0)
            lines.append("")
            lines.append(f"💼 رصيد المتجر الحالي: *{bal:.4f} $*")
        except Exception:
            pass

    return "\n".join(lines)


async def daily_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    """تقرير يومي يُرسل للأدمن عن آخر 24 ساعة."""
    if not config.ADMIN_ID:
        return
    since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    text = await _build_pubg_report(since, "تقرير آخر 24 ساعة")
    await _send_admin(context.application, text)


async def build_today_report() -> str:
    """تقرير منذ منتصف الليل UTC (للزر On-demand)."""
    now = datetime.utcnow()
    midnight = datetime(now.year, now.month, now.day, 0, 0, 0).isoformat()
    return await _build_pubg_report(midnight, "تقرير اليوم (منذ منتصف الليل UTC)")


async def _build_profit_report(since_iso: str, title: str) -> str:
    """تقرير الأرباح الصافية: مبيعات - تكلفة بالليرة (تكلفة الدولار × سعر شحن الدولار)."""
    stats = await asyncio.to_thread(db.get_sales_stats_since, since_iso)

    revenue_syp = stats["total_revenue_syp"]
    cost_usd = stats["total_cost_usd"]
    usd_rate = config.get_usd_to_syp()
    cost_syp = cost_usd * usd_rate
    profit_syp = revenue_syp - cost_syp
    margin = (profit_syp / revenue_syp * 100.0) if revenue_syp > 0 else 0.0

    lines = [
        f"💵 *{title}*",
        "",
        f"📦 طلبات منفّذة: *{stats['completed']}*",
    ]
    if stats["refunded"]:
        lines.append(f"↩️ مُسترَجَعة: {stats['refunded']}")
    if stats["pending"]:
        lines.append(f"⏳ قيد التنفيذ: {stats['pending']}")
    lines.append("")

    lines.append(f"💰 المبيعات الإجمالية: *{revenue_syp:,.0f} ل.س*")
    lines.append(f"💸 التكلفة بالدولار: {cost_usd:.2f} $")
    lines.append(f"💱 التكلفة بالليرة: {cost_syp:,.0f} ل.س")
    lines.append(f"   _(محسوبة بسعر شحن الدولار: {usd_rate:,.0f} ل.س)_")
    lines.append("")
    sign = "🟢" if profit_syp >= 0 else "🔴"
    lines.append(f"{sign} *الربح الصافي: {profit_syp:,.0f} ل.س*")
    lines.append(f"📊 هامش الربح: *{margin:.1f}%*")

    if stats["by_game"]:
        lines.append("")
        lines.append("*تفصيل حسب الفئة:*")
        sorted_games = sorted(
            stats["by_game"].items(),
            key=lambda x: x[1]["revenue"],
            reverse=True,
        )
        for game, slot in sorted_games[:10]:
            g_revenue = slot["revenue"]
            g_cost_syp = slot["cost_usd"] * usd_rate
            g_profit = g_revenue - g_cost_syp
            lines.append(
                f"  • *{game}* — {int(slot['count'])} طلب — "
                f"ربح {g_profit:,.0f} ل.س"
            )

    if fastcard.is_enabled():
        try:
            profile = await asyncio.to_thread(fastcard.get_profile)
            bal = float(profile.get("balance") or 0)
            lines.append("")
            lines.append(f"💼 رصيد المتجر الحالي: *{bal:.2f} $*")
        except Exception:
            pass

    return "\n".join(lines)


async def build_profit_today() -> str:
    now = datetime.utcnow()
    midnight = datetime(now.year, now.month, now.day, 0, 0, 0).isoformat()
    return await _build_profit_report(midnight, "أرباح اليوم")


async def build_profit_week() -> str:
    since = (datetime.utcnow() - timedelta(days=7)).isoformat()
    return await _build_profit_report(since, "أرباح آخر 7 أيام")


async def build_profit_month() -> str:
    since = (datetime.utcnow() - timedelta(days=30)).isoformat()
    return await _build_profit_report(since, "أرباح آخر 30 يوم")


async def build_profit_all_time() -> str:
    return await _build_profit_report("1970-01-01T00:00:00", "أرباح كل الفترة")


def _generate_coupon_code() -> str:
    """يولّد كود كوبون فريد عشوائي مثل BONUS-X9KQ4."""
    import random, string
    alphabet = string.ascii_uppercase + string.digits
    # جرّب 6 محاولات للحصول على كود غير مكرر
    for _ in range(6):
        suffix = "".join(random.choices(alphabet, k=5))
        code = f"BONUS-{suffix}"
        if not db.get_coupon_by_code(code):
            return code
    # fallback مع timestamp
    return f"BONUS-{int(datetime.utcnow().timestamp()) % 1000000}"


async def auto_coupon_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """يفحص كل 24 ساعة: لو فات AUTO_COUPON_INTERVAL_DAYS منذ آخر توليد → ينشئ كوبون جديد."""
    if not config.AUTO_COUPON_ENABLED:
        return
    try:
        last = await asyncio.to_thread(db.get_setting, "last_auto_coupon_at", "")
        now = datetime.utcnow()
        should_create = False
        if not last:
            should_create = True
        else:
            try:
                last_dt = datetime.fromisoformat(last)
                if (now - last_dt).total_seconds() >= config.AUTO_COUPON_INTERVAL_DAYS * 86400:
                    should_create = True
            except Exception:
                should_create = True

        if not should_create:
            return

        code = await asyncio.to_thread(_generate_coupon_code)
        value = float(config.AUTO_COUPON_VALUE_SYP)
        max_uses = int(config.AUTO_COUPON_MAX_USES)

        cid = await asyncio.to_thread(
            db.create_coupon, code, "fixed", value, 0, max_uses, None
        )
        await asyncio.to_thread(db.set_setting, "last_auto_coupon_at", now.isoformat())
        logger.info("Auto-coupon created: %s id=%s value=%s uses=%s", code, cid, value, max_uses)

        val_txt = f"{value:,.0f} ل.س".replace(",", "،")

        # 1) إخطار الأدمن
        admin_msg = (
            "🎟 *تم توليد كوبون دوري جديد!*\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            f"🔑 الكود: `{code}`\n"
            f"💰 القيمة: *{val_txt}*\n"
            f"👥 صالح لـ: *{max_uses} زبائن* (أول من يستخدمه)\n"
            f"⏰ التوليد القادم بعد: *{config.AUTO_COUPON_INTERVAL_DAYS} يوم*"
        )
        await _send_admin(context.application, admin_msg)

        # 2) Broadcast لكل الزبائن (لو مفعّل)
        if config.AUTO_COUPON_BROADCAST:
            user_ids = await asyncio.to_thread(db.all_user_ids)
            customer_msg = (
                "🎁 *عرض حصري — كوبون مجاني!*\n"
                "━━━━━━━━━━━━━━━━━\n\n"
                f"🔑 الكود: `{code}`\n"
                f"💰 رصيد مجاني: *{val_txt}*\n"
                f"⚡ صالح لأول *{max_uses} زبائن* فقط — اللي يسبق يستفيد!\n\n"
                "👈 ادخل من القائمة الرئيسية → *🎟 كود خصم* وادخل الكود.\n\n"
                "_بالتوفيق!_ 🍀"
            )
            sent = 0
            failed = 0
            for uid in user_ids:
                try:
                    await context.application.bot.send_message(
                        chat_id=uid,
                        text=customer_msg,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    sent += 1
                except Exception:
                    failed += 1
                await asyncio.sleep(0.05)
            logger.info("Auto-coupon broadcast: sent=%d failed=%d", sent, failed)
            await _send_admin(
                context.application,
                f"📢 تم إعلام الزبائن بالكوبون: ✅ {sent} | ⚠️ فشل: {failed}",
            )

    except Exception as e:
        logger.exception("auto_coupon_check failed: %s", e)


# SMM categories where Fastcard returns price-per-unit (مش per-package).
# نستخرج qty من label ونحسب equivalent price.
_SMM_UNIT_SOURCES = {
    "FC:igf", "FC:igl", "FC:igv", "FC:fbf",
    "FC:tgv", "FC:tgr",
    "INSTAGRAM_FOLLOWERS", "INSTAGRAM_LIKES", "INSTAGRAM_VIEWS",
    "FACEBOOK_FOLLOWERS", "TELEGRAM_VIEWS", "TELEGRAM_REACTIONS",
}


def _extract_qty_from_label(label: str) -> int | None:
    """يستخرج أول رقم كبير (≥50) من نص العرض، عادةً يكون qty لمنتجات SMM.
    يدعم الفواصل: 1,000 / 1.000 / 1000.
    """
    import re
    if not label:
        return None
    # نحذف الفواصل بين الأرقام لتسهيل الاستخراج
    cleaned = re.sub(r"(\d)[,.](\d{3})", r"\1\2", label)
    # نبحث عن أول رقم >= 50
    for m in re.finditer(r"\b(\d{2,7})\b", cleaned):
        n = int(m.group(1))
        if 50 <= n <= 1000000:
            return n
    return None


def _resolve_category_name(source: str) -> str:
    """يحوّل اسم القائمة (مثل PUBG_UC_OFFERS أو FC:igf) إلى اسم عربي للقسم."""
    if not source:
        return "❓ غير مصنّف"
    # 1) جرّب من PRICE_EDIT_CATEGORIES (attribute name)
    for _key, attr, title in config.PRICE_EDIT_CATEGORIES:
        if attr == source:
            return title
    # 2) Fastcard prefix → نقرأ من FASTCARD_CATEGORIES
    if source.startswith("FC:"):
        prefix = source[3:]
        cat = config.FASTCARD_CATEGORIES.get(prefix, {})
        title = cat.get("title")
        if title:
            return title
        # جرّب نلاقي من PRICE_EDIT_CATEGORIES بال attribute المتشابه
        attr = cat.get("offers_attr")
        if attr:
            for _key, a, t in config.PRICE_EDIT_CATEGORIES:
                if a == attr:
                    return t
    # 3) fallback: تحويل بسيط من snake_case إلى عنوان
    return source.replace("_OFFERS", "").replace("_", " ").title()


async def compute_price_check_data(threshold_pct: float = 1.0) -> dict:
    """يفحص الأسعار من Fastcard ويرجع بيانات منظمة للتقرير + الإصلاح التلقائي.

    المخرجات (dict):
      - ok: bool — هل الفحص نجح
      - error: str — في حال الفشل
      - syp_per_usd: float — سعر الصرف الحالي
      - checked, total: int
      - loss: list — منتجات بتباع بخسارة (التكلفة الجديدة > السعر للزبون)
      - thin: list — هامش ربح ≤ 5%
      - up:   list — التكلفة ارتفعت (ربح أقل)
      - down: list — التكلفة انخفضت (ربح أكثر)
      - missing, unavailable, smm_skipped: list
    كل عنصر في loss/thin/up/down يحوي:
      pid, label, source, offer_id, current_sale_syp,
      old_cost_usd, new_cost_usd, new_cost_syp,
      profit_syp, profit_pct, suggested_price_syp
    """
    if not fastcard.is_enabled():
        return {"ok": False, "error": "Fastcard API غير مفعّل."}
    try:
        api_products = await asyncio.to_thread(fastcard.get_products)
    except Exception as e:
        return {"ok": False, "error": f"فشل جلب أسعار Fastcard: {e}"}

    def _truthy(v) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, str):
            return v.strip().lower() not in ("", "0", "false", "no", "off")
        return bool(v)

    api_map = {}
    for p in api_products:
        try:
            pid = int(p.get("id", 0))
            price = float(p.get("price", 0) or 0)
            if pid and price > 0:
                api_map[pid] = {
                    "price": price,
                    "name": p.get("name", ""),
                    "available": _truthy(p.get("available", True)),
                }
        except (ValueError, TypeError):
            continue

    priced_offers = config.collect_priced_offers()
    syp_rate = config.get_syp_per_usd()
    target_margin = config.PROFIT_MARGIN  # هامش الربح المستهدف لاقتراح السعر

    loss, thin, up, down = [], [], [], []
    missing, unavailable, smm_skipped = [], [], []
    checked = 0

    for offer in priced_offers:
        pid = offer["product_id"]
        my_cost = offer["cost_usd"]
        label = offer["label"]
        source = offer.get("source", "")
        offer_id = offer.get("id")
        raw = offer.get("raw_offer", {})

        api_info = api_map.get(pid)
        if api_info is None:
            if offer["enabled"]:
                missing.append({"label": label, "pid": pid, "my_cost": my_cost})
            continue
        checked += 1
        if not api_info["available"] and offer["enabled"]:
            unavailable.append({"label": label, "pid": pid})
        api_price = api_info["price"]
        if my_cost <= 0:
            continue

        # SMM: API price per-unit، نضرب qty المُستخرَج
        if source in _SMM_UNIT_SOURCES:
            qty = _extract_qty_from_label(label)
            if qty is None:
                smm_skipped.append({"label": label, "pid": pid})
                continue
            api_price = api_price * qty

        # السعر الحالي للزبون بالليرة (override يدوي أو محسوب من سعر الصرف)
        try:
            current_sale_syp = config.get_offer_price(raw) if raw else 0
        except Exception:
            current_sale_syp = int(raw.get("price", 0) or 0)

        new_cost_syp = api_price * syp_rate
        profit_syp = current_sale_syp - new_cost_syp
        profit_pct = (profit_syp / new_cost_syp * 100.0) if new_cost_syp > 0 else 0.0

        # السعر المقترح لتحقيق هامش 12% (مدور لأقرب 500)
        suggested = config.round_up_to_500(new_cost_syp * (1 + target_margin))

        diff_pct = ((api_price - my_cost) / my_cost) * 100.0

        # حساب التكلفة القديمة بالليرة + هامش الربح القديم
        old_cost_syp = my_cost * syp_rate
        old_profit_syp = current_sale_syp - old_cost_syp
        old_profit_pct = (old_profit_syp / old_cost_syp * 100.0) if old_cost_syp > 0 else 0.0
        # الربح الإضافي المتوقع لو طبّقنا السعر المقترح
        new_profit_after_fix = suggested - new_cost_syp

        item = {
            "pid": pid,
            "label": label,
            "source": source,
            "category": _resolve_category_name(source),
            "offer_id": offer_id,
            "enabled": offer.get("enabled", True),
            "current_sale_syp": int(current_sale_syp),
            "old_cost_usd": my_cost,
            "new_cost_usd": api_price,
            "old_cost_syp": int(old_cost_syp),
            "new_cost_syp": int(new_cost_syp),
            "old_profit_syp": int(old_profit_syp),
            "old_profit_pct": old_profit_pct,
            "profit_syp": int(profit_syp),
            "profit_pct": profit_pct,
            "diff_pct": diff_pct,
            "suggested_price_syp": suggested,
            "profit_after_fix_syp": int(new_profit_after_fix),
        }

        # تصنيف المنتج بالأولوية
        if profit_pct < 0 and offer.get("enabled", True):
            loss.append(item)
        elif 0 <= profit_pct < 5 and offer.get("enabled", True):
            thin.append(item)
        elif diff_pct >= threshold_pct:
            up.append(item)
        elif diff_pct <= -threshold_pct:
            down.append(item)

    return {
        "ok": True,
        "syp_per_usd": syp_rate,
        "checked": checked,
        "total": len(priced_offers),
        "loss": loss,
        "thin": thin,
        "up": up,
        "down": down,
        "missing": missing,
        "unavailable": unavailable,
        "smm_skipped": smm_skipped,
    }


def _fmt_money(syp: int) -> str:
    """تنسيق مبلغ بالليرة مع فواصل."""
    return f"{int(syp):,}".replace(",", "،")


def _group_by_category(items: list) -> dict:
    """يجمع عناصر التقرير حسب اسم القسم. يُحافظ على ترتيب الأسوأ أولاً."""
    groups: dict = {}
    for it in items:
        cat = it.get("category", "❓ غير مصنّف")
        groups.setdefault(cat, []).append(it)
    return groups


def _fmt_pct(pct: float) -> str:
    """تنسيق نسبة مع إشارة + للزيادة."""
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def format_price_check_report(data: dict, threshold_pct: float = 1.0) -> str:
    """يحوّل dict من compute_price_check_data إلى نص Markdown منظم وواضح."""
    if not data.get("ok"):
        return f"❌ {data.get('error', 'فشل غير معروف')}"

    from datetime import datetime
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    checked = data["checked"]
    total = data["total"]
    syp_rate = data["syp_per_usd"]
    loss = data["loss"]
    thin = data["thin"]
    up = data["up"]
    down = data["down"]
    missing = data["missing"]
    unavailable = data["unavailable"]
    smm_skipped = data["smm_skipped"]

    # ===== الترويسة =====
    lines = [
        "🔍 *تقرير فحص أسعار Fastcard*",
        f"🕐 {now_str}",
        "━━━━━━━━━━━━━━━━━",
        "",
        "📋 *معلومات الفحص:*",
        f"  • منتجات مفحوصة: *{checked}* من أصل {total}",
        f"  • سعر صرف الدولار المعتمد: *{int(syp_rate):,}* ل.س",
        f"  • هامش الربح المستهدف عند الإصلاح: *12%*",
    ]

    # ===== ملخص الحالة =====
    lines += [
        "",
        "📊 *ملخّص الحالة:*",
        f"  🆘 خسائر فعلية (لازم تتدخّل): *{len(loss)}* منتج",
        f"  ⚠️ ربح ضعيف (أقل من 5%):       *{len(thin)}* منتج",
        f"  🔺 تكلفة ارتفعت (ربح أقل):     *{len(up)}* منتج",
        f"  🟢 تكلفة انخفضت (ربح أكثر):    *{len(down)}* منتج",
    ]
    if missing:
        lines.append(f"  📭 محذوف من Fastcard:           *{len(missing)}* منتج")
    if unavailable:
        lines.append(f"  🚫 غير متاح حالياً:              *{len(unavailable)}* منتج")
    if smm_skipped:
        lines.append(f"  ⏭️ SMM متخطّى (qty غير معروف):  *{len(smm_skipped)}* منتج")

    total_issues = len(loss) + len(thin) + len(up) + len(down)

    # حالة سليمة تماماً
    if total_issues == 0 and not missing and not unavailable:
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append("✅ *النتيجة: كل الأسعار سليمة*")
        lines.append("لا توجد منتجات تباع بخسارة، ولا تغيرات معتبرة في الأسعار.")
        return "\n".join(lines)

    # ===== شرح كيف نقرأ التقرير =====
    lines += [
        "",
        "━━━━━━━━━━━━━━━━━",
        "📖 *كيف تقرأ التقرير:*",
        "  • *بيع* = السعر اللي بيدفعه الزبون عندك",
        "  • *تكلفة* = السعر اللي بتدفعه أنت لـ Fastcard (مضروب بسعر الصرف)",
        "  • *ربح* = بيع − تكلفة (لكل بيعة)",
        "  • *المقترح* = سعر يضمنلك ربح 12% بناءً على التكلفة الجديدة",
    ]

    # ===== خسائر فعلية - الأهم =====
    if loss:
        total_loss_per_sale = sum(abs(it["profit_syp"]) for it in loss)
        avg_loss = total_loss_per_sale // max(1, len(loss))
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append(f"🆘 *خسائر فعلية — {len(loss)} منتج*")
        lines.append("_منتجات بتباع بأقل من تكلفتها = خسارة مباشرة لكل عملية بيع._")
        lines.append("")
        lines.append(f"💸 *إجمالي الخسارة لو باع كل منتج مرة واحدة:* {_fmt_money(total_loss_per_sale)} ل.س")
        lines.append(f"📉 *متوسط الخسارة لكل منتج:* {_fmt_money(avg_loss)} ل.س")

        # تجميع حسب القسم لعرض أوضح
        groups = _group_by_category(loss)
        # نعرض أول 3 أقسام بأكبر مجموع خسائر
        sorted_groups = sorted(
            groups.items(),
            key=lambda kv: sum(abs(it["profit_syp"]) for it in kv[1]),
            reverse=True,
        )
        shown_total = 0
        for cat_name, items in sorted_groups[:5]:
            cat_loss = sum(abs(it["profit_syp"]) for it in items)
            lines.append("")
            lines.append(f"📁 *{cat_name}* — {len(items)} منتج (خسارة {_fmt_money(cat_loss)} ل.س)")
            for it in sorted(items, key=lambda x: x["profit_syp"])[:4]:
                shown_total += 1
                lines.append(
                    f"  🆘 *{it['label'][:36]}* `#{it['pid']}`\n"
                    f"     بيع *{_fmt_money(it['current_sale_syp'])}* ← تكلفة *{_fmt_money(it['new_cost_syp'])}* ل.س\n"
                    f"     خسارة: *−{_fmt_money(abs(it['profit_syp']))}* ل.س ({_fmt_pct(it['profit_pct'])})\n"
                    f"     💡 سعر مقترح: *{_fmt_money(it['suggested_price_syp'])}* ل.س "
                    f"→ ربح *+{_fmt_money(it['profit_after_fix_syp'])}* ل.س"
                )
            if len(items) > 4:
                lines.append(f"     _... و {len(items) - 4} منتج آخر بنفس القسم._")
        remaining_groups = len(sorted_groups) - 5
        if remaining_groups > 0:
            lines.append(f"\n_... و {remaining_groups} قسم إضافي فيه منتجات خاسرة._")

    # ===== ربح ضعيف =====
    if thin:
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append(f"⚠️ *ربح ضعيف — {len(thin)} منتج*")
        lines.append("_منتجات هامش ربحها أقل من 5%، عرضة لتصبح خسارة لو ارتفعت التكلفة قليلاً._")
        lines.append("")
        groups = _group_by_category(thin)
        sorted_groups = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
        for cat_name, items in sorted_groups[:4]:
            lines.append(f"📁 *{cat_name}* — {len(items)} منتج")
            for it in sorted(items, key=lambda x: x["profit_pct"])[:3]:
                lines.append(
                    f"  ⚠️ *{it['label'][:36]}* `#{it['pid']}`\n"
                    f"     بيع *{_fmt_money(it['current_sale_syp'])}* • تكلفة *{_fmt_money(it['new_cost_syp'])}*\n"
                    f"     ربح حالي: *{_fmt_money(it['profit_syp'])}* ل.س ({_fmt_pct(it['profit_pct'])})\n"
                    f"     💡 المقترح: *{_fmt_money(it['suggested_price_syp'])}* ل.س"
                )
            if len(items) > 3:
                lines.append(f"     _... و {len(items) - 3} منتج آخر._")

    # ===== تكلفة ارتفعت لكن لسا مربح =====
    if up:
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append(f"🔺 *ارتفعت تكلفتها — {len(up)} منتج*")
        lines.append("_لسا الربح موجود، بس الهامش انخفض. مراقبة فقط._")
        lines.append("")
        groups = _group_by_category(up)
        sorted_groups = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
        for cat_name, items in sorted_groups[:3]:
            lines.append(f"📁 *{cat_name}* — {len(items)} منتج")
            for it in sorted(items, key=lambda x: -x["diff_pct"])[:3]:
                lines.append(
                    f"  🔺 *{it['label'][:36]}* `#{it['pid']}`\n"
                    f"     تكلفة: *{_fmt_money(it['old_cost_syp'])}* → *{_fmt_money(it['new_cost_syp'])}* ل.س "
                    f"({_fmt_pct(it['diff_pct'])})\n"
                    f"     هامش الربح حالياً: *{_fmt_pct(it['profit_pct'])}*"
                )
            if len(items) > 3:
                lines.append(f"     _... و {len(items) - 3}._")

    # ===== تكلفة انخفضت = فرصة =====
    if down:
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append(f"🟢 *انخفضت تكلفتها — {len(down)} منتج*")
        lines.append("_فرصة! ربحك زاد تلقائياً، أو ممكن تخفّض السعر للمنافسة._")
        lines.append("")
        groups = _group_by_category(down)
        sorted_groups = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
        for cat_name, items in sorted_groups[:3]:
            lines.append(f"📁 *{cat_name}* — {len(items)} منتج")
            for it in sorted(items, key=lambda x: x["diff_pct"])[:3]:
                lines.append(
                    f"  🟢 *{it['label'][:36]}* `#{it['pid']}`\n"
                    f"     تكلفة: *{_fmt_money(it['old_cost_syp'])}* → *{_fmt_money(it['new_cost_syp'])}* ل.س "
                    f"({_fmt_pct(it['diff_pct'])})\n"
                    f"     هامش الربح حالياً: *{_fmt_pct(it['profit_pct'])}*"
                )
            if len(items) > 3:
                lines.append(f"     _... و {len(items) - 3}._")

    # ===== تنبيهات إضافية =====
    if missing:
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append(f"📭 *عروض محذوفة من Fastcard ({len(missing)})*")
        lines.append("_هاي العروض ما عاد لها وجود في موقع Fastcard. ممكن المنتج اتلغى._")
        for it in missing[:6]:
            lines.append(f"  • `#{it['pid']}` {it['label'][:48]}")
        if len(missing) > 6:
            lines.append(f"  _... و {len(missing) - 6} منتج إضافي._")

    if unavailable:
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append(f"🚫 *عروض غير متاحة مؤقتاً ({len(unavailable)})*")
        lines.append("_هاي العروض موجودة في Fastcard بس مش متاحة للشراء حالياً._")
        for it in unavailable[:6]:
            lines.append(f"  • `#{it['pid']}` {it['label'][:48]}")
        if len(unavailable) > 6:
            lines.append(f"  _... و {len(unavailable) - 6} منتج إضافي._")

    if smm_skipped:
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append(f"⏭️ *منتجات رشق متخطّاة ({len(smm_skipped)})*")
        lines.append("_تعذّر حساب التكلفة لأن العنوان ما فيه رقم qty واضح._")
        for it in smm_skipped[:4]:
            lines.append(f"  • `#{it['pid']}` {it['label'][:48]}")
        if len(smm_skipped) > 4:
            lines.append(f"  _... و {len(smm_skipped) - 4} منتج إضافي._")

    # ===== خاتمة + توصيات =====
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━")
    lines.append("✅ *التوصيات:*")
    if loss:
        lines.append(
            f"  1️⃣ *عاجل:* عدّل أسعار {len(loss)} منتج خاسر فوراً — "
            f"اضغط زر *🛠️ تطبيق الأسعار المقترحة* بالأسفل."
        )
    if thin:
        order = 2 if loss else 1
        lines.append(
            f"  {order}️⃣ راجع {len(thin)} منتج ربحه ضعيف — "
            f"الزر يطبّق سعر يضمن لك 12% ربح."
        )
    if missing:
        lines.append(
            f"  • تحقّق يدوياً من {len(missing)} منتج محذوف من Fastcard — ممكن تخفيهم من البوت."
        )
    if down:
        lines.append(
            f"  • {len(down)} منتج انخفضت تكلفته — تقدر تخفّض أسعارهم لجذب زبائن أكتر، أو تتركهم لربح إضافي."
        )
    if not (loss or thin or missing or down):
        lines.append("  • لا توجد توصيات عاجلة — كل المنتجات بحالة جيدة. ✨")

    lines.append("")
    lines.append("_💡 السعر المقترح يضمن لك ربح 12% على التكلفة الجديدة من Fastcard._")
    lines.append("_📌 لتعديل سعر منتج محدد يدوياً: لوحة الأدمن ← 💲 تعديل أسعار المنتجات._")

    return "\n".join(lines)


async def build_price_check_report(threshold_pct: float = 1.0) -> str:
    """واجهة قديمة — تجمع البيانات وتنسّقها كنص."""
    data = await compute_price_check_data(threshold_pct)
    return format_price_check_report(data, threshold_pct)


async def apply_price_fix(data: dict) -> dict:
    """يطبّق الأسعار المقترحة كـ overrides لكل المنتجات الخاسرة + الضعيفة.

    يرجع: {applied: int, skipped: int, details: [{label, old, new}]}
    """
    from . import database as _db
    items = list(data.get("loss", [])) + list(data.get("thin", []))
    applied = 0
    skipped = 0
    details = []
    for it in items:
        offer_id = it.get("offer_id")
        new_price = int(it.get("suggested_price_syp", 0))
        if not offer_id or new_price <= 0:
            skipped += 1
            continue
        try:
            _db.set_price_override(str(offer_id), new_price)
            applied += 1
            details.append({
                "label": it.get("label", "?"),
                "old": it.get("current_sale_syp", 0),
                "new": new_price,
            })
        except Exception as e:
            logger.warning("apply_price_fix failed for %s: %s", offer_id, e)
            skipped += 1
    return {"applied": applied, "skipped": skipped, "details": details}


async def price_check_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """يُشغّل فحص الأسعار اليومي ويرسل التقرير للأدمن + قناة التوثيق."""
    if not config.ADMIN_ID:
        return
    try:
        report = await build_price_check_report()
        await _send_admin(context.application, report)
    except Exception as e:
        logger.exception("price_check_job failed: %s", e)


async def auto_exchange_rate_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """يجلب سعر الدولار من قناة @SaymouaaExchange ويُبلّغ الأدمن."""
    if not config.ADMIN_ID:
        return
    try:
        result = await exchange_rate.update_rate_from_channel()
        cur_rate = config.get_syp_per_usd()
        buy = result["buy"]
        sell = result["sell"]
        avg = result["avg"]
        old = result["old_rate"]
        changed = result["changed"]

        if changed:
            direction = "📈" if avg > old else "📉"
            msg = (
                f"💱 *تحديث سعر الصرف تلقائي*\n\n"
                f"🛒 شراء: *{buy:,.0f} ل.س/$*\n"
                f"💵 بيع:   *{sell:,.0f} ل.س/$*\n"
                f"📊 متوسط: *{avg:,.0f} ل.س/$*\n\n"
                f"{direction} تغيّر من *{old:,.0f}* إلى *{avg:,.0f}* ل.س/$\n"
                f"_المصدر: @SaymouaaExchange_"
            )
        else:
            msg = (
                f"🌐 *سعر الصرف من @SaymouaaExchange*\n\n"
                f"🛒 شراء: *{buy:,.0f} ل.س/$*\n"
                f"💵 بيع:   *{sell:,.0f} ل.س/$*\n"
                f"📊 متوسط محفوظ: *{cur_rate:,.0f} ل.س/$* _(لم يتغير)_"
            )
        await _send_admin(context.application, msg)
    except Exception as e:
        logger.warning("auto_exchange_rate_update failed: %s", e)


def schedule_jobs(app: Application) -> None:
    """يُسجّل المهام المجدولة على JobQueue الخاص بالتطبيق."""
    jq = app.job_queue
    if jq is None:
        logger.warning("JobQueue غير متاح — لن تعمل التنبيهات.")
        return

    # تقرير يومي عند الساعة المحددة UTC
    from datetime import time as _time
    jq.run_daily(
        daily_report,
        time=_time(
            hour=config.DAILY_REPORT_HOUR_UTC,
            minute=config.DAILY_REPORT_MINUTE_UTC,
            tzinfo=timezone.utc,
        ),
        name="daily_report",
    )

    # كوبون دوري تلقائي — يفحص كل 24 ساعة، يولّد عند مرور AUTO_COUPON_INTERVAL_DAYS
    if config.AUTO_COUPON_ENABLED:
        jq.run_repeating(
            auto_coupon_check,
            interval=86400,           # فحص يومي
            first=120,                # أول فحص بعد دقيقتين من الإقلاع
            name="auto_coupon_check",
        )

    # تحديث سعر الصرف تلقائياً من موقع الليرة اليوم كل ساعة
    jq.run_repeating(
        auto_exchange_rate_update,
        interval=3600,   # كل ساعة
        first=30,        # أول تحديث بعد 30 ثانية من الإقلاع
        name="exchange_rate_update",
    )

    # فحص أسعار Fastcard اليومي — يقارن cost_usd مع API ويرسل تنبيه بالفروق
    if fastcard.is_enabled():
        jq.run_daily(
            price_check_job,
            time=_time(
                hour=config.PRICE_CHECK_HOUR_UTC,
                minute=config.PRICE_CHECK_MINUTE_UTC,
                tzinfo=timezone.utc,
            ),
            name="price_check",
        )

    logger.info(
        "Scheduled jobs: daily_report at %02d:%02d UTC, "
        "auto_coupon=%s (every %s days, %s SYP for %s users)",
        config.DAILY_REPORT_HOUR_UTC,
        config.DAILY_REPORT_MINUTE_UTC,
        "ON" if config.AUTO_COUPON_ENABLED else "OFF",
        config.AUTO_COUPON_INTERVAL_DAYS,
        config.AUTO_COUPON_VALUE_SYP,
        config.AUTO_COUPON_MAX_USES,
    )
