# Collectors Alert System (Drop Radar)

Real-time alerts for limited drops (trading cards, toys, collectibles, watches, sneakers, big-box restocks), sent to a phone in seconds, plus a live dashboard on GitHub Pages.

**Alerts only.** It never adds to cart, buys, joins or skips a queue, solves CAPTCHAs or uses proxies to dodge blocks. If a site pushes back (429/403), it checks that site less often.

## How it works
- `alert/main.py` runs on the home PC around the clock (Task Scheduler starts `run_forever.cmd` at logon and restarts it if it stops).
- Every source in `sources.json` is checked on its own interval:
  - `shopify`: the store's product feed. New products and items coming back into stock.
  - `queue`: watches a homepage for a waiting room (Queue-it etc.). A queue appearing means a drop is starting.
  - `page`: new links or keywords appearing on a news or brand page.
  - `rss`: new posts on a feed.
- Alert levels:
  - **LIVE**: buyable now or the queue is up. Loud push.
  - **SOON**: a new page or announcement. Normal push.
  - **INFO**: a change. Dashboard only.
- `docs/` is the dashboard. The PC publishes `docs/data.json` every 10 minutes.

## Phone alerts
Copy `.env.example` to `.env` (never committed) and fill in:
- **Telegram bot** (alerts, and adding sites by text):
  1. In Telegram, message @BotFather, send `/newbot` and copy the token.
  2. Message your new bot once.
  3. Put the token in `TELEGRAM_BOT_TOKEN`.
  4. Find your chat id in the log (`ignored message from chat ...`) and put it in `TELEGRAM_CHAT_ID`.
- **Pushover** (optional, iPhone, can break through silent mode for LIVE alerts): put `PUSHOVER_TOKEN` and `PUSHOVER_USER` in `.env`.
- **ntfy** (optional, Android): set `NTFY_TOPIC`.

## Adding sites (text the bot)
```
/add https://example.com            watch everything new
/add https://example.com pokemon one_piece   only alert on these keywords
/list   /remove <id>   /status
```

## Run
```
python -m alert.main --once     # one pass, for testing
powershell -File install_task.ps1   # start at logon, keep running
```
