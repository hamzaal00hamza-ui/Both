"""
إعدادات البوت - كل الإعدادات الحساسة تأتي من متغيرات البيئة (Secrets)
"""
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "0")
try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except (ValueError, TypeError):
    ADMIN_ID = 0

ADMIN_CHANNEL = os.environ.get("ADMIN_CHANNEL", "")

DB_PATH = os.environ.get("DB_PATH", "bot/database.db")
# تأكد إن مجلد الـ DB موجود (مهم لـ Railway Volume على /data)
_db_dir = os.path.dirname(DB_PATH)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)

SYRIATEL_CASH_NUMBER = "0982493924"

# محفظة USDT — BSC BEP20 (يمكن تعديلها من لوحة الأدمن أو من هنا مباشرة)
USDT_WALLET_BEP20 = os.environ.get("USDT_WALLET_BEP20", "0x9a8e639b26ee2a7796b6a2d81d2df0a74cb615d5")

# ── Binance Pay — إيداع USDT أوتوماتيكي ──────────────────
BINANCE_API_KEY    = os.environ.get("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")
BINANCE_PAY_AUTO   = os.environ.get("BINANCE_PAY_AUTO", "1") == "1"
BINANCE_ORDER_EXPIRE_MINUTES = int(os.environ.get("BINANCE_ORDER_EXPIRE_MINUTES", "15"))


SHAMCASH_WALLET_CODE = "2ddc70bf6636ab6fc783f957e2fa5d81"
SHAMCASH_WALLET_NAME = "قيس ربيع جمول"

SUPPORT_USERNAME = "@Hamzaalshomari"

# صورة البانر التي تظهر عند /start (يمكن تغييرها من متغير البيئة START_BANNER_URL)
START_BANNER_URL = os.environ.get(
    "START_BANNER_URL",
    "https://raw.githubusercontent.com/hamzaal00hamza-ui/Both/main/assets/banner.jpg",
)

REFERRAL_SIGNUP_BONUS = 2000
REFERRAL_COMMISSION_PERCENT = 8

# نظام نقاط الولاء
# كل طلب ناجح = 1% من قيمته نقاط (1 نقطة = 1 ل.س)
# الزبون يستبدل نقاطه برصيد لما يجمع 1000 نقطة على الأقل
LOYALTY_EARN_PERCENT = 1.0          # نسبة كسب النقاط من قيمة الطلب
LOYALTY_REDEEM_RATE = 1             # 1 نقطة = 1 ل.س
LOYALTY_MIN_REDEEM = 1000           # أقل عدد نقاط قابل للاستبدال

# ===== كوبونات تلقائية دورية =====
# البوت يولّد كوبون جديد كل X يوم، صالح لـ Y زبائن، بقيمة Z ل.س ثابتة
AUTO_COUPON_ENABLED = True          # تفعيل/تعطيل التوليد التلقائي
AUTO_COUPON_INTERVAL_DAYS = 10      # كل كم يوم نولّد كوبون جديد
AUTO_COUPON_MAX_USES = 10           # عدد الزبائن المسموح لهم استخدامه
AUTO_COUPON_VALUE_SYP = 5000        # قيمة الكوبون بالليرة السورية (نوع fixed)
AUTO_COUPON_BROADCAST = False       # لا نرسل إعلان للزبائن — الأدمن فقط يستلم الكود وينشره يدوياً

LEVELS = [
    ("🥉 برونزي", 0, 4999),
    ("🥈 فضي", 5000, 14999),
    ("🥇 ذهبي", 15000, 49999),
    ("💎 بلاتيني", 50000, 149999),
    ("💠 ماسي", 150000, 499999),
    ("👑 VIP", 500000, 1499999),
    ("🏆 ملكي", 1500000, float("inf")),
]

# ===== أسعار الصرف =====
# القيم الافتراضية تُستخدم فقط لو الأدمن لم يضبط القيم من لوحة التحكم.
# الأدمن يقدر يعدّل القيم من /admin → 💱 سعر الصرف وتنطبق فوراً على كل العروض.

# سعر تسعير العروض: السعر النهائي = cost_usd × DEFAULT_SYP_PER_USD مدور لـ 500
DEFAULT_SYP_PER_USD = 14700

# سعر تحويل شحن شام كاش دولار → رصيد ل.س
DEFAULT_USD_TO_SYP = float(os.environ.get("USD_TO_SYP", "13100"))


def get_syp_per_usd() -> float:
    """سعر صرف الدولار المستخدم في تسعير العروض. يُقرأ من DB إذا تم ضبطه من لوحة الأدمن."""
    try:
        from . import database as _db
        val = _db.get_setting("syp_per_usd")
        if val:
            return float(val)
    except Exception:
        pass
    return float(DEFAULT_SYP_PER_USD)


def get_profit_margin() -> float:
    """هامش الربح المطبّق على العروض. يُقرأ من DB إذا تم ضبطه من لوحة الأدمن."""
    try:
        from . import database as _db
        val = _db.get_setting("profit_margin")
        if val is not None:
            return float(val)
    except Exception:
        pass
    return float(PROFIT_MARGIN)


def get_usd_to_syp() -> float:
    """سعر تحويل شحن شام كاش دولار → رصيد ل.س. يُقرأ من DB إذا تم ضبطه."""
    try:
        from . import database as _db
        val = _db.get_setting("usd_to_syp")
        if val:
            return float(val)
    except Exception:
        pass
    return float(DEFAULT_USD_TO_SYP)


def round_up_to_500(amount: float) -> int:
    """يدور المبلغ لأعلى لأقرب 500 ل.س."""
    if amount <= 0:
        return 0
    return int(((amount + 499) // 500) * 500)


PRICING_BASE_RATE = 14700  # سعر الصرف المرجعي الذي حُسبت عليه أسعار العروض الأصلية
PRICING_BASE_MARGIN = 0.12  # هامش الربح الأصلي المدمج في أسعار config
PROFIT_MARGIN = 0.05  # هامش الربح الحالي المطبّق على كل العروض


def get_offer_price(offer: dict) -> int:
    """يرجع سعر العرض بالليرة السورية.

    أولوية الحساب:
    1. لو عند الأدمن سعر يدوي محفوظ في DB لهذا العرض → نستخدمه (override).
    2. لو ما فيه `cost_usd` (رصيد محلي بل.س) → السعر ثابت من config.
    3. غير ذلك → نحسب: qty × cost_usd × rate × (1 + PROFIT_MARGIN) مدور لأقرب 500 ل.س.
    """
    # 1) فحص override يدوي من DB
    offer_id = offer.get("id")
    if offer_id:
        try:
            from . import database as _db
            ov = _db.get_price_override(str(offer_id))
            if ov is not None and ov > 0:
                return int(ov)
        except Exception:
            pass

    base_price = int(offer.get("price", 0) or 0)
    if base_price <= 0:
        return 0
    # 2) العروض اللي مالها علاقة بالدولار → سعر ثابت
    cost_usd = offer.get("cost_usd")
    if not cost_usd:
        return base_price
    # 3) العروض المرتبطة بالدولار → نحسب من cost_usd مع هامش الربح الحالي
    qty = offer.get("qty", 1) or 1
    current_rate = get_syp_per_usd()
    cost_syp = float(cost_usd) * qty * current_rate
    return round_up_to_500(cost_syp * (1 + get_profit_margin()))


# ===== خريطة كل أقسام المنتجات للوحة تعديل الأسعار =====
# (مفتاح_القسم, اسم_القائمة_في_config, العنوان_للعرض)
PRICE_EDIT_CATEGORIES = [
    ("pubg_uc",     "PUBG_UC_OFFERS",          "🪙 ببجي - شدات UC"),
    ("pubg_mem",    "PUBG_MEMBERSHIPS",        "👑 ببجي - عضويات"),
    ("pubg_codes",  "PUBG_CODES",              "🎟️ ببجي - أكواد شدات"),
    ("ff_dia",      "FREEFIRE_DIAMOND_OFFERS", "💎 فري فاير - جواهر"),
    ("ff_mem",      "FREEFIRE_MEMBERSHIPS",    "👑 فري فاير - عضويات"),
    ("ff_codes",    "FREEFIRE_CODES",          "🎟️ فري فاير - أكواد جواهر"),
    ("brawl",       "BRAWL_STARS_OFFERS",      "⭐ Brawl Stars"),
    ("coc",         "CLASH_OF_CLANS_OFFERS",   "🏰 Clash of Clans"),
    ("cor",         "CLASH_ROYALE_OFFERS",     "👑 Clash Royale"),
    ("hayday",      "HAY_DAY_OFFERS",          "🌾 Hay Day"),
    ("cod",         "COD_OFFERS",              "🔫 Call of Duty"),
    ("cod_pass",    "COD_PASS_OFFERS",         "🎟️ COD Battle Pass"),
    ("delta",       "DELTA_FORCE_OFFERS",      "💥 Delta Force"),
    ("minecraft",   "MINECRAFT_OFFERS",        "⛏️ Minecraft"),
    ("fortnite",    "FORTNITE_OFFERS",         "🎯 Fortnite"),
    ("ludo_w",      "LUDO_WORLD_OFFERS",       "🎲 Ludo World"),
    ("ludo_c",      "LUDO_CLUB_OFFERS",        "🎲 Ludo Club"),
    ("ludo_y",      "LUDO_YALLA_OFFERS",       "🎲 Ludo Yalla"),
    ("shahid",      "SHAHID_OFFERS",           "📺 Shahid"),
    ("youtube",     "YOUTUBE_OFFERS",          "▶️ YouTube"),
    ("anghami",     "ANGHAMI_OFFERS",          "🎵 Anghami"),
    ("osn",         "OSN_OFFERS",              "📺 OSN+"),
    ("chatgpt",     "CHATGPT_OFFERS",          "🤖 ChatGPT"),
    ("canva",       "CANVA_OFFERS",            "🎨 Canva"),
    ("snapchat",    "SNAPCHAT_OFFERS",         "👻 Snapchat"),
    ("nordvpn",     "NORDVPN_OFFERS",          "🛡️ NordVPN"),
    ("expressvpn",  "EXPRESSVPN_OFFERS",       "🛡️ ExpressVPN"),
    ("lagofast",    "LAGOFAST_OFFERS",         "⚡ LagoFast"),
    ("gearup",      "GEARUP_OFFERS",           "⚡ GearUP"),
    ("tgboost",     "TGBOOST_OFFERS",          "🚀 Telegram Boost"),
    ("visa",        "VISA_OFFERS",             "💳 Visa"),
    ("psn_us",      "PSN_US_OFFERS",           "🎮 PSN (US)"),
    ("psn_sa",      "PSN_SA_OFFERS",           "🎮 PSN (SA)"),
    ("psn_lb",      "PSN_LB_OFFERS",           "🎮 PSN (LB)"),
    ("psn_ae",      "PSN_AE_OFFERS",           "🎮 PSN (AE)"),
    ("steam_us",    "STEAM_US_OFFERS",         "🟦 Steam (US)"),
    ("steam_sa",    "STEAM_SA_OFFERS",         "🟦 Steam (SA)"),
    ("steam_tr",    "STEAM_TR_OFFERS",         "🟦 Steam (TR)"),
    ("itunes_us",   "ITUNES_US_OFFERS",        "🍎 iTunes (US)"),
    ("itunes_sa",   "ITUNES_SA_OFFERS",        "🍎 iTunes (SA)"),
    ("itunes_uk",   "ITUNES_UK_OFFERS",        "🍎 iTunes (UK)"),
    ("gplay_us",    "GPLAY_US_OFFERS",         "🤖 Google Play (US)"),
    ("gplay_sa",    "GPLAY_SA_OFFERS",         "🤖 Google Play (SA)"),
    ("gplay_tr",    "GPLAY_TR_OFFERS",         "🤖 Google Play (TR)"),
    ("xbox_us",     "XBOX_US_OFFERS",          "🟩 Xbox (US)"),
    ("xbox_sa",     "XBOX_SA_OFFERS",          "🟩 Xbox (SA)"),
    ("razer_gl",    "RAZER_GL_OFFERS",         "💚 Razer Gold (Global)"),
    ("razer_us",    "RAZER_US_OFFERS",         "💚 Razer Gold (US)"),
    ("razer_tr",    "RAZER_TR_OFFERS",         "💚 Razer Gold (TR)"),
    ("nintendo",    "NINTENDO_OFFERS",         "🎮 Nintendo"),
    ("netflix",     "NETFLIX_OFFERS",          "🎬 Netflix"),
    ("syr_bal",     "SYRIATEL_BALANCE_OFFERS", "📲 رصيد سيريتل"),
    ("syr_gas",     "SYRIATEL_GAS_OFFERS",     "🔥 سيريتل غاز"),
    ("syr_faw",     "SYRIATEL_FAWATEER_OFFERS","🧾 سيريتل فواتير"),
    ("syr_cash",    "SYRIATEL_CASH_OFFERS",    "💵 سيريتل كاش"),
    ("mtn_bal",     "MTN_BALANCE_OFFERS",      "📲 رصيد MTN"),
    ("mtn_gas",     "MTN_GAS_OFFERS",          "🔥 MTN غاز"),
    ("mtn_faw",     "MTN_FAWATEER_OFFERS",     "🧾 MTN فواتير"),
    ("mtn_cash",    "MTN_CASH_OFFERS",         "💵 MTN كاش"),
    ("sham_bal",    "SHAMCASH_BAL_OFFERS",     "💳 شام كاش"),
    ("payeer",      "PAYEER_OFFERS",           "💰 Payeer"),
    ("pm",          "PERFECTMONEY_OFFERS",     "💰 Perfect Money"),
    ("payoneer",    "PAYONEER_OFFERS",         "💰 Payoneer"),
    ("cliq_jo",     "CLIQ_JORDAN_OFFERS",      "💰 CliQ الأردن"),
    ("usdt_trc",    "USDT_TRC20_OFFERS",       "₮ USDT TRC20"),
    ("usdt_bep",    "USDT_BEP20_OFFERS",       "₮ USDT BEP20"),
    ("touch",       "TOUCH_OFFERS",            "📲 Touch (لبنان)"),
    ("alfa",        "ALFA_OFFERS",             "📲 Alfa (لبنان)"),
    ("whish",       "WHISH_OFFERS",            "💵 Whish (لبنان)"),
    ("asiacell",    "ASIACELL_OFFERS",         "📲 آسياسيل (العراق)"),
    ("zain_iq",     "ZAIN_IRAQ_OFFERS",        "📲 زين (العراق)"),
    ("turkcell",    "TURKCELL_OFFERS",         "📲 Turkcell (تركيا)"),
    ("tosla",       "TOSLA_OFFERS",            "💰 Tosla (تركيا)"),
    ("oldubil",     "OLDUBIL_OFFERS",          "💰 Oldubil (تركيا)"),
    ("vodafone",    "VODAFONE_CASH_OFFERS",    "💵 فودافون كاش (مصر)"),
    ("rcell",       "RCELL_OFFERS",            "📲 R Cell"),
    ("selam",       "SELAM_TELECOM_OFFERS",    "📲 Selam Telecom"),
    # خدمات الرشق (SMM)
    ("smm_igf",     "INSTAGRAM_FOLLOWERS",     "📸 رشق متابعين إنستغرام"),
    ("smm_igl",     "INSTAGRAM_LIKES",         "❤️ رشق لايكات إنستغرام"),
    ("smm_igv",     "INSTAGRAM_VIEWS",         "👁️ رشق مشاهدات إنستغرام"),
    ("smm_fbf",     "FACEBOOK_FOLLOWERS",      "👍 رشق متابعين فيسبوك"),
    ("smm_tgv",     "TELEGRAM_VIEWS",          "📊 رشق مشاهدات تلغرام"),
    ("smm_tgr",     "TELEGRAM_REACTIONS",      "💯 رشق تفاعل تلغرام"),
    # ألعاب جديدة
    ("ff_s2",       "FREEFIRE_S2_OFFERS",      "🔥 فري فاير - سيرفر 2"),
    ("ff_eu",       "FREEFIRE_EU_OFFERS",      "🔥 فري فاير - أوروبا"),
    ("rblx_us",     "ROBLOX_USA_OFFERS",       "🎮 Roblox USA"),
    ("rblx_ksa",    "ROBLOX_KSA_OFFERS",       "🎮 Roblox KSA"),
    ("rblx_ae",     "ROBLOX_UAE_OFFERS",       "🎮 Roblox UAE"),
    ("valo_gl",     "VALORANT_GLOBAL_OFFERS",  "🔫 Valorant عالمي"),
    ("valo_tr",     "VALORANT_TR_OFFERS",      "🔫 Valorant تركي"),
    ("bsk",         "BLOOD_STRIKE_OFFERS",     "💀 Blood Strike"),
    ("stmb",        "STUMBLE_GUYS_OFFERS",     "🎮 Stumble Guys"),
    ("ssus",        "SUPER_SUS_OFFERS",        "🛸 Super Sus"),
    # اشتراكات جديدة
    ("spfy",        "SPOTIFY_OFFERS",          "🎵 Spotify"),
    ("nova",        "NOVA_TV_OFFERS",          "📺 Nova TV"),
    ("pvpn",        "PROTONVPN_OFFERS",        "🛡️ Proton VPN"),
    ("svpn",        "SURFSHARK_OFFERS",        "🦈 SurfShark VPN"),
    # بطاقات PSN جديدة
    ("psn_bh",      "PSN_BH_OFFERS",           "🎮 PSN (Bahrain)"),
    ("psn_qa",      "PSN_QA_OFFERS",           "🎮 PSN (Qatar)"),
    ("psn_om",      "PSN_OM_OFFERS",           "🎮 PSN (Oman)"),
    ("psn_uk",      "PSN_UK_OFFERS",           "🎮 PSN (UK)"),
    ("psn_de",      "PSN_DE_OFFERS",           "🎮 PSN (Germany)"),
    # بطاقات Steam جديدة
    ("steam_ae",    "STEAM_AE_OFFERS",         "🟦 Steam (Emirates)"),
    ("steam_kw",    "STEAM_KW_OFFERS",         "🟦 Steam (Kuwait)"),
    ("steam_om",    "STEAM_OM_OFFERS",         "🟦 Steam (Oman)"),
]


def get_price_edit_offers(cat_key: str) -> list:
    """يرجع قائمة العروض لقسم معين من PRICE_EDIT_CATEGORIES."""
    import sys
    for key, attr, _title in PRICE_EDIT_CATEGORIES:
        if key == cat_key:
            return getattr(sys.modules[__name__], attr, []) or []
    return []


def get_price_edit_title(cat_key: str) -> str:
    """يرجع عنوان القسم."""
    for key, _attr, title in PRICE_EDIT_CATEGORIES:
        if key == cat_key:
            return title
    return cat_key


def find_offer_anywhere(offer_id: str):
    """يبحث عن عرض في كل قوائم العروض. يرجع (offer, cat_key) أو (None, None)."""
    if not offer_id:
        return None, None
    import sys
    mod = sys.modules[__name__]
    for key, attr, _title in PRICE_EDIT_CATEGORIES:
        offers = getattr(mod, attr, []) or []
        for o in offers:
            if o.get("id") == offer_id:
                return o, key
    return None, None


def build_cost_map() -> dict:
    """يبني قاموس موحد {label: cost_usd} من كل قوائم العروض في الموديول هذا.
    يستخدم لحساب التكلفة الفعلية للطلبات عند بناء تقارير الأرباح."""
    import sys
    mod = sys.modules[__name__]
    cost_map: dict = {}
    for name in dir(mod):
        if not name.endswith("_OFFERS"):
            continue
        val = getattr(mod, name, None)
        if not isinstance(val, list):
            continue
        for offer in val:
            if not isinstance(offer, dict):
                continue
            label = offer.get("label")
            cost = offer.get("cost_usd")
            if label and cost:
                cost_map[label] = float(cost)
    return cost_map


def collect_priced_offers() -> list:
    """يجمع كل العروض اللي فيها product_id+cost_usd من الموديول.
    يرجع قائمة [{id, product_id, cost_usd, label, source, enabled, raw_offer}].
    """
    import sys
    mod = sys.modules[__name__]
    seen: set = set()  # لتفادي تكرار نفس product_id
    result: list = []

    # 1) كل قوائم _OFFERS و _MEMBERSHIPS و _CODES
    for name in dir(mod):
        if not (name.endswith("_OFFERS") or name.endswith("_MEMBERSHIPS") or name.endswith("_CODES")):
            continue
        val = getattr(mod, name, None)
        if not isinstance(val, list):
            continue
        for offer in val:
            if not isinstance(offer, dict):
                continue
            pid = offer.get("product_id")
            cost = offer.get("cost_usd")
            label = offer.get("label", "?")
            if not pid or not cost:
                continue
            try:
                pid_int = int(pid)
            except (ValueError, TypeError):
                continue
            if pid_int in seen:
                continue
            seen.add(pid_int)
            result.append({
                "id": offer.get("id"),
                "product_id": pid_int,
                "cost_usd": float(cost),
                "label": label,
                "source": name,
                "enabled": offer.get("enabled", True),
                "raw_offer": offer,
            })

    # 2) قوائم Fastcard من FASTCARD_CATEGORIES (offers_attr يشير للقائمة)
    cats = getattr(mod, "FASTCARD_CATEGORIES", {})
    if isinstance(cats, dict):
        for prefix, cat in cats.items():
            attr = cat.get("offers_attr") if isinstance(cat, dict) else None
            if not attr:
                continue
            offers = getattr(mod, attr, None)
            if not isinstance(offers, list):
                continue
            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                pid = offer.get("product_id")
                cost = offer.get("cost_usd")
                label = offer.get("label", "?")
                if not pid or not cost:
                    continue
                try:
                    pid_int = int(pid)
                except (ValueError, TypeError):
                    continue
                if pid_int in seen:
                    continue
                seen.add(pid_int)
                result.append({
                    "id": offer.get("id"),
                    "product_id": pid_int,
                    "cost_usd": float(cost),
                    "label": label,
                    "source": f"FC:{prefix}",
                    "enabled": offer.get("enabled", True),
                    "raw_offer": offer,
                })
    return result


# Backward-compat: ثابت قديم — كل الاستخدامات النشطة استبدلت بـ get_usd_to_syp().
USD_TO_SYP = DEFAULT_USD_TO_SYP

PUBG_UC_OFFERS = [
    {"id": "uc_60",    "label": "60 شدة",                "uc": 60,   "price": 15000,  "product_id": 2832, "cost_usd": 0.902466, "manual_price": True},
    {"id": "uc_60v",   "label": "60 شدة (تحقق من الاسم)", "uc": 60,   "price": 15500,  "product_id": 7806, "cost_usd": 0.85,     "manual_price": True, "verify": True},
    {"id": "uc_325",  "label": "325 شدة",  "uc": 325,  "price": 73500,  "product_id": 2833, "cost_usd": 4.43372, "manual_price": True},
    {"id": "uc_660",  "label": "660 شدة",  "uc": 660,  "price": 146500, "product_id": 2834, "cost_usd": 8.86744, "manual_price": True},
    {"id": "uc_1800", "label": "1800 شدة", "uc": 1800, "price": 365500, "product_id": 2835, "cost_usd": 22.1686, "manual_price": True},
]

# عروض جواهر فري فاير — شحن تلقائي عبر Fastcard (سيرفر اوتو 1)
FREEFIRE_DIAMOND_OFFERS = [
    {"id": "ff_110",  "label": "100 + 10 جوهرة",   "diamonds": 110,  "price": 15500,  "product_id": 7709, "cost_usd": 0.94127, "manual_price": True},
    {"id": "ff_231",  "label": "210 + 21 جوهرة",   "diamonds": 231,  "price": 31000,  "product_id": 7710, "cost_usd": 1.88254, "manual_price": True},
    {"id": "ff_583",  "label": "530 + 53 جوهرة",   "diamonds": 583,  "price": 77500,  "product_id": 7711, "cost_usd": 4.706351, "manual_price": True},
    {"id": "ff_1188", "label": "1080 + 108 جوهرة", "diamonds": 1188, "price": 155000, "product_id": 7712, "cost_usd": 9.412701, "manual_price": True},
    {"id": "ff_2420", "label": "2200 + 220 جوهرة", "diamonds": 2420, "price": 310000, "product_id": 7713, "cost_usd": 18.825401, "manual_price": True},
]

# فري فاير سيرفر 2 — شحن تلقائي
FREEFIRE_S2_OFFERS = [
    {"id": "ff_s2_110",  "label": "100 + 10 جوهرة (سيرفر 2)",   "price": 14000,  "product_id": 7642, "cost_usd": 0.95,   "enabled": True},
    {"id": "ff_s2_231",  "label": "210 + 21 جوهرة (سيرفر 2)",   "price": 28000,  "product_id": 7643, "cost_usd": 1.899,  "enabled": True},
    {"id": "ff_s2_583",  "label": "530 + 53 جوهرة (سيرفر 2)",   "price": 70000,  "product_id": 7644, "cost_usd": 4.75,   "enabled": True},
    {"id": "ff_s2_1188", "label": "1080 + 108 جوهرة (سيرفر 2)", "price": 140000, "product_id": 7645, "cost_usd": 9.5,    "enabled": True},
    {"id": "ff_s2_2420", "label": "2200 + 220 جوهرة (سيرفر 2)", "price": 280000, "product_id": 7646, "cost_usd": 18.981, "enabled": True},
]

# فري فاير أوروبا — شحن تلقائي
FREEFIRE_EU_OFFERS = [
    {"id": "ff_eu_100",   "label": "100 جوهرة (أوروبا)",            "price": 14500,   "product_id": 7793, "cost_usd": 0.968,   "enabled": True},
    {"id": "ff_eu_310",   "label": "310 جوهرة (أوروبا)",            "price": 43500,   "product_id": 7794, "cost_usd": 2.925,   "enabled": True},
    {"id": "ff_eu_520",   "label": "520 جوهرة (أوروبا)",            "price": 66500,   "product_id": 7795, "cost_usd": 4.5,     "enabled": True},
    {"id": "ff_eu_1060",  "label": "1060 جوهرة (أوروبا)",           "price": 133000,  "product_id": 7796, "cost_usd": 9.0,     "enabled": True},
    {"id": "ff_eu_2180",  "label": "2180 جوهرة (أوروبا)",           "price": 270500,  "product_id": 7797, "cost_usd": 18.337,  "enabled": True},
    {"id": "ff_eu_5600",  "label": "5600 جوهرة (أوروبا)",           "price": 647500,  "product_id": 7798, "cost_usd": 43.874,  "enabled": True},
    {"id": "ff_eu_wk",    "label": "عضوية أسبوعية (أوروبا)",        "price": 5000,    "product_id": 7800, "cost_usd": 0.315,   "enabled": True},
    {"id": "ff_eu_wkmem", "label": "عضوية أسبوعية VIP (أوروبا)",   "price": 29000,   "product_id": 7801, "cost_usd": 1.913,   "enabled": True},
    {"id": "ff_eu_mo",    "label": "عضوية شهرية (أوروبا)",          "price": 133000,  "product_id": 7802, "cost_usd": 8.978,   "enabled": True},
    {"id": "ff_eu_ev3",   "label": "Evo Access 3D (أوروبا)",        "price": 9500,    "product_id": 7803, "cost_usd": 0.63,    "enabled": True},
    {"id": "ff_eu_ev7",   "label": "Evo Access 7D (أوروبا)",        "price": 14000,   "product_id": 7804, "cost_usd": 0.945,   "enabled": True},
    {"id": "ff_eu_ev30",  "label": "Evo Access 30D (أوروبا)",       "price": 37000,   "product_id": 7805, "cost_usd": 2.475,   "enabled": True},
]

# ===== أقسام تلقائية إضافية (Fastcard) =====
# كل عرض: id (داخلي), label, price (ل.س), product_id (Fastcard), cost_usd, enabled
# الحقول المطلوبة من المستخدم تتعرّف بـ input_fields داخل FASTCARD_CATEGORIES
PUBG_MEMBERSHIPS = [
    {"id": "pm_first",  "label": "🛒 حزمة الشراء الأول",          "price": 14500,    "product_id": 7756, "cost_usd": 0.8676,   "manual_price": True, "enabled": True},
    {"id": "pm_arms",   "label": "🔫 حزمة مواد أسلحة نارية",       "price": 43000,    "product_id": 7766, "cost_usd": 2.6029,   "manual_price": True, "enabled": True},
    {"id": "pm_logo",   "label": "🏆 حزمة الشعار الأسطوري",        "price": 71500,    "product_id": 7757, "cost_usd": 4.3372,   "manual_price": True, "enabled": True},
    {"id": "pm_p1",     "label": "👑 Prime — شهر",                "price": 14500,    "product_id": 7758, "cost_usd": 0.8676,   "manual_price": True, "enabled": True},
    {"id": "pm_p3",     "label": "👑 Prime — 3 شهور",             "price": 43000,    "product_id": 7760, "cost_usd": 2.6029,   "manual_price": True, "enabled": True},
    {"id": "pm_p6",     "label": "👑 Prime — 6 شهور",             "price": 86000,    "product_id": 7761, "cost_usd": 5.2048,   "manual_price": True, "enabled": True},
    {"id": "pm_p12",    "label": "👑 Prime — سنة كاملة",          "price": 171500,   "product_id": 7759, "cost_usd": 10.4167,  "manual_price": True, "enabled": True},
    {"id": "pm_pp1",    "label": "💎 Prime Plus — شهر",           "price": 143000,   "product_id": 7762, "cost_usd": 8.6814,   "manual_price": True, "enabled": True},
    {"id": "pm_pp3",    "label": "💎 Prime Plus — 3 شهور",        "price": 429000,   "product_id": 7764, "cost_usd": 26.0362,  "manual_price": True, "enabled": True},
    {"id": "pm_pp6",    "label": "💎 Prime Plus — 6 شهور",        "price": 857500,   "product_id": 7765, "cost_usd": 52.0803,  "manual_price": True, "enabled": True},
    {"id": "pm_pp12",   "label": "💎 Prime Plus — سنة كاملة",     "price": 1715000,  "product_id": 7763, "cost_usd": 104.1606, "manual_price": True, "enabled": True},
    {"id": "pm_ep50",   "label": "🎟️ Elite Pass LV1-50",          "price": 80500,    "product_id": 7754, "cost_usd": 4.8636,   "manual_price": True, "enabled": True},
    {"id": "pm_ep100",  "label": "🎟️ Elite Pass LV1-100",         "price": 160500,   "product_id": 7753, "cost_usd": 9.7192,   "manual_price": True, "enabled": True},
    {"id": "pm_epp100", "label": "🎟️ Elite Pass Plus LV1-100",    "price": 400500,   "product_id": 7755, "cost_usd": 24.3098,  "manual_price": True, "enabled": True},
    {"id": "pm_wd1",    "label": "📅 Weekly Deal Pack 1",         "price": 15000,    "product_id": 7767, "cost_usd": 0.8836,   "manual_price": True, "enabled": True},
    {"id": "pm_wd2",    "label": "📅 Weekly Deal Pack 2",         "price": 44000,    "product_id": 7768, "cost_usd": 2.6427,   "manual_price": True, "enabled": True},
    {"id": "pm_wmy",    "label": "📅 Weekly Mythic Emblem",        "price": 44000,    "product_id": 7769, "cost_usd": 2.6427,   "manual_price": True, "enabled": True},
]

FREEFIRE_MEMBERSHIPS = [
    {"id": "fm_wk",     "label": "📅 عضوية أسبوعية",              "price": 35500,    "product_id": 6228, "cost_usd": 2.15,     "manual_price": True, "enabled": True},
    {"id": "fm_mo",     "label": "👑 عضوية شهرية",                "price": 170000,   "product_id": 6229, "cost_usd": 10.3,     "manual_price": True, "enabled": True},
    {"id": "fm_mo2",    "label": "👑 عضوية شهرية (سيرفر 2)",      "price": 130000,   "product_id": 7647, "cost_usd": 7.89,     "manual_price": True, "enabled": True},
    {"id": "fm_lvl6",   "label": "🎖️ تصريح لفل 6",                "price": 10000,     "product_id": 7085, "cost_usd": 0.6,      "manual_price": True, "enabled": True},
    {"id": "fm_lvl10",  "label": "🎖️ تصريح لفل 10",               "price": 15000,    "product_id": 7086, "cost_usd": 0.9,      "manual_price": True, "enabled": True},
    {"id": "fm_lvl15",  "label": "🎖️ تصريح لفل 15",               "price": 15000,    "product_id": 7087, "cost_usd": 0.9,      "manual_price": True, "enabled": True},
    {"id": "fm_lvl20",  "label": "🎖️ تصريح لفل 20",               "price": 15000,    "product_id": 7088, "cost_usd": 0.9,      "manual_price": True, "enabled": True},
    {"id": "fm_lvl25",  "label": "🎖️ تصريح لفل 25",               "price": 15000,    "product_id": 7089, "cost_usd": 0.9,      "manual_price": True, "enabled": True},
    {"id": "fm_lvl30",  "label": "🎖️ تصريح لفل 30",               "price": 22500,    "product_id": 7090, "cost_usd": 1.35,     "manual_price": True, "enabled": True},
    {"id": "fm_boyah",  "label": "🎫 Boyah Pass Card",            "price": 53000,    "product_id": 7091, "cost_usd": 3.2,      "manual_price": True, "enabled": True},
]

# أكواد ببجي — من المخزون. لا يحتاج Player ID
PUBG_CODES = [
    {"id": "pc_60",   "label": "🎟️ كود 60 شدة",     "price": 15500,   "product_id": 7783, "cost_usd": 0.9139,  "manual_price": True, "enabled": True},
    {"id": "pc_60p",  "label": "🎟️ كود 60 شدة (بكج)", "price": 15500,   "product_id": 2843, "cost_usd": 0.92,    "manual_price": True, "enabled": True},
    {"id": "pc_325",  "label": "🎟️ كود 325 شدة",    "price": 75500,   "product_id": 2844, "cost_usd": 4.5641,  "manual_price": True, "enabled": True},
    {"id": "pc_660",  "label": "🎟️ كود 660 شدة",    "price": 150500,  "product_id": 2845, "cost_usd": 9.1271,  "manual_price": True, "enabled": True},
    {"id": "pc_1800", "label": "🎟️ كود 1800 شدة",   "price": 376000,  "product_id": 2846, "cost_usd": 22.8173, "manual_price": True, "enabled": True},
    {"id": "pc_3850", "label": "🎟️ كود 3850 شدة",   "price": 751500,  "product_id": 2847, "cost_usd": 45.6337, "manual_price": True, "enabled": True},
    {"id": "pc_8100", "label": "🎟️ كود 8100 شدة",   "price": 1503000, "product_id": 2848, "cost_usd": 91.2664, "manual_price": True, "enabled": True},
]

# أكواد فري فاير — من المخزون. ⚠️ كل العروض حالياً نافد مخزونها (enabled=False)
FREEFIRE_CODES = [
    {"id": "fc_231",  "label": "🎟️ كود 231 جوهرة",  "price": 27500,   "product_id": 4246, "cost_usd": 1.8688,  "enabled": True},
    {"id": "fc_583",  "label": "🎟️ كود 583 جوهرة",  "price": 68500,   "product_id": 7143, "cost_usd": 4.6721,  "enabled": True},
    {"id": "fc_1188", "label": "🎟️ كود 1188 جوهرة", "price": 137000,  "product_id": 7144, "cost_usd": 9.3442,  "enabled": True},
    {"id": "fc_2420", "label": "🎟️ كود 2420 جوهرة", "price": 274000,  "product_id": 7145, "cost_usd": 18.6885, "enabled": True},
]

# ===== ألعاب Supercell (شحن مباشر بالإيميل والباسورد) =====
# هذه الألعاب تتطلب: الإيميل، كلمة المرور، رقم واتساب — ويتم الشحن على حساب اللاعب مباشرة
BRAWL_STARS_OFFERS = [
    {"id": "bs_30",    "label": "💎 30 جوهرة",    "price": 34000,    "product_id": 7181, "cost_usd": 2.0537,   "manual_price": True, "enabled": True},
    {"id": "bs_80",    "label": "💎 80 جوهرة",    "price": 85000,    "product_id": 7182, "cost_usd": 5.1342,   "manual_price": True, "enabled": True},
    {"id": "bs_170",   "label": "💎 170 جوهرة",   "price": 169500,   "product_id": 7183, "cost_usd": 10.2684,  "manual_price": True, "enabled": True},
    {"id": "bs_360",   "label": "💎 360 جوهرة",   "price": 338500,   "product_id": 7184, "cost_usd": 20.5368,  "manual_price": True, "enabled": True},
    {"id": "bs_950",   "label": "💎 950 جوهرة",   "price": 845500,   "product_id": 7185, "cost_usd": 51.342,   "manual_price": True, "enabled": True},
    {"id": "bs_2000",  "label": "💎 2000 جوهرة",  "price": 1691000,  "product_id": 7186, "cost_usd": 102.684,  "manual_price": True, "enabled": True},
    {"id": "bs_pass",  "label": "🎫 براول باس عادي", "price": 207500, "product_id": 7187, "cost_usd": 12.6,     "manual_price": True, "enabled": True},
    {"id": "bs_pass+", "label": "🎫 براول باس بلس",  "price": 273000, "product_id": 7188, "cost_usd": 16.56,    "manual_price": True, "enabled": True},
]

CLASH_OF_CLANS_OFFERS = [
    {"id": "coc_80",     "label": "💎 80 جوهرة",      "price": 17000,    "product_id": 7097, "cost_usd": 1.0268,   "manual_price": True, "enabled": True},
    {"id": "coc_500",    "label": "💎 500 جوهرة",     "price": 85000,    "product_id": 7098, "cost_usd": 5.1342,   "manual_price": True, "enabled": True},
    {"id": "coc_1200",   "label": "💎 1200 جوهرة",    "price": 169500,   "product_id": 7099, "cost_usd": 10.2684,  "manual_price": True, "enabled": True},
    {"id": "coc_2500",   "label": "💎 2500 جوهرة",    "price": 338500,   "product_id": 7100, "cost_usd": 20.5368,  "manual_price": True, "enabled": True},
    {"id": "coc_6500",   "label": "💎 6500 جوهرة",    "price": 845500,   "product_id": 7101, "cost_usd": 51.342,   "manual_price": True, "enabled": True},
    {"id": "coc_14000",  "label": "💎 14000 جوهرة",   "price": 1691000,  "product_id": 7102, "cost_usd": 102.684,  "manual_price": True, "enabled": True},
    {"id": "coc_gold",   "label": "🎫 تذكرة ذهبية",   "price": 118500,   "product_id": 7103, "cost_usd": 7.1879,   "manual_price": True, "enabled": True},
]

CLASH_ROYALE_OFFERS = [
    {"id": "cr_80",     "label": "💎 80 جوهرة",      "price": 17000,    "product_id": 7189, "cost_usd": 1.0268,   "manual_price": True, "enabled": True},
    {"id": "cr_500",    "label": "💎 500 جوهرة",     "price": 85000,    "product_id": 7190, "cost_usd": 5.1342,   "manual_price": True, "enabled": True},
    {"id": "cr_1200",   "label": "💎 1200 جوهرة",    "price": 169500,   "product_id": 7191, "cost_usd": 10.2684,  "manual_price": True, "enabled": True},
    {"id": "cr_2500",   "label": "💎 2500 جوهرة",    "price": 338500,   "product_id": 7192, "cost_usd": 20.5368,  "manual_price": True, "enabled": True},
    {"id": "cr_6500",   "label": "💎 6500 جوهرة",    "price": 845500,   "product_id": 7193, "cost_usd": 51.342,   "manual_price": True, "enabled": True},
    {"id": "cr_14000",  "label": "💎 14000 جوهرة",   "price": 1691000,  "product_id": 7194, "cost_usd": 102.684,  "manual_price": True, "enabled": True},
    {"id": "cr_pass",   "label": "🎫 باس رويال",     "price": 255500,   "product_id": 7195, "cost_usd": 15.5,     "manual_price": True, "enabled": True},
]

# Hay Day — كل العروض حالياً نافد مخزونها (enabled=False) — جاهزين للتفعيل لما يرجعوا
HAY_DAY_OFFERS = [
    {"id": "hd_50",    "label": "💎 50 جوهرة",    "price": 12000,    "product_id": 7196, "cost_usd": 0.8215,   "enabled": True},
    {"id": "hd_130",   "label": "💎 130 جوهرة",   "price": 30500,    "product_id": 7197, "cost_usd": 2.0537,   "enabled": True},
    {"id": "hd_275",   "label": "💎 275 جوهرة",   "price": 60500,    "product_id": 7198, "cost_usd": 4.1074,   "enabled": True},
    {"id": "hd_570",   "label": "💎 570 جوهرة",   "price": 121000,   "product_id": 7199, "cost_usd": 8.2147,   "enabled": True},
    {"id": "hd_1500",  "label": "💎 1500 جوهرة",  "price": 241500,   "product_id": 7200, "cost_usd": 16.4294,  "enabled": True},
    {"id": "hd_4000",  "label": "💎 4000 جوهرة",  "price": 603000,   "product_id": 7201, "cost_usd": 41.0736,  "enabled": True},
    {"id": "hd_pass",  "label": "🎫 فارم باس",    "price": 91000,    "product_id": 7202, "cost_usd": 6.161,    "enabled": True},
]

# الحقول القياسية لطلبات Supercell
SUPERCELL_FIELDS = [
    {"key": "الايميل", "label": "الإيميل تبع حساب Supercell ID", "type": "email"},
    {"key": "كلمة المرور", "label": "كلمة المرور", "type": "password", "sensitive": True},
    {"key": "رقم واتساب", "label": "رقم الواتساب (للتواصل عند الحاجة)", "type": "phone"},
]

# ============= COD / Delta / Minecraft / Fortnite / Ludo =============

# Call of Duty Mobile - شدات (تتطلب Player ID + إيميل + رقم واتساب) ✅ كلها متوفرة
COD_OFFERS = [
    {"id": "cod_160",   "label": "💎 80 + 80 نقطة",       "price": 17000,    "product_id": 3173, "cost_usd": 1.02684,  "manual_price": True, "enabled": True},
    {"id": "cod_460",   "label": "💎 400 + 60 نقطة",      "price": 68000,    "product_id": 3174, "cost_usd": 4.10736,  "manual_price": True, "enabled": True},
    {"id": "cod_960",   "label": "💎 800 + 160 نقطة",     "price": 135500,   "product_id": 3175, "cost_usd": 8.21472,  "manual_price": True, "enabled": True},
    {"id": "cod_2600",  "label": "💎 2000 + 600 نقطة",    "price": 338500,   "product_id": 3176, "cost_usd": 20.5368,  "manual_price": True, "enabled": True},
    {"id": "cod_5400",  "label": "💎 4000 + 1400 نقطة",   "price": 676500,   "product_id": 3177, "cost_usd": 41.0736,  "manual_price": True, "enabled": True},
    {"id": "cod_11600", "label": "💎 8000 + 3600 نقطة",   "price": 1691000,  "product_id": 3178, "cost_usd": 102.684,  "manual_price": True, "enabled": True},
]

# Call of Duty Mobile - Battle Pass (يطلب Player ID فقط)
COD_PASS_OFFERS = [
    {"id": "codbp_basic",  "label": "🎫 Battle Pass",         "price": 85000,  "product_id": 3179, "cost_usd": 5.142161, "manual_price": True, "enabled": True},
    {"id": "codbp_bundle", "label": "🎫 Battle Pass Bundle",  "price": 207000, "product_id": 3180, "cost_usd": 12.56884, "manual_price": True, "enabled": True},
]

# الحقول المطلوبة لشدات COD - حسب Fastcard: Player ID + الايميل + رقم واتساب
COD_FIELDS = [
    {"key": "playerId",      "label": "Player ID (الرقم داخل اللعبة - من شاشة الحساب)", "type": "id"},
    {"key": "الايميل",       "label": "الإيميل المرتبط بحساب Call of Duty",              "type": "email"},
    {"key": "رقم واتساب",    "label": "رقم الواتساب (للتواصل عند الحاجة)",                "type": "phone"},
]

# Delta Force - شدات وعروض (تتطلب الايدي فقط)
DELTA_FORCE_OFFERS = [
    {"id": "df_60",    "label": "🪙 60 Coins",                          "price": 21500,    "product_id": 3214, "cost_usd": 1.29549,   "manual_price": True, "enabled": True},
    {"id": "df_320",   "label": "🪙 320 Coins",                         "price": 65000,    "product_id": 3215, "cost_usd": 3.92627,   "manual_price": True, "enabled": True},
    {"id": "df_460",   "label": "🪙 460 Coins",                         "price": 93500,    "product_id": 3216, "cost_usd": 5.674486,  "manual_price": True, "enabled": True},
    {"id": "df_750",   "label": "🪙 750 Coins",                         "price": 129000,   "product_id": 3217, "cost_usd": 7.81075,   "manual_price": True, "enabled": True},
    {"id": "df_1480",  "label": "🪙 1480 Coins",                        "price": 258000,   "product_id": 3218, "cost_usd": 15.66329,  "manual_price": True, "enabled": True},
    {"id": "df_1980",  "label": "🪙 1980 Coins",                        "price": 321500,   "product_id": 3219, "cost_usd": 19.526875, "manual_price": True, "enabled": True},
    {"id": "df_3950",  "label": "🪙 3950 Coins",                        "price": 641500,   "product_id": 3220, "cost_usd": 38.947285, "manual_price": True, "enabled": True},
    {"id": "df_8100",  "label": "🪙 8100 Coins",                        "price": 1261000,  "product_id": 3221, "cost_usd": 76.58117,  "manual_price": True, "enabled": True},
    {"id": "df_bhd1",  "label": "🎟️ بلاك هوك داون - التكوين",            "price": 59000,    "product_id": 3222, "cost_usd": 3.561105,  "manual_price": True, "enabled": True},
    {"id": "df_bhd2",  "label": "🎟️ بلاك هوك داون - إعادة التشكيل",       "price": 107000,    "product_id": 3223, "cost_usd": 6.474465,  "manual_price": True, "enabled": True},
    {"id": "df_sg1",   "label": "🎒 إمدادات الحارس الصامت",              "price": 22000,    "product_id": 3224, "cost_usd": 1.31738,   "manual_price": True, "enabled": True},
    {"id": "df_sg2",   "label": "🎒 إمدادات الحارس الصامت متقدم",        "price": 39500,    "product_id": 3225, "cost_usd": 2.39596,   "manual_price": True, "enabled": True},
]

# Minecraft - أكواد جاهزة (ما بدها أي حقول)
MINECRAFT_OFFERS = [
    {"id": "mc_1720", "label": "🪙 كود 1720 كوينز ماين كرافت", "price": 149500, "product_id": 4069, "cost_usd": 9.069425,  "manual_price": True, "enabled": True},
    {"id": "mc_3500", "label": "🪙 كود 3500 كوينز ماين كرافت", "price": 299000, "product_id": 4217, "cost_usd": 18.149795, "manual_price": True, "enabled": True},
]

# Fortnite - أكواد V-Bucks (ما بدها حقول)
FORTNITE_OFFERS = [
    {"id": "fn_1000", "label": "💎 بطاقة 1000 V-Bucks", "price": 206000, "product_id": 3888, "cost_usd": 12.508145, "manual_price": True, "enabled": True},
    {"id": "fn_2800", "label": "💎 بطاقة 2800 V-Bucks", "price": 408500, "product_id": 3889, "cost_usd": 24.796395, "manual_price": True, "enabled": True},
    {"id": "fn_5000", "label": "💎 بطاقة 5000 V-Bucks", "price": 653500, "product_id": 3890, "cost_usd": 39.680601, "manual_price": True, "enabled": True},
]

# Ludo World - شحن مباشر بالايدي
LUDO_WORLD_OFFERS = [
    {"id": "lw_10k", "label": "🪙 10,000 كوينز", "price": 18000, "product_id": 6998, "cost_usd": 1.063655, "manual_price": True, "enabled": True},
    {"id": "lw_30k", "label": "🪙 30,000 كوينز", "price": 35500, "product_id": 6999, "cost_usd": 2.126315, "manual_price": True, "enabled": True},
    {"id": "lw_70k", "label": "🪙 70,000 كوينز", "price": 70500, "product_id": 7000, "cost_usd": 4.27452,  "manual_price": True, "enabled": True},
]

# Ludo Club - شحن مباشر بالايدي
LUDO_CLUB_OFFERS = [
    {"id": "lc_1m3",  "label": "🪙 1.3M Coins",  "price": 11500,  "product_id": 3250, "cost_usd": 0.69849,  "manual_price": True, "enabled": True},
    {"id": "lc_3m3",  "label": "🪙 3.3M Coins",  "price": 23000,  "product_id": 3251, "cost_usd": 1.376085, "manual_price": True, "enabled": True},
    {"id": "lc_13m5", "label": "🪙 13.5M Coins", "price": 120500, "product_id": 3252, "cost_usd": 7.296335, "manual_price": True, "enabled": True},
    {"id": "lc_70m",  "label": "🪙 70M Coins",   "price": 163500, "product_id": 3253, "cost_usd": 9.90224,  "manual_price": True, "enabled": True},
]

# YALLA Ludo - شحن مباشر بالايدي
LUDO_YALLA_OFFERS = [
    {"id": "yl_830",   "label": "💎 830 الماس",   "price": 32000,   "product_id": 3108, "cost_usd": 1.919356,  "manual_price": True, "enabled": True},
    {"id": "yl_2320",  "label": "💎 2320 الماس",  "price": 79000,   "product_id": 3109, "cost_usd": 4.771025,  "manual_price": True, "enabled": True},
    {"id": "yl_5150",  "label": "💎 5150 الماس",  "price": 156500,  "product_id": 3110, "cost_usd": 9.49429,   "manual_price": True, "enabled": True},
    {"id": "yl_13580", "label": "💎 13,580 الماس", "price": 391000,  "product_id": 3111, "cost_usd": 23.73473,  "manual_price": True, "enabled": True},
    {"id": "yl_27800", "label": "💎 27,800 الماس", "price": 782000,  "product_id": 3112, "cost_usd": 47.468465, "manual_price": True, "enabled": True},
    {"id": "yl_55800", "label": "💎 55,800 الماس", "price": 1563500, "product_id": 3113, "cost_usd": 94.935935, "manual_price": True, "enabled": True},
]

# ===== ألعاب جديدة =====

# Roblox — بطاقات هدايا (أكواد جاهزة)
ROBLOX_USA_OFFERS = [
    {"id": "rblx_us_10",  "label": "🎮 Roblox USA 10$",  "price": 143000,  "product_id": 3763, "cost_usd": 9.69,    "enabled": True},
    {"id": "rblx_us_15",  "label": "🎮 Roblox USA 15$",  "price": 214500,  "product_id": 3764, "cost_usd": 14.535,  "enabled": True},
    {"id": "rblx_us_20",  "label": "🎮 Roblox USA 20$",  "price": 286000,  "product_id": 3765, "cost_usd": 19.38,   "enabled": True},
    {"id": "rblx_us_25",  "label": "🎮 Roblox USA 25$",  "price": 357500,  "product_id": 3766, "cost_usd": 24.225,  "enabled": True},
    {"id": "rblx_us_50",  "label": "🎮 Roblox USA 50$",  "price": 715000,  "product_id": 3767, "cost_usd": 48.449,  "enabled": True},
    {"id": "rblx_us_100", "label": "🎮 Roblox USA 100$", "price": 1430000, "product_id": 3768, "cost_usd": 96.897,  "enabled": True},
]

ROBLOX_KSA_OFFERS = [
    {"id": "rblx_ksa_20",  "label": "🎮 Roblox KSA 20 SAR",  "price": 79500,   "product_id": 3769, "cost_usd": 5.385,   "enabled": True},
    {"id": "rblx_ksa_50",  "label": "🎮 Roblox KSA 50 SAR",  "price": 199000,  "product_id": 3770, "cost_usd": 13.472,  "enabled": True},
    {"id": "rblx_ksa_100", "label": "🎮 Roblox KSA 100 SAR", "price": 398000,  "product_id": 3771, "cost_usd": 26.964,  "enabled": True},
    {"id": "rblx_ksa_200", "label": "🎮 Roblox KSA 200 SAR", "price": 796000,  "product_id": 3772, "cost_usd": 53.906,  "enabled": True},
]

ROBLOX_UAE_OFFERS = [
    {"id": "rblx_ae_20",  "label": "🎮 Roblox UAE 20 AED",  "price": 81000,   "product_id": 3774, "cost_usd": 5.49,    "enabled": True},
    {"id": "rblx_ae_50",  "label": "🎮 Roblox UAE 50 AED",  "price": 202500,  "product_id": 3775, "cost_usd": 13.734,  "enabled": True},
    {"id": "rblx_ae_100", "label": "🎮 Roblox UAE 100 AED", "price": 405500,  "product_id": 3776, "cost_usd": 27.467,  "enabled": True},
    {"id": "rblx_ae_200", "label": "🎮 Roblox UAE 200 AED", "price": 811000,  "product_id": 3777, "cost_usd": 54.944,  "enabled": True},
]

# Valorant — بطاقات VP (أكواد جاهزة)
VALORANT_GLOBAL_OFFERS = [
    {"id": "valo_gl_475",  "label": "🔫 Valorant 475 VP — 5$",   "price": 69500,   "product_id": 4195, "cost_usd": 4.714,  "enabled": True},
    {"id": "valo_gl_1000", "label": "🔫 Valorant 1000 VP — 10$", "price": 139000,  "product_id": 4196, "cost_usd": 9.428,  "enabled": True},
    {"id": "valo_gl_2050", "label": "🔫 Valorant 2050 VP — 20$", "price": 278500,  "product_id": 4197, "cost_usd": 18.856, "enabled": True},
    {"id": "valo_gl_2600", "label": "🔫 Valorant 2600 VP — 25$", "price": 348000,  "product_id": 4198, "cost_usd": 23.57,  "enabled": True},
    {"id": "valo_gl_5350", "label": "🔫 Valorant 5350 VP — 50$", "price": 696000,  "product_id": 4199, "cost_usd": 47.139, "enabled": True},
    {"id": "valo_gl_8650", "label": "🔫 Valorant 8650 VP — 80$", "price": 1138000, "product_id": 4200, "cost_usd": 77.038, "enabled": True},
]

VALORANT_TR_OFFERS = [
    {"id": "valo_tr_115",  "label": "🔫 Valorant 115 VP (تركي)",  "price": 13500,  "product_id": 7807, "cost_usd": 0.916,  "enabled": True},
    {"id": "valo_tr_375",  "label": "🔫 Valorant 375 VP (تركي)",  "price": 39500,  "product_id": 7808, "cost_usd": 2.678,  "enabled": True},
    {"id": "valo_tr_825",  "label": "🔫 Valorant 825 VP (تركي)",  "price": 82500,  "product_id": 7809, "cost_usd": 5.594,  "enabled": True},
    {"id": "valo_tr_1700", "label": "🔫 Valorant 1700 VP (تركي)", "price": 169000, "product_id": 7810, "cost_usd": 11.462, "enabled": True},
    {"id": "valo_tr_2925", "label": "🔫 Valorant 2925 VP (تركي)", "price": 281000, "product_id": 7811, "cost_usd": 19.038, "enabled": True},
]

# Blood Strike — شحن مباشر بالايدي
BLOOD_STRIKE_OFFERS = [
    {"id": "bsk_320",  "label": "💀 320 Gold",    "price": 46000,   "product_id": 3201, "cost_usd": 3.096,  "enabled": True},
    {"id": "bsk_540",  "label": "💀 540 Gold",    "price": 76500,   "product_id": 3202, "cost_usd": 5.16,   "enabled": True},
    {"id": "bsk_1100", "label": "💀 1100 Gold",   "price": 152500,  "product_id": 3203, "cost_usd": 10.32,  "enabled": True},
    {"id": "bsk_2260", "label": "💀 2260 Gold",   "price": 305000,  "product_id": 3204, "cost_usd": 20.64,  "enabled": True},
    {"id": "bsk_5800", "label": "💀 5800 Gold",   "price": 762500,  "product_id": 3205, "cost_usd": 51.6,   "enabled": True},
    {"id": "bsk_ep",   "label": "🎟️ Elite Pass",  "price": 61000,   "product_id": 3206, "cost_usd": 4.128,  "enabled": True},
    {"id": "bsk_pp",   "label": "🎟️ Premium Pass", "price": 137500, "product_id": 3207, "cost_usd": 9.288,  "enabled": True},
]

# Stumble Guys — شحن مباشر بالايدي
STUMBLE_GUYS_OFFERS = [
    {"id": "stmb_800",   "label": "🎮 800 Gams",          "price": 31500,  "product_id": 7073, "cost_usd": 2.1156,   "enabled": True},
    {"id": "stmb_1600",  "label": "🎮 1600 + 75 Tokens",  "price": 52500,  "product_id": 7074, "cost_usd": 3.53976,  "enabled": True},
    {"id": "stmb_5000",  "label": "🎮 5000 + 275 Tokens", "price": 130000, "product_id": 7075, "cost_usd": 8.76168,  "enabled": True},
    {"id": "stmb_120t",  "label": "🎟️ 120 Tokens",        "price": 38500,  "product_id": 7076, "cost_usd": 2.59032,  "enabled": True},
    {"id": "stmb_1300t", "label": "🎟️ 1300 Tokens",       "price": 315500, "product_id": 7077, "cost_usd": 21.34176, "enabled": True},
]

# Super Sus — شحن مباشر بالايدي
SUPER_SUS_OFFERS = [
    {"id": "ssus_100",  "label": "🛸 GoldStar رمز 100",  "price": 41000,  "product_id": 7052, "cost_usd": 2.76576,  "enabled": True},
    {"id": "ssus_520",  "label": "🛸 GoldStar 520",      "price": 68000,  "product_id": 7053, "cost_usd": 4.61304,  "enabled": True},
    {"id": "ssus_1060", "label": "🛸 GoldStar 1060",     "price": 136500, "product_id": 7054, "cost_usd": 9.24672,  "enabled": True},
    {"id": "ssus_2180", "label": "🛸 GoldStar 2180",     "price": 273000, "product_id": 7055, "cost_usd": 18.4728,  "enabled": True},
    {"id": "ssus_5600", "label": "🛸 GoldStar 5600",     "price": 681500, "product_id": 7056, "cost_usd": 46.09944, "enabled": True},
]


# ===== اشتراكات تطبيقات (Apps Subscriptions) =====
SPOTIFY_OFFERS = [
    {"id": "spfy_7266", "label": "🎵 سبوتيفاي — شهر",     "price": 65500,  "product_id": 7266, "cost_usd": 4.415,  "enabled": True},
    {"id": "spfy_7267", "label": "🎵 سبوتيفاي — شهران",   "price": 153000, "product_id": 7267, "cost_usd": 10.343, "enabled": True},
    {"id": "spfy_7268", "label": "🎵 سبوتيفاي — 6 أشهر",  "price": 284000, "product_id": 7268, "cost_usd": 19.206, "enabled": True},
]

SHAHID_OFFERS = [
    {"id": "sh_3298", "label": "📺 شاهد VIP — شهر / جهاز واحد",      "price": 66000,  "product_id": 3298, "cost_usd": 4.0,    "manual_price": True, "enabled": True},
    {"id": "sh_3299", "label": "📺 شاهد VIP — 3 أشهر / جهاز واحد",    "price": 165000, "product_id": 3299, "cost_usd": 10.0,   "manual_price": True, "enabled": True},
    {"id": "sh_3300", "label": "📺 شاهد VIP — شهر / 5 أجهزة",        "price": 105000,  "product_id": 3300, "cost_usd": 6.355,  "manual_price": True, "enabled": True},
    {"id": "sh_3301", "label": "📺 شاهد VIP — 3 أشهر / 5 أجهزة",      "price": 182000, "product_id": 3301, "cost_usd": 11.025, "manual_price": True, "enabled": True},
    {"id": "sh_3302", "label": "📺 شاهد VIP الكامل — 3 أشهر",         "price": 590000, "product_id": 3302, "cost_usd": 35.83,  "manual_price": True, "enabled": True},
    {"id": "sh_3303", "label": "📺 شاهد VIP 12 شهر — على إيميلك",    "price": 224000, "product_id": 3303, "cost_usd": 15.177, "manual_price": True, "enabled": True},
]

YOUTUBE_OFFERS = [
    {"id": "yt_3286", "label": "📹 يوتيوب بريميوم — شهر",   "price": 84500,  "product_id": 3286, "cost_usd": 5.13,  "manual_price": True, "enabled": True},
    {"id": "yt_3287", "label": "📹 يوتيوب بريميوم — 3 أشهر", "price": 262500, "product_id": 3287, "cost_usd": 15.92, "manual_price": True, "enabled": True},
    {"id": "yt_3288", "label": "📹 يوتيوب بريميوم — 6 أشهر", "price": 465500, "product_id": 3288, "cost_usd": 28.25, "manual_price": True, "enabled": True},
    {"id": "yt_3289", "label": "📹 يوتيوب بريميوم — سنة",   "price": 710500, "product_id": 3289, "cost_usd": 43.13, "manual_price": True, "enabled": True},
]

ANGHAMI_OFFERS = [
    {"id": "an_3318", "label": "🎵 انغامي بلس — 3 أشهر", "price": 39500,  "product_id": 3318, "cost_usd": 2.37, "manual_price": True, "enabled": True},
    {"id": "an_3319", "label": "🎵 انغامي بلس — 6 أشهر", "price": 42500,  "product_id": 3319, "cost_usd": 2.56, "manual_price": True, "enabled": True},
    {"id": "an_3320", "label": "🎵 انغامي بلس — سنة",   "price": 127500, "product_id": 3320, "cost_usd": 7.72, "manual_price": True, "enabled": True},
]

OSN_OFFERS = [
    {"id": "osn_7257", "label": "🍿 OSN+ — شهر / جهاز واحد",   "price": 41500,  "product_id": 7257, "cost_usd": 2.50,  "manual_price": True, "enabled": True},
    {"id": "osn_7258", "label": "🍿 OSN+ — 3 أشهر / جهاز واحد", "price": 98000,  "product_id": 7258, "cost_usd": 5.95,  "manual_price": True, "enabled": True},
    {"id": "osn_7259", "label": "🍿 OSN+ — سنة / جهاز واحد",   "price": 266500, "product_id": 7259, "cost_usd": 16.17, "manual_price": True, "enabled": True},
]

CHATGPT_OFFERS = [
    {"id": "gpt_4225", "label": "🤖 ChatGPT Plus — شهر", "price": 115500, "product_id": 4225, "cost_usd": 7.0, "manual_price": True, "enabled": True},
]

CANVA_OFFERS = [
    {"id": "cv_3312", "label": "🎨 Canva Pro — سنة",          "price": 76500,  "product_id": 3312, "cost_usd": 4.62,  "manual_price": True, "enabled": True},
    {"id": "cv_3313", "label": "🎨 Canva Pro — سنتين",        "price": 127000, "product_id": 3313, "cost_usd": 7.70,  "manual_price": True, "enabled": True},
    {"id": "cv_7023", "label": "🎨 Canva Pro — 4 سنوات",      "price": 254000, "product_id": 7023, "cost_usd": 15.40, "manual_price": True, "enabled": True},
    {"id": "cv_3314", "label": "🎨 Canva Pro — مدى الحياة",   "price": 177500, "product_id": 3314, "cost_usd": 10.78, "manual_price": True, "enabled": True},
]

SNAPCHAT_OFFERS = [
    {"id": "snap_3290", "label": "👻 Snapchat+ — 3 أشهر", "price": 110000,  "product_id": 3290, "cost_usd": 6.67,  "manual_price": True, "enabled": True},
    {"id": "snap_3291", "label": "👻 Snapchat+ — 6 أشهر", "price": 203000, "product_id": 3291, "cost_usd": 12.32, "manual_price": True, "enabled": True},
    {"id": "snap_3292", "label": "👻 Snapchat+ — سنة",   "price": 423000, "product_id": 3292, "cost_usd": 25.67, "manual_price": True, "enabled": True},
]

NORDVPN_OFFERS = [
    {"id": "nv_3400", "label": "🛡️ Nord VPN — شهر",   "price": 29500,  "product_id": 3400, "cost_usd": 1.77,  "manual_price": True, "enabled": True},
    {"id": "nv_3401", "label": "🛡️ Nord VPN — 6 أشهر", "price": 144500, "product_id": 3401, "cost_usd": 8.76,  "manual_price": True, "enabled": True},
    {"id": "nv_3402", "label": "🛡️ Nord VPN — سنة",   "price": 300500, "product_id": 3402, "cost_usd": 18.24, "manual_price": True, "enabled": True},
]

EXPRESSVPN_OFFERS = [
    {"id": "ev_7777", "label": "🟦 Express VPN — شهر (PC/موبايل) — حساب جاهز", "price": 17000, "product_id": 7777, "cost_usd": 1.03, "manual_price": True, "enabled": True},
    {"id": "ev_7776", "label": "🟦 Express VPN — شهر (PC) — كود تفعيل",        "price": 37000, "product_id": 7776, "cost_usd": 2.24, "manual_price": True, "enabled": True},
    {"id": "ev_7775", "label": "🟦 Express VPN — شهر (موبايل) — كود تفعيل",   "price": 36000, "product_id": 7775, "cost_usd": 2.16, "manual_price": True, "enabled": True},
]

LAGOFAST_OFFERS = [
    {"id": "lv_4213", "label": "⚡ LagoFast VPN — شهر", "price": 79000, "product_id": 4213, "cost_usd": 4.77, "manual_price": True, "enabled": True},
]

GEARUP_OFFERS = [
    {"id": "gu_7358", "label": "🚀 GearUP Booster — أسبوع", "price": 25500,  "product_id": 7358, "cost_usd": 1.54,  "manual_price": True, "enabled": True},
    {"id": "gu_4210", "label": "🚀 GearUP Booster — شهر",   "price": 56000,  "product_id": 4210, "cost_usd": 3.39,  "manual_price": True, "enabled": True},
    {"id": "gu_4211", "label": "🚀 GearUP Booster — 3 أشهر", "price": 118500, "product_id": 4211, "cost_usd": 7.19,  "manual_price": True, "enabled": True},
    {"id": "gu_4212", "label": "🚀 GearUP Booster — سنة",   "price": 364000, "product_id": 4212, "cost_usd": 22.08, "manual_price": True, "enabled": True},
]

# تعزيز قنوات تلغرام (يحتاج رابط القناة)
TGBOOST_OFFERS = [
    {"id": "tg_7728", "label": "📢 تعزيز قناة تلغرام بريميوم — يوم",   "price": 500, "product_id": 7728, "cost_usd": 0.028, "manual_price": True, "enabled": True},
    {"id": "tg_7729", "label": "📢 تعزيز قناة تلغرام بريميوم — 7 أيام", "price": 2000, "product_id": 7729, "cost_usd": 0.110, "manual_price": True, "enabled": True},
    {"id": "tg_7730", "label": "📢 تعزيز قناة تلغرام بريميوم — 15 يوم", "price": 3500, "product_id": 7730, "cost_usd": 0.199, "manual_price": True, "enabled": True},
    {"id": "tg_7731", "label": "📢 تعزيز قناة تلغرام بريميوم — 30 يوم", "price": 6000, "product_id": 7731, "cost_usd": 0.342, "manual_price": True, "enabled": True},
]

# Nova TV — اشتراك بث تلفزيوني
NOVA_TV_OFFERS = [
    {"id": "nova_3mo",  "label": "📺 Nova TV — 3 أشهر",    "price": 32500,  "product_id": 7263, "cost_usd": 2.189, "enabled": True},
    {"id": "nova_6mo",  "label": "📺 Nova TV — 6 أشهر",    "price": 65000,  "product_id": 7264, "cost_usd": 4.378, "enabled": True},
    {"id": "nova_12mo", "label": "📺 Nova TV — سنة كاملة", "price": 130000, "product_id": 7265, "cost_usd": 8.756, "enabled": True},
]

# Proton VPN
PROTONVPN_OFFERS = [
    {"id": "pvpn_mo", "label": "🛡️ Proton VPN — شهر", "price": 29000, "product_id": 4208, "cost_usd": 1.9608, "enabled": True},
]

# SurfShark VPN
SURFSHARK_OFFERS = [
    {"id": "svpn_mo", "label": "🦈 SurfShark VPN — شهر", "price": 38500, "product_id": 4209, "cost_usd": 2.611, "enabled": True},
]


# ===== خدمات الرشق (SMM Boost) — يستخدم qty مع unit price =====
# لكل offer: السعر النهائي = price (محسوب من unit_cost_usd × qty × USD_TO_SYP × مارجن، مدور لـ 500)
# Fastcard API: qty يُمرَّر كميةاً، product_id ثابت
# ملاحظة: المنتجات الـ SMM فيها minimum quantity (e.g. 100, 1000) فلازم qty >= min
INSTAGRAM_FOLLOWERS = [
    # 7557 = $0.0041/متابع — حقيقي vip بدون نزول، min=100 (افتراضي)
    {"id": "igf_1k",   "label": "📸 1,000 متابع انستغرام (حقيقي/مضمون)",   "price": 68000,   "product_id": 7557, "qty": 1000,  "cost_usd": 4.10,  "manual_price": True, "enabled": True},
    {"id": "igf_5k",   "label": "📸 5,000 متابع انستغرام (حقيقي/مضمون)",   "price": 1688000,  "product_id": 7557, "qty": 5000,  "cost_usd": 20.50, "manual_price": True, "enabled": True},
    {"id": "igf_10k",  "label": "📸 10,000 متابع انستغرام (حقيقي/مضمون)",  "price": 6750500,  "product_id": 7557, "qty": 10000, "cost_usd": 41.00, "manual_price": True, "enabled": True},
]

INSTAGRAM_LIKES = [
    # 7563 = $0.0041/لايك — vip عربي مضمون مدى الحياة
    {"id": "igl_500",  "label": "❤️ 500 لايك إنستغرام (عربي/مضمون)",   "price": 17000,  "product_id": 7563, "qty": 500,  "cost_usd": 2.05,  "manual_price": True, "enabled": True},
    {"id": "igl_1k",   "label": "❤️ 1,000 لايك إنستغرام (عربي/مضمون)", "price": 68000,  "product_id": 7563, "qty": 1000, "cost_usd": 4.10,  "manual_price": True, "enabled": True},
    {"id": "igl_5k",   "label": "❤️ 5,000 لايك إنستغرام (عربي/مضمون)", "price": 1688000, "product_id": 7563, "qty": 5000, "cost_usd": 20.50, "manual_price": True, "enabled": True},
]

INSTAGRAM_VIEWS = [
    # 7575 = $0.0001/مشاهدة — سريع، كل أنواع الفديو
    {"id": "igv_5k",   "label": "👁️ 5,000 مشاهدة فيديو إنستغرام",    "price": 41500, "product_id": 7575, "qty": 5000,   "cost_usd": 0.50, "manual_price": True, "enabled": True},
    {"id": "igv_10k",  "label": "👁️ 10,000 مشاهدة فيديو إنستغرام",   "price": 165000, "product_id": 7575, "qty": 10000,  "cost_usd": 1.00, "manual_price": True, "enabled": True},
    {"id": "igv_50k",  "label": "👁️ 50,000 مشاهدة فيديو إنستغرام",   "price": 4116000, "product_id": 7575, "qty": 50000,  "cost_usd": 5.00, "manual_price": True, "enabled": True},
]

FACEBOOK_FOLLOWERS = [
    # 7592 = $0.0023/متابع — صفحة عرب، السرعة 50k/يوم، مضمون مدى الحياة
    {"id": "fbf_1k",   "label": "👍 1,000 متابع صفحة فيسبوك (عرب/مضمون)",  "price": 38000,  "product_id": 7592, "qty": 1000,  "cost_usd": 2.30,  "manual_price": True, "enabled": True},
    {"id": "fbf_5k",   "label": "👍 5,000 متابع صفحة فيسبوك (عرب/مضمون)",  "price": 947000, "product_id": 7592, "qty": 5000,  "cost_usd": 11.50, "manual_price": True, "enabled": True},
    {"id": "fbf_10k",  "label": "👍 10,000 متابع صفحة فيسبوك (عرب/مضمون)", "price": 3787000, "product_id": 7592, "qty": 10000, "cost_usd": 23.00, "manual_price": True, "enabled": True},
]

TELEGRAM_VIEWS = [
    # 7748 = $0.0041/مشاهدة لآخر 100 منشور
    {"id": "tgv_100",  "label": "📊 100 مشاهدة لآخر 100 منشور تلغرام",  "price": 1000,  "product_id": 7748, "qty": 100,  "cost_usd": 0.41, "manual_price": True, "enabled": True},
    {"id": "tgv_500",  "label": "📊 500 مشاهدة لآخر 100 منشور تلغرام",  "price": 17000, "product_id": 7748, "qty": 500,  "cost_usd": 2.05, "manual_price": True, "enabled": True},
    {"id": "tgv_1k",   "label": "📊 1,000 مشاهدة لآخر 100 منشور تلغرام", "price": 68000, "product_id": 7748, "qty": 1000, "cost_usd": 4.10, "manual_price": True, "enabled": True},
]

TELEGRAM_REACTIONS = [
    # 7732 = $0.0008/تفاعل — بريميوم تلغرام (لايك)
    {"id": "tgr_500",  "label": "💯 500 تفاعل/لايك تلغرام (بريميوم)",  "price": 3500,  "product_id": 7732, "qty": 500,  "cost_usd": 0.40, "manual_price": True, "enabled": True},
    {"id": "tgr_1k",   "label": "💯 1,000 تفاعل/لايك تلغرام (بريميوم)", "price": 13500, "product_id": 7732, "qty": 1000, "cost_usd": 0.80, "manual_price": True, "enabled": True},
    {"id": "tgr_5k",   "label": "💯 5,000 تفاعل/لايك تلغرام (بريميوم)", "price": 329500, "product_id": 7732, "qty": 5000, "cost_usd": 4.00, "manual_price": True, "enabled": True},
]


# ===== بطاقات Cards: عروض كل منصة (تعرض حسب الدولة) =====
# === VISA Prepaid Cards ===
VISA_OFFERS = [
    {"id": "vs_6937", "label": "💳 VISA 3$",  "price": 58000,  "product_id": 6937, "cost_usd": 3.5,  "manual_price": True, "enabled": True},
    {"id": "vs_7308", "label": "💳 VISA 4$",  "price": 72500,  "product_id": 7308, "cost_usd": 4.4,  "manual_price": True, "enabled": True},
    {"id": "vs_6305", "label": "💳 VISA 5$",  "price": 91000,  "product_id": 6305, "cost_usd": 5.5,  "manual_price": True, "enabled": True},
    {"id": "vs_7692", "label": "💳 VISA 10$", "price": 181500, "product_id": 7692, "cost_usd": 11.0, "manual_price": True, "enabled": True},
]


# === Playstation USA ===
PSN_US_OFFERS = [
    {"id": "ps_us_3653", "label": "بلاي ستيشن امريكي 4$", "price": 64000, "product_id": 3653, "cost_usd": 3.877515, "manual_price": True, "enabled": True},
    {"id": "ps_us_3654", "label": "بلاي ستيشن امريكي 10$", "price": 164000, "product_id": 3654, "cost_usd": 9.95398, "manual_price": True, "enabled": True},
    {"id": "ps_us_3655", "label": "بلاي ستيشن امريكي 25$", "price": 386500, "product_id": 3655, "cost_usd": 23.45215, "manual_price": True, "enabled": True},
    {"id": "ps_us_3656", "label": "بلاي ستيشن امريكي 50$", "price": 759500, "product_id": 3656, "cost_usd": 46.12223, "manual_price": True, "enabled": True},
    {"id": "ps_us_3660", "label": "بلاي ستيشن امريكي 100$", "price": 1519000, "product_id": 3660, "cost_usd": 92.243465, "manual_price": True, "enabled": True},
    {"id": "ps_us_3661", "label": "بلاي ستيشن امريكي 110$", "price": 1517000, "product_id": 3661, "cost_usd": 103.19742, "enabled": True},
]

# === Playstation KSA ===
PSN_SA_OFFERS = [
    {"id": "ps_sa_3674", "label": "بلاي ستيشن سعودي 10$", "price": 169500, "product_id": 3674, "cost_usd": 10.267405, "manual_price": True, "enabled": True},
    {"id": "ps_sa_3676", "label": "بلاي ستيشن سعودي 20$", "price": 334000, "product_id": 3676, "cost_usd": 20.263175, "manual_price": True, "enabled": True},
    {"id": "ps_sa_3680", "label": "بلاي ستيشن سعودي 50$", "price": 841000, "product_id": 3680, "cost_usd": 51.06141, "manual_price": True, "enabled": True},
    {"id": "ps_sa_3683", "label": "بلاي ستيشن سعودي 100$", "price": 1668000, "product_id": 3683, "cost_usd": 101.311895, "manual_price": True, "enabled": True},
    {"id": "ps_sa_3673", "label": "بلاي ستيشن سعودي 5$", "price": 1517000, "product_id": 3673, "cost_usd": 103.19742, "enabled": True},
    {"id": "ps_sa_3675", "label": "بلاي ستيشن سعودي 15$", "price": 1517000, "product_id": 3675, "cost_usd": 103.19742, "enabled": True},
    {"id": "ps_sa_3677", "label": "بلاي ستيشن سعودي 30$", "price": 1517000, "product_id": 3677, "cost_usd": 103.19742, "enabled": True},
    {"id": "ps_sa_3678", "label": "بلاي ستيشن سعودي 40$", "price": 1517000, "product_id": 3678, "cost_usd": 103.19742, "enabled": True},
    {"id": "ps_sa_3679", "label": "بلاي ستيشن سعودي 45$", "price": 1517000, "product_id": 3679, "cost_usd": 103.19742, "enabled": True},
    {"id": "ps_sa_3681", "label": "بلاي ستيشن سعودي 60$", "price": 1517000, "product_id": 3681, "cost_usd": 103.19742, "enabled": True},
    {"id": "ps_sa_3682", "label": "بلاي ستيشن سعودي 70$", "price": 1517000, "product_id": 3682, "cost_usd": 103.19742, "enabled": True},
]

# === Playstation Lebanon ===
PSN_LB_OFFERS = [
    {"id": "ps_lb_3663", "label": "بلاي ستيشن لبناني 10$", "price": 154000, "product_id": 3663, "cost_usd": 9.32912, "manual_price": True, "enabled": True},
    {"id": "ps_lb_3665", "label": "بلاي ستيشن لبناني 20$", "price": 307500, "product_id": 3665, "cost_usd": 18.657245, "manual_price": True, "enabled": True},
    {"id": "ps_lb_3669", "label": "بلاي ستيشن لبناني 50$", "price": 768000, "product_id": 3669, "cost_usd": 46.64361, "manual_price": True, "enabled": True},
    {"id": "ps_lb_3672", "label": "بلاي ستيشن لبناني 100$", "price": 1536000, "product_id": 3672, "cost_usd": 93.286225, "manual_price": True, "enabled": True},
]

# === Playstation Emirates ===
PSN_AE_OFFERS = [
    {"id": "ps_ae_4111", "label": "10$ PSN UAE", "price": 161500, "product_id": 4111, "cost_usd": 9.797765, "manual_price": True, "enabled": True},
    {"id": "ps_ae_4112", "label": "20$ PSN UAE", "price": 323000, "product_id": 4112, "cost_usd": 19.59553, "manual_price": True, "enabled": True},
    {"id": "ps_ae_4113", "label": "50$ PSN UAE", "price": 807000, "product_id": 4113, "cost_usd": 48.98783, "manual_price": True, "enabled": True},
    {"id": "ps_ae_4114", "label": "100$ PSN UAE", "price": 1613500, "product_id": 4114, "cost_usd": 97.97566, "manual_price": True, "enabled": True},
]

# === PSN Bahrain ===
PSN_BH_OFFERS = [
    {"id": "ps_bh_10",  "label": "بلاي ستيشن بحريني 10$",  "price": 141000,  "product_id": 3708, "cost_usd": 9.533,  "enabled": True},
    {"id": "ps_bh_20",  "label": "بلاي ستيشن بحريني 20$",  "price": 282000,  "product_id": 3709, "cost_usd": 19.066, "enabled": True},
    {"id": "ps_bh_50",  "label": "بلاي ستيشن بحريني 50$",  "price": 704000,  "product_id": 3713, "cost_usd": 47.663, "enabled": True},
    {"id": "ps_bh_100", "label": "بلاي ستيشن بحريني 100$", "price": 1408500, "product_id": 3716, "cost_usd": 95.326, "enabled": True},
]

# === PSN Qatar ===
PSN_QA_OFFERS = [
    {"id": "ps_qa_10",  "label": "بلاي ستيشن قطري 10$",  "price": 145500,  "product_id": 4093, "cost_usd": 9.847,  "enabled": True},
    {"id": "ps_qa_20",  "label": "بلاي ستيشن قطري 20$",  "price": 291000,  "product_id": 3684, "cost_usd": 19.694, "enabled": True},
    {"id": "ps_qa_100", "label": "بلاي ستيشن قطري 100$", "price": 1455000, "product_id": 3689, "cost_usd": 98.468, "enabled": True},
]

# === PSN Oman ===
PSN_OM_OFFERS = [
    {"id": "ps_om_10",  "label": "بلاي ستيشن عماني 10$",  "price": 145500,  "product_id": 3690, "cost_usd": 9.847,  "enabled": True},
    {"id": "ps_om_20",  "label": "بلاي ستيشن عماني 20$",  "price": 291000,  "product_id": 3691, "cost_usd": 19.694, "enabled": True},
    {"id": "ps_om_50",  "label": "بلاي ستيشن عماني 50$",  "price": 727500,  "product_id": 3694, "cost_usd": 49.234, "enabled": True},
    {"id": "ps_om_100", "label": "بلاي ستيشن عماني 100$", "price": 1455000, "product_id": 3697, "cost_usd": 98.468, "enabled": True},
]

# === PSN UK ===
PSN_UK_OFFERS = [
    {"id": "ps_uk_10",  "label": "بلاي ستيشن بريطاني 10£",  "price": 202000,  "product_id": 3699, "cost_usd": 13.654,  "enabled": True},
    {"id": "ps_uk_20",  "label": "بلاي ستيشن بريطاني 20£",  "price": 403000,  "product_id": 3701, "cost_usd": 27.309,  "enabled": True},
    {"id": "ps_uk_50",  "label": "بلاي ستيشن بريطاني 50£",  "price": 1008500, "product_id": 3706, "cost_usd": 68.27,   "enabled": True},
    {"id": "ps_uk_100", "label": "بلاي ستيشن بريطاني 100£", "price": 2017000, "product_id": 3707, "cost_usd": 136.541, "enabled": True},
]

# === PSN Germany ===
PSN_DE_OFFERS = [
    {"id": "ps_de_5",   "label": "بلاي ستيشن ألماني 5€",   "price": 93000,   "product_id": 3736, "cost_usd": 6.286,   "enabled": True},
    {"id": "ps_de_10",  "label": "بلاي ستيشن ألماني 10€",  "price": 186000,  "product_id": 3737, "cost_usd": 12.571,  "enabled": True},
    {"id": "ps_de_25",  "label": "بلاي ستيشن ألماني 25€",  "price": 347000,  "product_id": 3740, "cost_usd": 23.504,  "enabled": True},
    {"id": "ps_de_50",  "label": "بلاي ستيشن ألماني 50€",  "price": 882500,  "product_id": 3744, "cost_usd": 59.71,   "enabled": True},
    {"id": "ps_de_100", "label": "بلاي ستيشن ألماني 100€", "price": 1733000, "product_id": 3747, "cost_usd": 117.324, "enabled": True},
]

# === Steam USA ===
STEAM_US_OFFERS = [
    {"id": "st_us_3387", "label": "بطاقة ستيم اميركي 5$", "price": 93000, "product_id": 3387, "cost_usd": 5.64762, "manual_price": True, "enabled": True},
    {"id": "st_us_3388", "label": "بطاقة ستيم اميركي 10$", "price": 184500, "product_id": 3388, "cost_usd": 11.192556, "manual_price": True, "enabled": True},
    {"id": "st_us_3389", "label": "بطاقة ستيم اميركي 20$", "price": 345000, "product_id": 3389, "cost_usd": 20.947536, "manual_price": True, "enabled": True},
    {"id": "st_us_3390", "label": "بطاقة ستيم اميركي 50$", "price": 855500, "product_id": 3390, "cost_usd": 51.958104, "manual_price": True, "enabled": True},
    {"id": "st_us_3392", "label": "بطاقة ستيم اميركي 100$", "price": 1741500, "product_id": 3392, "cost_usd": 105.76452, "manual_price": True, "enabled": True},
]

# === Steam KAS ===
STEAM_SA_OFFERS = [
    {"id": "st_sa_3393", "label": "ستيم سعودي 20 ريال", "price": 91000, "product_id": 3393, "cost_usd": 5.5123, "manual_price": True, "enabled": True},
    {"id": "st_sa_3394", "label": "ستيم سعودي 40 ريال", "price": 182000, "product_id": 3394, "cost_usd": 11.0246, "manual_price": True, "enabled": True},
    {"id": "st_sa_3395", "label": "ستيم سعودي 50 ريال", "price": 227000, "product_id": 3395, "cost_usd": 13.78075, "manual_price": True, "enabled": True},
    {"id": "st_sa_3396", "label": "ستيم سعودي 100 ريال", "price": 454000, "product_id": 3396, "cost_usd": 27.560506, "manual_price": True, "enabled": True},
    {"id": "st_sa_3397", "label": "ستيم سعودي 200 ريال", "price": 908000, "product_id": 3397, "cost_usd": 55.121011, "manual_price": True, "enabled": True},
]

# === Steam TURKEY ===
STEAM_TR_OFFERS = [
    {"id": "st_tr_3385", "label": "بطاقة ستيم تركي 50TL", "price": 56000, "product_id": 3385, "cost_usd": 3.395935, "manual_price": True, "enabled": True},
    {"id": "st_tr_3386", "label": "بطاقة ستيم تركي 100TL", "price": 112500, "product_id": 3386, "cost_usd": 6.81177, "manual_price": True, "enabled": True},
]

# === Steam Emirates ===
STEAM_AE_OFFERS = [
    {"id": "st_ae_20",  "label": "ستيم إماراتي 20 AED",  "price": 86500,   "product_id": 4045, "cost_usd": 5.852,   "enabled": True},
    {"id": "st_ae_40",  "label": "ستيم إماراتي 40 AED",  "price": 173000,  "product_id": 4046, "cost_usd": 11.713,  "enabled": True},
    {"id": "st_ae_50",  "label": "ستيم إماراتي 50 AED",  "price": 216000,  "product_id": 4047, "cost_usd": 14.634,  "enabled": True},
    {"id": "st_ae_75",  "label": "ستيم إماراتي 75 AED",  "price": 324000,  "product_id": 4048, "cost_usd": 21.955,  "enabled": True},
    {"id": "st_ae_100", "label": "ستيم إماراتي 100 AED", "price": 432500,  "product_id": 4049, "cost_usd": 29.277,  "enabled": True},
    {"id": "st_ae_200", "label": "ستيم إماراتي 200 AED", "price": 865000,  "product_id": 4050, "cost_usd": 58.554,  "enabled": True},
    {"id": "st_ae_400", "label": "ستيم إماراتي 400 AED", "price": 1730000, "product_id": 4051, "cost_usd": 117.118, "enabled": True},
]

# === Steam Kuwait ===
STEAM_KW_OFFERS = [
    {"id": "st_kw_5",  "label": "ستيم كويتي 5 دينار",  "price": 252500,  "product_id": 4052, "cost_usd": 17.081, "enabled": True},
    {"id": "st_kw_10", "label": "ستيم كويتي 10 دينار", "price": 505000,  "product_id": 4053, "cost_usd": 34.162, "enabled": True},
    {"id": "st_kw_15", "label": "ستيم كويتي 15 دينار", "price": 759000,  "product_id": 4054, "cost_usd": 51.372, "enabled": True},
    {"id": "st_kw_20", "label": "ستيم كويتي 20 دينار", "price": 1005500, "product_id": 4055, "cost_usd": 68.066, "enabled": True},
    {"id": "st_kw_30", "label": "ستيم كويتي 30 دينار", "price": 1509000, "product_id": 4056, "cost_usd": 102.12, "enabled": True},
]

# === Steam Oman ===
STEAM_OM_OFFERS = [
    {"id": "st_om_5",   "label": "ستيم عماني 5$",   "price": 78000,   "product_id": 4057, "cost_usd": 5.272,   "enabled": True},
    {"id": "st_om_10",  "label": "ستيم عماني 10$",  "price": 156000,  "product_id": 4058, "cost_usd": 10.554,  "enabled": True},
    {"id": "st_om_20",  "label": "ستيم عماني 20$",  "price": 308000,  "product_id": 4059, "cost_usd": 20.828,  "enabled": True},
    {"id": "st_om_50",  "label": "ستيم عماني 50$",  "price": 771500,  "product_id": 4060, "cost_usd": 52.209,  "enabled": True},
    {"id": "st_om_75",  "label": "ستيم عماني 75$",  "price": 1156000, "product_id": 4061, "cost_usd": 78.254,  "enabled": True},
    {"id": "st_om_100", "label": "ستيم عماني 100$", "price": 1541000, "product_id": 4062, "cost_usd": 104.332, "enabled": True},
]

# === iTunes USA ===
ITUNES_US_OFFERS = [
    {"id": "it_us_6322", "label": "$ 2 iTunes USA", "price": 32500, "product_id": 6322, "cost_usd": 1.960136, "manual_price": True, "enabled": True},
    {"id": "it_us_6323", "label": "$ 3 iTunes USA", "price": 49000, "product_id": 6323, "cost_usd": 2.956146, "manual_price": True, "enabled": True},
    {"id": "it_us_6324", "label": "$ 5 iTunes USA", "price": 78000, "product_id": 6324, "cost_usd": 4.719285, "manual_price": True, "enabled": True},
    {"id": "it_us_6325", "label": "$ 10 iTunes USA", "price": 156500, "product_id": 6325, "cost_usd": 9.49031, "manual_price": True, "enabled": True},
    {"id": "it_us_6326", "label": "$ 15 iTunes USA", "price": 234000, "product_id": 6326, "cost_usd": 14.2086, "manual_price": True, "enabled": True},
    {"id": "it_us_6327", "label": "$ 20 iTunes USA", "price": 311000, "product_id": 6327, "cost_usd": 18.876145, "manual_price": True, "enabled": True},
    {"id": "it_us_6328", "label": "$ 25 iTunes USA", "price": 388500, "product_id": 6328, "cost_usd": 23.594435, "manual_price": True, "enabled": True},
    {"id": "it_us_6329", "label": "$ 50 iTunes USA", "price": 777000, "product_id": 6329, "cost_usd": 47.18887, "manual_price": True, "enabled": True},
    {"id": "it_us_6330", "label": "$ 100 iTunes USA", "price": 1562500, "product_id": 6330, "cost_usd": 94.896135, "manual_price": True, "enabled": True},
]

# === iTunes KSA ===
ITUNES_SA_OFFERS = [
    {"id": "it_sa_6382", "label": "iTunes KSA 50 SAR", "price": 221000, "product_id": 6382, "cost_usd": 13.413595, "manual_price": True, "enabled": True},
    {"id": "it_sa_6383", "label": "iTunes KSA 100 SAR", "price": 442000, "product_id": 6383, "cost_usd": 26.830175, "manual_price": True, "enabled": True},
    {"id": "it_sa_6384", "label": "iTunes KSA 200 SAR", "price": 883500, "product_id": 6384, "cost_usd": 53.653385, "manual_price": True, "enabled": True},
    {"id": "it_sa_6385", "label": "iTunes KSA 400 SAR", "price": 1767000, "product_id": 6385, "cost_usd": 107.30677, "manual_price": True, "enabled": True},
]

# === iTunes UK ===
ITUNES_UK_OFFERS = [
    {"id": "it_uk_6331", "label": "£ 5 iTunes UK", "price": 115000, "product_id": 6331, "cost_usd": 6.95704, "manual_price": True, "enabled": True},
    {"id": "it_uk_6332", "label": "£ 10 iTunes UK", "price": 229500, "product_id": 6332, "cost_usd": 13.91209, "manual_price": True, "enabled": True},
    {"id": "it_uk_6333", "label": "£ 25 iTunes UK", "price": 573000, "product_id": 6333, "cost_usd": 34.780225, "manual_price": True, "enabled": True},
    {"id": "it_uk_6334", "label": "£ 50 iTunes UK", "price": 1145500, "product_id": 6334, "cost_usd": 69.55846, "manual_price": True, "enabled": True},
    {"id": "it_uk_6335", "label": "£ 100 iTunes UK", "price": 2290500, "product_id": 6335, "cost_usd": 139.115925, "manual_price": True, "enabled": True},
]

# === Google USA ===
GPLAY_US_OFFERS = [
    {"id": "gp_us_4168", "label": "بطاقة غوغل 5$ امريكي", "price": 84500, "product_id": 4168, "cost_usd": 5.107335, "manual_price": True, "enabled": True},
    {"id": "gp_us_4169", "label": "بطاقة غوغل 10$ امريكي", "price": 168500, "product_id": 4169, "cost_usd": 10.21467, "manual_price": True, "enabled": True},
    {"id": "gp_us_4170", "label": "بطاقة غوغل 25$ امريكي", "price": 420500, "product_id": 4170, "cost_usd": 25.536675, "manual_price": True, "enabled": True},
    {"id": "gp_us_4171", "label": "بطاقة غوغل 50$ امريكي", "price": 841000, "product_id": 4171, "cost_usd": 51.07335, "manual_price": True, "enabled": True},
    {"id": "gp_us_4172", "label": "بطاقة غوغل 100$ امريكي", "price": 1517000, "product_id": 4172, "cost_usd": 103.19742, "enabled": True},
]

# === Google KSA ===
GPLAY_SA_OFFERS = [
    {"id": "gp_sa_4020", "label": "بطاقة غوغل 5 ريال سعودي", "price": 23000, "product_id": 4020, "cost_usd": 1.368125, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4021", "label": "بطاقة غوغل 6 ريال سعودي", "price": 27500, "product_id": 4021, "cost_usd": 1.656676, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4022", "label": "بطاقة غوغل 7 ريال سعودي", "price": 32000, "product_id": 4022, "cost_usd": 1.93428, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4023", "label": "بطاقة غوغل 8 ريال سعودي", "price": 36500, "product_id": 4023, "cost_usd": 2.20094, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4024", "label": "بطاقة غوغل 9 ريال سعودي", "price": 41000, "product_id": 4024, "cost_usd": 2.478545, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4025", "label": "بطاقة غوغل 10 ريال سعودي", "price": 45500, "product_id": 4025, "cost_usd": 2.7462, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4026", "label": "بطاقة غوغل 15 ريال سعودي", "price": 68000, "product_id": 4026, "cost_usd": 4.113331, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4027", "label": "بطاقة غوغل 20 ريال سعودي", "price": 90500, "product_id": 4027, "cost_usd": 5.48046, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4028", "label": "بطاقة غوغل 30 ريال سعودي", "price": 135500, "product_id": 4028, "cost_usd": 8.225665, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4214", "label": "بطاقة غوغل 40 ريال سعودي", "price": 181000, "product_id": 4214, "cost_usd": 10.97087, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4030", "label": "بطاقة غوغل 50 ريال سعودي", "price": 226000, "product_id": 4030, "cost_usd": 13.706125, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4031", "label": "بطاقة غوغل 60 ريال سعودي", "price": 271000, "product_id": 4031, "cost_usd": 16.45133, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4032", "label": "بطاقة غوغل 70 ريال سعودي", "price": 316500, "product_id": 4032, "cost_usd": 19.196535, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4033", "label": "بطاقة غوغل 75 ريال سعودي", "price": 339000, "product_id": 4033, "cost_usd": 20.563665, "manual_price": True, "enabled": True},
    {"id": "gp_sa_4034", "label": "بطاقة غوغل 80 ريال سعودي", "price": 363500, "product_id": 4034, "cost_usd": 22.048205, "manual_price": True, "enabled": True},
]

# === Google Turkey ===
GPLAY_TR_OFFERS = [
    {"id": "gp_tr_4173", "label": "بطاقة غوغل 25TL تركي", "price": 9500, "product_id": 4173, "cost_usd": 0.566155, "manual_price": True, "enabled": True},
    {"id": "gp_tr_4174", "label": "بطاقة غوغل 50TL تركي", "price": 19000, "product_id": 4174, "cost_usd": 1.131315, "manual_price": True, "enabled": True},
    {"id": "gp_tr_4175", "label": "بطاقة غوغل 100TL تركي", "price": 37500, "product_id": 4175, "cost_usd": 2.261635, "manual_price": True, "enabled": True},
    {"id": "gp_tr_4176", "label": "بطاقة غوغل 250TL تركي", "price": 93500, "product_id": 4176, "cost_usd": 5.652595, "manual_price": True, "enabled": True},
    {"id": "gp_tr_4177", "label": "بطاقة غوغل 500TL تركي", "price": 186500, "product_id": 4177, "cost_usd": 11.304195, "manual_price": True, "enabled": True},
    {"id": "gp_tr_4178", "label": "بطاقة غوغل 1000TL تركي", "price": 372500, "product_id": 4178, "cost_usd": 22.607395, "manual_price": True, "enabled": True},
]

# === XBOX USA ===
XBOX_US_OFFERS = [
    {"id": "xb_us_4185", "label": "بطاقة اكس بوكس 5$ امريكي", "price": 78500, "product_id": 4185, "cost_usd": 4.743165, "manual_price": True, "enabled": True},
    {"id": "xb_us_4186", "label": "بطاقة اكس بوكس 10$ امريكي", "price": 156500, "product_id": 4186, "cost_usd": 9.485335, "manual_price": True, "enabled": True},
    {"id": "xb_us_4188", "label": "بطاقة اكس بوكس 20$ امريكي", "price": 312500, "product_id": 4188, "cost_usd": 18.97067, "manual_price": True, "enabled": True},
    {"id": "xb_us_4189", "label": "بطاقة اكس بوكس 25$ امريكي", "price": 390500, "product_id": 4189, "cost_usd": 23.71284, "manual_price": True, "enabled": True},
    {"id": "xb_us_3933", "label": "بطاقة اكس بوكس 50$ امريكي", "price": 781000, "product_id": 3933, "cost_usd": 47.424685, "manual_price": True, "enabled": True},
    {"id": "xb_us_3934", "label": "بطاقة اكس بوكس 100$ امريكي", "price": 1562000, "product_id": 3934, "cost_usd": 94.84937, "manual_price": True, "enabled": True},
    {"id": "xb_us_4187", "label": "بطاقة اكس بوكس 15$ امريكي", "price": 1517000, "product_id": 4187, "cost_usd": 103.19742, "enabled": True},
]

# === XBOX KSA ===
XBOX_SA_OFFERS = [
    {"id": "xb_sa_4039", "label": "بطاقة اكس بوكس 50 ريال سعودي", "price": 216500, "product_id": 4039, "cost_usd": 13.133005, "manual_price": True, "enabled": True},
    {"id": "xb_sa_4040", "label": "بطاقة اكس بوكس 100 ريال سعودي", "price": 432500, "product_id": 4040, "cost_usd": 26.26601, "manual_price": True, "enabled": True},
    {"id": "xb_sa_4041", "label": "بطاقة اكس بوكس 200 ريال سعودي", "price": 865000, "product_id": 4041, "cost_usd": 52.53202, "manual_price": True, "enabled": True},
    {"id": "xb_sa_4042", "label": "بطاقة اكس بوكس 300 ريال سعودي", "price": 1297500, "product_id": 4042, "cost_usd": 78.79803, "manual_price": True, "enabled": True},
]

# === RAZER GLOBAL ===
RAZER_GL_OFFERS = [
    {"id": "rz_gl_3604", "label": "1$ RAZER عالمي", "price": 16000, "product_id": 3604, "cost_usd": 0.970125, "manual_price": True, "enabled": True},
    {"id": "rz_gl_3605", "label": "2$ RAZER عالمي", "price": 32000, "product_id": 3605, "cost_usd": 1.939255, "manual_price": True, "enabled": True},
    {"id": "rz_gl_3610", "label": "100$ RAZER عالمي", "price": 30500, "product_id": 3610, "cost_usd": 2.064626, "enabled": True},
    {"id": "rz_gl_3606", "label": "5$ RAZER عالمي", "price": 80000, "product_id": 3606, "cost_usd": 4.84764, "manual_price": True, "enabled": True},
    {"id": "rz_gl_3607", "label": "10$ RAZER عالمي", "price": 160000, "product_id": 3607, "cost_usd": 9.694285, "manual_price": True, "enabled": True},
    {"id": "rz_gl_3608", "label": "20$ RAZER عالمي", "price": 319500, "product_id": 3608, "cost_usd": 19.387575, "manual_price": True, "enabled": True},
    {"id": "rz_gl_3609", "label": "50$ RAZER عالمي", "price": 798000, "product_id": 3609, "cost_usd": 48.467445, "manual_price": True, "enabled": True},
]

# === RAZER USA ===
RAZER_US_OFFERS = [
    {"id": "rz_us_3611", "label": "5$ RAZER اميركي", "price": 80500, "product_id": 3611, "cost_usd": 4.87152, "manual_price": True, "enabled": True},
    {"id": "rz_us_3612", "label": "10$ RAZER اميركي", "price": 160000, "product_id": 3612, "cost_usd": 9.690305, "manual_price": True, "enabled": True},
    {"id": "rz_us_3613", "label": "20$ RAZER اميركي", "price": 319500, "product_id": 3613, "cost_usd": 19.379615, "manual_price": True, "enabled": True},
    {"id": "rz_us_3614", "label": "50$ RAZER اميركي", "price": 798000, "product_id": 3614, "cost_usd": 48.447546, "manual_price": True, "enabled": True},
    {"id": "rz_us_3615", "label": "100$ RAZER اميركي", "price": 1595500, "product_id": 3615, "cost_usd": 96.895091, "manual_price": True, "enabled": True},
]

# === RAZER TURKEY ===
RAZER_TR_OFFERS = [
    {"id": "rz_tr_4159", "label": "RAZER 5TL تركي", "price": 2000, "product_id": 4159, "cost_usd": 0.110445, "manual_price": True, "enabled": True},
    {"id": "rz_tr_4160", "label": "RAZER 10TL تركي", "price": 4000, "product_id": 4160, "cost_usd": 0.22089, "manual_price": True, "enabled": True},
    {"id": "rz_tr_4161", "label": "RAZER 15TL تركي", "price": 5500, "product_id": 4161, "cost_usd": 0.33034, "manual_price": True, "enabled": True},
    {"id": "rz_tr_4162", "label": "RAZER 25TL تركي", "price": 9500, "product_id": 4162, "cost_usd": 0.55123, "manual_price": True, "enabled": True},
    {"id": "rz_tr_4163", "label": "RAZER 50TL تركي", "price": 18500, "product_id": 4163, "cost_usd": 1.101465, "manual_price": True, "enabled": True},
    {"id": "rz_tr_4164", "label": "RAZER 100TL تركي", "price": 36500, "product_id": 4164, "cost_usd": 2.201935, "manual_price": True, "enabled": True},
    {"id": "rz_tr_4165", "label": "RAZER 250TL تركي", "price": 91000, "product_id": 4165, "cost_usd": 5.50434, "manual_price": True, "enabled": True},
    {"id": "rz_tr_4166", "label": "RAZER 500TL تركي", "price": 181500, "product_id": 4166, "cost_usd": 11.007685, "manual_price": True, "enabled": True},
    {"id": "rz_tr_4167", "label": "RAZER 1000TL تركي", "price": 362500, "product_id": 4167, "cost_usd": 22.01537, "manual_price": True, "enabled": True},
]

# === Nintendo ===
NINTENDO_OFFERS = [
    {"id": "nt_us_3809", "label": "بطاقة نينتيندو 10$", "price": 152500, "product_id": 3809, "cost_usd": 9.23957, "manual_price": True, "enabled": True},
    {"id": "nt_us_3810", "label": "بطاقة نينتيندو 20$", "price": 303000, "product_id": 3810, "cost_usd": 18.380635, "manual_price": True, "enabled": True},
    {"id": "nt_us_3811", "label": "بطاقة نينتيندو 50$", "price": 757000, "product_id": 3811, "cost_usd": 45.97895, "manual_price": True, "enabled": True},
]

# === NETFLIX ===
NETFLIX_OFFERS = [
    {"id": "nflx_7035", "label": "حساب نتفلكس مستخدم واحد , شهر واحد", "price": 41500, "product_id": 7035, "cost_usd": 2.5, "manual_price": True, "enabled": True},
    {"id": "nflx_7036", "label": "حساب نتفلكس مستخدم واحد | 3 اشهر", "price": 123500, "product_id": 7036, "cost_usd": 7.5, "manual_price": True, "enabled": True},
    {"id": "nflx_3296", "label": "أشتراك شهر دقة 1080", "price": 153000, "product_id": 3296, "cost_usd": 9.26345, "manual_price": True, "enabled": True},
    {"id": "nflx_3297", "label": "اشتراك شهر دقة 4K", "price": 181500, "product_id": 3297, "cost_usd": 10.999725, "manual_price": True, "enabled": True},
    {"id": "nflx_7039", "label": "حساب نتفلكس كامل - شهر 4K", "price": 181500, "product_id": 7039, "cost_usd": 11.0, "manual_price": True, "enabled": True},
    {"id": "nflx_7037", "label": "حساب نتفلكس مستخدم واحد | 6 اشهر", "price": 230500, "product_id": 7037, "cost_usd": 14.0, "manual_price": True, "enabled": True},
    {"id": "nflx_7038", "label": "حساب نتفلكس مستخدم واحد | 12 اشهر", "price": 436500, "product_id": 7038, "cost_usd": 26.5, "manual_price": True, "enabled": True},
    {"id": "nflx_7040", "label": "حساب نتفلكس كامل - 3 شهر 4K", "price": 512000, "product_id": 7040, "cost_usd": 31.097731, "manual_price": True, "enabled": True},
    {"id": "nflx_7041", "label": "حساب نتفلكس كامل - 6 شهر 4K", "price": 979000, "product_id": 7041, "cost_usd": 59.462195, "manual_price": True, "enabled": True},
    {"id": "nflx_7042", "label": "حساب نتفلكس كامل - 12 شهر 4K", "price": 2062500, "product_id": 7042, "cost_usd": 125.26652, "manual_price": True, "enabled": True},
]


# تعريف الأقسام التلقائية. key = الـ prefix المستخدم في callback_data
# input_fields = قائمة حقول يدخلها المستخدم بالترتيب. فاضية = ما في حقول (للأكواد).
# ===== قسم الرصيد (27 خدمة من Fastcard cat=449) — مولّدة من API =====
# ===== أقسام رصيد الموبايل (سيرياتيل + MTN) =====
# ملاحظة مهمة: API فاستكارد يستخدم نظام داخلي بالليرة الجديدة (1 وحدة API ≈ 100 ل.س قديمة).
# نحن نعرض ونسعّر للزبون بالليرة السورية القديمة. هامش الربح ~10% مدوّر لأقرب 500 ل.س.
# `qty` = القيمة المرسلة لـ API (ليرة جديدة). `manual_price=True` يمنع إعادة الحساب من cost_usd.

SYRIATEL_BALANCE_OFFERS = [
    {"id": "syriatel_balance_3039_961",    "label": "📲 رصيد سيريتل ≈ 1,000 ل.س",   "price": 1500,   "product_id": 3039, "qty": 9.61,    "manual_price": True, "enabled": True},
    {"id": "syriatel_balance_3039_2019",   "label": "📲 رصيد سيريتل ≈ 2,000 ل.س",   "price": 2500,   "product_id": 3039, "qty": 20.19,   "manual_price": True, "enabled": True},
    {"id": "syriatel_balance_3039_4038",   "label": "📲 رصيد سيريتل ≈ 4,000 ل.س",   "price": 4500,   "product_id": 3039, "qty": 40.38,   "manual_price": True, "enabled": True},
    {"id": "syriatel_balance_3039_10096",  "label": "📲 رصيد سيريتل ≈ 10,000 ل.س",  "price": 11500,  "product_id": 3039, "qty": 100.96,  "manual_price": True, "enabled": True},
    {"id": "syriatel_balance_3039_10575",  "label": "📲 رصيد سيريتل ≈ 10,500 ل.س",  "price": 12000,  "product_id": 3039, "qty": 105.75,  "manual_price": True, "enabled": True},
    {"id": "syriatel_balance_3039_16057",  "label": "📲 رصيد سيريتل ≈ 16,000 ل.س",  "price": 18000,  "product_id": 3039, "qty": 160.57,  "manual_price": True, "enabled": True},
    {"id": "syriatel_balance_3039_24038",  "label": "📲 رصيد سيريتل ≈ 24,000 ل.س",  "price": 26500,  "product_id": 3039, "qty": 240.38,  "manual_price": True, "enabled": True},
    {"id": "syriatel_balance_3039_43269",  "label": "📲 رصيد سيريتل ≈ 43,000 ل.س",  "price": 48000,  "product_id": 3039, "qty": 432.69,  "manual_price": True, "enabled": True},
    {"id": "syriatel_balance_3039_62019",  "label": "📲 رصيد سيريتل ≈ 62,000 ل.س",  "price": 68500,  "product_id": 3039, "qty": 620.19,  "manual_price": True, "enabled": True},
    {"id": "syriatel_balance_3039_105769", "label": "📲 رصيد سيريتل ≈ 105,000 ل.س", "price": 116500, "product_id": 3039, "qty": 1057.69, "manual_price": True, "enabled": True},
    {"id": "syriatel_balance_3039_210576", "label": "📲 رصيد سيريتل ≈ 210,000 ل.س", "price": 232000, "product_id": 3039, "qty": 2105.76, "manual_price": True, "enabled": True},
]

# لـ amount: qty المرسل = القيمة بالليرة القديمة المعروضة ÷ 100 (تحويل قديمة → جديدة).
SYRIATEL_GAS_OFFERS = [
    {"id": "syriatel_gas_3042_10000",   "label": "⛽ كازية سيريتل 10,000 ل.س",    "price": 11000,   "product_id": 3042, "qty": 100,   "manual_price": True, "enabled": True},
    {"id": "syriatel_gas_3042_25000",   "label": "⛽ كازية سيريتل 25,000 ل.س",    "price": 27500,   "product_id": 3042, "qty": 250,   "manual_price": True, "enabled": True},
    {"id": "syriatel_gas_3042_50000",   "label": "⛽ كازية سيريتل 50,000 ل.س",    "price": 55000,   "product_id": 3042, "qty": 500,   "manual_price": True, "enabled": True},
    {"id": "syriatel_gas_3042_100000",  "label": "⛽ كازية سيريتل 100,000 ل.س",   "price": 110000,  "product_id": 3042, "qty": 1000,  "manual_price": True, "enabled": True},
    {"id": "syriatel_gas_3042_500000",  "label": "⛽ كازية سيريتل 500,000 ل.س",   "price": 550000,  "product_id": 3042, "qty": 5000,  "manual_price": True, "enabled": True},
    {"id": "syriatel_gas_3042_1000000", "label": "⛽ كازية سيريتل 1,000,000 ل.س", "price": 1100000, "product_id": 3042, "qty": 10000, "manual_price": True, "enabled": True},
]

SYRIATEL_FAWATEER_OFFERS = [
    {"id": "syriatel_fawateer_3041_5000",   "label": "🧾 فاتورة سيريتل 5,000 ل.س",   "price": 5500,   "product_id": 3041, "qty": 50,   "manual_price": True, "enabled": True},
    {"id": "syriatel_fawateer_3041_10000",  "label": "🧾 فاتورة سيريتل 10,000 ل.س",  "price": 11000,  "product_id": 3041, "qty": 100,  "manual_price": True, "enabled": True},
    {"id": "syriatel_fawateer_3041_25000",  "label": "🧾 فاتورة سيريتل 25,000 ل.س",  "price": 27500,  "product_id": 3041, "qty": 250,  "manual_price": True, "enabled": True},
    {"id": "syriatel_fawateer_3041_50000",  "label": "🧾 فاتورة سيريتل 50,000 ل.س",  "price": 55000,  "product_id": 3041, "qty": 500,  "manual_price": True, "enabled": True},
    {"id": "syriatel_fawateer_3041_100000", "label": "🧾 فاتورة سيريتل 100,000 ل.س", "price": 110000, "product_id": 3041, "qty": 1000, "manual_price": True, "enabled": True},
    {"id": "syriatel_fawateer_3041_250000", "label": "🧾 فاتورة سيريتل 250,000 ل.س", "price": 275000, "product_id": 3041, "qty": 2500, "manual_price": True, "enabled": True},
    {"id": "syriatel_fawateer_3041_500000", "label": "🧾 فاتورة سيريتل 500,000 ل.س", "price": 550000, "product_id": 3041, "qty": 5000, "manual_price": True, "enabled": True},
]

SYRIATEL_CASH_OFFERS = [
    {"id": "syriatel_cash_3040_5000",   "label": "💵 سيريتل كاش 5,000 ل.س",   "price": 5500,   "product_id": 3040, "qty": 50,   "manual_price": True, "enabled": True},
    {"id": "syriatel_cash_3040_10000",  "label": "💵 سيريتل كاش 10,000 ل.س",  "price": 11000,  "product_id": 3040, "qty": 100,  "manual_price": True, "enabled": True},
    {"id": "syriatel_cash_3040_25000",  "label": "💵 سيريتل كاش 25,000 ل.س",  "price": 27500,  "product_id": 3040, "qty": 250,  "manual_price": True, "enabled": True},
    {"id": "syriatel_cash_3040_50000",  "label": "💵 سيريتل كاش 50,000 ل.س",  "price": 55000,  "product_id": 3040, "qty": 500,  "manual_price": True, "enabled": True},
    {"id": "syriatel_cash_3040_100000", "label": "💵 سيريتل كاش 100,000 ل.س", "price": 110000, "product_id": 3040, "qty": 1000, "manual_price": True, "enabled": True},
    {"id": "syriatel_cash_3040_250000", "label": "💵 سيريتل كاش 250,000 ل.س", "price": 275000, "product_id": 3040, "qty": 2500, "manual_price": True, "enabled": True},
    {"id": "syriatel_cash_3040_500000", "label": "💵 سيريتل كاش 500,000 ل.س", "price": 550000, "product_id": 3040, "qty": 5000, "manual_price": True, "enabled": True},
]

# رصيد MTN: قيم qty الأصلية بالليرة الجديدة (10 = 1,000 ل.س قديمة، 30 = 3,000، إلخ)
MTN_BALANCE_OFFERS = [
    {"id": "mtn_balance_3043_1000",   "label": "📲 رصيد MTN 1,000 ل.س",   "price": 1500,   "product_id": 3043, "qty": 10,   "manual_price": True, "enabled": True},
    {"id": "mtn_balance_3043_3000",   "label": "📲 رصيد MTN 3,000 ل.س",   "price": 3500,   "product_id": 3043, "qty": 30,   "manual_price": True, "enabled": True},
    {"id": "mtn_balance_3043_7000",   "label": "📲 رصيد MTN 7,000 ل.س",   "price": 8000,   "product_id": 3043, "qty": 70,   "manual_price": True, "enabled": True},
    {"id": "mtn_balance_3043_15000",  "label": "📲 رصيد MTN 15,000 ل.س",  "price": 16500,  "product_id": 3043, "qty": 150,  "manual_price": True, "enabled": True},
    {"id": "mtn_balance_3043_26000",  "label": "📲 رصيد MTN 26,000 ل.س",  "price": 29000,  "product_id": 3043, "qty": 260,  "manual_price": True, "enabled": True},
    {"id": "mtn_balance_3043_36000",  "label": "📲 رصيد MTN 36,000 ل.س",  "price": 40000,  "product_id": 3043, "qty": 360,  "manual_price": True, "enabled": True},
    {"id": "mtn_balance_3043_48000",  "label": "📲 رصيد MTN 48,000 ل.س",  "price": 53000,  "product_id": 3043, "qty": 480,  "manual_price": True, "enabled": True},
    {"id": "mtn_balance_3043_70000",  "label": "📲 رصيد MTN 70,000 ل.س",  "price": 77000,  "product_id": 3043, "qty": 700,  "manual_price": True, "enabled": True},
    {"id": "mtn_balance_3043_250000", "label": "📲 رصيد MTN 250,000 ل.س", "price": 275000, "product_id": 3043, "qty": 2500, "manual_price": True, "enabled": True},
    {"id": "mtn_balance_3043_480000", "label": "📲 رصيد MTN 480,000 ل.س", "price": 528000, "product_id": 3043, "qty": 4800, "manual_price": True, "enabled": True},
]

MTN_GAS_OFFERS = [
    {"id": "mtn_gas_3046_10000",   "label": "⛽ كازية MTN 10,000 ل.س",    "price": 11000,   "product_id": 3046, "qty": 100,   "manual_price": True, "enabled": True},
    {"id": "mtn_gas_3046_25000",   "label": "⛽ كازية MTN 25,000 ل.س",    "price": 27500,   "product_id": 3046, "qty": 250,   "manual_price": True, "enabled": True},
    {"id": "mtn_gas_3046_50000",   "label": "⛽ كازية MTN 50,000 ل.س",    "price": 55000,   "product_id": 3046, "qty": 500,   "manual_price": True, "enabled": True},
    {"id": "mtn_gas_3046_100000",  "label": "⛽ كازية MTN 100,000 ل.س",   "price": 110000,  "product_id": 3046, "qty": 1000,  "manual_price": True, "enabled": True},
    {"id": "mtn_gas_3046_500000",  "label": "⛽ كازية MTN 500,000 ل.س",   "price": 550000,  "product_id": 3046, "qty": 5000,  "manual_price": True, "enabled": True},
    {"id": "mtn_gas_3046_1000000", "label": "⛽ كازية MTN 1,000,000 ل.س", "price": 1100000, "product_id": 3046, "qty": 10000, "manual_price": True, "enabled": True},
]

MTN_FAWATEER_OFFERS = [
    {"id": "mtn_fawateer_3045_5000",   "label": "🧾 فاتورة MTN 5,000 ل.س",   "price": 5500,   "product_id": 3045, "qty": 50,   "manual_price": True, "enabled": True},
    {"id": "mtn_fawateer_3045_10000",  "label": "🧾 فاتورة MTN 10,000 ل.س",  "price": 11000,  "product_id": 3045, "qty": 100,  "manual_price": True, "enabled": True},
    {"id": "mtn_fawateer_3045_25000",  "label": "🧾 فاتورة MTN 25,000 ل.س",  "price": 27500,  "product_id": 3045, "qty": 250,  "manual_price": True, "enabled": True},
    {"id": "mtn_fawateer_3045_50000",  "label": "🧾 فاتورة MTN 50,000 ل.س",  "price": 55000,  "product_id": 3045, "qty": 500,  "manual_price": True, "enabled": True},
    {"id": "mtn_fawateer_3045_100000", "label": "🧾 فاتورة MTN 100,000 ل.س", "price": 110000, "product_id": 3045, "qty": 1000, "manual_price": True, "enabled": True},
    {"id": "mtn_fawateer_3045_250000", "label": "🧾 فاتورة MTN 250,000 ل.س", "price": 275000, "product_id": 3045, "qty": 2500, "manual_price": True, "enabled": True},
    {"id": "mtn_fawateer_3045_500000", "label": "🧾 فاتورة MTN 500,000 ل.س", "price": 550000, "product_id": 3045, "qty": 5000, "manual_price": True, "enabled": True},
]

MTN_CASH_OFFERS = [
    {"id": "mtn_cash_3044_5000",   "label": "💵 MTN كاش 5,000 ل.س",   "price": 5500,   "product_id": 3044, "qty": 50,   "manual_price": True, "enabled": True},
    {"id": "mtn_cash_3044_10000",  "label": "💵 MTN كاش 10,000 ل.س",  "price": 11000,  "product_id": 3044, "qty": 100,  "manual_price": True, "enabled": True},
    {"id": "mtn_cash_3044_25000",  "label": "💵 MTN كاش 25,000 ل.س",  "price": 27500,  "product_id": 3044, "qty": 250,  "manual_price": True, "enabled": True},
    {"id": "mtn_cash_3044_50000",  "label": "💵 MTN كاش 50,000 ل.س",  "price": 55000,  "product_id": 3044, "qty": 500,  "manual_price": True, "enabled": True},
    {"id": "mtn_cash_3044_100000", "label": "💵 MTN كاش 100,000 ل.س", "price": 110000, "product_id": 3044, "qty": 1000, "manual_price": True, "enabled": True},
    {"id": "mtn_cash_3044_250000", "label": "💵 MTN كاش 250,000 ل.س", "price": 275000, "product_id": 3044, "qty": 2500, "manual_price": True, "enabled": True},
    {"id": "mtn_cash_3044_500000", "label": "💵 MTN كاش 500,000 ل.س", "price": 550000, "product_id": 3044, "qty": 5000, "manual_price": True, "enabled": True},
]

SHAMCASH_BAL_OFFERS = [
    # هامش ربح 10% فوق التكلفة. الأسعار محسوبة يدوياً ومدورة لأقرب 500 ل.س.
    {"id": "shamcash_bal_3096_min10k", "label": "💳 شحن SHAM CASH 10,000 ل.س (≈ 0.67$)", "price": 11000, "product_id": 3096, "qty": 0.67, "manual_price": True, "enabled": True},
    {"id": "shamcash_bal_3096_50", "label": "💳 شحن SHAM CASH 50$", "price": 825000, "product_id": 3096, "qty": 50, "manual_price": True, "enabled": True},
    {"id": "shamcash_bal_3096_100", "label": "💳 شحن SHAM CASH 100$", "price": 1650000, "product_id": 3096, "qty": 100, "manual_price": True, "enabled": True},
    {"id": "shamcash_bal_3096_500", "label": "💳 شحن SHAM CASH 500$", "price": 8247000, "product_id": 3096, "qty": 500, "manual_price": True, "enabled": True},
    {"id": "shamcash_bal_3096_1000", "label": "💳 شحن SHAM CASH 1,000$", "price": 16494000, "product_id": 3096, "qty": 1000, "manual_price": True, "enabled": True},
]

PAYEER_OFFERS = [
    # هامش ربح 12% فوق التكلفة (qty × cost_usd × 14700 × 1.12) مدور لأقرب 500 ل.س.
    {"id": "payeer_3047_50", "label": "🟢 شحن PAYEER 50$", "price": 854000, "product_id": 3047, "cost_usd": 1.037109, "qty": 50, "manual_price": True, "enabled": True},
    {"id": "payeer_3047_200", "label": "🟢 شحن PAYEER 200$", "price": 3415000, "product_id": 3047, "cost_usd": 1.037109, "qty": 200, "manual_price": True, "enabled": True},
    {"id": "payeer_3047_500", "label": "🟢 شحن PAYEER 500$", "price": 8537500, "product_id": 3047, "cost_usd": 1.037109, "qty": 500, "manual_price": True, "enabled": True},
    {"id": "payeer_3047_1000", "label": "🟢 شحن PAYEER 1,000$", "price": 17075000, "product_id": 3047, "cost_usd": 1.037109, "qty": 1000, "manual_price": True, "enabled": True},
    {"id": "payeer_3047_2000", "label": "🟢 شحن PAYEER 2,000$", "price": 34150000, "product_id": 3047, "cost_usd": 1.037109, "qty": 2000, "manual_price": True, "enabled": True},
    {"id": "payeer_3047_5000", "label": "🟢 شحن PAYEER 5,000$", "price": 85375000, "product_id": 3047, "cost_usd": 1.037109, "qty": 5000, "manual_price": True, "enabled": True},
]

PERFECTMONEY_OFFERS = [
    # هامش ربح 12% فوق التكلفة.
    {"id": "perfectmoney_3049_10", "label": "🟡 Perfect Money 10$", "price": 177000, "product_id": 3049, "cost_usd": 1.073406, "qty": 10, "manual_price": True, "enabled": True},
    {"id": "perfectmoney_3049_25", "label": "🟡 Perfect Money 25$", "price": 442000, "product_id": 3049, "cost_usd": 1.073406, "qty": 25, "manual_price": True, "enabled": True},
    {"id": "perfectmoney_3049_50", "label": "🟡 Perfect Money 50$", "price": 884000, "product_id": 3049, "cost_usd": 1.073406, "qty": 50, "manual_price": True, "enabled": True},
    {"id": "perfectmoney_3049_100", "label": "🟡 Perfect Money 100$", "price": 1767500, "product_id": 3049, "cost_usd": 1.073406, "qty": 100, "manual_price": True, "enabled": True},
]

PAYONEER_OFFERS = [
    {"id": "payoneer_3052_100", "label": "🟠 Payoneer 100$", "price": 157768500, "product_id": 3052, "cost_usd": 107.325317, "qty": 100, "enabled": True},  # auto-disabled: price needs manual review
    {"id": "payoneer_3052_250", "label": "🟠 Payoneer 250$", "price": 394421000, "product_id": 3052, "cost_usd": 107.325317, "qty": 250, "enabled": True},  # auto-disabled: price needs manual review
]

CLIQ_JORDAN_OFFERS = [
    {"id": "cliq_jordan_7771_5000", "label": "🏦 CLIQ JORDAN 5,000 د.أ", "price": 107369000, "product_id": 7771, "cost_usd": 1.4608, "qty": 5000, "enabled": True},  # auto-disabled: price needs manual review
    {"id": "cliq_jordan_7771_25000", "label": "🏦 CLIQ JORDAN 25,000 د.أ", "price": 536844000, "product_id": 7771, "cost_usd": 1.4608, "qty": 25000, "enabled": True},  # auto-disabled: price needs manual review
    {"id": "cliq_jordan_7771_50000", "label": "🏦 CLIQ JORDAN 50,000 د.أ", "price": 1073688000, "product_id": 7771, "cost_usd": 1.4608, "qty": 50000, "enabled": True},  # auto-disabled: price needs manual review
    {"id": "cliq_jordan_7771_100000", "label": "🏦 CLIQ JORDAN 100,000 د.أ", "price": 2147376000, "product_id": 7771, "cost_usd": 1.4608, "qty": 100000, "enabled": True},  # auto-disabled: price needs manual review
    {"id": "cliq_jordan_7771_250000", "label": "🏦 CLIQ JORDAN 250,000 د.أ", "price": 5368440000, "product_id": 7771, "cost_usd": 1.4608, "qty": 250000, "enabled": True},  # auto-disabled: price needs manual review
    {"id": "cliq_jordan_7771_500000", "label": "🏦 CLIQ JORDAN 500,000 د.أ", "price": 10736880000, "product_id": 7771, "cost_usd": 1.4608, "qty": 500000, "enabled": True},  # auto-disabled: price needs manual review
]

USDT_TRC20_OFFERS = [
    # هامش ربح 12% فوق التكلفة.
    {"id": "usdt_trc20_4252_10", "label": "₮ USDT TRC20 — 10$", "price": 170000, "product_id": 4252, "cost_usd": 1.03, "qty": 10, "manual_price": True, "enabled": True},
    {"id": "usdt_trc20_4252_25", "label": "₮ USDT TRC20 — 25$", "price": 424000, "product_id": 4252, "cost_usd": 1.03, "qty": 25, "manual_price": True, "enabled": True},
    {"id": "usdt_trc20_4252_50", "label": "₮ USDT TRC20 — 50$", "price": 848000, "product_id": 4252, "cost_usd": 1.03, "qty": 50, "manual_price": True, "enabled": True},
    {"id": "usdt_trc20_4252_100", "label": "₮ USDT TRC20 — 100$", "price": 1696000, "product_id": 4252, "cost_usd": 1.03, "qty": 100, "manual_price": True, "enabled": True},
]

USDT_BEP20_OFFERS = [
    # هامش ربح 12% فوق التكلفة.
    {"id": "usdt_bep20_4251_10", "label": "₮ USDT BEP20 — 10$", "price": 170000, "product_id": 4251, "cost_usd": 1.03, "qty": 10, "manual_price": True, "enabled": True},
    {"id": "usdt_bep20_4251_50", "label": "₮ USDT BEP20 — 50$", "price": 848000, "product_id": 4251, "cost_usd": 1.03, "qty": 50, "manual_price": True, "enabled": True},
    {"id": "usdt_bep20_4251_100", "label": "₮ USDT BEP20 — 100$", "price": 1696000, "product_id": 4251, "cost_usd": 1.03, "qty": 100, "manual_price": True, "enabled": True},
    {"id": "usdt_bep20_4251_250", "label": "₮ USDT BEP20 — 250$", "price": 4239500, "product_id": 4251, "cost_usd": 1.03, "qty": 250, "manual_price": True, "enabled": True},
    {"id": "usdt_bep20_4251_500", "label": "₮ USDT BEP20 — 500$", "price": 8479000, "product_id": 4251, "cost_usd": 1.03, "qty": 500, "manual_price": True, "enabled": True},
]

TOUCH_OFFERS = [
    {"id": "touch_3090", "label": "MTC 1.67$", "price": 38000, "product_id": 3090, "cost_usd": 2.289495, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "touch_3091", "label": "MTC 3.79$", "price": 80500, "product_id": 3091, "cost_usd": 4.88943, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "touch_3092", "label": "MTC 4.5$", "price": 94500, "product_id": 3092, "cost_usd": 5.722245, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "touch_3093", "label": "MTC 7.58$", "price": 154500, "product_id": 3093, "cost_usd": 9.36295, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "touch_3094", "label": "MTC 15.15$", "price": 298500, "product_id": 3094, "cost_usd": 18.12094, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "touch_3095", "label": "MTC 22.73$", "price": 445500, "product_id": 3095, "cost_usd": 27.04609, "qty": 1, "manual_price": True, "enabled": True},
]

ALFA_OFFERS = [
    {"id": "alfa_3086", "label": "ALFA 3.03$", "price": 67000, "product_id": 3086, "cost_usd": 4.057611, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "alfa_3087", "label": "ALFA 4.50$", "price": 94500, "product_id": 3087, "cost_usd": 5.722245, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "alfa_3088", "label": "ALFA 7.58$", "price": 154500, "product_id": 3088, "cost_usd": 9.36295, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "alfa_3089", "label": "ALFA 15.15$", "price": 295000, "product_id": 3089, "cost_usd": 17.89209, "qty": 1, "manual_price": True, "enabled": True},
]

WHISH_OFFERS = [
    # هامش ربح 12% فوق التكلفة.
    {"id": "whish_7770_50", "label": "🇱🇧 Whish Money 50$", "price": 854000, "product_id": 7770, "cost_usd": 1.037188, "qty": 50, "manual_price": True, "enabled": True},
    {"id": "whish_7770_100", "label": "🇱🇧 Whish Money 100$", "price": 1708000, "product_id": 7770, "cost_usd": 1.037188, "qty": 100, "manual_price": True, "enabled": True},
    {"id": "whish_7770_500", "label": "🇱🇧 Whish Money 500$", "price": 8538500, "product_id": 7770, "cost_usd": 1.037188, "qty": 500, "manual_price": True, "enabled": True},
    {"id": "whish_7770_1000", "label": "🇱🇧 Whish Money 1,000$", "price": 17076500, "product_id": 7770, "cost_usd": 1.037188, "qty": 1000, "manual_price": True, "enabled": True},
    {"id": "whish_7770_2000", "label": "🇱🇧 Whish Money 2,000$", "price": 34153000, "product_id": 7770, "cost_usd": 1.037188, "qty": 2000, "manual_price": True, "enabled": True},
]

ASIACELL_OFFERS = [
    # هامش ربح 12% فوق التكلفة.
    {"id": "asiacell_3055_2000", "label": "اسيا سيل — 2,000", "price": 23000, "product_id": 3055, "cost_usd": 0.000693, "qty": 2000, "manual_price": True, "enabled": True},
    {"id": "asiacell_3055_3000", "label": "اسيا سيل — 3,000", "price": 34500, "product_id": 3055, "cost_usd": 0.000693, "qty": 3000, "manual_price": True, "enabled": True},
    {"id": "asiacell_3055_4000", "label": "اسيا سيل — 4,000", "price": 46000, "product_id": 3055, "cost_usd": 0.000693, "qty": 4000, "manual_price": True, "enabled": True},
    {"id": "asiacell_3055_5000", "label": "اسيا سيل — 5,000", "price": 57500, "product_id": 3055, "cost_usd": 0.000693, "qty": 5000, "manual_price": True, "enabled": True},
    {"id": "asiacell_3055_6000", "label": "اسيا سيل — 6,000", "price": 68500, "product_id": 3055, "cost_usd": 0.000693, "qty": 6000, "manual_price": True, "enabled": True},
    {"id": "asiacell_3055_8000", "label": "اسيا سيل — 8,000", "price": 91500, "product_id": 3055, "cost_usd": 0.000693, "qty": 8000, "manual_price": True, "enabled": True},
    {"id": "asiacell_3055_10000", "label": "اسيا سيل — 10,000", "price": 114500, "product_id": 3055, "cost_usd": 0.000693, "qty": 10000, "manual_price": True, "enabled": True},
    {"id": "asiacell_3055_12000", "label": "اسيا سيل — 12,000", "price": 137000, "product_id": 3055, "cost_usd": 0.000693, "qty": 12000, "manual_price": True, "enabled": True},
    {"id": "asiacell_3055_15000", "label": "اسيا سيل — 15,000", "price": 171500, "product_id": 3055, "cost_usd": 0.000693, "qty": 15000, "manual_price": True, "enabled": True},
    {"id": "asiacell_3055_30000", "label": "اسيا سيل — 30,000", "price": 342500, "product_id": 3055, "cost_usd": 0.000693, "qty": 30000, "manual_price": True, "enabled": True},
    {"id": "asiacell_3055_50000", "label": "اسيا سيل — 50,000", "price": 570500, "product_id": 3055, "cost_usd": 0.000693, "qty": 50000, "manual_price": True, "enabled": True},
    {"id": "asiacell_3056", "label": "ASIA CELL 5000", "price": 63500, "product_id": 3056, "cost_usd": 3.833736, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "asiacell_3057", "label": "ASIA CELL 10000", "price": 126500, "product_id": 3057, "cost_usd": 7.666475, "qty": 1, "manual_price": True, "enabled": True},
]

ZAIN_IRAQ_OFFERS = [
    # هامش ربح 12% فوق التكلفة (qty × cost_usd × 14700 × 1.12) مدور لأقرب 500 ل.س.
    {"id": "zain_iraq_3304_5000", "label": "Zain 5000 — 5,000", "price": 68000, "product_id": 3304, "cost_usd": 0.000826, "qty": 5000, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3304_10000", "label": "Zain 5000 — 10,000", "price": 136000, "product_id": 3304, "cost_usd": 0.000826, "qty": 10000, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3304_15000", "label": "Zain 5000 — 15,000", "price": 204000, "product_id": 3304, "cost_usd": 0.000826, "qty": 15000, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3304_20000", "label": "Zain 5000 — 20,000", "price": 272000, "product_id": 3304, "cost_usd": 0.000826, "qty": 20000, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3304_25000", "label": "Zain 5000 — 25,000", "price": 340000, "product_id": 3304, "cost_usd": 0.000826, "qty": 25000, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3304_30000", "label": "Zain 5000 — 30,000", "price": 408000, "product_id": 3304, "cost_usd": 0.000826, "qty": 30000, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3304_40000", "label": "Zain 5000 — 40,000", "price": 544000, "product_id": 3304, "cost_usd": 0.000826, "qty": 40000, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3304_50000", "label": "Zain 5000 — 50,000", "price": 680000, "product_id": 3304, "cost_usd": 0.000826, "qty": 50000, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3305", "label": "10000 Zain", "price": 127500, "product_id": 3305, "cost_usd": 7.74309, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3306", "label": "15000 Zain", "price": 191500, "product_id": 3306, "cost_usd": 11.612645, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3307", "label": "20000 Zain", "price": 255000, "product_id": 3307, "cost_usd": 15.48419, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3308", "label": "25000 Zain", "price": 319000, "product_id": 3308, "cost_usd": 19.355735, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3309", "label": "30000 Zain", "price": 382500, "product_id": 3309, "cost_usd": 23.22529, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3310", "label": "40000 Zain", "price": 510000, "product_id": 3310, "cost_usd": 30.96838, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "zain_iraq_3311", "label": "50000 Zain", "price": 637500, "product_id": 3311, "cost_usd": 38.709481, "qty": 1, "manual_price": True, "enabled": True},
]

TURKCELL_OFFERS = [
    {"id": "turkcell_2855", "label": "200 ليرات تروكسل", "price": 149500, "product_id": 2855, "cost_usd": 9.063455, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "turkcell_2856", "label": "TRUKCELL 1000DK 2GB", "price": 203500, "product_id": 2856, "cost_usd": 12.333025, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "turkcell_2857", "label": "TRUKCELL 1000DK 4GB", "price": 233500, "product_id": 2857, "cost_usd": 14.169795, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "turkcell_2858", "label": "TRUKCELL 1000DK 8GB", "price": 280500, "product_id": 2858, "cost_usd": 17.01848, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "turkcell_2861", "label": "TRUKCELL 1000DK 34GB", "price": 351500, "product_id": 2861, "cost_usd": 21.329815, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "turkcell_2863", "label": "TRUKCELL ليرات كسر 50", "price": 35500, "product_id": 2863, "cost_usd": 2.134275, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "turkcell_3035", "label": "TRUKCELL ليرات كسر 150", "price": 103000, "product_id": 3035, "cost_usd": 6.25457, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "turkcell_3036", "label": "TRUKCELL 1000DK 12GB", "price": 396000, "product_id": 3036, "cost_usd": 24.04119, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "turkcell_3037", "label": "TRUKCELL 1000DK 20GB", "price": 430500, "product_id": 3037, "cost_usd": 26.127705, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "turkcell_3038", "label": "TRUKCELL 1000DK 50GB", "price": 357000, "product_id": 3038, "cost_usd": 21.66712, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "turkcell_3523", "label": "ليرات كسر 200", "price": 33500, "product_id": 3523, "cost_usd": 2.034775, "qty": 1, "manual_price": True, "enabled": True},
]

TOSLA_OFFERS = [
    # هامش ربح 12% فوق التكلفة (qty × cost_usd × 14700 × 1.12) مدور لأقرب 500 ل.س.
    {"id": "tosla_3051_100", "label": "🇹🇷 TOSLA 100 ₺", "price": 5131500, "product_id": 3051, "cost_usd": 3.116569, "qty": 100, "manual_price": True, "enabled": True},
    {"id": "tosla_3051_500", "label": "🇹🇷 TOSLA 500 ₺", "price": 25656000, "product_id": 3051, "cost_usd": 3.116569, "qty": 500, "manual_price": True, "enabled": True},
    {"id": "tosla_3051_1000", "label": "🇹🇷 TOSLA 1,000 ₺", "price": 51311500, "product_id": 3051, "cost_usd": 3.116569, "qty": 1000, "manual_price": True, "enabled": True},
    {"id": "tosla_3051_2000", "label": "🇹🇷 TOSLA 2,000 ₺", "price": 102622500, "product_id": 3051, "cost_usd": 3.116569, "qty": 2000, "manual_price": True, "enabled": True},
]

OLDUBIL_OFFERS = [
    # هامش ربح 12% فوق التكلفة (qty × cost_usd × 14700 × 1.12) مدور لأقرب 500 ل.س.
    {"id": "oldubil_3050_100", "label": "🇹🇷 Oldubil 100 ₺", "price": 5131500, "product_id": 3050, "cost_usd": 3.116569, "qty": 100, "manual_price": True, "enabled": True},
    {"id": "oldubil_3050_500", "label": "🇹🇷 Oldubil 500 ₺", "price": 25656000, "product_id": 3050, "cost_usd": 3.116569, "qty": 500, "manual_price": True, "enabled": True},
    {"id": "oldubil_3050_1000", "label": "🇹🇷 Oldubil 1,000 ₺", "price": 51311500, "product_id": 3050, "cost_usd": 3.116569, "qty": 1000, "manual_price": True, "enabled": True},
    {"id": "oldubil_3050_2000", "label": "🇹🇷 Oldubil 2,000 ₺", "price": 102622500, "product_id": 3050, "cost_usd": 3.116569, "qty": 2000, "manual_price": True, "enabled": True},
]

VODAFONE_CASH_OFFERS = [
    # هامش ربح 12% فوق التكلفة (qty × cost_usd × 14700 × 1.12) مدور لأقرب 500 ل.س.
    {"id": "vodafone_cash_3054_50", "label": "🇪🇬 Vodafone Cash 50 جنيه", "price": 18500, "product_id": 3054, "cost_usd": 0.0222, "qty": 50, "manual_price": True, "enabled": True},
    {"id": "vodafone_cash_3054_100", "label": "🇪🇬 Vodafone Cash 100 جنيه", "price": 37000, "product_id": 3054, "cost_usd": 0.0222, "qty": 100, "manual_price": True, "enabled": True},
    {"id": "vodafone_cash_3054_500", "label": "🇪🇬 Vodafone Cash 500 جنيه", "price": 183000, "product_id": 3054, "cost_usd": 0.0222, "qty": 500, "manual_price": True, "enabled": True},
    {"id": "vodafone_cash_3054_1000", "label": "🇪🇬 Vodafone Cash 1,000 جنيه", "price": 366000, "product_id": 3054, "cost_usd": 0.0222, "qty": 1000, "manual_price": True, "enabled": True},
    {"id": "vodafone_cash_3054_2000", "label": "🇪🇬 Vodafone Cash 2,000 جنيه", "price": 731500, "product_id": 3054, "cost_usd": 0.0222, "qty": 2000, "manual_price": True, "enabled": True},
]

RCELL_OFFERS = [
    # هامش ربح 12% فوق التكلفة.
    {"id": "rcell_3048_25", "label": "📱 R-Cell 25", "price": 66000, "product_id": 3048, "cost_usd": 0.16003, "qty": 25, "manual_price": True, "enabled": True},
    {"id": "rcell_3048_50", "label": "📱 R-Cell 50", "price": 132000, "product_id": 3048, "cost_usd": 0.16003, "qty": 50, "manual_price": True, "enabled": True},
]

SELAM_TELECOM_OFFERS = [
    {"id": "selam_telecom_3080", "label": "40GB باقة شهر", "price": 55000, "product_id": 3080, "cost_usd": 3.33922, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "selam_telecom_3081", "label": "120GB باقة سلام السنوية", "price": 385000, "product_id": 3081, "cost_usd": 23.373545, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "selam_telecom_3082", "label": "40GB باقة الطلاب والنقابات", "price": 44500, "product_id": 3082, "cost_usd": 2.697445, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "selam_telecom_3083", "label": "60GB باقة 3 اشهر", "price": 118500, "product_id": 3083, "cost_usd": 7.19186, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "selam_telecom_3084", "label": "10GB باقة شهر", "price": 34000, "product_id": 3084, "cost_usd": 2.05567, "qty": 1, "manual_price": True, "enabled": True},
    {"id": "selam_telecom_3085", "label": "3MB باقة انترنت مفتوح", "price": 76500, "product_id": 3085, "cost_usd": 4.623766, "qty": 1, "manual_price": True, "enabled": True},
]

PAPRA_OFFERS: list = []  # لا منتجات متاحة على Fastcard حالياً


FASTCARD_CATEGORIES = {
    "pm": {
        "title": "👑 عضويات ببجي موبايل",
        "game": "PUBG",
        "input_fields": [{"key": "playerId", "label": "Player ID (الرقم الموجود بحسابك ببجي)", "type": "id"}],
        "back_callback": "store:pubg",
        "offers_attr": "PUBG_MEMBERSHIPS",
    },
    "fm": {
        "title": "👑 عضويات فري فاير",
        "game": "FREEFIRE",
        "input_fields": [{"key": "playerId", "label": "Player ID (الرقم الموجود بحسابك فري فاير)", "type": "id"}],
        "back_callback": "store:freefire",
        "offers_attr": "FREEFIRE_MEMBERSHIPS",
    },
    "pc": {
        "title": "🎟️ أكواد شدات ببجي",
        "game": "PUBG",
        "input_fields": [],
        "back_callback": "store:pubg",
        "offers_attr": "PUBG_CODES",
    },
    "fc": {
        "title": "🎟️ أكواد جواهر فري فاير",
        "game": "FREEFIRE",
        "input_fields": [],
        "back_callback": "store:freefire",
        "offers_attr": "FREEFIRE_CODES",
    },
    "bs": {
        "title": "🎮 Brawl Stars (شحن مباشر)",
        "game": "BRAWL_STARS",
        "input_fields": SUPERCELL_FIELDS,
        "back_callback": "store:supercell",
        "offers_attr": "BRAWL_STARS_OFFERS",
    },
    "coc": {
        "title": "🎮 Clash of Clans (شحن مباشر)",
        "game": "CLASH_OF_CLANS",
        "input_fields": SUPERCELL_FIELDS,
        "back_callback": "store:supercell",
        "offers_attr": "CLASH_OF_CLANS_OFFERS",
    },
    "cr": {
        "title": "🎮 Clash Royale (شحن مباشر)",
        "game": "CLASH_ROYALE",
        "input_fields": SUPERCELL_FIELDS,
        "back_callback": "store:supercell",
        "offers_attr": "CLASH_ROYALE_OFFERS",
    },
    "hd": {
        "title": "🎮 Hay Day (شحن مباشر)",
        "game": "HAY_DAY",
        "input_fields": SUPERCELL_FIELDS,
        "back_callback": "store:supercell",
        "offers_attr": "HAY_DAY_OFFERS",
    },
    "cod": {
        "title": "🪖 شدات Call of Duty Mobile",
        "game": "COD",
        "input_fields": COD_FIELDS,
        "back_callback": "store:cod",
        "offers_attr": "COD_OFFERS",
    },
    "cdbp": {
        "title": "🪖 Battle Pass — Call of Duty Mobile",
        "game": "COD",
        "input_fields": [{"key": "playerId", "label": "Player ID (الرقم داخل اللعبة)", "type": "id"}],
        "back_callback": "store:cod",
        "offers_attr": "COD_PASS_OFFERS",
    },
    "df": {
        "title": "🪖 Delta Force",
        "game": "DELTA_FORCE",
        "input_fields": [{"key": "playerId", "label": "الايدي تبع حسابك بدلتا فورس", "type": "id"}],
        "back_callback": "store:games",
        "offers_attr": "DELTA_FORCE_OFFERS",
    },
    "mc": {
        "title": "⛏️ Minecraft — أكواد كوينز",
        "game": "MINECRAFT",
        "input_fields": [],
        "back_callback": "store:games",
        "offers_attr": "MINECRAFT_OFFERS",
    },
    "fn": {
        "title": "🎮 Fortnite — أكواد V-Bucks",
        "game": "FORTNITE",
        "input_fields": [],
        "back_callback": "store:games",
        "offers_attr": "FORTNITE_OFFERS",
    },
    "lw": {
        "title": "🎲 Ludo World (شحن مباشر)",
        "game": "LUDO_WORLD",
        "input_fields": [{"key": "playerId", "label": "الايدي تبع حسابك بـ Ludo World", "type": "id"}],
        "back_callback": "store:ludo",
        "offers_attr": "LUDO_WORLD_OFFERS",
    },
    "lc": {
        "title": "🎲 Ludo Club (شحن مباشر)",
        "game": "LUDO_CLUB",
        "input_fields": [{"key": "playerId", "label": "الايدي تبع حسابك بـ Ludo Club", "type": "id"}],
        "back_callback": "store:ludo",
        "offers_attr": "LUDO_CLUB_OFFERS",
    },
    "yl": {
        "title": "🎲 Yalla Ludo (شحن مباشر)",
        "game": "YALLA_LUDO",
        "input_fields": [{"key": "playerId", "label": "الايدي تبع حسابك بـ Yalla Ludo", "type": "id"}],
        "back_callback": "store:ludo",
        "offers_attr": "LUDO_YALLA_OFFERS",
    },
    # ===== ألعاب جديدة =====
    "ff_s2": {
        "title": "🔥 فري فاير — سيرفر 2 (شحن تلقائي)",
        "game": "FREEFIRE_S2",
        "input_fields": [{"key": "playerId", "label": "🆔 الايدي تبعك بفري فاير", "type": "id"}],
        "back_callback": "store:freefire",
        "offers_attr": "FREEFIRE_S2_OFFERS",
    },
    "ff_eu": {
        "title": "🔥 فري فاير — أوروبا (شحن تلقائي)",
        "game": "FREEFIRE_EU",
        "input_fields": [{"key": "playerId", "label": "🆔 الايدي تبعك بفري فاير (حساب أوروبي)", "type": "id"}],
        "back_callback": "store:freefire",
        "offers_attr": "FREEFIRE_EU_OFFERS",
    },
    "bsk": {
        "title": "💀 Blood Strike — شحن مباشر",
        "game": "BLOOD_STRIKE",
        "input_fields": [{"key": "playerId", "label": "🆔 الايدي تبعك ببلود سترايك", "type": "id"}],
        "back_callback": "store:games",
        "offers_attr": "BLOOD_STRIKE_OFFERS",
    },
    "stmb": {
        "title": "🎮 Stumble Guys — شحن مباشر",
        "game": "STUMBLE_GUYS",
        "input_fields": [{"key": "playerId", "label": "🆔 الايدي تبعك بـ Stumble Guys", "type": "id"}],
        "back_callback": "store:games",
        "offers_attr": "STUMBLE_GUYS_OFFERS",
    },
    "ssus": {
        "title": "🛸 Super Sus — شحن مباشر",
        "game": "SUPER_SUS",
        "input_fields": [{"key": "playerId", "label": "🆔 الايدي تبعك بـ Super Sus", "type": "id"}],
        "back_callback": "store:games",
        "offers_attr": "SUPER_SUS_OFFERS",
    },
    # ===== Roblox — بطاقات هدايا =====
    "rblx_us":  {"title": "🎮 Roblox USA",      "game": "ROBLOX_US",  "input_fields": [], "back_callback": "cards:roblox", "offers_attr": "ROBLOX_USA_OFFERS"},
    "rblx_ksa": {"title": "🎮 Roblox KSA",      "game": "ROBLOX_KSA", "input_fields": [], "back_callback": "cards:roblox", "offers_attr": "ROBLOX_KSA_OFFERS"},
    "rblx_ae":  {"title": "🎮 Roblox UAE",      "game": "ROBLOX_AE",  "input_fields": [], "back_callback": "cards:roblox", "offers_attr": "ROBLOX_UAE_OFFERS"},
    # ===== Valorant — بطاقات VP =====
    "valo_gl":  {"title": "🔫 Valorant عالمي",  "game": "VALORANT_GL","input_fields": [], "back_callback": "cards:valorant", "offers_attr": "VALORANT_GLOBAL_OFFERS"},
    "valo_tr":  {"title": "🔫 Valorant تركي",   "game": "VALORANT_TR","input_fields": [], "back_callback": "cards:valorant", "offers_attr": "VALORANT_TR_OFFERS"},
    # ===== اشتراكات جديدة =====
    "spfy": {"title": "🎵 سبوتيفاي",     "game": "SPOTIFY",   "input_fields": [], "back_callback": "menu:subs", "offers_attr": "SPOTIFY_OFFERS"},
    "nova": {"title": "📺 Nova TV",       "game": "NOVA_TV",   "input_fields": [], "back_callback": "menu:subs", "offers_attr": "NOVA_TV_OFFERS"},
    "pvpn": {"title": "🛡️ Proton VPN",   "game": "PROTONVPN", "input_fields": [], "back_callback": "menu:subs", "offers_attr": "PROTONVPN_OFFERS"},
    "svpn": {"title": "🦈 SurfShark VPN","game": "SURFSHARK",  "input_fields": [], "back_callback": "menu:subs", "offers_attr": "SURFSHARK_OFFERS"},
    # ===== Cards: PlayStation =====
    "ps_us": {"title": "🎮 PlayStation USA",       "game": "PSN_US", "input_fields": [], "back_callback": "cards:psn", "offers_attr": "PSN_US_OFFERS"},
    "ps_sa": {"title": "🎮 PlayStation السعودية",  "game": "PSN_SA", "input_fields": [], "back_callback": "cards:psn", "offers_attr": "PSN_SA_OFFERS"},
    "ps_lb": {"title": "🎮 PlayStation لبنان",     "game": "PSN_LB", "input_fields": [], "back_callback": "cards:psn", "offers_attr": "PSN_LB_OFFERS"},
    "ps_ae": {"title": "🎮 PlayStation الإمارات", "game": "PSN_AE", "input_fields": [], "back_callback": "cards:psn", "offers_attr": "PSN_AE_OFFERS"},
    "ps_bh": {"title": "🎮 PlayStation البحرين",  "game": "PSN_BH", "input_fields": [], "back_callback": "cards:psn", "offers_attr": "PSN_BH_OFFERS"},
    "ps_qa": {"title": "🎮 PlayStation قطر",      "game": "PSN_QA", "input_fields": [], "back_callback": "cards:psn", "offers_attr": "PSN_QA_OFFERS"},
    "ps_om": {"title": "🎮 PlayStation عُمان",    "game": "PSN_OM", "input_fields": [], "back_callback": "cards:psn", "offers_attr": "PSN_OM_OFFERS"},
    "ps_uk": {"title": "🎮 PlayStation UK",        "game": "PSN_UK", "input_fields": [], "back_callback": "cards:psn", "offers_attr": "PSN_UK_OFFERS"},
    "ps_de": {"title": "🎮 PlayStation ألمانيا",  "game": "PSN_DE", "input_fields": [], "back_callback": "cards:psn", "offers_attr": "PSN_DE_OFFERS"},
    # ===== Cards: Steam =====
    "st_us": {"title": "🚂 Steam USA",       "game": "STEAM_US", "input_fields": [], "back_callback": "cards:steam", "offers_attr": "STEAM_US_OFFERS"},
    "st_sa": {"title": "🚂 Steam السعودية", "game": "STEAM_SA", "input_fields": [], "back_callback": "cards:steam", "offers_attr": "STEAM_SA_OFFERS"},
    "st_tr": {"title": "🚂 Steam تركيا",    "game": "STEAM_TR", "input_fields": [], "back_callback": "cards:steam", "offers_attr": "STEAM_TR_OFFERS"},
    "st_ae": {"title": "🚂 Steam الإمارات","game": "STEAM_AE", "input_fields": [], "back_callback": "cards:steam", "offers_attr": "STEAM_AE_OFFERS"},
    "st_kw": {"title": "🚂 Steam الكويت",  "game": "STEAM_KW", "input_fields": [], "back_callback": "cards:steam", "offers_attr": "STEAM_KW_OFFERS"},
    "st_om": {"title": "🚂 Steam عُمان",   "game": "STEAM_OM", "input_fields": [], "back_callback": "cards:steam", "offers_attr": "STEAM_OM_OFFERS"},
    # ===== Cards: iTunes =====
    "it_us": {"title": "🍎 iTunes USA", "game": "ITUNES_US", "input_fields": [], "back_callback": "cards:itunes", "offers_attr": "ITUNES_US_OFFERS"},
    "it_sa": {"title": "🍎 iTunes السعودية", "game": "ITUNES_SA", "input_fields": [], "back_callback": "cards:itunes", "offers_attr": "ITUNES_SA_OFFERS"},
    "it_uk": {"title": "🍎 iTunes UK", "game": "ITUNES_UK", "input_fields": [], "back_callback": "cards:itunes", "offers_attr": "ITUNES_UK_OFFERS"},
    # ===== Cards: Google Play =====
    "gp_us": {"title": "📱 Google Play USA", "game": "GPLAY_US", "input_fields": [], "back_callback": "cards:gplay", "offers_attr": "GPLAY_US_OFFERS"},
    "gp_sa": {"title": "📱 Google Play السعودية", "game": "GPLAY_SA", "input_fields": [], "back_callback": "cards:gplay", "offers_attr": "GPLAY_SA_OFFERS"},
    "gp_tr": {"title": "📱 Google Play تركيا", "game": "GPLAY_TR", "input_fields": [], "back_callback": "cards:gplay", "offers_attr": "GPLAY_TR_OFFERS"},
    # ===== Cards: Xbox =====
    "xb_us": {"title": "🎮 Xbox USA", "game": "XBOX_US", "input_fields": [], "back_callback": "cards:xbox", "offers_attr": "XBOX_US_OFFERS"},
    "xb_sa": {"title": "🎮 Xbox السعودية", "game": "XBOX_SA", "input_fields": [], "back_callback": "cards:xbox", "offers_attr": "XBOX_SA_OFFERS"},
    # ===== Cards: Razer Gold =====
    "rz_gl": {"title": "🟢 Razer Gold عالمي", "game": "RAZER_GL", "input_fields": [], "back_callback": "cards:razer", "offers_attr": "RAZER_GL_OFFERS"},
    "rz_us": {"title": "🟢 Razer Gold USA", "game": "RAZER_US", "input_fields": [], "back_callback": "cards:razer", "offers_attr": "RAZER_US_OFFERS"},
    "rz_tr": {"title": "🟢 Razer Gold تركيا", "game": "RAZER_TR", "input_fields": [], "back_callback": "cards:razer", "offers_attr": "RAZER_TR_OFFERS"},
    # ===== Cards: Nintendo / Netflix / VISA =====
    "nt_us": {"title": "🎮 Nintendo USA", "game": "NINTENDO", "input_fields": [], "back_callback": "cards:menu", "offers_attr": "NINTENDO_OFFERS"},
    "nflx":  {"title": "📺 Netflix — اشتراكات", "game": "NETFLIX", "input_fields": [], "back_callback": "cards:menu", "offers_attr": "NETFLIX_OFFERS"},
    "vs":    {"title": "💳 بطاقات VISA مدفوعة مسبقاً", "game": "VISA", "input_fields": [], "back_callback": "cards:menu", "offers_attr": "VISA_OFFERS"},

    # ===== اشتراكات تطبيقات (Apps Subscriptions) =====
    "sh":   {"title": "📺 Shahid VIP",        "game": "SHAHID",   "input_fields": [], "back_callback": "menu:subs", "offers_attr": "SHAHID_OFFERS"},
    "yt":   {"title": "📹 YouTube Premium",   "game": "YOUTUBE",
             "input_fields": [{"key": "playerId", "label": "📧 الإيميل المرتبط بحساب يوتيوب", "type": "email"}],
             "back_callback": "menu:subs", "offers_attr": "YOUTUBE_OFFERS"},
    "an":   {"title": "🎵 Anghami Plus",      "game": "ANGHAMI",
             "input_fields": [{"key": "playerId", "label": "👤 اسم المستخدم في انغامي", "type": "text"}],
             "back_callback": "menu:subs", "offers_attr": "ANGHAMI_OFFERS"},
    "osn":  {"title": "🍿 OSN+",              "game": "OSN",      "input_fields": [], "back_callback": "menu:subs", "offers_attr": "OSN_OFFERS"},
    "gpt":  {"title": "🤖 ChatGPT Plus",      "game": "CHATGPT",
             "input_fields": [{"key": "playerId", "label": "📧 إيميل حساب ChatGPT", "type": "email"}],
             "back_callback": "menu:subs", "offers_attr": "CHATGPT_OFFERS"},
    "cv":   {"title": "🎨 Canva Pro",         "game": "CANVA",
             "input_fields": [{"key": "playerId", "label": "📧 إيميل حساب Canva", "type": "email"}],
             "back_callback": "menu:subs", "offers_attr": "CANVA_OFFERS"},
    "snap": {"title": "👻 Snapchat+",         "game": "SNAPCHAT",
             "input_fields": [{"key": "playerId", "label": "👤 اسم مستخدم سناب شات", "type": "text"}],
             "back_callback": "menu:subs", "offers_attr": "SNAPCHAT_OFFERS"},
    "nv":   {"title": "🛡️ Nord VPN",          "game": "NORDVPN",  "input_fields": [], "back_callback": "menu:subs", "offers_attr": "NORDVPN_OFFERS"},
    "ev":   {"title": "🟦 Express VPN",       "game": "EXPRESSVPN","input_fields": [], "back_callback": "menu:subs", "offers_attr": "EXPRESSVPN_OFFERS"},
    "lv":   {"title": "⚡ LagoFast VPN",       "game": "LAGOFAST",
             "input_fields": [{"key": "playerId", "label": "📧 إيميلك", "type": "email"}],
             "back_callback": "menu:subs", "offers_attr": "LAGOFAST_OFFERS"},
    "gu":   {"title": "🚀 GearUP Booster",    "game": "GEARUP",   "input_fields": [], "back_callback": "menu:subs", "offers_attr": "GEARUP_OFFERS"},
    "tg":   {"title": "📢 تعزيز قنوات تلغرام", "game": "TGBOOST",
             "input_fields": [{"key": "playerId", "label": "🔗 رابط القناة (مثال: https://t.me/yourchannel)", "type": "text"}],
             "back_callback": "menu:subs", "offers_attr": "TGBOOST_OFFERS"},

    # ===== قسم الرصيد (مطابق لقسم الرصيد في موقع Fastcard cat=449) =====
    # — اتصالات سورية —
    # ملاحظة: 3039 (سيرياتيل بالنس) و 3043 (MTN بالنس) من نوع specificPackage في API
    # → تبقى قوائم محددة. باقي الأقسام (3040/3041/3042/3044/3045/3046) من نوع amount مفتوح
    # → فيها custom_amount=True يخلي الزبون يكتب المبلغ اللي بدّه بنفسه.
    # السعر يُحسب: المبلغ_بالليرة_القديمة × (1 + markup_pct/100) ثم تقريب لأقرب 500.
    # qty المرسلة للـ API = المبلغ_بالليرة_القديمة ÷ 100 (ليرة جديدة).
    "bal_syr":   {"title": "📱 رصيد SYRIATEL",   "game": "SYRIATEL_BAL",   "input_fields": [{"key": "playerId", "label": "📞 رقم الجوال (مثال: 0944xxxxxx)", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "SYRIATEL_BALANCE_OFFERS"},
    "bal_sgas":  {"title": "⛽ كازية SYRIATEL",  "game": "SYRIATEL_GAS",   "input_fields": [{"key": "playerId", "label": "📞 رقم الجوال المربوط بالكازية", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "SYRIATEL_GAS_OFFERS",
                  "custom_amount": True, "product_id": 3042, "min_amount": 5000, "max_amount": 2000000, "markup_pct": 10},
    "bal_sfaw":  {"title": "🧾 فواتير SYRIATEL",  "game": "SYRIATEL_FAW",   "input_fields": [{"key": "playerId", "label": "📞 رقم الاشتراك/الجوال", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "SYRIATEL_FAWATEER_OFFERS",
                  "custom_amount": True, "product_id": 3041, "min_amount": 1000, "max_amount": 1000000, "markup_pct": 10},
    "bal_scash": {"title": "💵 SYRIATEL CASH",   "game": "SYRIATEL_CASH",  "input_fields": [{"key": "playerId", "label": "📞 رقم محفظة سيرياتيل كاش", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "SYRIATEL_CASH_OFFERS",
                  "custom_amount": True, "product_id": 3040, "min_amount": 10000, "max_amount": 1000000, "markup_pct": 10},
    "bal_mtn":   {"title": "📱 رصيد MTN",        "game": "MTN_BAL",        "input_fields": [{"key": "playerId", "label": "📞 رقم الجوال (مثال: 0934xxxxxx)", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "MTN_BALANCE_OFFERS"},
    "bal_mgas":  {"title": "⛽ كازية MTN",       "game": "MTN_GAS",        "input_fields": [{"key": "playerId", "label": "📞 رقم الجوال المربوط بالكازية", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "MTN_GAS_OFFERS",
                  "custom_amount": True, "product_id": 3046, "min_amount": 5000, "max_amount": 2000000, "markup_pct": 10},
    "bal_mfaw":  {"title": "🧾 فواتير MTN",       "game": "MTN_FAW",        "input_fields": [{"key": "playerId", "label": "📞 رقم الاشتراك/الجوال", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "MTN_FAWATEER_OFFERS",
                  "custom_amount": True, "product_id": 3045, "min_amount": 1000, "max_amount": 1000000, "markup_pct": 10},
    "bal_mcash": {"title": "💵 MTN CASH",        "game": "MTN_CASH",       "input_fields": [{"key": "playerId", "label": "📞 رقم محفظة MTN كاش", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "MTN_CASH_OFFERS",
                  "custom_amount": True, "product_id": 3044, "min_amount": 1000, "max_amount": 1000000, "markup_pct": 10},
    "bal_sham":  {"title": "💳 SHAM CASH",       "game": "SHAMCASH_BAL",   "input_fields": [{"key": "playerId", "label": "🔢 رقم محفظة شام كاش", "type": "text"}], "back_callback": "store:balance", "offers_attr": "SHAMCASH_BAL_OFFERS"},
    # — محافظ رقمية / تحويلات بنكية —
    "bal_payeer":{"title": "🟢 PAYEER",          "game": "PAYEER",         "input_fields": [{"key": "playerId", "label": "🔢 رقم حساب Payeer (P...)", "type": "text"}], "back_callback": "store:balance", "offers_attr": "PAYEER_OFFERS"},
    "bal_pm":    {"title": "🟡 Perfect Money",   "game": "PERFECTMONEY",   "input_fields": [{"key": "playerId", "label": "🔢 رقم حساب Perfect Money (U...)", "type": "text"}], "back_callback": "store:balance", "offers_attr": "PERFECTMONEY_OFFERS"},
    "bal_payo":  {"title": "🟠 Payoneer",        "game": "PAYONEER",       "input_fields": [{"key": "playerId", "label": "📧 إيميل حساب Payoneer", "type": "email"}], "back_callback": "store:balance", "offers_attr": "PAYONEER_OFFERS"},
    "bal_cliq":  {"title": "🏦 CLIQ JORDAN",     "game": "CLIQ_JORDAN",    "input_fields": [{"key": "playerId", "label": "🏷️ Alias أو رقم الموبايل المسجّل بـ CLIQ", "type": "text"}], "back_callback": "store:balance", "offers_attr": "CLIQ_JORDAN_OFFERS"},
    # — عملات رقمية —
    "bal_trc":   {"title": "₮ USDT — TRC20",     "game": "USDT_TRC20",     "input_fields": [{"key": "playerId", "label": "🔗 عنوان محفظة TRC20 (يبدأ بـ T...)", "type": "text"}], "back_callback": "store:balance", "offers_attr": "USDT_TRC20_OFFERS"},
    "bal_bep":   {"title": "₮ USDT — BEP20",     "game": "USDT_BEP20",     "input_fields": [{"key": "playerId", "label": "🔗 عنوان محفظة BEP20 (يبدأ بـ 0x...)", "type": "text"}], "back_callback": "store:balance", "offers_attr": "USDT_BEP20_OFFERS"},
    # — اتصالات لبنان —
    "bal_touch": {"title": "🇱🇧 Touch (لبنان)",   "game": "TOUCH",          "input_fields": [{"key": "playerId", "label": "📞 رقم Touch", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "TOUCH_OFFERS"},
    "bal_alfa":  {"title": "🇱🇧 Alfa Telecom",    "game": "ALFA",           "input_fields": [{"key": "playerId", "label": "📞 رقم Alfa", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "ALFA_OFFERS"},
    "bal_whish": {"title": "🇱🇧 Whish Money",     "game": "WHISH",          "input_fields": [{"key": "playerId", "label": "📞 رقم محفظة Whish", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "WHISH_OFFERS"},
    # — اتصالات عراق —
    "bal_asia":  {"title": "🇮🇶 Asia Cell",       "game": "ASIACELL",       "input_fields": [{"key": "playerId", "label": "📞 رقم Asia Cell", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "ASIACELL_OFFERS"},
    "bal_zain":  {"title": "🇮🇶 Zain Iraq",       "game": "ZAIN_IRAQ",      "input_fields": [{"key": "playerId", "label": "📞 رقم Zain Iraq", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "ZAIN_IRAQ_OFFERS"},
    # — اتصالات تركيا —
    "bal_turk":  {"title": "🇹🇷 Turkcell",        "game": "TURKCELL",       "input_fields": [{"key": "playerId", "label": "📞 رقم Turkcell", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "TURKCELL_OFFERS"},
    "bal_tosla": {"title": "🇹🇷 TOSLA",           "game": "TOSLA",          "input_fields": [{"key": "playerId", "label": "📞 رقم/إيميل حساب TOSLA", "type": "text"}], "back_callback": "store:balance", "offers_attr": "TOSLA_OFFERS"},
    "bal_oldu":  {"title": "🇹🇷 Oldubil",         "game": "OLDUBIL",        "input_fields": [{"key": "playerId", "label": "📞 رقم/إيميل حساب Oldubil", "type": "text"}], "back_callback": "store:balance", "offers_attr": "OLDUBIL_OFFERS"},
    # — مصر —
    "bal_voda":  {"title": "🇪🇬 Vodafone Cash",   "game": "VODAFONE_CASH",  "input_fields": [{"key": "playerId", "label": "📞 رقم محفظة Vodafone Cash", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "VODAFONE_CASH_OFFERS"},
    # — أخرى —
    "bal_rcell": {"title": "📱 R-Cell",           "game": "RCELL",          "input_fields": [{"key": "playerId", "label": "📞 رقم R-Cell", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "RCELL_OFFERS"},
    "bal_selam": {"title": "📱 Selam Telecom",    "game": "SELAM_TELECOM",  "input_fields": [{"key": "playerId", "label": "📞 رقم Selam Telecom", "type": "phone"}], "back_callback": "store:balance", "offers_attr": "SELAM_TELECOM_OFFERS"},
    "bal_papra": {"title": "💳 PAPRA",            "game": "PAPRA",          "input_fields": [{"key": "playerId", "label": "🔢 رقم/معرّف حساب PAPRA", "type": "text"}], "back_callback": "store:balance", "offers_attr": "PAPRA_OFFERS"},

    # ===== خدمات الرشق (SMM) — جميعها تتطلب رابط الحساب أو المنشور =====
    "igf":  {"title": "📸 متابعين انستغرام",  "game": "SMM_IG_F",
             "input_fields": [{"key": "playerId", "label": "🔗 رابط حساب انستغرام (مثال: https://instagram.com/username)", "type": "text"}],
             "back_callback": "menu:smm", "offers_attr": "INSTAGRAM_FOLLOWERS"},
    "igl":  {"title": "❤️ لايكات إنستغرام",   "game": "SMM_IG_L",
             "input_fields": [{"key": "playerId", "label": "🔗 رابط منشور/فيديو الإنستغرام", "type": "text"}],
             "back_callback": "menu:smm", "offers_attr": "INSTAGRAM_LIKES"},
    "igv":  {"title": "👁️ مشاهدات إنستغرام",  "game": "SMM_IG_V",
             "input_fields": [{"key": "playerId", "label": "🔗 رابط الفيديو/الريلز", "type": "text"}],
             "back_callback": "menu:smm", "offers_attr": "INSTAGRAM_VIEWS"},
    "fbf":  {"title": "👍 متابعين فيسبوك",     "game": "SMM_FB_F",
             "input_fields": [{"key": "playerId", "label": "🔗 رابط صفحة الفيسبوك", "type": "text"}],
             "back_callback": "menu:smm", "offers_attr": "FACEBOOK_FOLLOWERS"},
    "tgv":  {"title": "📊 مشاهدات تلغرام",    "game": "SMM_TG_V",
             "input_fields": [{"key": "playerId", "label": "🔗 رابط القناة (مشاهدات لآخر 100 منشور)", "type": "text"}],
             "back_callback": "menu:smm", "offers_attr": "TELEGRAM_VIEWS"},
    "tgr":  {"title": "💯 تفاعل/لايك تلغرام",  "game": "SMM_TG_R",
             "input_fields": [{"key": "playerId", "label": "🔗 رابط منشور التلغرام", "type": "text"}],
             "back_callback": "menu:smm", "offers_attr": "TELEGRAM_REACTIONS"},
}


# مصفوفات تحقق من صحة الحقول حسب النوع — (validator, error_message)
def _validate_id(v: str) -> bool:
    return v.isdigit() and 5 <= len(v) <= 15

def _validate_email(v: str) -> bool:
    if "@" not in v or len(v) > 100 or len(v) < 5:
        return False
    parts = v.split("@")
    if len(parts) != 2 or not parts[0] or "." not in parts[1]:
        return False
    return True

def _validate_password(v: str) -> bool:
    return 4 <= len(v) <= 100

def _validate_phone(v: str) -> bool:
    digits = sum(1 for c in v if c.isdigit())
    return 8 <= digits <= 20 and len(v) <= 25

FIELD_VALIDATORS = {
    "id":       (_validate_id,       "⚠️ لازم يكون أرقام فقط (بين 5 و15 خانة)."),
    "email":    (_validate_email,    "⚠️ إيميل غير صحيح. تأكد من الصيغة (example@mail.com)."),
    "password": (_validate_password, "⚠️ كلمة المرور قصيرة جداً (4 خانات على الأقل)."),
    "phone":    (_validate_phone,    "⚠️ رقم واتساب غير صحيح. ابعت الرقم مع رمز الدولة (مثال: 963944xxxxxx)."),
    "text":     (lambda v: 1 <= len(v) <= 200, "⚠️ القيمة غير صالحة."),
}


def build_custom_balance_offer(prefix: str, amount_old_syp: int):
    """يبني عرض ديناميكي لقسم رصيد مفتوح المبلغ.
    - amount_old_syp: المبلغ بالليرة السورية القديمة (اللي كتبه الزبون).
    - السعر = المبلغ × (1 + markup_pct/100) مدوّر لأقرب 500 ل.س.
    - qty المرسلة للـ API = المبلغ ÷ 100 (تحويل لليرة الجديدة).
    يرجع (offer_dict, category_dict) أو (None, None) لو القسم غير مدعوم أو المبلغ خارج النطاق.
    """
    cat = FASTCARD_CATEGORIES.get(prefix)
    if not cat or not cat.get("custom_amount"):
        return None, None
    try:
        amount = int(amount_old_syp)
    except (TypeError, ValueError):
        return None, None
    min_a = int(cat.get("min_amount", 1000))
    max_a = int(cat.get("max_amount", 1000000))
    if amount < min_a or amount > max_a:
        return None, None

    markup = float(cat.get("markup_pct", 10)) / 100.0
    raw_price = amount * (1 + markup)
    # تقريب لأقرب 500 ل.س للأعلى
    price = int(((raw_price + 499) // 500) * 500)

    qty_new_syp = round(amount / 100.0, 4)

    offer = {
        "id": f"custom_{amount}",
        "label": f"{cat['title'].split(' ', 1)[1] if ' ' in cat['title'] else cat['title']} — {amount:,} ل.س".replace(",", "،"),
        "price": price,
        "product_id": cat["product_id"],
        "qty": qty_new_syp,
        "manual_price": True,
        "enabled": True,
        "custom_amount_value": amount,
    }
    return offer, cat


def get_fastcard_offer(prefix: str, offer_id: str, custom_offer: dict | None = None):
    """يرجع (offer_dict, category_dict) أو (None, None).
    - لو offer_id يبدأ بـ 'custom_' و custom_offer مُمرَّر → نستخدمه (للأقسام مفتوحة المبلغ).
    """
    cat = FASTCARD_CATEGORIES.get(prefix)
    if not cat:
        return None, None
    if offer_id and offer_id.startswith("custom_") and custom_offer:
        if custom_offer.get("id") == offer_id:
            return custom_offer, cat
        return None, None
    import sys
    offers = getattr(sys.modules[__name__], cat["offers_attr"], [])
    offer = next((o for o in offers if o["id"] == offer_id), None)
    return offer, cat


def mask_field_value(field: dict, value: str) -> str:
    """يخفي القيم الحساسة (كلمة المرور) في شاشات التأكيد والإشعارات."""
    if field.get("sensitive") or field.get("type") == "password":
        if not value:
            return ""
        n = len(value)
        if n <= 2:
            return "•" * n
        return value[0] + "•" * (n - 2) + value[-1]
    return value


# مفاتيح حساسة يجب حذفها من أي شي بينحفظ بقاعدة البيانات أو اللوغ
_SENSITIVE_KEYS = {"password", "pwd", "pass", "كلمة المرور", "كلمة مرور"}

def _redact_value(v):
    if isinstance(v, dict):
        return {k: ("[REDACTED]" if k in _SENSITIVE_KEYS else _redact_value(val)) for k, val in v.items()}
    if isinstance(v, list):
        return [_redact_value(x) for x in v]
    return v

def sanitize_for_storage(data, extra_redact_values=None) -> str:
    """
    يرجع تمثيل نصي آمن لأي رد API لتخزينه بقاعدة البيانات.
    - يستبدل قيم المفاتيح الحساسة (password وما يشابهها) بـ [REDACTED]
    - يستبدل أي قيمة نصية تطابق extra_redact_values (مثلاً قيمة الباسورد الفعلية لو ظهرت بأي مكان)
    """
    redacted = _redact_value(data) if isinstance(data, (dict, list)) else data
    text = str(redacted)
    if extra_redact_values:
        for v in extra_redact_values:
            if v and isinstance(v, str) and len(v) >= 3:
                text = text.replace(v, "[REDACTED]")
    return text


def summarize_fields_for_db(fields: list, values: dict) -> str:
    """يلخّص قيم الحقول المُجمَّعة بشكل آمن للحفظ بقاعدة البيانات (بدون الباسورد)."""
    parts = []
    for f in fields:
        v = values.get(f["key"], "")
        if not v:
            continue
        if f.get("sensitive") or f.get("type") == "password":
            continue  # ما نحفظ الباسورد
        if f.get("type") == "email":
            parts.append(v)
        elif f.get("type") == "phone":
            parts.append(f"WA:{v}")
        elif f.get("type") == "id":
            parts.append(v)
        else:
            parts.append(v)
    return " / ".join(parts) if parts else "—"


# ===== Fastcard / Ahminix Store API =====
FASTCARD_TOKEN = os.environ.get("FASTCARD_TOKEN", "")
FASTCARD_BASE = os.environ.get("FASTCARD_BASE", "https://fastcard1.store/client/api")

# ===== Monitoring / Alerts =====
# تنبيه الأدمن لما رصيد المتجر ينخفض (USD)
LOW_BALANCE_THRESHOLD_USD = float(os.environ.get("LOW_BALANCE_THRESHOLD_USD", "5.0"))
# كل كم ثانية يتفقّد البوت رصيد المتجر
BALANCE_CHECK_INTERVAL = int(os.environ.get("BALANCE_CHECK_INTERVAL", "43200"))  # 12 ساعة
# ساعة إرسال التقرير اليومي (UTC). 21 UTC = منتصف الليل بدمشق
DAILY_REPORT_HOUR_UTC = int(os.environ.get("DAILY_REPORT_HOUR_UTC", "21"))
DAILY_REPORT_MINUTE_UTC = int(os.environ.get("DAILY_REPORT_MINUTE_UTC", "0"))
# ساعة فحص أسعار Fastcard اليومي (UTC). 06 UTC = 9 صباحاً بدمشق
PRICE_CHECK_HOUR_UTC = int(os.environ.get("PRICE_CHECK_HOUR_UTC", "6"))
PRICE_CHECK_MINUTE_UTC = int(os.environ.get("PRICE_CHECK_MINUTE_UTC", "0"))
# مدة الانتظار الإجمالية (ثواني) لـ polling حالة الطلب بعد إنشائه
FASTCARD_POLL_TIMEOUT = int(os.environ.get("FASTCARD_POLL_TIMEOUT", "45"))
FASTCARD_POLL_INTERVAL = int(os.environ.get("FASTCARD_POLL_INTERVAL", "3"))

# ===== Fastcard Website Login (للتحقق من اسم اللاعب) =====
# مطلوب يدوياً لأن seller API ما بتدعم redeemtech_check_player
FASTCARD_WEB_BASE = os.environ.get("FASTCARD_WEB_BASE", "https://fastcard1.store")
FASTCARD_WEB_USERNAME = os.environ.get("FASTCARD_WEB_USERNAME", "")
FASTCARD_WEB_PASSWORD = os.environ.get("FASTCARD_WEB_PASSWORD", "")
# تكلفة التحقق من الاسم بالدولار (بتخصم من رصيد المستخدم بل.س على أساس سعر صرف Sham Cash)
FASTCARD_VERIFY_COST_USD = float(os.environ.get("FASTCARD_VERIFY_COST_USD", "0.03"))

# ===== Sham Cash Auto Integration =====
# توثيق الـ API: https://shamcash-api.com/docs
SHAMCASH_TOKEN = os.environ.get("SHAMCASH_TOKEN", "")
SHAMCASH_API_URL = os.environ.get("SHAMCASH_API_URL", "https://api.shamcash-api.com/v1")
SHAMCASH_ACCOUNT_ID = os.environ.get("SHAMCASH_ACCOUNT_ID", "")  # اختياري — لو فاضي بنجيب أول حساب active
SHAMCASH_AUTO_VERIFY = os.environ.get("SHAMCASH_AUTO_VERIFY", "true").lower() == "true"
SHAMCASH_VERIFY_WINDOW_MIN = int(os.environ.get("SHAMCASH_VERIFY_WINDOW_MIN", "30"))

# ===== Syriatel Cash Auto Integration =====
# توثيق الـ API: https://api.melchersman.com/syr-cash/api-docs
SYRIATEL_CASH_TOKEN = os.environ.get("SYRIATEL_CASH_TOKEN", "")
SYRIATEL_CASH_API_URL = os.environ.get("SYRIATEL_CASH_API_URL", "https://api.melchersman.com/syr-cash/v1")
SYRIATEL_CASH_AUTO_VERIFY = os.environ.get("SYRIATEL_CASH_AUTO_VERIFY", "true").lower() == "true"


def get_level_for_amount(total_recharged: float) -> str:
    for name, low, high in LEVELS:
        if low <= total_recharged <= high:
            return name
    return "برونزي"


