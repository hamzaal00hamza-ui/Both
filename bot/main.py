"""
نقطة تشغيل البوت
"""
import json
import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
 
from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault, MenuButtonCommands
from telegram.ext import Application
 
from . import config, database as db
from .handlers_user import register_user_handlers
from .handlers_admin import register_admin_handlers
from .jobs import schedule_jobs
 
# مفتاح سري لحماية نقطة التحقق (الموقع لازم يبعته)
CHECK_API_SECRET = os.environ.get("CHECK_API_SECRET", "")
 
 
class _HealthHandler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
 
    def do_GET(self):
        parsed = urlparse(self.path)
 
        # ===== نقطة التحقق من اسم اللاعب (للموقع) =====
        if parsed.path == "/api/check-player":
            q = parse_qs(parsed.query)
            secret = (q.get("secret", [""])[0]).strip()
            player = (q.get("player", [""])[0]).strip()
            product = q.get("product", ["0"])[0]
 
            expected = (CHECK_API_SECRET or "").strip()
 
            # وضع تشخيص: أضف &debug=1 لرؤية القيم (احذفه بعد الحل)
            if q.get("debug", [""])[0] == "1":
                self._json(200, {
                    "secret_from_url": secret,
                    "secret_len_url": len(secret),
                    "secret_expected_len": len(expected),
                    "match": secret == expected,
                    "expected_is_set": bool(expected),
                })
                return
 
            if expected and secret != expected:
                self._json(403, {"ok": False, "msg": "unauthorized"})
                return
            if not player:
                self._json(200, {"ok": False, "msg": "أدخل ID اللاعب أولاً"})
                return
            try:
                product_id = int(product) if str(product).isdigit() else 0
            except Exception:
                product_id = 0
 
            try:
                from .fastcard_web import check_player
                res = check_player(player, product_id or 7816)
                # توحيد شكل الرد للموقع
                name = res.get("player_name") or res.get("name") or res.get("username")
                valid = res.get("valid")
                success = res.get("success")
                if (success or (valid and valid != "invalid")) and name:
                    self._json(200, {"ok": True, "name": name})
                else:
                    self._json(200, {"ok": False, "msg": "ID غير صحيح أو لم يتم العثور على اللاعب"})
            except Exception as e:
                logging.getLogger(__name__).warning(f"check-player api error: {e}")
                self._json(200, {"ok": False, "soft": True, "msg": "تعذّر التحقق حالياً"})
            return
 
        # ===== health check =====
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK - Telegram bot is running\n")
 
    def log_message(self, *args, **kwargs):
        pass
 
 
def _start_health_server():
    port = int(os.environ.get("PORT", "8080"))
    try:
        server = HTTPServer(("0.0.0.0", port), _HealthHandler)
        logging.getLogger(__name__).info(f"Health server listening on :{port}")
        server.serve_forever()
    except Exception as e:
        logging.getLogger(__name__).error(f"Health server failed: {e}")
 
 
async def _post_init(app: Application) -> None:
    public_cmds = [
        BotCommand("start", "🏠 القائمة الرئيسية"),
    ]
    await app.bot.set_my_commands(public_cmds, scope=BotCommandScopeDefault())
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
 
    if config.ADMIN_ID:
        admin_cmds = [
            BotCommand("start", "🏠 القائمة الرئيسية"),
            BotCommand("admin", "🛠️ لوحة الأدمن"),
        ]
        try:
            await app.bot.set_my_commands(
                admin_cmds, scope=BotCommandScopeChat(chat_id=config.ADMIN_ID)
            )
        except Exception as e:
            logging.getLogger(__name__).warning(f"set admin commands failed: {e}")
 
 
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
 
 
def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN غير مضبوط. أضفه عبر الأسرار (Secrets).")
        sys.exit(1)
 
    db.init_db()
    logger.info("Database initialized.")
 
    if not config.ADMIN_ID:
        logger.warning("ADMIN_ID is not set — لوحة الأدمن وإشعارات الطلبات معطلة. أضفها كمتغير بيئة.")
 
    app = Application.builder().token(config.BOT_TOKEN).post_init(_post_init).build()
 
    register_admin_handlers(app)
    register_user_handlers(app)
 
    schedule_jobs(app)
 
    # health check server في thread منفصل (Replit deployment يتوقع port مفتوح)
    t = threading.Thread(target=_start_health_server, daemon=True)
    t.start()
 
    logger.info("Bot is starting (polling)...")
    app.run_polling(allowed_updates=None, drop_pending_updates=True)
 
 
if __name__ == "__main__":
    main()
