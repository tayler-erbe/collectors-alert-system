"""Discord: forward drop posts from Charles's OWN private server to Telegram.

How it stays within Discord's rules: Charles "Follows" the announcement channels of drop servers (PokePings, Poke RestockR,
TheHobbyBin, PackPing, ...) into his private server. Discord itself copies those posts in. Our bot, a real bot account that
Tayler created and invited only to HIS server, reads his channels. We never read other servers and never use his personal
account (self-bots are banned).

.env:  DISCORD_BOT_TOKEN=...   DISCORD_GUILD_ID=<his server id>
Every text channel in his server is watched automatically, so following a new channel needs no change here.
Posts that match his interests (or a restock word) -> LIVE/SOON alert; others -> dashboard only.
"""
import json
import os
import time
import urllib.error
import urllib.request

from . import store

API = "https://discord.com/api/v10"
UA = "DiscordBot (https://github.com/tayler-erbe/collectors-alert-system, 1.0)"
INTEREST = ["pokemon", "pokémon", "lorcana", "one piece", "dragon ball", "star wars", "disney", "hot wheels", "rlc",
            "g-shock", "gshock", "bear walker", "topps", "panini"]
LIVE_WORDS = ["live", "in stock", "restock", "queue is open", "queue open", "available now", "add to cart", "atc", "dropped"]
CHANNEL_REFRESH_S = 600


def _get(path):
    req = urllib.request.Request(API + path, headers={"Authorization": "Bot " + os.environ["DISCORD_BOT_TOKEN"], "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry = json.loads(e.read() or b"{}").get("retry_after", 5)
            time.sleep(min(float(retry), 30))
            return None
        raise


def _text(m):
    parts = [m.get("content") or ""]
    for e in m.get("embeds", []):
        parts += [e.get("title") or "", e.get("description") or ""]
        parts += [f"{f.get('name', '')}: {f.get('value', '')}" for f in e.get("fields", [])]
    return "\n".join(p for p in parts if p).strip()


def _link(m, guild):
    for e in m.get("embeds", []):
        if e.get("url"):
            return e["url"]
    return f"https://discord.com/channels/{guild}/{m['channel_id']}/{m['id']}"


def configured():
    return bool(os.environ.get("DISCORD_BOT_TOKEN") and os.environ.get("DISCORD_GUILD_ID"))


def check(c):
    """Returns a list of (level, source_name, title, url, detail). The first look at a channel only records where we are."""
    guild = os.environ["DISCORD_GUILD_ID"]
    chans = store.kv_get(c, "discord_channels", {})
    if time.time() - store.kv_get(c, "discord_channels_t", 0) > CHANNEL_REFRESH_S:
        got = _get(f"/guilds/{guild}/channels") or []
        chans = {ch["id"]: ch["name"] for ch in got if ch.get("type") in (0, 5)}   # text and announcement channels
        store.kv_set(c, "discord_channels", chans)
        store.kv_set(c, "discord_channels_t", time.time())
    last = store.kv_get(c, "discord_last", {})
    out = []
    for cid, cname in chans.items():
        after = last.get(cid)
        msgs = _get(f"/channels/{cid}/messages?limit=50" + (f"&after={after}" if after else "")) or []
        if not msgs:
            continue
        newest = max(msgs, key=lambda m: int(m["id"]))["id"]
        if after:   # not the first look
            for m in sorted(msgs, key=lambda m: int(m["id"])):
                t = _text(m)
                if not t:
                    continue
                low = t.lower()
                author = (m.get("author") or {}).get("username", "")
                interest = any(k in low for k in INTEREST)
                level = "LIVE" if interest and any(w in low for w in LIVE_WORDS) else "SOON" if interest else "INFO"
                title = t.splitlines()[0][:140]
                out.append((level, f"Discord #{cname} ({author})", title, _link(m, guild), t[len(title):][:600].strip()))
        last[cid] = newest
    store.kv_set(c, "discord_last", last)
    return out
