"""
لوحات الأزرار (Inline Keyboards)
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from . import config


def admin_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("/start"), KeyboardButton("/admin")]],
        resize_keyboard=True,
    )


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 حسابي", callback_data="menu:account")],
        [InlineKeyboardButton("💰 شحن رصيد الحساب", callback_data="menu:recharge")],
        [InlineKeyboardButton("🛒 المتجر", callback_data="menu:store")],
        [InlineKeyboardButton("💎 نقاطي", callback_data="menu:loyalty"),
         InlineKeyboardButton("🎟 كود خصم", callback_data="menu:coupon")],
        [InlineKeyboardButton("👥 دعوة الأصدقاء", callback_data="menu:referral")],
        [InlineKeyboardButton("📞 التواصل مع الدعم", callback_data="menu:support")],
    ])


def coupon_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ إلغاء", callback_data="menu:main")],
    ])


def loyalty_menu(can_redeem: bool, suggested_redeem: int = 0) -> InlineKeyboardMarkup:
    rows = []
    if can_redeem:
        if suggested_redeem > 0:
            rows.append([InlineKeyboardButton(
                f"💱 استبدال كل النقاط ({suggested_redeem:,})".replace(",", "،"),
                callback_data=f"loyalty:redeem_all"
            )])
        rows.append([InlineKeyboardButton(
            f"✏️ استبدال مبلغ مخصص", callback_data="loyalty:redeem_custom"
        )])
    rows.append([InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def loyalty_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ إلغاء", callback_data="menu:loyalty")],
    ])


def back_to_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="menu:main")],
    ])


def referral_menu(referral_link: str, share_text: str) -> InlineKeyboardMarkup:
    """شاشة دعوة الأصدقاء: زر مشاركة عبر تلغرام + رجوع."""
    from urllib.parse import quote
    share_url = f"https://t.me/share/url?url={quote(referral_link)}&text={quote(share_text)}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 شارك الرابط مع أصدقائك", url=share_url)],
        [InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="menu:main")],
    ])


def recharge_methods() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 سيرياتيل كاش", callback_data="recharge:syriatel")],
        [InlineKeyboardButton("💳 شام كاش (ل.س)", callback_data="recharge:shamcash")],
        [InlineKeyboardButton("💵 شام كاش (دولار)", callback_data="recharge:shamcash_usd")],
        [InlineKeyboardButton("💎 USDT (BEP20 / BSC)", callback_data="recharge:usdt")],
        [InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="menu:main")],
    ])


def store_menu() -> InlineKeyboardMarkup:
    """قائمة المتجر الرئيسية."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 الألعاب", callback_data="store:games")],
        [InlineKeyboardButton("💳 البطاقات", callback_data="store:cards")],
        [InlineKeyboardButton("💎 اشتراكات تطبيقات", callback_data="store:subs")],
        [InlineKeyboardButton("📈 خدمات الرشق (متابعين/لايكات)", callback_data="store:smm")],
        [InlineKeyboardButton("📱 الرصيد (تعبئة جوال)", callback_data="store:balance")],
        [InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="menu:main")],
    ])


def balance_menu() -> InlineKeyboardMarkup:
    """قائمة الرصيد الفرعية — 27 خدمة (مطابقة لقسم الرصيد في موقع Fastcard)."""
    return InlineKeyboardMarkup([
        # — اتصالات سورية —
        [InlineKeyboardButton("📱 رصيد SYRIATEL", callback_data="fclist:bal_syr"),
         InlineKeyboardButton("📱 رصيد MTN", callback_data="fclist:bal_mtn")],
        [InlineKeyboardButton("⛽ كازية SYRIATEL", callback_data="fclist:bal_sgas"),
         InlineKeyboardButton("⛽ كازية MTN", callback_data="fclist:bal_mgas")],
        [InlineKeyboardButton("🧾 فواتير SYRIATEL", callback_data="fclist:bal_sfaw"),
         InlineKeyboardButton("🧾 فواتير MTN", callback_data="fclist:bal_mfaw")],
        [InlineKeyboardButton("💵 SYRIATEL CASH", callback_data="fclist:bal_scash"),
         InlineKeyboardButton("💵 MTN CASH", callback_data="fclist:bal_mcash")],
        [InlineKeyboardButton("💳 SHAM CASH", callback_data="fclist:bal_sham")],
        # — محافظ رقمية / بنكية —
        [InlineKeyboardButton("🟢 PAYEER", callback_data="fclist:bal_payeer"),
         InlineKeyboardButton("🟡 Perfect Money", callback_data="fclist:bal_pm")],
        [InlineKeyboardButton("🟠 Payoneer", callback_data="fclist:bal_payo"),
         InlineKeyboardButton("🏦 CLIQ Jordan", callback_data="fclist:bal_cliq")],
        # — عملات رقمية —
        [InlineKeyboardButton("₮ USDT TRC20", callback_data="fclist:bal_trc"),
         InlineKeyboardButton("₮ USDT BEP20", callback_data="fclist:bal_bep")],
        # — لبنان —
        [InlineKeyboardButton("🇱🇧 Touch", callback_data="fclist:bal_touch"),
         InlineKeyboardButton("🇱🇧 Alfa", callback_data="fclist:bal_alfa")],
        [InlineKeyboardButton("🇱🇧 Whish Money", callback_data="fclist:bal_whish")],
        # — عراق —
        [InlineKeyboardButton("🇮🇶 Asia Cell", callback_data="fclist:bal_asia"),
         InlineKeyboardButton("🇮🇶 Zain Iraq", callback_data="fclist:bal_zain")],
        # — تركيا —
        [InlineKeyboardButton("🇹🇷 Turkcell", callback_data="fclist:bal_turk"),
         InlineKeyboardButton("🇹🇷 TOSLA", callback_data="fclist:bal_tosla")],
        [InlineKeyboardButton("🇹🇷 Oldubil", callback_data="fclist:bal_oldu")],
        # — مصر —
        [InlineKeyboardButton("🇪🇬 Vodafone Cash", callback_data="fclist:bal_voda")],
        # — أخرى —
        [InlineKeyboardButton("📱 R-Cell", callback_data="fclist:bal_rcell"),
         InlineKeyboardButton("📱 Selam Telecom", callback_data="fclist:bal_selam")],
        [InlineKeyboardButton("💳 PAPRA", callback_data="fclist:bal_papra")],
        [InlineKeyboardButton("⬅️ المتجر", callback_data="menu:store")],
    ])


def games_menu() -> InlineKeyboardMarkup:
    """قائمة الألعاب الفرعية (تحت 🎮 الألعاب)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 ببجي موبايل", callback_data="store:pubg")],
        [InlineKeyboardButton("🔥 فري فاير", callback_data="store:freefire")],
        [InlineKeyboardButton("🏰 ألعاب Supercell", callback_data="store:supercell")],
        [InlineKeyboardButton("🪖 كول أوف ديوتي موبايل", callback_data="store:cod")],
        [InlineKeyboardButton("🪖 دلتا فورس", callback_data="store:delta")],
        [InlineKeyboardButton("⛏️ ماين كرافت", callback_data="store:minecraft")],
        [InlineKeyboardButton("🎮 فورتنايت", callback_data="store:fortnite")],
        [InlineKeyboardButton("🎲 ألعاب لودو", callback_data="store:ludo")],
        [InlineKeyboardButton("⬅️ المتجر", callback_data="menu:store")],
    ])


def cards_menu() -> InlineKeyboardMarkup:
    """قائمة البطاقات الرئيسية (8 منصات)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 PlayStation (PSN)", callback_data="cards:psn")],
        [InlineKeyboardButton("🚂 Steam", callback_data="cards:steam")],
        [InlineKeyboardButton("🍎 iTunes", callback_data="cards:itunes")],
        [InlineKeyboardButton("📱 Google Play", callback_data="cards:gplay")],
        [InlineKeyboardButton("🎮 Xbox", callback_data="cards:xbox")],
        [InlineKeyboardButton("🟢 Razer Gold", callback_data="cards:razer")],
        [InlineKeyboardButton("🎮 Nintendo", callback_data="fclist:nt_us")],
        [InlineKeyboardButton("📺 Netflix (اشتراكات)", callback_data="fclist:nflx")],
        [InlineKeyboardButton("💳 بطاقات VISA", callback_data="fclist:vs")],
        [InlineKeyboardButton("⬅️ المتجر", callback_data="menu:store")],
    ])


def cards_platform_menu(platform: str) -> InlineKeyboardMarkup:
    """قائمة دول/مناطق منصة بطاقات معينة (PSN/Steam/iTunes/...)."""
    options = {
        "psn":    [("🇺🇸 أمريكي", "ps_us"), ("🇸🇦 سعودي", "ps_sa"), ("🇱🇧 لبناني", "ps_lb"), ("🇦🇪 إماراتي", "ps_ae")],
        "steam":  [("🇺🇸 أمريكي", "st_us"), ("🇸🇦 سعودي", "st_sa"), ("🇹🇷 تركي", "st_tr")],
        "itunes": [("🇺🇸 أمريكي", "it_us"), ("🇸🇦 سعودي", "it_sa"), ("🇬🇧 بريطاني", "it_uk")],
        "gplay":  [("🇺🇸 أمريكي", "gp_us"), ("🇸🇦 سعودي", "gp_sa"), ("🇹🇷 تركي", "gp_tr")],
        "xbox":   [("🇺🇸 أمريكي", "xb_us"), ("🇸🇦 سعودي", "xb_sa")],
        "razer":  [("🌐 عالمي", "rz_gl"), ("🇺🇸 أمريكي", "rz_us"), ("🇹🇷 تركي", "rz_tr")],
    }
    rows = [[InlineKeyboardButton(label, callback_data=f"fclist:{prefix}")]
            for label, prefix in options.get(platform, [])]
    rows.append([InlineKeyboardButton("⬅️ البطاقات", callback_data="cards:menu")])
    return InlineKeyboardMarkup(rows)


def subs_menu() -> InlineKeyboardMarkup:
    """قائمة اشتراكات التطبيقات."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📺 Shahid VIP", callback_data="fclist:sh")],
        [InlineKeyboardButton("📹 YouTube Premium", callback_data="fclist:yt")],
        [InlineKeyboardButton("📺 Netflix", callback_data="fclist:nflx")],
        [InlineKeyboardButton("🎵 Anghami Plus", callback_data="fclist:an")],
        [InlineKeyboardButton("🍿 OSN+", callback_data="fclist:osn")],
        [InlineKeyboardButton("🤖 ChatGPT Plus", callback_data="fclist:gpt")],
        [InlineKeyboardButton("🎨 Canva Pro", callback_data="fclist:cv")],
        [InlineKeyboardButton("👻 Snapchat+", callback_data="fclist:snap")],
        [InlineKeyboardButton("🛡️ Nord VPN", callback_data="fclist:nv")],
        [InlineKeyboardButton("🟦 Express VPN", callback_data="fclist:ev")],
        [InlineKeyboardButton("⚡ LagoFast VPN", callback_data="fclist:lv")],
        [InlineKeyboardButton("🚀 GearUP Booster", callback_data="fclist:gu")],
        [InlineKeyboardButton("📢 تعزيز قنوات تلغرام", callback_data="fclist:tg")],
        [InlineKeyboardButton("⬅️ المتجر", callback_data="menu:store")],
    ])


def smm_menu() -> InlineKeyboardMarkup:
    """قائمة خدمات الرشق (متابعين/إعجابات/مشاهدات)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 متابعين انستغرام", callback_data="fclist:igf")],
        [InlineKeyboardButton("❤️ لايكات إنستغرام", callback_data="fclist:igl")],
        [InlineKeyboardButton("👁️ مشاهدات إنستغرام", callback_data="fclist:igv")],
        [InlineKeyboardButton("👍 متابعين فيسبوك", callback_data="fclist:fbf")],
        [InlineKeyboardButton("📊 مشاهدات تلغرام", callback_data="fclist:tgv")],
        [InlineKeyboardButton("💯 تفاعل/لايك تلغرام", callback_data="fclist:tgr")],
        [InlineKeyboardButton("⬅️ المتجر", callback_data="menu:store")],
    ])


def supercell_sections() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Brawl Stars", callback_data="sc:bs")],
        [InlineKeyboardButton("🏰 Clash of Clans", callback_data="sc:coc")],
        [InlineKeyboardButton("👑 Clash Royale", callback_data="sc:cr")],
        [InlineKeyboardButton("🌾 Hay Day", callback_data="sc:hd")],
        [InlineKeyboardButton("⬅️ المتجر", callback_data="menu:store")],
    ])


def cod_sections() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 شدات (نقاط COD)", callback_data="cdnav:packs")],
        [InlineKeyboardButton("🎫 Battle Pass", callback_data="cdnav:bp")],
        [InlineKeyboardButton("⬅️ المتجر", callback_data="menu:store")],
    ])


def ludo_sections() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Ludo World", callback_data="lunav:lw")],
        [InlineKeyboardButton("🎲 Ludo Club", callback_data="lunav:lc")],
        [InlineKeyboardButton("🎲 Yalla Ludo", callback_data="lunav:yl")],
        [InlineKeyboardButton("⬅️ المتجر", callback_data="menu:store")],
    ])


def pubg_sections() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 شدات", callback_data="pubg:uc")],
        [InlineKeyboardButton("👑 عضويات ببجي", callback_data="pubg:membership")],
        [InlineKeyboardButton("🎟️ أكواد شدات", callback_data="pubg:codes")],
        [InlineKeyboardButton("⬅️ المتجر", callback_data="menu:store")],
    ])


def pubg_uc_offers(stock: dict = None) -> InlineKeyboardMarkup:
    rows = []
    for offer in config.PUBG_UC_OFFERS:
        rows.append([InlineKeyboardButton(
            f"🪙 {offer['label']} - {config.get_offer_price(offer)} ل.س",
            callback_data=f"pubg_uc:{offer['id']}"
        )])
    rows.append([InlineKeyboardButton("⬅️ ببجي موبايل", callback_data="store:pubg")])
    return InlineKeyboardMarkup(rows)


def pubg_uc_confirm(offer_id: str, price: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ تأكيد الشراء ({price:.0f} ل.س)", callback_data=f"pubg_uc_confirm:{offer_id}")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="pubg:uc")],
    ])


def freefire_sections() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 جواهر (تلقائي)", callback_data="ff:diamonds")],
        [InlineKeyboardButton("👑 عضويات فري فاير", callback_data="ff:membership")],
        [InlineKeyboardButton("🎟️ أكواد جواهر", callback_data="ff:codes")],
        [InlineKeyboardButton("⬅️ المتجر", callback_data="menu:store")],
    ])


def freefire_diamond_offers() -> InlineKeyboardMarkup:
    rows = []
    for offer in config.FREEFIRE_DIAMOND_OFFERS:
        rows.append([InlineKeyboardButton(
            f"💎 {offer['label']} - {config.get_offer_price(offer)} ل.س",
            callback_data=f"ff_dia:{offer['id']}"
        )])
    rows.append([InlineKeyboardButton("⬅️ فري فاير", callback_data="store:freefire")])
    return InlineKeyboardMarkup(rows)


def freefire_diamond_confirm(offer_id: str, price: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ تأكيد الشراء ({price:.0f} ل.س)", callback_data=f"ff_dia_confirm:{offer_id}")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="ff:diamonds")],
    ])


def fastcard_offers_list(prefix: str) -> InlineKeyboardMarkup:
    """قائمة عامة لأي قسم تلقائي عبر Fastcard. prefix من FASTCARD_CATEGORIES."""
    cat = config.FASTCARD_CATEGORIES.get(prefix)
    if not cat:
        return back_to_main()
    import sys
    offers = getattr(sys.modules["bot.config"], cat["offers_attr"], [])
    rows = []
    for offer in offers:
        if not offer.get("enabled", True):
            label = f"🔴 {offer['label']} — نفد المخزون"
            rows.append([InlineKeyboardButton(label, callback_data=f"fcsold:{prefix}")])
        else:
            label = f"{offer['label']} — {config.get_offer_price(offer):,} ل.س".replace(",", "،")
            rows.append([InlineKeyboardButton(label, callback_data=f"fcbuy:{prefix}:{offer['id']}")])
    rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data=cat["back_callback"])])
    return InlineKeyboardMarkup(rows)


def fastcard_confirm(prefix: str, offer_id: str, price: float) -> InlineKeyboardMarkup:
    cat = config.FASTCARD_CATEGORIES.get(prefix, {})
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ تأكيد الشراء ({price:,.0f} ل.س)".replace(",", "،"),
                              callback_data=f"fcconf:{prefix}:{offer_id}")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data=f"fclist:{prefix}")],
    ])


def insufficient_balance() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 شحن رصيد الحساب", callback_data="menu:recharge")],
        [InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="menu:main")],
    ])


def cancel_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ إلغاء", callback_data="menu:main")],
    ])


def syriatel_after_amount(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تحقق تلقائي (حولت بالفعل)", callback_data=f"syr_verify:{req_id}")],
        [InlineKeyboardButton("⏳ انتظار مراجعة يدوية", callback_data=f"syr_manual:{req_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="menu:main")],
    ])


def syriatel_retry(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"syr_verify:{req_id}")],
        [InlineKeyboardButton("⏳ مراجعة يدوية", callback_data=f"syr_manual:{req_id}")],
        [InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="menu:main")],
    ])


def shamcash_after_amount(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تحقق تلقائي (حولت بالفعل)", callback_data=f"sc_verify:{req_id}")],
        [InlineKeyboardButton("📸 إرسال صورة (يدوي)", callback_data=f"sc_manual:{req_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="menu:main")],
    ])


def shamcash_retry(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"sc_verify:{req_id}")],
        [InlineKeyboardButton("📸 إرسال صورة بدلاً", callback_data=f"sc_manual:{req_id}")],
        [InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="menu:main")],
    ])


def shamcash_usd_after_amount(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تحقق تلقائي (حولت بالفعل)", callback_data=f"sc_verify_usd:{req_id}")],
        [InlineKeyboardButton("📸 إرسال صورة (يدوي)", callback_data=f"sc_manual:{req_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="menu:main")],
    ])


def shamcash_usd_retry(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"sc_verify_usd:{req_id}")],
        [InlineKeyboardButton("📸 إرسال صورة بدلاً", callback_data=f"sc_manual:{req_id}")],
        [InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="menu:main")],
    ])


def admin_recharge_decision(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ قبول", callback_data=f"adm_rch:approve:{req_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"adm_rch:reject:{req_id}"),
        ],
    ])


def admin_order_decision(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تم التنفيذ", callback_data=f"adm_ord:approve:{order_id}"),
            InlineKeyboardButton("❌ رفض/استرجاع", callback_data=f"adm_ord:reject:{order_id}"),
        ],
    ])


def admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 إحصائيات", callback_data="admin:stats")],
        [InlineKeyboardButton("⏳ الطلبات المعلقة", callback_data="admin:pending")],
        [InlineKeyboardButton("💼 حالة المتجر (API)", callback_data="admin:supplier")],
        [InlineKeyboardButton("📱 رصيد سرياتيل كاش", callback_data="admin:syriatel_balance")],
        [InlineKeyboardButton("🔍 فحص أسعار Fastcard الآن", callback_data="admin:price_check")],
        [InlineKeyboardButton("📈 تقرير اليوم", callback_data="admin:today_report")],
        [InlineKeyboardButton("💵 الأرباح", callback_data="admin:profit")],
        [InlineKeyboardButton("🏆 أفضل الزبائن", callback_data="admin:top_users")],
        [InlineKeyboardButton("⭐ تقييمات الزبائن", callback_data="admin:ratings")],
        [InlineKeyboardButton("🎟 الكوبونات", callback_data="admin:coupons")],
        [InlineKeyboardButton("💱 سعر الصرف", callback_data="admin:rates")],
        [InlineKeyboardButton("💲 تعديل أسعار المنتجات", callback_data="admin:prices")],
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin:search_user")],
        [InlineKeyboardButton("✏️ تعديل رصيد", callback_data="admin:edit_balance")],
        [InlineKeyboardButton("🚫 حظر/فك حظر", callback_data="admin:toggle_ban")],
        [InlineKeyboardButton("📢 إشعار جماعي", callback_data="admin:broadcast")],
        [InlineKeyboardButton("📡 قناة توثيق الطلبات", callback_data="admin:channel")],
        [InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="menu:main")],
    ])


def admin_price_categories(page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """قائمة كل أقسام المنتجات لتعديل الأسعار، مع pagination."""
    cats = config.PRICE_EDIT_CATEGORIES
    total = len(cats)
    start = page * per_page
    end = min(start + per_page, total)
    rows = []
    for key, _attr, title in cats[start:end]:
        rows.append([InlineKeyboardButton(title, callback_data=f"admin:prices:cat:{key}")])
    # pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"admin:prices:page:{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"admin:prices:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ رجوع للوحة الأدمن", callback_data="admin:panel")])
    return InlineKeyboardMarkup(rows)


def admin_price_offers(cat_key: str, page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
    """قائمة عروض قسم معين مع السعر الحالي. الضغط يعدل السعر."""
    from . import database as _db
    offers = config.get_price_edit_offers(cat_key)
    overrides = _db.list_price_overrides()
    total = len(offers)
    start = page * per_page
    end = min(start + per_page, total)
    rows = []
    for o in offers[start:end]:
        oid = o.get("id", "")
        is_override = oid in overrides
        cur_price = config.get_offer_price(o)
        marker = " ✏️" if is_override else ""
        label = o.get("label", oid)
        # قص العنوان لو طويل
        if len(label) > 28:
            label = label[:26] + "…"
        btn_text = f"{label} - {cur_price:,} ل.س{marker}".replace(",", "،")
        rows.append([InlineKeyboardButton(btn_text, callback_data=f"admin:prices:offer:{cat_key}:{oid}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"admin:prices:catpg:{cat_key}:{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"admin:prices:catpg:{cat_key}:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ رجوع للأقسام", callback_data="admin:prices")])
    rows.append([InlineKeyboardButton("🏠 لوحة الأدمن", callback_data="admin:panel")])
    return InlineKeyboardMarkup(rows)


def admin_price_offer_actions(cat_key: str, offer_id: str, has_override: bool) -> InlineKeyboardMarkup:
    """شاشة العرض الواحد: تعديل السعر أو إرجاعه للحساب التلقائي."""
    rows = []
    if has_override:
        rows.append([InlineKeyboardButton("🔄 إرجاع للحساب التلقائي", callback_data=f"admin:prices:reset:{cat_key}:{offer_id}")])
    rows.append([InlineKeyboardButton("⬅️ رجوع لعروض القسم", callback_data=f"admin:prices:cat:{cat_key}")])
    rows.append([InlineKeyboardButton("🏠 لوحة الأدمن", callback_data="admin:panel")])
    return InlineKeyboardMarkup(rows)


def admin_price_cancel(cat_key: str, offer_id: str) -> InlineKeyboardMarkup:
    """زر إلغاء أثناء انتظار إدخال السعر الجديد."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ إلغاء", callback_data=f"admin:prices:offer:{cat_key}:{offer_id}")],
    ])


def admin_price_check_actions(has_fixable: bool) -> InlineKeyboardMarkup:
    """أزرار تقرير فحص الأسعار: إعادة فحص + إصلاح تلقائي + رجوع."""
    rows = []
    if has_fixable:
        rows.append([InlineKeyboardButton(
            "🛠️ تطبيق الأسعار المقترحة (إصلاح الخسائر)",
            callback_data="admin:price_check:fix",
        )])
    rows.append([InlineKeyboardButton("🔄 إعادة الفحص", callback_data="admin:price_check")])
    rows.append([InlineKeyboardButton("⬅️ رجوع للوحة الأدمن", callback_data="admin:panel")])
    return InlineKeyboardMarkup(rows)


def admin_price_check_fix_confirm() -> InlineKeyboardMarkup:
    """تأكيد قبل تطبيق الأسعار المقترحة تلقائياً."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ نعم، طبّق الأسعار المقترحة", callback_data="admin:price_check:fix:yes")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="admin:price_check")],
    ])


def admin_rates_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 جلب السعر من @SaymouaaExchange", callback_data="admin:rates:fetch")],
        [InlineKeyboardButton("✏️ تعديل سعر تسعير العروض", callback_data="admin:rates:set_offers")],
        [InlineKeyboardButton("✏️ تعديل سعر شحن الدولار", callback_data="admin:rates:set_recharge")],
        [InlineKeyboardButton("💎 ضبط محفظة USDT (BEP20)", callback_data="admin:rates:set_usdt_wallet")],
        [InlineKeyboardButton("⬅️ رجوع للوحة الأدمن", callback_data="admin:panel")],
    ])


def admin_rates_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ إلغاء", callback_data="admin:rates")],
    ])


def admin_rates_apply_fetched(rate: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ تطبيق {rate:,} ل.س/$".replace(",", "،"), callback_data=f"admin:rates:apply:{rate}")],
        [InlineKeyboardButton("❌ تجاهل", callback_data="admin:rates")],
    ])


def admin_profit_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 أرباح اليوم", callback_data="admin:profit:today")],
        [InlineKeyboardButton("📆 أرباح آخر 7 أيام", callback_data="admin:profit:week")],
        [InlineKeyboardButton("🗓 أرباح آخر 30 يوم", callback_data="admin:profit:month")],
        [InlineKeyboardButton("🏆 أرباح كل الفترة", callback_data="admin:profit:all")],
        [InlineKeyboardButton("📈 رسم بياني", callback_data="admin:chart")],
        [InlineKeyboardButton("⬅️ رجوع للوحة الأدمن", callback_data="admin:panel")],
    ])


def rating_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """5 نجوم للتقييم بعد إكمال طلب."""
    row = [
        InlineKeyboardButton("⭐", callback_data=f"rate:{order_id}:1"),
        InlineKeyboardButton("⭐⭐", callback_data=f"rate:{order_id}:2"),
        InlineKeyboardButton("⭐⭐⭐", callback_data=f"rate:{order_id}:3"),
    ]
    row2 = [
        InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f"rate:{order_id}:4"),
        InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f"rate:{order_id}:5"),
    ]
    return InlineKeyboardMarkup([row, row2, [
        InlineKeyboardButton("⏭ تخطّي", callback_data=f"rate:{order_id}:0"),
    ]])


def admin_coupons_panel(coupons: list) -> InlineKeyboardMarkup:
    """قائمة الكوبونات للأدمن. كل كوبون → زر تعطيل."""
    rows = [[InlineKeyboardButton("➕ إنشاء كوبون جديد", callback_data="admin:coupon:new")]]
    for c in coupons[:15]:
        active = int(c.get("active") or 0)
        status = "✅" if active else "🚫"
        code = c.get("code", "—")
        if active:
            rows.append([InlineKeyboardButton(
                f"{status} {code}",
                callback_data=f"admin:coupon:disable:{c['id']}"
            )])
        else:
            rows.append([InlineKeyboardButton(f"{status} {code} (معطّل)", callback_data="admin:coupons")])
    rows.append([InlineKeyboardButton("⬅️ رجوع للوحة الأدمن", callback_data="admin:panel")])
    return InlineKeyboardMarkup(rows)


def admin_coupon_type_picker() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💯 نسبة مئوية (%)", callback_data="admin:coupon:type:percent")],
        [InlineKeyboardButton("💵 مبلغ ثابت (ل.س)", callback_data="admin:coupon:type:fixed")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="admin:coupons")],
    ])


def admin_coupon_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ إلغاء", callback_data="admin:coupons")],
    ])


def admin_chart_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آخر 7 أيام", callback_data="admin:chart:7")],
        [InlineKeyboardButton("📊 آخر 30 يوم", callback_data="admin:chart:30")],
        [InlineKeyboardButton("📊 آخر 90 يوم", callback_data="admin:chart:90")],
        [InlineKeyboardButton("⬅️ رجوع لقائمة الأرباح", callback_data="admin:profit")],
    ])


def admin_profit_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ رجوع لقائمة الأرباح", callback_data="admin:profit")],
        [InlineKeyboardButton("🏠 لوحة الأدمن", callback_data="admin:panel")],
    ])


def back_to_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ رجوع للوحة الأدمن", callback_data="admin:panel")],
    ])


def admin_codes_menu(inventory: dict) -> InlineKeyboardMarkup:
    rows = []
    for offer in config.PUBG_UC_OFFERS:
        avail = inventory.get(offer["id"], 0)
        rows.append([InlineKeyboardButton(
            f"🪙 {offer['label']} — متوفر: {avail}",
            callback_data=f"admin_codes:add:{offer['id']}"
        )])
    rows.append([InlineKeyboardButton("🗑️ تفريغ كل المخزون", callback_data="admin_codes:clear_menu")])
    rows.append([InlineKeyboardButton("⬅️ رجوع للوحة الأدمن", callback_data="admin:panel")])
    return InlineKeyboardMarkup(rows)


def admin_codes_clear_menu() -> InlineKeyboardMarkup:
    rows = []
    for offer in config.PUBG_UC_OFFERS:
        rows.append([InlineKeyboardButton(
            f"🗑️ تفريغ {offer['label']}",
            callback_data=f"admin_codes:clear:{offer['id']}"
        )])
    rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin:codes")])
    return InlineKeyboardMarkup(rows)
