# Integrations and environment

`src/config.py` requires `.env`. Important names are `DB_HOST`, `DB_PORT`,
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `TELEGRAM_TOKEN`, `API_BASE_URL`,
`API_BASE_PATH`, and `APP_ENV`. Do not reveal their values.

`telegram_bot.py` configures the Mini App menu and notification worker. `/start`
offers the Mini App; `telegram_webapp_service.py` validates Telegram `initData`
when linking an account.

With `APP_ENV=TEST` and no `CLOUDFLARE_TUNNEL_TOKEN`, cloudflared creates a
temporary `*.trycloudflare.com` URL to localhost. It changes after every restart.
The bot checks DNS and HTTPS before publishing it in the menu, and does not send
permanent inline buttons for temporary URLs. A named tunnel uses
`CLOUDFLARE_TUNNEL_TOKEN` plus stable HTTPS `TELEGRAM_WEB_APP_URL`.

`/webhooks/whatsapp` validates Meta's challenge and HMAC SHA-256 signature using
`WHATSAPP_WEBHOOK_VERIFY_TOKEN` and `META_APP_SECRET`. WhatsApp flow logic is in
`whatsapp_service.py` and `whatsapp_conversation_service.py`.
