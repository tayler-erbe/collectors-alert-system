# Drop Radar: domain knowledge (keep this current)

Owner: Tayler. User: her husband (collector and reseller). Started 22 Oct 2026. The `drop-radar` agent keeps this file up to date after every change, every weekly review and every monthly research pass.

## What he wants
- Alerts the moment a limited drop goes live, and **before** it drops whenever possible.
- Main interests: **PokÃ©mon, Disney Lorcana, One Piece, Dragon Ball (cards), Star Wars, Disney**; Hot Wheels Red Line Club (they are members); limited **G-Shock / Casio**, BOLDR, Seiko, Timex, Citizen watches; Bear Walker collab skate decks.
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
| PokÃ©mon Center | Random drops Mon to Thu, 8 to 11 am PT; the hardest to get | Waiting-room watch every minute in that window; site answers 403 to scripts, so the radar backs off. A paid monitor (PokePings) is the realistic way to get second-level speed |
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
- Runs from Task Scheduler (`install_task.ps1` â†’ `run_forever.cmd`).

## Hard rules
1. **Alerts only.** Never add to cart or check out, never join, skip or get around queues, never solve CAPTCHAs, never use rotating proxies, fake accounts or Discord self-bots.
2. If a site pushes back (429 or 403), check it less often or drop it. Never evade.
3. No secrets in the repo. `.env` is local only; the repo is public for GitHub Pages.
4. Recurring work runs through Task Scheduler or the job queue, never a chat-session shell.

## Feedback loop
- **He sends:** any text or dictation to the Telegram bot. To add a site straight away: `/add <url> [keywords]`. For issues with alerts or the website, ideas, or "put this on the radar", he just types or speaks it.
- **Backup:** an email to Tayler's Gmail with "Drop Radar" in the subject. The weekly review also searches her Gmail for that subject when a session has Gmail access.
- **Daily review** (watcher every 15 min queues a Claude job as soon as there is a new note or a source failed 24 h; max 8 a day, priority 9): read new notes, apply the changes (sources, keywords, windows, fixes), mark each note done in `feedback/done.jsonl`, and send him a summary on Telegram.
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
- 22 Oct 2026: added Reddit RSS (r/PKMNTCGDeals, r/PokemonRestocks, r/LorcanaRestocks; every 30 min) and Motor1 RSS (RLC sale dates). Reddit answered "403 Blocked" to our feed reads on the first day, so these may stay blocked; the proper route is a registered Reddit script app (before 31 Oct), as RSS ends 13 Nov. PokÃ©mon Center window now starts at 7:00 am PT (queues seen from 7:09 am).
- 22 Oct 2026: Discord reader built (alert/discord_feed.py). It reads every text channel in Charles's OWN private server every 30 s (channels he "Follows" from drop servers) through a bot Tayler creates. It needs DISCORD_BOT_TOKEN in .env (set 22 Oct; bot "Drop Radar", app id 1562962668107726938, read-only permissions 66560). His server is detected automatically when he authorizes the invite link, and a "Discord connected" Telegram message is sent.

- 22 Oct 2026: Discord reader now checks every 10 s; posts about IN-STORE stock (in-store, BrickSeek, store #, spotted at...) go to the dashboard only, because Charles wants online drops only. PokePings: its Discord listing claims free tier + ACO + monitors (unverified); earlier research said 8.99/mo. Auto-checkout is not part of Drop Radar (alerts only).

- 22 Oct 2026 (Charles, note #5): the website must never link to anything that downloads (feed files). Each source has a 'link' (a normal page); the dashboard uses it. Sources can be paused with "enabled": false (Reddit until an app is registered, BOLDR site down).

- 22 Oct 2026, resale-potential research (about 35 searches; prices are snapshots, often thin or from sellers; not financial advice):
  - **Pokemon 30th Celebration Ultra-Premium Collection Day / Night** (Espeon / Umbreon): out 6 Nov 2026, reported MSRP $179.99 (icv2 62819). Pre-sale listings on TCGplayer start around $665 (Dexerto, Oct 2026). 30th Celebration ETBs sold around $300 on eBay just after release, and Knock Out Collections went from $9.99 to $20-30 (icv2 63400, Sep 2026). The Japanese M6a box fell 63% in 15 days around release (thecardshopfinder, 16 Sep 2026), so hype fades fast.
  - **Delta Reign** (Pokemon): out 6 Nov 2026, prereleases 24 Oct to 1 Nov. Pokemon Center ETB $59.99 (11 packs, stamped Kyogre promo); pre-orders sold out in about an hour on 30 Sep. TCGplayer showed $527.97 on 1 Oct, but on only 3 listings (outof.games). Comparables: Ascended Heroes ETB $54.99 to about $155 on eBay (Aug 2026 guide); Perfect Order PC ETB about $124, 52-week range $121-307 (pokemonwizard).
  - **Further Pokemon dates:** Unova Heavy Hitters Premium Collection $59.99, 30th Celebration Binder Collection $31.99 and ex Tins $21.99, all 4 Dec 2026 (icv2 63405). Valentine's Day Box reported for 27 Jan 2027 (PokeBeach via Zatu; not official). Pokemon Night Out: LA 24 Oct, London 10 Nov; exclusive merch is to go online at Pokemon Center in limited quantities after the shows (resellcalendar, May 2026).
  - **Lorcana Hyperia City** (Coco): out 23 Oct 2026. Booster display MSRP $143.76; Illumineer's Trove $49.99 (Target already showed out of stock); Beast Gift Box $29.99 on 13 Nov (icv2 63037, 63121). Retailers list the display at $199-249. Comparable: Wilds Unknown 2-display lot, retail $288, averaged $463 on StockX over 3 months (21 sales).
  - **One Piece OP-18 "The Dominance of God"**: English 20 Nov 2026, $4.99 a pack, box price not printed (Samurai Sword, 8 Oct 2026). Japanese boxes have run well above MSRP: OP-13 went from ¥6,000 to about ¥27,000 by mid-2026, and OP-17 buyback was about ¥19,000 against ¥5,760 MSRP (Samurai Sword, a seller). No reliable English sealed resale data was found.
  - **Premium Bandai One Piece Premium Card Collections** ($20; Heroines Special Set $70; a reprint went on sale 14 May 2026). Prices rise after the order windows close (bonus-action; Samurai Sword guide).
  - **Dragon Ball Fusion World FB12 "Reach the God"**: Japan 12 Dec, English reported 18 Dec 2026 (unconfirmed). US shops show FB09/FB10 boxes out of stock at $180-240 (asking prices). Japanese MB01 went from ¥7,920 MSRP to about ¥91,000 (SNKRDUNK, Jun 2026; marketplace source).
  - **Bear Walker x One Piece** blind boxes (21 Aug 2026): $110 retail, unopened about $180-240 on eBay. The GEAR5 numbered cruiser ($395) resold unevenly, $370 to $1,000 (resellcalendar, 22 Aug 2026). Bear Walker hinted at Zoro and Ace boards "soon". bearwalker.com/products.json redirects (Queue-it), so the queue watcher plus Instagram stay the signal.
  - **Santa Cruz x Pokemon TCG blind-bag decks** already dropped on 17 Oct 2026 at 6 am PT: 30 designs plus 3 gold variants of 500 each (santacruzskateboards.com/pokemon, probed 22 Oct: 200, plain HTML). The 2023 bags sold for $100 and resold for $250-350. Find out whether our Santa Cruz page source (every 30 min) alerted.
  - **Hot Wheels RLC:** a Datsun 240Z "Chase Z" is due "this fall", and a 1995 BMW M3 E36 is the 2027 membership car (autoevolution, 12 Oct 2026). No Nov/Dec sale dates were found. Margins are thin: RLC BNR34 sold $41-60 on eBay in 2025.
  - **Watches:** no US anime G-Shock collab found for the next 3 months. BlackEyePatch DW-5600BEP-9 is Asia only, and Coca-Cola GA-2100CC-3A is only a rumor. Seiko 145th "Edo purple" limited editions (Oct 2026) run 2,000 to 9,999 pieces, which is too many for reliable resale. Noah x Timex Boatswain sold out (Maxim, Oct 2026). Resale evidence for watches is weak.
  - **Market context:** modern sealed Pokemon corrected 20-30% by Q1 2026, and Prismatic Evolutions is about 40-50% off its peak and near MSRP (pokemonpricetracker; a tool seller).

- 22 Oct 2026 (Charles, note #7 "Yes"): he accepted the weekly resale picks offer. Flag file `data/picks_weekly_approved` created; the Monday `radar-picks-*` jobs now run. Daily review health check: all sources fine; only Reddit (403, paused), BOLDR (down, paused) and Casio (403, slow checks) are failing, all known. Zoomies now checks OK.

- 22 Oct 2026 (late) daily review: no open notes (inbox 7, done 7). Health: only Casio (403, slow checks), BOLDR (down, paused) and Reddit x3 (403, paused) fail, all known; no source failing over 24 h that is not already handled. No changes made.
- 22 Oct 2026 evening: Charles judged everything sent so far as low value (junk keyword alerts linking to tracker pages, an irrelevant anime-news match, mainstream picks). Rules changed: news/tracker sources dashboard-only unless live/restock, no alerts from config changes, collab feeds need franchise+product word. Biggest remaining lever: the Discord hookup to restock-monitor servers.

- 22 Oct 2026 (late) daily review, notes #8 and #9:
  - **#8 "only interested in MSRP, no resell websites":** RULE: Charles wants retail (MSRP) information only. No resale sites as sources and no resale prices (eBay, StockX, TCGplayer, SNKRDUNK) in picks or alerts. Weekly picks now give: retail price, exact release date/time in PT, direct store link, and whether it is online. Resell Calendar source paused (`"enabled": false`; it was dashboard-only anyway). The older "resale-potential research" above is background only and must not be repeated to him.
  - **#9 "I already knew Spinnaker went live two hours ago":** the Spinnaker alert ("Crazy", back in stock, $600) fired at 20:38 PT, a restock seen late: the source checked only every 15 min and the product was in the 16:09 baseline. Spinnaker now checks every 2 min. Lesson: for small watch brands that drop often, 15 min is too slow; and he is often ahead of the radar on brands he follows, so only alert on what he can't easily see himself (restocks, exact times, early pages).
  - Health: only Casio (403, slow), BOLDR (down, paused), Reddit x3 (403, paused) fail, all known; none new over 24 h.

- 22 Oct 2026 (night) daily review: no open notes (inbox 9, all in done.jsonl). Health: only Casio (403, slow), BOLDR (down, paused), Reddit x3 (403, paused) fail, all known; --once ran clean. No changes, no Telegram sent (nothing new to confirm).

- 23 Oct 2026 daily review, notes #10-#14:
  - **#10 "Only include limited edition watches":** RULE: watch sources alert only on limited/collab/franchise keywords. Removed 5 Sports/Presage/Prospex/Marlin/Q Timex/"x " and "release"/"pre-order" (G-Central, Worn & Wound, Monochrome).
  - **#11 Target links useless:** the midnight Target reminders were a tracker guess with no link. Code: fixed reminders in sources.json can now carry `"url"` (alert/main.py run_reminders). Never present a tracker expectation as a confirmed Target drop.
  - **#12/#13 questions:** Target stock/timing is invisible to us (app only). Alerts should include a timeframe when known. Pokemon Center 403s scripts (hourly backoff); Discord reader healthy. Lorcana Hyperia City out 23 Oct: display $143.76, Trove $49.99, Prerelease Box $39.99 (icv2); Target/Walmart via TCG Drop Radar pages; Ravensburger blocks.
  - **#14:** no confirmed US Seiko collab date found (Puella Magi Madoka Magica chronographs 31 Aug 2026; Seiko 5 x Rowing Blazers sold out).
  - Health: only Casio (403), BOLDR (down), Reddit x3 (403) never ok, all known/paused; Pokemon Center news 403 from 7 am window, backing off. Code changed, loop restarted.

- 23 Oct 2026 (16:30) daily review, run by hand from Tayler's session because the queued reviews were blocked by the Claude launch budget. Notes #4, #5, #11, #12, #13, #15, #16 confirmed on Telegram (#4/#5/#11-#13 had been handled earlier but looked open, see bug 4).
  - **Bug 1, loop frozen up to 1 h (fixed):** `net.get` slept out a host's backoff (up to 3600 s for Pokemon Center/Casio 403s), freezing the WHOLE loop. Every source, Discord and Telegram commands effectively ran once an hour (events clustered at :28/:29). The Bear Walker "Kaido Collection" queue (event kaido102326, opened 12:00 PT 23 Oct) was announced at 11:29 but "OPEN NOW" only went out at 13:29. A host in backoff is now skipped (raises Blocked) instead of slept on.
  - **Bug 2, Shopify catalogue churn (fixed):** products.json returns at most 250 products. On big catalogs (Timex, Mattel) old products scroll in and out, and about 25 ordinary Timex watches (Easy Reader...) alerted as "new" overnight. Now an unseen product is "new" only if published in the last 14 days (`NEW_DAYS`), and an item that had been out of the window (last_seen older than max(3x interval, 1 h)) is never reported "back in stock". Not-buyable alerts say "the store has not announced a time" (his note #12: every alert needs a timeframe; we never guess one).
  - **Bug 3, restart didn't restart:** at 12:49 `schtasks /End` killed run_forever.cmd but left the python child (started 22 Oct 20:38) running, so code changes never went live. A code restart must also kill the python `alert.main` process (Get-CimInstance Win32_Process ... Stop-Process) before `/Run`, then check that exactly one new process exists.
  - **Bug 4, notes looked open forever (fixed):** notes_watcher matched done.jsonl on exact (t, text), and reviews had shortened the text, so 5 handled notes kept queueing reviews. It now matches on `t` only. It also ignores paused sources (`enabled: false`) for the >24 h health trigger.
  - **Discord is NOT connected:** the bot is in 0 servers (checked /users/@me/guilds, 23 Oct 16:35). The 12:49 reply "Discord reader healthy" was wrong; it only meant the code ran without errors. Charles was sent the invite link (https://discord.com/oauth2/authorize?client_id=1562962668107726938&permissions=66560&scope=bot) and steps: make a server, add the bot, Follow drop channels. Until the "Discord connected" message arrives, Discord gives no signal.
  - **Mattel Creations keywords now RLC only** (`red line club`, `rlc`; RLC products carry tag `brand_RLC`). Ten F1 "flash sale" Hot Wheels Premium cars ($10-25, tag `flashsale`, published 23 Oct) had alerted LIVE. Upcoming RLC product pages exist before the sale: Datsun 240Z Standard/Chase (published 22 Oct), Dodge Challenger (21 Oct, hidden_from_view), VW Rockster (20 Oct, hidden). Charles unticked the 240Z pick, so we don't push it.
  - **Casio G-Shock US paused:** 403 on every check since 22 Oct (>24 h). G-Central covers G-Shock limited news.
  - **Known facts (23 Oct):**
    - Worn & Wound x Timex "Field Watch w/a Twist" Storm (TW2Y52300) and Whirlpool: $299, limited to 500 per colour, announced 13 Nov 2025 (wornandwound.com). Out of stock on timex.ca at $399.
    - Timex answered 429 to one product .json request today; never probe Timex beyond the loop.
    - Lorcana Hyperia City (out 23 Oct): Target display A-1013166579 at $143.99 (MSRP; icv2 says $143.76), out of stock online at 16:30 PT. Miniature Market $189.99 (over MSRP). GameStop out of stock (he doesn't want GameStop). Official where-to-buy list: local game stores, Ravensburger store, Amazon.
    - Target product pages load stock client-side (static HTML has no availability text), so a direct Target product watch isn't possible without their private API. Don't build one.
    - No confirmed Target Pokemon drop for the night of 22-23 Oct was found.
    - Costco: no confirmed online Pokemon drop. Random weekdays, roughly monthly, sells out in under 5 min, sometimes behind a queue; busiest Oct-Dec. 30th Celebration ETB + booster bundle seen at $57.49 (warehouse, 16 Oct, out of stock).
    - Sam's: last online drop 21 Jul 2026 (Ascended Heroes Focused Fighters $54.98, 10 pm CT, Plus first). tcgdropradar (updated 20 Oct) claims online drops usually come 6-10 am CT on weekday mornings (unverified).
  - Cancelled the redundant queue job radar-daily-20261023T1630. Loop restarted 16:33 (new PID), --once clean.

- 23 Oct 2026 (17:16) Tayler's session: note #14 re-answered in full on Telegram (one message: Seiko answer, 30-day list, Discord status; sent 17:16 PT, not silent).
  - **Watch collab research (about 25 searches; dates as reported):**
    - Seiko: no collab with a US date in the next 60 days. Seiko x One Piece (5,000 pcs, ¥76,780, PREMICO Japan only, orders from 17 Aug 2026, ships mid-Jan 2027; fandomwire/toy-people). Seiko x Sega 65th (¥71,500, Japan, Oct 2026, Sega JP store; notebookcheck Feb 2026). Seiko 145th "Edo purple" wave (2,000-9,999 pcs, Japan on sale 9 Oct; US unpriced; notebookcheck, maxim). Seiko Metronome x Disney Mickey "Conductor" (500/100 pcs, JDM, only seen on reseller watchoutz). Seiko Metronome Fragment (VA Tokyo, 11 Feb 2026, sold out). Madoka Magica chronos (31 Aug), Rowing Blazers (sold out), HUF (Feb, $400).
    - G-Shock: MR-G Super Blue MRGB5000SA-2, 500 pcs, $6,600, and GMWB5000SB-1A2 $770, both "coming late November" on Casio US (notebookcheck). 2500 "CasioNaut" series Nov 2026, not limited, leaked US $145-300. Pokémon 30th GA-110PKM-7A ($270 US, pre-order 1 Jul, out 17 Jul 2026; g-central, complex). Coca-Cola GA-2100CC-3A still a rumor; Royal Navy model 2 "later 2026", no date.
    - Citizen: x Detective Conan 30th, ¥43,780, Japan mid-Nov 2026 (Kaito Kid 2,000 pcs; toy-people/jumpichiban). Mandalorian CA0857-09W $450, on sale since spring, not limited. 2026 Disney Collection (Pooh, Beauty and the Beast, Moana). No One Piece/Pokémon/Dragon Ball Citizen.
    - Timex: only Peanuts models (not limited); the Huckberry x Timex "Oct 25" search hit is from 2020, ignore. Spinnaker Fleuss seconde/seconde 2026: Quiet 850, Crazy 1,500, $600 (gearpatrol), already live.
  - **30-day list:** Walmart Collectibles Drawing entry 2-3 pm PT on Wednesdays (16, 23 Sep, 21 Oct; hip2save 21 Oct listed 30th Celebration bundles at MSRP). 6 Nov: Delta Reign, 30th UPC Day/Night, Mew/Mewtwo 30th Figure Collections, Ditto Premium Collection. 13 Nov Beast Gift Box. 20 Nov OP-18. Hot Wheels RLC Datsun 240Z page (jpm47) is up: $28, limit 2, Chase 5,000 numbered, no sale date in the description (one .js probe 23 Oct). No Nov/Dec RLC dates published (autoevolution 12 Oct preview lists models only). Pokémon Night Out merch went online 24 Sep. ONE PIECE DAY'26 PCC was a Japan P-Bandai lottery (22 Aug-7 Sep); no US date. No English Fusion World set in the window.
  - **sources.json reminders:** added `walmart-draw-wed` (Wed 13:55, url walmart.com). Updated text and added store `url` to pk-30th-upc-1106 (pokemoncenter.com), lorcana-beast-1113 and op18-1120 (Target search), pk-dec-wave-1204. --once clean (no alerts).
  - **Discord (17:05):** bot is in 1 server, "Drop Radar" (id 1563334095822659614): 4 channels = 2 categories, 1 text (#general), 1 voice. #general holds 1 message, the bot's own join notice (type 7). No followed channels or webhook posts yet, so Discord still gives no drop signal. Charles was told to Follow an announcement channel into his server.

- 24 Oct 2026 (05:45) daily review, note #19 (check Pokemon drops at his sites + limited stuff today): answered on Telegram. Searched web + tcgdropradar: no confirmed Pokemon or limited drop for Sat 24 Oct; no radar LIVE events overnight. Tracker patterns (unverified): Target restocks overnight ~1-3 am ET, Pokemon Center/Walmart weekday only, Costco random weekdays. Health: only Casio (403, paused), BOLDR (down, paused), Reddit x3 (403, paused) fail, all known; resellcalendar paused. --once clean. No code or sources.json changes.
