"""
طبقة قاعدة البيانات - SQLite
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

from . import config


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0,
                level TEXT DEFAULT '🥉 برونزي',
                total_recharged REAL DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                created_at TEXT,
                referrer_id INTEGER,
                signup_bonus_paid INTEGER DEFAULT 0
            )
        """)
        for col_def in (
            ("referrer_id", "INTEGER"),
            ("signup_bonus_paid", "INTEGER DEFAULT 0"),
            ("loyalty_points", "INTEGER DEFAULT 0"),
        ):
            try:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col_def[0]} {col_def[1]}")
            except sqlite3.OperationalError:
                pass
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recharge_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                method TEXT,
                amount REAL,
                transaction_code TEXT,
                photo_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game TEXT,
                item TEXT,
                price REAL,
                player_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                api_order_id TEXT,
                api_uuid TEXT,
                api_response TEXT
            )
        """)
        # ترقية الجداول القديمة (لو موجودة بدون أعمدة API)
        for col in ("api_order_id", "api_uuid", "api_response"):
            try:
                cur.execute(f"ALTER TABLE orders ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consumed_transactions (
                transaction_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                consumed_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uc_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id TEXT NOT NULL,
                code TEXT NOT NULL,
                status TEXT DEFAULT 'available',
                user_id INTEGER,
                order_id INTEGER,
                created_at TEXT,
                sold_at TEXT,
                UNIQUE(offer_id, code)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_uc_codes_status ON uc_codes(offer_id, status)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS referral_commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_user_id INTEGER NOT NULL,
                recharge_amount REAL NOT NULL,
                commission REAL NOT NULL,
                created_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_refcom_referrer ON referral_commissions(referrer_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id)")
        # جدول إعدادات عامة (سعر الصرف، إلخ)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """)
        # جدول تقييمات الطلبات (5 نجوم بعد كل طلب ناجح)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS order_ratings (
                order_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                stars INTEGER NOT NULL,
                comment TEXT,
                created_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ratings_user ON order_ratings(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ratings_created ON order_ratings(created_at)")
        # جدول كوبونات الخصم
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount_type TEXT NOT NULL,           -- 'percent' أو 'fixed'
                discount_value REAL NOT NULL,
                min_order REAL DEFAULT 0,
                max_uses INTEGER DEFAULT 0,            -- 0 = لا يوجد حد
                used_count INTEGER DEFAULT 0,
                expires_at TEXT,                       -- ISO أو NULL
                active INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons(code)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coupon_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coupon_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                order_id INTEGER,
                applied_amount REAL NOT NULL,          -- ل.س الخصم الفعلي المطبّق
                created_at TEXT,
                FOREIGN KEY (coupon_id) REFERENCES coupons(id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_coupon_uses_user ON coupon_uses(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_coupon_uses_coupon ON coupon_uses(coupon_id)")
        # جدول override يدوي لأسعار المنتجات (له الأولوية على الحساب التلقائي)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS price_overrides (
                offer_id TEXT PRIMARY KEY,
                price INTEGER NOT NULL,
                updated_at TEXT
            )
        """)
        # Migration: إعادة حساب مستوى كل المستخدمين الموجودين بناءً على إجمالي شحنهم
        # (يضمن استخدام أسماء المستويات الجديدة مع الإيموجي وإضافة VIP/ملكي)
        cur.execute("SELECT user_id, total_recharged FROM users")
        for u in cur.fetchall():
            new_level = config.get_level_for_amount(float(u["total_recharged"] or 0))
            cur.execute("UPDATE users SET level = ? WHERE user_id = ?", (new_level, u["user_id"]))
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def now_iso() -> str:
    return datetime.utcnow().isoformat()


# ===== إعدادات عامة (سعر الصرف وغيرها) =====

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """يقرأ قيمة إعداد من جدول settings. يرجع default لو غير موجود."""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            if row and row["value"] is not None:
                return str(row["value"])
    except sqlite3.Error:
        pass
    return default


def set_setting(key: str, value: str) -> None:
    """يضيف أو يحدث قيمة إعداد."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, str(value), now_iso()),
        )
        conn.commit()


# ===== تعديل أسعار المنتجات يدوياً (override) =====

def get_price_override(offer_id: str) -> Optional[int]:
    """يرجع السعر اليدوي المحفوظ لعرض معين، أو None إذا لا يوجد."""
    if not offer_id:
        return None
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT price FROM price_overrides WHERE offer_id = ?", (offer_id,))
            row = cur.fetchone()
            if row and row["price"] is not None:
                return int(row["price"])
    except sqlite3.Error:
        pass
    return None


def set_price_override(offer_id: str, price: int) -> None:
    """يحفظ سعر يدوي لعرض معين (له الأولوية على الحساب التلقائي)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO price_overrides (offer_id, price, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(offer_id) DO UPDATE SET price = excluded.price, updated_at = excluded.updated_at",
            (offer_id, int(price), now_iso()),
        )
        conn.commit()


def delete_price_override(offer_id: str) -> None:
    """يحذف السعر اليدوي ويرجع العرض للحساب التلقائي."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM price_overrides WHERE offer_id = ?", (offer_id,))
        conn.commit()


def list_price_overrides() -> Dict[str, int]:
    """يرجع dict {offer_id: price} لكل الأسعار اليدوية المحفوظة."""
    out: Dict[str, int] = {}
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT offer_id, price FROM price_overrides")
            for r in cur.fetchall():
                out[str(r["offer_id"])] = int(r["price"])
    except sqlite3.Error:
        pass
    return out


def get_or_create_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> Dict[str, Any]:
    """يرجع المستخدم. الحقل المشتق `is_new` يكون True فقط عند أول إنشاء."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        is_new = False
        if row is None:
            cur.execute(
                "INSERT INTO users (user_id, username, first_name, balance, level, total_recharged, is_banned, created_at) VALUES (?, ?, ?, 0, '🥉 برونزي', 0, 0, ?)",
                (user_id, username or "", first_name or "", now_iso()),
            )
            conn.commit()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            is_new = True
        else:
            if (username or "") != (row["username"] or "") or (first_name or "") != (row["first_name"] or ""):
                cur.execute(
                    "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                    (username or "", first_name or "", user_id),
                )
                conn.commit()
        result = dict(row)
        result["is_new"] = is_new
        return result


def attach_referrer(user_id: int, referrer_id: int, signup_bonus: float) -> Optional[Dict[str, Any]]:
    """يربط مستخدم جديد بمن أحاله ويعطيه مكافأة الانضمام (مرة واحدة فقط).
    شروط: المستخدم لم يكن له referrer سابقاً، ولم يأخذ signup_bonus، والمحيل موجود وغير محظور وليس هو نفسه."""
    if user_id == referrer_id:
        return None
    with get_conn() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.cursor()
            # المُحيل يجب أن يكون موجود وغير محظور
            cur.execute("SELECT is_banned FROM users WHERE user_id = ?", (referrer_id,))
            ref_row = cur.fetchone()
            if ref_row is None or int(ref_row["is_banned"] or 0) == 1:
                conn.rollback()
                return None
            # ربط الإحالة فقط إذا لم يتم سابقاً (شرط ذرّي في WHERE)
            cur.execute(
                "UPDATE users SET referrer_id = ?, signup_bonus_paid = 1, "
                "balance = COALESCE(balance,0) + ? "
                "WHERE user_id = ? AND referrer_id IS NULL "
                "AND COALESCE(signup_bonus_paid,0) = 0",
                (referrer_id, signup_bonus, user_id),
            )
            if cur.rowcount == 0:
                conn.rollback()
                return None
            cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            new_balance = float(cur.fetchone()["balance"] or 0)
            conn.commit()
            return {"bonus_amount": float(signup_bonus), "new_balance": new_balance,
                    "referrer_id": referrer_id}
        except sqlite3.Error:
            try:
                conn.rollback()
            except Exception:
                pass
            return None


def get_referral_stats(user_id: int) -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM users WHERE referrer_id = ?", (user_id,))
        invited = int(cur.fetchone()["c"] or 0)
        cur.execute(
            "SELECT COALESCE(SUM(commission), 0) AS s, COUNT(*) AS c FROM referral_commissions WHERE referrer_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        return {
            "invited_count": invited,
            "commission_total": float(row["s"] or 0),
            "commission_orders": int(row["c"] or 0),
        }


def record_referral_commission(referrer_id: int, referred_user_id: int,
                                recharge_amount: float, commission: float):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO referral_commissions (referrer_id, referred_user_id, recharge_amount, commission, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (referrer_id, referred_user_id, recharge_amount, commission, now_iso()),
        )
        conn.commit()


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def set_banned(user_id: int, banned: bool):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if banned else 0, user_id))
        conn.commit()


def update_balance(user_id: int, delta: float, count_as_recharge: bool = False):
    """Atomic balance update. Uses BEGIN IMMEDIATE + SQL increment to be race-safe.
    يرجع dict مع `level_changed` (True فقط عند ترقية فعلية لمستوى أعلى)
    و `previous_level` (المستوى السابق قبل التحديث)."""
    with get_conn() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.cursor()
            # نقرأ المستوى الحالي قبل التحديث لمقارنته لاحقاً
            cur.execute("SELECT level FROM users WHERE user_id = ?", (user_id,))
            prev_row = cur.fetchone()
            previous_level = prev_row["level"] if prev_row else None
            recharge_delta = delta if count_as_recharge and delta > 0 else 0
            cur.execute(
                "UPDATE users SET balance = COALESCE(balance,0) + ?, "
                "total_recharged = COALESCE(total_recharged,0) + ? WHERE user_id = ?",
                (delta, recharge_delta, user_id),
            )
            if cur.rowcount == 0:
                conn.rollback()
                return None
            cur.execute(
                "SELECT balance, total_recharged, referrer_id FROM users WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            new_total = float(row["total_recharged"] or 0)
            new_level = config.get_level_for_amount(new_total)
            cur.execute("UPDATE users SET level = ? WHERE user_id = ?", (new_level, user_id))
            conn.commit()
            level_changed = bool(previous_level and previous_level != new_level)
            return {
                "balance": float(row["balance"] or 0),
                "total_recharged": new_total,
                "level": new_level,
                "previous_level": previous_level,
                "level_changed": level_changed,
                "referrer_id": row["referrer_id"],
            }
        except sqlite3.Error:
            try:
                conn.rollback()
            except Exception:
                pass
            return None


def set_balance(user_id: int, new_balance: float):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        conn.commit()


def create_recharge_request(user_id: int, method: str, amount: float,
                             transaction_code: Optional[str] = None,
                             photo_file_id: Optional[str] = None) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO recharge_requests (user_id, method, amount, transaction_code, photo_file_id, status, created_at) VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (user_id, method, amount, transaction_code, photo_file_id, now_iso()),
        )
        conn.commit()
        return cur.lastrowid


def get_recharge_request(req_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM recharge_requests WHERE id = ?", (req_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_recharge_status(req_id: int, status: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE recharge_requests SET status = ? WHERE id = ?", (status, req_id))
        conn.commit()


def create_order(user_id: int, game: str, item: str, price: float, player_id: str,
                 api_uuid: Optional[str] = None) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO orders (user_id, game, item, price, player_id, status, created_at, api_uuid) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
            (user_id, game, item, price, player_id, now_iso(), api_uuid),
        )
        conn.commit()
        return cur.lastrowid


def update_order_api(order_id: int, *, api_order_id: Optional[str] = None,
                     api_uuid: Optional[str] = None, api_response: Optional[str] = None,
                     status: Optional[str] = None):
    sets, vals = [], []
    if api_order_id is not None:
        sets.append("api_order_id = ?"); vals.append(api_order_id)
    if api_uuid is not None:
        sets.append("api_uuid = ?"); vals.append(api_uuid)
    if api_response is not None:
        sets.append("api_response = ?"); vals.append(api_response)
    if status is not None:
        sets.append("status = ?"); vals.append(status)
    if not sets:
        return
    vals.append(order_id)
    with get_conn() as conn:
        conn.cursor().execute(f"UPDATE orders SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()


def get_order(order_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_order_status(order_id: int, status: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        conn.commit()


def count_user_orders(user_id: int) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT (SELECT COUNT(*) FROM orders WHERE user_id = ?) + (SELECT COUNT(*) FROM recharge_requests WHERE user_id = ?) AS total",
            (user_id, user_id),
        )
        row = cur.fetchone()
        return int(row["total"] or 0)


def get_pending_recharges(limit: int = 20) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM recharge_requests WHERE status = 'pending' ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


def get_pending_orders(limit: int = 20) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE status = 'pending' ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


def get_pubg_stats_since(since_iso: str) -> Dict[str, Any]:
    """إحصائيات مبيعات شدات PUBG التي مرّت عبر الـAPI منذ وقت معيّن (UTC ISO).
    يحسب إجمالي المبالغ بالـ ل.س والتكلفة بالدولار من PUBG_UC_OFFERS."""
    from . import config as _cfg
    cost_by_label = {o["label"]: float(o.get("cost_usd") or 0) for o in _cfg.PUBG_UC_OFFERS}

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT item, price, status FROM orders "
            "WHERE game = 'PUBG' AND api_uuid IS NOT NULL AND created_at >= ?",
            (since_iso,),
        )
        rows = [dict(r) for r in cur.fetchall()]

    completed = [r for r in rows if r["status"] in ("completed", "approved")]
    refunded = [r for r in rows if r["status"] in ("refunded", "rejected", "failed")]
    pending = [r for r in rows if r["status"] in ("pending",)]

    total_revenue_syp = sum(float(r["price"] or 0) for r in completed)
    total_cost_usd = sum(cost_by_label.get(r["item"], 0.0) for r in completed)
    by_item: Dict[str, int] = {}
    for r in completed:
        by_item[r["item"]] = by_item.get(r["item"], 0) + 1

    return {
        "completed": len(completed),
        "refunded": len(refunded),
        "pending": len(pending),
        "total_revenue_syp": total_revenue_syp,
        "total_cost_usd": total_cost_usd,
        "by_item": by_item,
    }


# ============= كوبونات الخصم =============

def create_coupon(code: str, discount_type: str, discount_value: float,
                  min_order: float = 0, max_uses: int = 0, expires_at: Optional[str] = None) -> Optional[int]:
    """ينشئ كوبون. يرجع id الكوبون أو None لو الكود مكرّر."""
    code = (code or "").strip().upper()
    if not code or discount_type not in ("percent", "fixed"):
        return None
    if discount_type == "percent" and not (0 < discount_value <= 100):
        return None
    if discount_type == "fixed" and discount_value <= 0:
        return None
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO coupons (code, discount_type, discount_value, min_order, "
                "max_uses, used_count, expires_at, active, created_at) "
                "VALUES (?, ?, ?, ?, ?, 0, ?, 1, ?)",
                (code, discount_type, float(discount_value), float(min_order or 0),
                 int(max_uses or 0), expires_at, now_iso()),
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def get_coupon_by_code(code: str) -> Optional[Dict[str, Any]]:
    code = (code or "").strip().upper()
    if not code:
        return None
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM coupons WHERE code = ?", (code,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_coupons(active_only: bool = False, limit: int = 50) -> list:
    with get_conn() as conn:
        cur = conn.cursor()
        if active_only:
            cur.execute("SELECT * FROM coupons WHERE active = 1 ORDER BY created_at DESC LIMIT ?", (limit,))
        else:
            cur.execute("SELECT * FROM coupons ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


def deactivate_coupon(coupon_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE coupons SET active = 0 WHERE id = ?", (coupon_id,))
        conn.commit()
        return cur.rowcount > 0


def has_user_used_coupon(coupon_id: int, user_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM coupon_uses WHERE coupon_id = ? AND user_id = ?", (coupon_id, user_id))
        return cur.fetchone() is not None


def validate_coupon_for_user(code: str, user_id: int, order_amount: float) -> Dict[str, Any]:
    """يتحقق من كود + يرجع dict:
       {ok: bool, error: str|None, coupon: dict|None, discount: float}
       discount = قيمة الخصم المحسوبة بـ ل.س (لا يمكن تتجاوز order_amount)."""
    coupon = get_coupon_by_code(code)
    if not coupon:
        return {"ok": False, "error": "❌ الكود غير صحيح.", "coupon": None, "discount": 0.0}
    if not int(coupon.get("active") or 0):
        return {"ok": False, "error": "❌ هذا الكود معطّل.", "coupon": coupon, "discount": 0.0}
    expires = coupon.get("expires_at")
    if expires:
        try:
            from datetime import datetime, timezone
            exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            if exp_dt < now_dt:
                return {"ok": False, "error": "⌛ الكود منتهي الصلاحية.", "coupon": coupon, "discount": 0.0}
        except Exception:
            pass
    max_uses = int(coupon.get("max_uses") or 0)
    used = int(coupon.get("used_count") or 0)
    if max_uses > 0 and used >= max_uses:
        return {"ok": False, "error": "⚠️ هذا الكود استُنفذ بالكامل.", "coupon": coupon, "discount": 0.0}
    min_order = float(coupon.get("min_order") or 0)
    if min_order > 0 and order_amount < min_order:
        return {
            "ok": False,
            "error": f"⚠️ الكود يتطلب طلب بقيمة *{min_order:,.0f} ل.س* على الأقل.".replace(",", "،"),
            "coupon": coupon,
            "discount": 0.0,
        }
    if has_user_used_coupon(int(coupon["id"]), int(user_id)):
        return {"ok": False, "error": "⚠️ سبق وأنّك استخدمت هذا الكود.", "coupon": coupon, "discount": 0.0}

    dtype = coupon["discount_type"]
    dval = float(coupon["discount_value"])
    if dtype == "percent":
        discount = order_amount * (dval / 100.0)
    else:
        discount = dval
    discount = min(discount, order_amount)
    discount = round(discount / 100) * 100  # تقريب لأقرب 100 ل.س
    if discount <= 0:
        return {"ok": False, "error": "⚠️ قيمة الخصم صفر.", "coupon": coupon, "discount": 0.0}
    return {"ok": True, "error": None, "coupon": coupon, "discount": float(discount)}


def consume_coupon(coupon_id: int, user_id: int, order_id: Optional[int],
                   applied_amount: float) -> bool:
    """يسجل استخدام الكوبون + يزيد used_count بشكل atomic."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            cur.execute(
                "INSERT INTO coupon_uses (coupon_id, user_id, order_id, applied_amount, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (coupon_id, user_id, order_id, float(applied_amount), now_iso()),
            )
            cur.execute(
                "UPDATE coupons SET used_count = used_count + 1 WHERE id = ?",
                (coupon_id,),
            )
            cur.execute("COMMIT")
            return True
        except Exception:
            try:
                cur.execute("ROLLBACK")
            except Exception:
                pass
            return False


def get_loyalty_points(user_id: int) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT loyalty_points FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return 0
        return int(row["loyalty_points"] or 0)


def add_loyalty_points(user_id: int, points: int) -> int:
    """يضيف نقاط ولاء للمستخدم. يرجع الرصيد الجديد للنقاط."""
    points = int(points)
    if points <= 0:
        return get_loyalty_points(user_id)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET loyalty_points = COALESCE(loyalty_points, 0) + ? WHERE user_id = ?",
            (points, user_id),
        )
        conn.commit()
        cur.execute("SELECT loyalty_points FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return int(row["loyalty_points"] or 0) if row else 0


def redeem_loyalty_points(user_id: int, points: int, syp_per_point: int = 1) -> Optional[Dict[str, Any]]:
    """يحوّل نقاط الولاء إلى رصيد ل.س. يرجع dict يحتوي:
       {points_used, syp_added, new_points, new_balance} لو نجح، أو None لو فشل (نقاط ناقصة).
       يستخدم transaction واحدة آمنة (atomic)."""
    points = int(points)
    if points <= 0:
        return None
    syp_added = points * int(syp_per_point)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            cur.execute("SELECT loyalty_points, balance FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if not row:
                cur.execute("ROLLBACK")
                return None
            current = int(row["loyalty_points"] or 0)
            if current < points:
                cur.execute("ROLLBACK")
                return None
            cur.execute(
                "UPDATE users SET loyalty_points = loyalty_points - ?, balance = balance + ? WHERE user_id = ?",
                (points, syp_added, user_id),
            )
            cur.execute("SELECT loyalty_points, balance FROM users WHERE user_id = ?", (user_id,))
            new_row = dict(cur.fetchone())
            cur.execute("COMMIT")
            return {
                "points_used": points,
                "syp_added": syp_added,
                "new_points": int(new_row["loyalty_points"] or 0),
                "new_balance": float(new_row["balance"] or 0),
            }
        except Exception:
            try:
                cur.execute("ROLLBACK")
            except Exception:
                pass
            return None


def add_rating(order_id: int, user_id: int, stars: int, comment: str = "") -> bool:
    """يحفظ تقييم لطلب. يرجع True لو تم الحفظ، False لو الطلب مقيّم سابقاً."""
    stars = max(1, min(5, int(stars)))
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO order_ratings (order_id, user_id, stars, comment, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (order_id, user_id, stars, comment or "", now_iso()),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def has_rated(order_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM order_ratings WHERE order_id = ?", (order_id,))
        return cur.fetchone() is not None


def get_ratings_summary() -> Dict[str, Any]:
    """يرجع متوسط التقييم، عدد التقييمات الكلي، وتوزيع النجوم."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS cnt, COALESCE(AVG(stars), 0) AS avg_stars FROM order_ratings"
        )
        row = dict(cur.fetchone())
        cur.execute("SELECT stars, COUNT(*) AS c FROM order_ratings GROUP BY stars")
        dist = {int(r["stars"]): int(r["c"]) for r in cur.fetchall()}
    return {
        "count": int(row["cnt"]),
        "avg": float(row["avg_stars"]),
        "distribution": dist,  # {1: 0, 2: 1, ..., 5: 12}
    }


def get_recent_ratings(limit: int = 20) -> list:
    """يرجع آخر التقييمات مع معلومات الطلب والمستخدم."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                r.order_id,
                r.user_id,
                r.stars,
                r.comment,
                r.created_at,
                o.item AS order_item,
                u.username AS username,
                u.first_name AS first_name
            FROM order_ratings r
            LEFT JOIN orders o ON o.id = r.order_id
            LEFT JOIN users u ON u.user_id = r.user_id
            ORDER BY r.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_top_spenders(limit: int = 10) -> list:
    """يرجع قائمة أكثر الزبائن إنفاقاً (مرتبة من الأعلى).
    كل عنصر: {user_id, username, first_name, level, total_recharged,
              orders_count, total_spent_syp}.
    `total_spent_syp` = مجموع أسعار الطلبات الناجحة (completed/approved).
    `total_recharged` = إجمالي الشحن (من جدول users)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                u.user_id,
                u.username,
                u.first_name,
                u.level,
                COALESCE(u.total_recharged, 0) AS total_recharged,
                COALESCE(u.balance, 0) AS balance,
                COUNT(o.id) AS orders_count,
                COALESCE(SUM(o.price), 0) AS total_spent_syp
            FROM users u
            LEFT JOIN orders o
                ON o.user_id = u.user_id
                AND o.status IN ('completed', 'approved')
            GROUP BY u.user_id
            HAVING total_spent_syp > 0 OR total_recharged > 0
            ORDER BY total_spent_syp DESC, total_recharged DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_daily_profit_series(days: int = 30) -> Dict[str, Any]:
    """يرجع سلسلة أرباح يومية لآخر `days` يوم. يستخدم لرسم البياني.
    شكل النتيجة: {labels: [...], revenue: [...], cost_syp: [...], profit: [...]}
    """
    from . import config as _cfg
    cost_map = _cfg.build_cost_map()
    usd_rate = _cfg.get_usd_to_syp()

    from datetime import datetime as _dt, timedelta as _td

    end = _dt.utcnow().date()
    start = end - _td(days=days - 1)
    since_iso = _dt(start.year, start.month, start.day).isoformat()

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT created_at, item, price FROM orders "
            "WHERE created_at >= ? AND status IN ('completed', 'approved')",
            (since_iso,),
        )
        rows = [dict(r) for r in cur.fetchall()]

    # يوم → (revenue_syp, cost_usd)
    buckets: Dict[str, list] = {}
    for r in rows:
        ts = r.get("created_at") or ""
        day_key = ts[:10]  # YYYY-MM-DD
        if day_key not in buckets:
            buckets[day_key] = [0.0, 0.0]
        buckets[day_key][0] += float(r.get("price") or 0)
        buckets[day_key][1] += cost_map.get(r.get("item"), 0.0)

    labels: list = []
    revenue: list = []
    cost_syp: list = []
    profit: list = []
    for i in range(days):
        d = start + _td(days=i)
        key = d.isoformat()
        rev, cu = buckets.get(key, [0.0, 0.0])
        c_syp = cu * usd_rate
        labels.append(d.strftime("%m-%d"))
        revenue.append(rev)
        cost_syp.append(c_syp)
        profit.append(rev - c_syp)

    return {
        "labels": labels,
        "revenue": revenue,
        "cost_syp": cost_syp,
        "profit": profit,
        "days": days,
    }


def get_sales_stats_since(since_iso: str) -> Dict[str, Any]:
    """تقرير شامل لكل المبيعات (كل المنتجات) منذ وقت معيّن.
    يحسب: إجمالي المبيعات بالليرة، التكلفة بالدولار، تفصيل بحسب اللعبة/الفئة.
    يشمل كل الطلبات الناجحة (completed/approved) بغضّ النظر عن api_uuid."""
    from . import config as _cfg
    cost_map = _cfg.build_cost_map()

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT game, item, price, status FROM orders WHERE created_at >= ?",
            (since_iso,),
        )
        rows = [dict(r) for r in cur.fetchall()]

    completed = [r for r in rows if r["status"] in ("completed", "approved")]
    refunded = [r for r in rows if r["status"] in ("refunded", "rejected", "failed")]
    pending = [r for r in rows if r["status"] in ("pending",)]

    total_revenue_syp = sum(float(r["price"] or 0) for r in completed)
    total_cost_usd = sum(cost_map.get(r["item"], 0.0) for r in completed)

    # تفصيل بحسب اللعبة/الفئة
    by_game: Dict[str, Dict[str, float]] = {}
    for r in completed:
        g = r["game"] or "غير محدد"
        slot = by_game.setdefault(g, {"count": 0, "revenue": 0.0, "cost_usd": 0.0})
        slot["count"] += 1
        slot["revenue"] += float(r["price"] or 0)
        slot["cost_usd"] += cost_map.get(r["item"], 0.0)

    return {
        "completed": len(completed),
        "refunded": len(refunded),
        "pending": len(pending),
        "total_revenue_syp": total_revenue_syp,
        "total_cost_usd": total_cost_usd,
        "by_game": by_game,
    }


def get_stats() -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM users")
        users = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM orders")
        orders = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM recharge_requests")
        recharges = cur.fetchone()["c"]
        cur.execute("SELECT COALESCE(SUM(amount), 0) AS s FROM recharge_requests WHERE status = 'approved'")
        total_recharged = cur.fetchone()["s"]
        cur.execute("SELECT COALESCE(SUM(price), 0) AS s FROM orders WHERE status IN ('approved','completed')")
        total_sold = cur.fetchone()["s"]
        return {
            "users": users,
            "orders": orders,
            "recharges": recharges,
            "total_recharged": total_recharged,
            "total_sold": total_sold,
        }


def add_uc_codes(offer_id: str, codes: List[str]) -> int:
    """يضيف أكواد بالجملة. يتجاهل المكرر. يرجع عدد المضاف فعلياً."""
    added = 0
    ts = now_iso()
    with get_conn() as conn:
        cur = conn.cursor()
        for raw in codes:
            code = (raw or "").strip()
            if not code:
                continue
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO uc_codes (offer_id, code, status, created_at) VALUES (?, ?, 'available', ?)",
                    (offer_id, code, ts),
                )
                if cur.rowcount > 0:
                    added += 1
            except sqlite3.Error:
                continue
        conn.commit()
    return added


def count_available_codes(offer_id: str) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS c FROM uc_codes WHERE offer_id = ? AND status = 'available'",
            (offer_id,),
        )
        return int(cur.fetchone()["c"] or 0)


def codes_inventory() -> Dict[str, int]:
    """يرجع dict: offer_id -> available count لكل العروض."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT offer_id, COUNT(*) AS c FROM uc_codes WHERE status = 'available' GROUP BY offer_id"
        )
        return {row["offer_id"]: int(row["c"]) for row in cur.fetchall()}


def claim_uc_code(offer_id: str, user_id: int, order_id: int) -> Optional[str]:
    """احتجاز كود لمستخدم بشكل ذرّي. يرجع الكود أو None لو نفد."""
    with get_conn() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.cursor()
            cur.execute(
                "SELECT id, code FROM uc_codes WHERE offer_id = ? AND status = 'available' ORDER BY id LIMIT 1",
                (offer_id,),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return None
            cur.execute(
                "UPDATE uc_codes SET status = 'sold', user_id = ?, order_id = ?, sold_at = ? WHERE id = ?",
                (user_id, order_id, now_iso(), row["id"]),
            )
            conn.commit()
            return row["code"]
        except sqlite3.Error:
            try:
                conn.rollback()
            except Exception:
                pass
            return None


def clear_available_codes(offer_id: str) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM uc_codes WHERE offer_id = ? AND status = 'available'",
            (offer_id,),
        )
        conn.commit()
        return cur.rowcount


def is_transaction_consumed(transaction_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM consumed_transactions WHERE transaction_id = ?", (transaction_id,))
        return cur.fetchone() is not None


def consume_transaction(transaction_id: int, user_id: int, amount: float) -> bool:
    """Atomically claim a transaction. Returns True if claimed, False if already consumed."""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO consumed_transactions (transaction_id, user_id, amount, consumed_at) VALUES (?, ?, ?, ?)",
                (transaction_id, user_id, amount, now_iso()),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def all_user_ids() -> List[int]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE is_banned = 0")
        return [int(r["user_id"]) for r in cur.fetchall()]
