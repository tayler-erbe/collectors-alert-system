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
- Quiet hours 9 pm to 3 am PT (Tayler, 22 Oct 2026): alerts arrive silently in Telegram, loud channels skipped (QUIET_HOURS_PT in .env to change).
- Alert levels: **LIVE** (loud push), **SOON** (push), **INFO** (dashboard only).
- Phone: a Telegram bot (alerts, `/add`, `/remove`, `/list`, `/status`, `/remind`, `/reminders`). Anything else he texts or dictates, plus screenshots, photos, files and voice notes, is saved to `feedback/inbox.jsonl` with attachments in `feedback/attachments/` (LOCAL only, git-ignored: the repo is public). Voice notes are saved as audio; tell him the keyboard mic (speech-to-text) is better because the review reads text. Optional: Pushover (loud iPhone alerts), ntfy.
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
- **Daily review** (hourly watcher queues a Claude job the same day when there are open notes or a source failed 24 h; max 2 a day): read new notes, apply the changes (sources, keywords, windows, fixes), mark each note done in `feedback/done.jsonl`, and send him a summary on Telegram.
- **Monthly research** (job queue, 1st of the month): a deep dive into new drop sources, changed store procedures, new tools and monitors, and broken sources (the health table); improve the radar without being asked, then update this file.

## Known facts (dated)
- 22 Oct 2026: Reddit stops accepting new public API requests after 31 Oct 2026, and its RSS feeds end 13 Nov 2026. Nitter (X RSS) is effectively dead. The X API is pay-per-use. Instagram has no official way to get alerts for others' posts, so he keeps native post notifications on for key brands.
- 22 Oct 2026: bearwalker.com sat behind a Queue-it room (event "kaido1023") all afternoon.
- 22 Oct 2026, community-sources research (about 36 searches):
  - **Telegram:** no credible public US drop channel found for any of his categories. The drop communities are on Discord. A Telegram user-client is only worth building if he names channels he already follows.
  - **Telegram user clients are allowed.** The API is "100% open for all developers" (core.telegram.org/api). You need your own api_id from my.telegram.org, one per phone number. Accounts that log in through unofficial clients are "automatically put under observation", and flooding or spam gets a permanent ban (core.telegram.org/api/obtaining_api_id). The API terms forbid acting without the user's consent and using Telegram data to train AI (core.telegram.org/api/terms). Telethon is not standard library, so it would need an exception to the code-style rule.
  - **Discord channel Follow:** it only works on announcement channels (megaphone icon). The follower needs Manage Webhooks in the target channel. Posts arrive as a webhook under the source server's name, with role mentions stripped. The source admin decides which posts are published. Unfollow in Server Settings > Integrations > Channels Followed. API: `POST /channels/{id}/followers` (docs.discord.com/developers/resources/channel). Our bot can then read his own server's channel over REST (`GET /channels/{id}/messages`, which plain urllib can do). Most restock servers post alerts in ordinary channels, so check each server for a followable channel.
  - **Discord restock servers** (listing counts, self-reported):
    - PokePings: about 43k members; covers Pokemon Center, Target, Best Buy and Amazon; $8.99 a month with a 5-day trial (tcgdropradar.com, reviewed 20 Oct 2026; affiliate site).
    - Poke RestockR / Emerald Alerts: about 55k members; 35 US retailers; has a free tier, but Costco and Sam's may be paid-only.
    - Pokemon Restocks and Alerts: about 88k members; free.
    - PKMNTCGDeals: about 94k members; free; discord.gg/pkmntcgdeals.
    - TheHobbyBin: free.
    - TrackaLacker: free alerts, app push, about 37k Discord members; also covers Lorcana, Mattel Creations and P-Bandai products.
    - PackPing: free; One Piece, Pokemon and Lorcana, US and Canada; about 1.4k members.
    - TCGTRACKER (One Piece): $7.99 a month.
    - Poke Alerts app: $5.99 a month.
    - PokeNotify: $7.99 a month.
  - **Speed** (pagecrawl.io, updated 25 Sep 2026): paid bots (Hayha, Stock Informer) take seconds; Discord servers take 15 s to 5 min; retailer notify-me emails take 5 to 30 min; the Pokemon Center newsletter takes hours.
  - **Pokemon Center queues:** US openings 8 Jun to 22 Jul 2026 fell between 10:09 am and 1:13 pm ET, which is 7:09 to 10:13 am PT. Five of ten were on a Wednesday. X account @switchstock posts "Queue is Now Open" (tcgdropradar.com/pokemon-center-queue). Our Mon-Thu 8-11 am PT window misses some 7 am PT openings: think about starting it at 7:00.
  - **Walmart Collectibles Drawing:** a free-entry lottery that started 31 Aug 2026. You need a Walmart account with an address and a payment card saved; winners' orders are placed automatically (Dexerto, Kotaku, godisageek Sep 2026). r/PKMNTCGDeals posted "WALMART LOTTERY LIVE FOR 1 HOUR" and "WALMART QUEUE IS LIVE" on 21-22 Oct 2026, so the sub is very active and fast for Walmart, Target and Amazon.
  - **Reddit:** r/PKMNTCGDeals (about 122k members) is the one sub clearly worth it. r/PokemonRestocks (about 960) and r/LorcanaRestocks (about 505) are small. Reddit returned errors after two quick RSS reads today, so poll it gently. Reddit's API needs approval under the Responsible Builder Policy (Nov 2025).
  - **X API** is pay-per-use: $0.005 per post read, billed per post returned, capped at 2M reads a month. Basic and Pro tiers are closed to new sign-ups (postproxy.dev, opentweet.io, 2026). Watching 5 to 10 accounts with since_id should cost roughly $5 to $30 a month.
  - **Official lists:** Pokemon Center has email only ("Get Email Updates", marketing opt-in; slow; no SMS). Premium Bandai lottery and event entries go through the BANDAI TCG+ app (EB-05 event lottery 25 Sep to 4 Oct 2026). hobbyDB has no drop alerts. Sole Retriever app: sneaker restock, shock-drop and raffle alerts.
  - **RLC sale dates** are reported days ahead by autoevolution and motor1: F40 on 18 Aug and Skyline GT-R on 29 Sep 2026, both 9 am PT. Orange Track Diecast's RLC tag feed is stale (last post Apr 2026).
- Open items:
  - Telegram bot token from him.
  - iPhone or Android (Pushover?).
  - GitHub Pages switched on.
  - Task install.
  - Reddit registration before 31 Oct: yes or no.
  - Best Buy API key.
  - Zoomies URL.
  - Paid monitors: PokePings ~$9/mo; Restockr X free for 25 items.
  - (22 Oct) Community hook-in: does he want a private Discord server plus our bot to receive followed announcement channels? Which Telegram channels, if any, does he already follow? Should we try an X API trial with a $10 cap?
- 22 Oct 2026 (Charles): Bear Walker's "Kaido" Queue-it event (kaido1023, started 12:00 pm PT 22 Oct) is an AUSTRALIAN release, not his. Bear Walker's Instagram: 4 carved One Piece boards drop Friday 23 Oct (time not announced); reminder set for 8 am PT.
- 22 Oct 2026 bug fixed: Bear Walker runs an always-on Queue-it "safety net"; scripts get the queue page on roughly every other request, so "queue page seen" flapped 9 alerts in 30 min. The queue watcher now announces each Queue-it EVENT once (name and start time in PT), sends LIVE once when a future start time arrives, never alerts "closed", and for sites without event details needs 3 queue readings in a row (max 1 alert per 12 h).
- Confirmations: every note gets "received" automatically on arrival and a "processed" message from the daily review naming the note and what was done.
- 22 Oct 2026: added Reddit RSS (r/PKMNTCGDeals, r/PokemonRestocks, r/LorcanaRestocks; every 30 min) and Motor1 RSS (RLC sale dates). Reddit answered "403 Blocked" to our feed reads on the first day, so these may stay blocked; the proper route is a registered Reddit script app (before 31 Oct), as RSS ends 13 Nov. Pokémon Center window now starts at 7:00 am PT (queues seen from 7:09 am).
- 22 Oct 2026: Discord reader built (alert/discord_feed.py). It reads every text channel in Charles's OWN private server every 30 s (channels he "Follows" from drop servers) through a bot Tayler creates. It needs DISCORD_BOT_TOKEN and DISCORD_GUILD_ID in .env.
