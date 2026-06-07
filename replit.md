# Telegram Bot for Game Top-ups

This Telegram bot allows users to top up games (PUBG, Free Fire, Call of Duty) and purchase various digital goods.

## Run & Operate

- **Run Bot**: `python -m bot.main` (uses long polling)
- **Environment Variables**:
    - `BOT_TOKEN`: Telegram bot token from @BotFather
    - `ADMIN_ID`: Admin's Telegram user ID (for notifications and `/admin` panel)
    - `SHAMCASH_TOKEN`: Bearer token for Sham Cash API
    - `SHAMCASH_API_URL`: (Optional) Sham Cash API base URL, defaults to `https://api.shamcash-api.com/v1`
    - `SHAMCASH_ACCOUNT_ID`: (Optional) Sham Cash account ID
    - `SHAMCASH_AUTO_VERIFY`: (Optional) `true` to enable automatic verification (default)
    - `SHAMCASH_VERIFY_WINDOW_MIN`: (Optional) Time window in minutes for Sham Cash transaction lookup (default 30)
    - `SYRIATEL_CASH_TOKEN`: Syriatel Cash API token
    - `SYRIATEL_CASH_API_URL`: (Optional) Syriatel Cash API base URL, defaults to `https://api.melchersman.com/syr-cash/v1`
    - `SYRIATEL_CASH_AUTO_VERIFY`: (Optional) `true` to enable automatic verification (default)
    - `USD_TO_SYP`: (Optional) Default USD to SYP conversion rate (default 13100)
    - `PRICE_CHECK_HOUR_UTC`: (Optional) Hour (UTC) for daily price check job (default 6)
    - `PRICE_CHECK_MINUTE_UTC`: (Optional) Minute (UTC) for daily price check job (default 0)
    - `AUTO_COUPON_BROADCAST`: (Optional) `True` to broadcast auto-generated coupons to all users (default `False`)

## Stack

- **Language**: Python 3.11
- **Framework**: `python-telegram-bot` 21.6
- **Database**: SQLite (`bot/database.db`)
- **Build Tool**: `pnpm` (for historical `api-server` and `mockup-sandbox` workspaces, not directly used by the bot)

## Where things live

- `bot/main.py`: Bot entry point.
- `bot/config.py`: Configuration and environment variables.
- `bot/database.py`: SQLite database layer.
- `bot/keyboards.py`: Inline keyboard definitions.
- `bot/handlers_user.py`: User-facing handlers and conversations.
- `bot/handlers_admin.py`: Admin panel handlers.
- `bot/shamcash.py`: Sham Cash automatic verification integration.
- `bot/fastcard.py`: Fastcard API client.
- `bot/syriatel_cash.py`: Syriatel Cash API client.
- `bot/notify.py`: Notification module for admin and channel.
- `bot/jobs.py`: Scheduled jobs (e.g., price checks, auto-coupons).
- `bot/chart.py`: Profit chart generation.
- **DB Schema**: Defined implicitly in `bot/database.py` (functions like `create_tables`).
- **API Contracts**:
    - Sham Cash API: [https://shamcash-api.com/docs](https://shamcash-api.com/docs)
    - Syriatel Cash API: [https://api.melchersman.com/syr-cash/api-docs](https://api.melchersman.com/syr-cash/api-docs)
- **Offer Definitions**: `bot/config.py` (`_OFFERS`, `_MEMBERSHIPS`, `_CODES`, `FASTCARD_CATEGORIES`).

## Architecture decisions

- **Dynamic Pricing**: Offer prices are dynamically calculated based on `cost_usd` and current `syp_per_usd` exchange rates, rounded for user convenience, ensuring pricing flexibility.
- **Referral System**: A multi-faceted referral system rewards both referrer (percentage of referred user's top-ups) and new users (signup bonus), encouraging growth.
- **ConversationHandler Re-entry**: Enabled `allow_reentry=True` for all `ConversationHandler` instances to prevent users from getting stuck in previous conversation states, improving robustness.
- **Automated Transaction Verification**: Integrated automatic verification for Syriatel Cash and Sham Cash payments, significantly reducing manual admin overhead and speeding up user top-ups.
- **Secure Handling of Sensitive Data**: Passwords and sensitive input fields are redacted from logs and stored securely (hashed or summarized), and Telegram messages containing sensitive data are immediately deleted to enhance user privacy and security.
- **Modular Notification System**: Centralized notification logic in `bot/notify.py` to send messages to both admin DMs and a dedicated documentation channel, ensuring all important events are archived and monitored.

## Product

- **User-facing Capabilities**:
    - **Game Top-ups**: PUBG Mobile (UC, memberships, codes), Free Fire (diamonds, memberships, codes), Supercell (Brawl Stars, CoC, Clash Royale, Hay Day), Call of Duty Mobile (CP, Battle Pass), Delta Force, Minecraft, Fortnite, Ludo.
    - **Digital Cards**: PlayStation, Steam, iTunes, Google Play, Xbox, Razer Gold, Nintendo, Netflix, VISA Prepaid.
    - **App Subscriptions**: Shahid VIP, YouTube Premium, Netflix, Anghami Plus, OSN+, ChatGPT Plus, Canva Pro, Snapchat+, VPNs (Nord, Express, LagoFast), Telegram channel boosts.
    - **SMM Services**: Instagram followers/likes/views, Facebook followers, Telegram views/engagement.
    - **Syriatel Cash / MTN Balance Top-ups**: Custom amounts with dynamic pricing based on old SYP currency.
    - **Sham Cash Integration**: Automatic verification for USD top-ups.
    - **Loyalty Program**: Earn points on purchases, redeemable for balance.
    - **Discount Coupons**: Apply fixed or percentage-based coupons.
    - **Referral System**: Invite friends and earn commission; new users get a signup bonus.
- **Admin Panel**:
    - **Statistics & Reports**: View pending orders, search, modify balance, ban users, broadcast messages.
    - **Profit Reports**: Detailed profit analysis by period (daily, weekly, monthly, all-time) with net profit, margin, and category breakdown.
    - **Profit Charts**: Visual representation of sales, costs, and daily profit over time.
    - **Exchange Rate Management**: Adjust `syp_per_usd` (offer pricing) and `usd_to_syp` (Sham Cash conversion).
    - **Top Spenders**: List of users by total approved spending.
    - **Order Ratings**: View average rating, distribution, and recent reviews; automatic alerts for low ratings.
    - **Coupon Management**: Create, disable, and view coupons; activate auto-coupon generation.
    - **Fastcard Price Check**: Daily job to detect price changes in Fastcard offers and alert admin.
    - **Syriatel Cash Balance**: On-demand check of the bot's Syriatel Cash wallet balance.
    - **Order Documentation Channel**: Configure a Telegram channel for archiving all order notifications.

## User preferences

- _Populate as you build_

## Gotchas

- **Syriatel Cash Pricing**: All Syriatel/MTN balance section prices are displayed and priced in "old SYP". The Fastcard API uses an internal system where 1 API unit is equivalent to 100 old SYP. Manual pricing is applied to these offers.
- **Fastcard Price Discrepancies**: Fastcard does not notify the bot of price changes. The daily price check job helps identify these, but manual adjustments to `cost_usd` in `config.py` might still be needed.
- **ConversationHandler State**: Ensure `allow_reentry=True` is consistently applied to all `ConversationHandler` definitions to prevent users from getting stuck in previous conversation states.
- **Transaction Consumption**: The `consume_transaction` mechanism relies on atomic `INSERT` into `consumed_transactions` to prevent double-spending; any `IntegrityError` will lead to rejection.

## Pointers

- **python-telegram-bot Documentation**: [https://python-telegram-bot.org/en/stable/](https://python-telegram-bot.org/en/stable/)
- **SQLite Documentation**: [https://www.sqlite.org/docs.html](https://www.sqlite.org/docs.html)
- **Fastcard API (Internal)**: Refer to the internal Fastcard API documentation for product IDs and structure.
- **Sham Cash API Documentation**: [https://shamcash-api.com/docs](https://shamcash-api.com/docs)
- **Syriatel Cash API Documentation (Melchersman)**: [https://api.melchersman.com/syr-cash/api-docs](https://api.melchersman.com/syr-cash/api-docs)
- **Matplotlib Documentation (for charts)**: [https://matplotlib.org/stable/contents.html](https://matplotlib.org/stable/contents.html)