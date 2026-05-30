"""
نظام التحقق التلقائي من إيداع USDT على شبكة BSC BEP20
عبر BscScan API — بدون Binance Pay Merchant

الاستخدام:
  1. أضف لـ Railway Variables:
       BSCSCAN_API_KEY = مفتاحك
       USDT_WALLET_BEP20 = عنوان محفظتك

  2. ضيف في jobs.py:
       from .usdt_bsc import check_usdt_deposits
       jq.run_repeating(check_usdt_deposits, interval=60, first=30, name="usdt_bsc_check")
"""

import logging
import time
from typing import Optional, List, Dict, Any

import requests

from . import config

logger = logging.getLogger(__name__)

# عنوان عقد USDT على BSC
USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
BSCSCAN_BASE  = "https://api.bscscan.com/api"
WALLET        = "0x9a8e639b26ee2a7796b6a2d81d2df0a74cb615d5"

# cache آخر tx تم فحصه
_last_checked_block: Optional[int] = None


def get_api_key() -> str:
    return getattr(config, "BSCSCAN_API_KEY", "J3GJFY11ZEUJQUB2DAZ6IMWGVAWYWYMXGU")


def get_wallet() -> str:
    return getattr(config, "USDT_WALLET_BEP20", WALLET)


def fetch_incoming_usdt(start_block: int = 0) -> List[Dict[str, Any]]:
    """
    يجلب كل تحويلات USDT الواردة للمحفظة من BscScan.
    يرجع قائمة من العمليات.
    """
    params = {
        "module":           "account",
        "action":           "tokentx",
        "contractaddress":  USDT_CONTRACT,
        "address":          get_wallet(),
        "startblock":       start_block,
        "endblock":         "latest",
        "sort":             "desc",
        "apikey":           get_api_key(),
    }
    try:
        resp = requests.get(BSCSCAN_BASE, params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "1":
            return data.get("result", [])
    except Exception as e:
        logger.error(f"BscScan API error: {e}")
    return []


def find_tx_by_hash(tx_hash: str) -> Optional[Dict[str, Any]]:
    """يبحث عن عملية برقم الـ hash."""
    txs = fetch_incoming_usdt()
    for tx in txs:
        if tx.get("hash", "").lower() == tx_hash.lower():
            # تأكد إن الوجهة هي محفظتنا
            if tx.get("to", "").lower() == get_wallet().lower():
                return tx
    return None


def verify_deposit(tx_hash: str, expected_amount_usdt: float, tolerance: float = 0.01) -> bool:
    """
    يتحقق من عملية USDT:
    - الـ hash صحيح
    - الوجهة هي محفظتنا
    - المبلغ متطابق (مع هامش tolerance)
    يرجع True لو كل شي صح.
    """
    tx = find_tx_by_hash(tx_hash)
    if not tx:
        return False

    try:
        # USDT decimals = 18 على BSC
        decimals = int(tx.get("tokenDecimal", 18))
        amount = int(tx.get("value", 0)) / (10 ** decimals)
    except (ValueError, TypeError):
        return False

    if abs(amount - expected_amount_usdt) > tolerance:
        logger.warning(f"USDT amount mismatch: got {amount}, expected {expected_amount_usdt}")
        return False

    return True


async def check_usdt_deposits(context) -> None:
    """
    Job دوري كل دقيقة — يفحص طلبات USDT المعلقة ويضيف الرصيد تلقائياً.
    """
    from . import database as db
    import json

    try:
        pending = db.get_settings_like("usdt_pending_")
    except Exception:
        return

    for key, val in (pending or {}).items():
        try:
            order = json.loads(val)
        except Exception:
            continue

        user_id   = order.get("user_id")
        tx_hash   = order.get("tx_hash", "")
        amount    = float(order.get("amount", 0))
        created   = float(order.get("created", 0))

        # انتهت المهلة 24 ساعة
        if time.time() - created > 86400:
            db.delete_setting(key)
            continue

        if not tx_hash:
            continue

        # تحقق من البلوكتشين
        verified = verify_deposit(tx_hash, amount)
        if verified:
            db.delete_setting(key)
            syp_per_usd = config.get_usd_to_syp()
            amount_syp  = amount * syp_per_usd
            try:
                db.add_balance(user_id, amount_syp)
                req_id = db.create_recharge_request(
                    user_id, "usdt", amount_syp,
                    transaction_code=tx_hash,
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🎉 *تم التحقق من إيداعك!*\n\n"
                        f"💎 *{amount} USDT* أضيفت لرصيدك تلقائياً ⚡\n"
                        f"💰 الرصيد المضاف: *{amount_syp:,.0f} ل.س*\n"
                        f"🔑 رقم الطلب: `{req_id}`"
                    ),
                    parse_mode="Markdown",
                )
                if config.ADMIN_ID:
                    await context.bot.send_message(
                        chat_id=config.ADMIN_ID,
                        text=(
                            f"✅ *إيداع USDT أوتو — #{req_id}*\n"
                            f"👤 `{user_id}`\n"
                            f"💎 {amount} USDT — {amount_syp:,.0f} ل.س\n"
                            f"🔗 `{tx_hash}`"
                        ),
                        parse_mode="Markdown",
                    )
            except Exception as e:
                logger.error(f"USDT credit error: {e}")
