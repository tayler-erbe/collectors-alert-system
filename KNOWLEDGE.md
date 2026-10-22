# Drop Radar: domain knowledge (keep this current)

Owner: Tayler. User: her husband (collector and reseller). Started 22 Oct 2026. The `drop-radar` agent keeps this file up to date after every change, every weekly review and every monthly research pass.

## What he wants
- Alerts the moment a limited drop goes live, and **before** it drops whenever possible.
- Main interests: **Pokémon, Disney Lorcana, One Piece, Dragon Ball (cards), Star Wars, Disney**; Hot Wheels Red Line Club (they are members); limited **G-Shock / Casio**, BOLDR, Seiko, Timex, Citizen watches; Bear Walker collab skate decks.
- He does **not** much want limited toys in general. He does not want GameStop ("don't want to pay retail").
- He is US-based and Pacific time. He uses Amazon Japan and watches Japan as a leading indicator.

## His routine (his words, 22 Oct 2026)
| Store | How drops work | What the radar does |
|---|---|---|
| Premium Bandai | Random nights ~7 pm PT (One Piece, Dragon Ball cards, limited items) | Reminder at 6:50 pm; checks the new-arrivals page every minute from 6:40 to 7:40 pm |
| Topps | New releases carry a countdown timer; usually daily, 9 to 11 | Site blocks scripts (403). He texts the timer time: `/remind 9:30 Topps ...` |
| Nintendo | No timer; limited items sell out fast | Store merchandise page, every 15 min |
| Target | Release drawings, pre-sale and pre-order; no notice | App-based. TCG Drop Radar Target page every 15 min; keep app notifications on |
| BOLDR | Limited watches; he follows them on Instagram for pre-sale or pre-order | Site timed out on 22 Oct; Instagram is the main signal |
| Ravensburger (Lorcana) | Shop pre-orders for new sets | ravensburger.us blocks (403). Lorcana news page every 15 min |
| Walmart | Walmart Wednesday: a lottery or raffle with collectible drops ~1 to 3 pm and 6 pm PT | Reminders Wed 12:50 and 17:50; TCG Drop Radar Walmart page |
| Best Buy | Drops section (wait for it to go live, then join); card pre-orders | Bot-guarded. TCG Drop Radar Best Buy page. The official Products API needs a free key (open item) |
| Mattel Creations (Hot Wheels RLC) | Drops about every 2 weeks at 9 am PT; sell out instantly | Shopify product feed (new RLC products show up before the drop) plus waiting-room watch; 30 to 60 s checks 8:45 to 9:30 am |
| Meccha Japan | Resale site; shows what releases in the US the next day | Site has a human-verification wall. Not watched (we never get around bot checks) |
| Pokémon Center | Random drops Mon to Thu, 8 to 11 am PT; the hardest to get | Waiting-room watch every minute in that window; site answers 403 to scripts, so the radar backs off. A paid monitor (PokePings) is the realistic way to get second-level speed |
| Sam's Club, Costco | Online drops with no notice; found through Instagram and other sites | TCG Drop Radar Costco and Sam's pages every 15 min |
| Nike (SNKRS and the main Nike app), Adidas Confirmed, Foot Locker, Dick's | App drops or lotteries; Nike and Dick's also do random drops | App notifications on; Foot Locker release-dates page hourly. Apps are heavily bot-guarded: do not poll them |
| Zoomies, Casio G-Shock | Limited G-Shock releases | Casio blocks (403) and gets slow checks; G-Central RSS covers G-Shock news. The Zoomies URL is still to confirm |

## How it works (code)
- `alert/main.py`: the always-on loop. `sources.json`: what is watched, with intervals, keywords, drop `windows` (PT) and fixed `reminders`.
- Source kinds:
  - `shopify`: `/products.json`; new products and back-in-stock.
  - `queue`: a Queue-it waiting room appearing on the homepage means a drop is starting.
  - `page`: new keyword links or keywords on a page.
  - `rss`: new posts on a feed.
- Alert levels: **LIVE** (loud push), **SOON** (push), **INFO** (dashboard only).
- Phone: a Telegram bot (alerts, `/add`, `/remove`, `/list`, `/status`, `/remind`, `/reminders`). Anything else he texts or dictates is saved to `feedback/inbox.jsonl`. Optional: Pushover (loud iPhone alerts), ntfy.
- Dashboard: `docs/` on GitHub Pages; the PC publishes `docs/data.json` every 10 min.
- Runs from Task Scheduler (`install_task.ps1` → `run_forever.cmd`).

## Hard rules
1. **Alerts only.** Never add to cart or check out, never join, skip or get around queues, never solve CAPTCHAs, never use rotating proxies, fake accounts or Discord self-bots.
2. If a site pushes back (429 or 403), check it less often or drop it. Never evade.
3. No secrets in the repo. `.env` is local only; the repo is public for GitHub Pages.
4. Recurring work runs through Task Scheduler or the job queue, never a chat-session shell.

## Feedback loop
- **He sends:** any text or dictation to the Telegram bot. To add a site straight away: `/add <url> [keywords]`. For issues with alerts or the website, ideas, or "put this on the radar", he just types or speaks it.
- **Backup:** an email to Tayler's Gmail with "Drop Radar" in the subject. The weekly review also searches her Gmail for that subject when a session has Gmail access.
- **Weekly review** (job queue, Mondays): read new notes, apply the changes (sources, keywords, windows, fixes), mark each note done in `feedback/done.jsonl`, and send him a summary on Telegram.
- **Monthly research** (job queue, 1st of the month): a deep dive into new drop sources, changed store procedures, new tools and monitors, and broken sources (the health table); improve the radar without being asked, then update this file.

## Known facts (dated)
- 22 Oct 2026: Reddit stops accepting new public API requests after 31 Oct 2026, and its RSS feeds end 13 Nov 2026. Nitter (X RSS) is effectively dead. The X API is pay-per-use. Instagram has no official way to get alerts for others' posts, so he keeps native post notifications on for key brands.
- 22 Oct 2026: bearwalker.com sat behind a Queue-it room (event "kaido1023") all afternoon.
- Open items:
  - Telegram bot token from him.
  - iPhone or Android (Pushover?).
  - GitHub Pages switched on.
  - Task install.
  - Reddit registration before 31 Oct: yes or no.
  - Best Buy API key.
  - Zoomies URL.
  - Paid monitors: PokePings ~$9/mo; Restockr X free for 25 items.
