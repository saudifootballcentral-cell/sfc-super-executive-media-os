# SFC Super Executive Media OS — Credential Matrix

All connectors follow the MOCK pattern: credential-ready but no real API calls without credentials set.

| Platform | Auth Type | Railway Environment Variables | Route | Status |
|----------|-----------|-------------------------------|-------|--------|
| X (via Buffer) | OAuth 2.0 Bearer | `BUFFER_ACCESS_TOKEN` ✅ | Buffer | ACTIVE |
| X (Direct) | OAuth 1.0a | `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET` | Direct | WAITING_CREDENTIALS |
| YouTube (Direct) | OAuth 2.0 | `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_CHANNEL_ID` | Direct | WAITING_CREDENTIALS |
| Instagram (via Buffer) | OAuth 2.0 | `BUFFER_INSTAGRAM_PROFILE_ID` | Buffer | WAITING_BUFFER_PROFILE |
| Instagram (Direct Graph API) | Long-lived token | `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Direct | WAITING_CREDENTIALS |
| TikTok (via Buffer) | OAuth 2.0 | `BUFFER_TIKTOK_PROFILE_ID` | Buffer | WAITING_BUFFER_PROFILE |
| TikTok (Direct) | OAuth 2.0 | `TIKTOK_ACCESS_TOKEN`, `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` | Direct | WAITING_CREDENTIALS |
| Facebook (via Buffer) | Page Token | `BUFFER_FACEBOOK_PROFILE_ID` | Buffer | WAITING_BUFFER_PROFILE |
| Facebook (Direct Graph API) | Page Access Token | `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID` | Direct | WAITING_CREDENTIALS |
| LinkedIn (via Buffer) | OAuth 2.0 | `BUFFER_LINKEDIN_PROFILE_ID` | Buffer | WAITING_BUFFER_PROFILE |
| LinkedIn (Direct) | OAuth 2.0 | `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_ORGANIZATION_ID` | Direct | WAITING_CREDENTIALS |
| Threads (via Buffer) | OAuth 2.0 | `BUFFER_THREADS_PROFILE_ID` | Buffer only | WAITING_BUFFER_PROFILE |
| Telegram (Direct) | Bot Token | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID` | Direct only | WAITING_CREDENTIALS |
| WhatsApp Business (Direct) | Bearer Token | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_BUSINESS_ACCOUNT_ID` | Direct only | WAITING_CREDENTIALS |
| Discord (Direct) | Bot Token | `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`, `DISCORD_SERVER_ID` | Direct only | WAITING_CREDENTIALS |
| Pinterest (Direct) | OAuth 2.0 | `PINTEREST_ACCESS_TOKEN`, `PINTEREST_BOARD_ID` | Direct only | WAITING_CREDENTIALS |
| Reddit (Direct) | OAuth 2.0 Password | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD` | Direct only | WAITING_CREDENTIALS |
| Medium (Direct) | Integration Token | `MEDIUM_ACCESS_TOKEN`, `MEDIUM_AUTHOR_ID` | Direct only | WAITING_CREDENTIALS |
| WordPress (Direct) | Application Password | `WORDPRESS_SITE_URL`, `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD` | Direct only | WAITING_CREDENTIALS |
| Email/Newsletter (Direct) | SMTP Credentials | `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_FROM_ADDRESS`, `EMAIL_LIST_ID` | Direct only | WAITING_CREDENTIALS |
| Webhook (Direct) | HMAC Secret | `WEBHOOK_URL`, `WEBHOOK_SECRET` (per-webhook) | Direct only | READY (no creds required) |

## Activation Steps

### To activate X Direct:
1. Apply for Elevated access at developer.twitter.com
2. Create OAuth 1.0a credentials
3. Set `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET` in Railway

### To activate Instagram Direct:
1. Create a Meta Business App with `instagram_basic`, `instagram_content_publish` permissions
2. Generate a long-lived Page Access Token
3. Set `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_BUSINESS_ACCOUNT_ID` in Railway

### To activate Buffer profiles (Instagram, TikTok, Facebook, LinkedIn, Threads):
1. Connect each social account in app.buffer.com
2. Copy the profile ID from Buffer's channel settings
3. Set `BUFFER_{PLATFORM}_PROFILE_ID` in Railway

### To activate Telegram:
1. Create a bot via @BotFather on Telegram
2. Add the bot to your channel as admin
3. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL_ID` in Railway

### To activate WhatsApp Business:
1. Create a Meta Business App with WhatsApp permissions
2. Add a WhatsApp Business phone number
3. Set `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_BUSINESS_ACCOUNT_ID` in Railway

### To activate Discord:
1. Create a Discord application + Bot at discord.com/developers
2. Add the bot to your server with `Send Messages` permission
3. Set `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`, `DISCORD_SERVER_ID` in Railway

## Router Logic

The `PublisherRouter` (`src/sfc/connectors/routing/publisher_router.py`) selects the route:

```
PLATFORM_PREFER_DIRECT=true → try Direct first
Direct credentials present → use Direct API
Buffer profile ID present → use Buffer
Neither → skip with warning
```

Set `PLATFORM_PREFER_DIRECT=true` in Railway to always prefer direct API connectors when both paths are available.
