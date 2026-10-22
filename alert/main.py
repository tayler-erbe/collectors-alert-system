"""The always-on loop: checks each source when it is due, sends alerts, answers the Telegram bot, refreshes the dashboard.
  python -m alert.main            run forever (Task Scheduler starts it at logon and restarts it if it stops)
  python -m alert.main --once     check every source once and exit (testing)
"""
import json
import random
import subprocess
import sys
import time
import traceback
import urllib.parse
import urllib.request
from pathlib import Path

from . import checkers, net, notify, schedule, store

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources.json"
DASH = ROOT / "docs" / "data.json"
DASH_EVERY_S = 600


def load_sources():
    return json.loads(SOURCES.read_text(encoding="utf-8"))


def save_sources(d):
    SOURCES.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def check(c, src):
    fn = checkers.KINDS[src["kind"]]
    try:
        found = fn(c, src)
        store.health(c, src["id"])
    except net.Blocked as e:
        store.health(c, src["id"], str(e))
        return
    except Exception as e:
        store.health(c, src["id"], f"{type(e).__name__}: {e}")
        print("check failed", src["id"], e, flush=True)
        return
    for level, title, url, detail in found:
        store.event(c, src["id"], level, title, url, detail)
        notify.send(level, src["name"], title, url, detail)


# ------------------------------------------------------------------ Telegram commands (only from allowed chats)
def guess_kind(url):
    u = url.lower()
    if u.endswith((".xml", ".rss", "/feed", "/rss", ".atom")) or "/feed/" in u:
        return "rss"
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(url))
    try:
        st, txt = net.get(base + "/products.json?limit=1", accept="application/json")
        if '"products"' in txt[:200]:
            return "shopify"
    except Exception:
        pass
    return "page"


def handle(cmd, args):
    d = load_sources()
    if cmd == "/add" and args:
        url = args[0] if args[0].startswith("http") else "https://" + args[0]
        kind = guess_kind(url)
        if kind == "shopify":
            url = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(url))
        sid = urllib.parse.urlsplit(url).netloc.replace("www.", "").split(".")[0]
        sid = sid + ("-" + str(len(d["sources"])) if any(s["id"] == sid for s in d["sources"]) else "")
        kws = [a.replace("_", " ") for a in args[1:]]
        d["sources"].append({"id": sid, "name": urllib.parse.urlsplit(url).netloc, "kind": kind, "url": url,
                             "interval_s": 300 if kind != "page" else 600, "keywords": kws, "group": "added",
                             "added": time.strftime("%Y-%m-%d")})
        save_sources(d)
        return (f"Added {sid} ({kind}), checked every {d['sources'][-1]['interval_s'] // 60} min"
                + (f", keywords: {', '.join(kws)}" if kws else ", alerts on anything new") + ".\nThe first check only learns what's there; alerts start after that.")
    if cmd == "/remove" and args:
        n = len(d["sources"])
        d["sources"] = [s for s in d["sources"] if s["id"] != args[0]]
        save_sources(d)
        return f"Removed {args[0]}." if len(d["sources"]) < n else f"No source called {args[0]}. Send /list."
    if cmd == "/remind":
        r = schedule.parse_remind(args)
        if not r:
            return "Use: /remind 9:30 Topps Chrome   or   /remind 10/24 7pm Premium Bandai One Piece (Pacific time)"
        when, text = r
        c = store.conn()
        rem = store.kv_get(c, "reminders", [])
        rem.append({"at": when.isoformat(), "text": text, "warned": False})
        store.kv_set(c, "reminders", rem)
        return f"OK: I'll ping you 10 min before and at {when:%a %b %d %I:%M %p} PT: {text}"
    if cmd == "/reminders":
        c = store.conn()
        rem = store.kv_get(c, "reminders", [])
        return "\n".join(f"{r['at'][5:16].replace('T', ' ')} {r['text']}" for r in rem) or "No reminders set."
    if cmd == "/list":
        return "\n".join(f"{s['id']}: {s['name']} ({s['kind']}, {s['interval_s'] // 60 or 1} min)" for s in d["sources"])
    if cmd == "/status":
        c = store.conn()
        rows = c.execute("SELECT source, ok_t, err FROM health").fetchall()
        bad = [f"{r[0]}: {r[2]}" for r in rows if r[2]]
        return f"{len(rows)} sources checked. " + ("Problems:\n" + "\n".join(bad) if bad else "All fine.")
    return ("Commands:\n/add <url> [keyword ...]  watch a site (use_underscores for multi-word keywords)\n"
            "/remove <id>\n/list\n/status\n/remind <time> <what>   e.g. /remind 9:30 Topps timer (Pacific)\n/reminders\n"
            "Anything else you type or dictate is saved as a note: a site to add, a problem, an idea.")


def telegram_poll(c):
    tok = notify.os.environ.get("TELEGRAM_BOT_TOKEN")
    allowed = {x.strip() for x in notify.os.environ.get("TELEGRAM_ALLOWED_CHATS", notify.os.environ.get("TELEGRAM_CHAT_ID", "")).split(",") if x.strip()}
    if not tok:
        return
    off = store.kv_get(c, "tg_offset", 0)
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/getUpdates?timeout=0&offset={off}", timeout=15) as r:
            ups = json.loads(r.read()).get("result", [])
    except Exception as e:
        print("telegram poll failed", e, flush=True)
        return
    for u in ups:
        store.kv_set(c, "tg_offset", u["update_id"] + 1)
        m = u.get("message") or {}
        chat, text = str(m.get("chat", {}).get("id", "")), (m.get("text") or "").strip()
        if not text:
            continue
        if chat not in allowed:
            print("ignored message from chat", chat, flush=True)   # first-time setup: put this id in TELEGRAM_CHAT_ID
            continue
        parts = text.split()
        if not parts[0].startswith("/"):
            # Anything that isn't a command is feedback: a site to add, a problem with an alert or the website, an idea.
            # It goes to feedback/inbox.jsonl (committed with the dashboard), which the weekly review job reads and acts on.
            fb = ROOT / "feedback" / "inbox.jsonl"
            fb.parent.mkdir(exist_ok=True)
            with fb.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M"), "from": chat, "text": text}, ensure_ascii=False) + "\n")
            n = sum(1 for _ in fb.open(encoding="utf-8"))
            notify.telegram(f"Got it, saved as note #{n}. It gets worked on in the weekly update. (To add a site right away: /add <url>)", chat_id=chat)
            continue
        try:
            reply = handle(parts[0].split("@")[0].lower(), parts[1:])
        except Exception as e:
            reply = f"Sorry, that failed: {e}"
        notify.telegram(reply, chat_id=chat)


def run_reminders(c, fixed):
    now = schedule.pt_now()
    sent = set(store.kv_get(c, "fixed_sent", []))
    for key, text in schedule.due_reminders(fixed, sent, now):
        notify.send("SOON", "Reminder", text, "", "")
        sent.add(key)
    store.kv_set(c, "fixed_sent", sorted(sent)[-200:])
    rem, keep = store.kv_get(c, "reminders", []), []
    import datetime as dt
    for r in rem:
        at = dt.datetime.fromisoformat(r["at"])
        if not r["warned"] and now >= at - dt.timedelta(minutes=10):
            notify.send("SOON", "Reminder", f"In 10 min: {r['text']}", "", f"{at:%I:%M %p} PT")
            r["warned"] = True
        if now >= at:
            notify.send("LIVE", "Reminder", f"NOW: {r['text']}", "", "")
            continue
        keep.append(r)
    if keep != rem:
        store.kv_set(c, "reminders", keep)


# ------------------------------------------------------------------ dashboard (GitHub Pages reads docs/data.json)
def export_dashboard(c, push=True):
    srcs = load_sources()["sources"]
    health = {r[0]: {"ok": r[1], "err_t": r[2], "err": r[3], "checks": r[4]} for r in c.execute("SELECT * FROM health")}
    ev = [dict(zip(("t", "source", "level", "title", "url", "detail"), r)) for r in
          c.execute("SELECT t, source, level, title, url, detail FROM events ORDER BY t DESC LIMIT 300")]
    names = {s["id"]: s["name"] for s in srcs}
    for e in ev:
        e["source_name"] = names.get(e["source"], e["source"])
    data = {"updated": time.time(), "events": ev,
            "sources": [{"id": s["id"], "name": s["name"], "kind": s["kind"], "url": s["url"], "group": s.get("group", ""),
                         "interval_s": s["interval_s"], **health.get(s["id"], {})} for s in srcs]}
    DASH.write_text(json.dumps(data, indent=1), encoding="utf-8")
    if push:
        g = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
        g("add", "docs/data.json", "sources.json", "feedback")
        if g("diff", "--cached", "--quiet").returncode:
            g("commit", "-m", "dashboard data update")
            r = g("push", "-q")
            if r.returncode:
                print("dashboard push failed:", r.stderr[:300], flush=True)


def main():
    notify.load_env()
    c = store.conn()
    once = "--once" in sys.argv
    due = {}
    last_dash = 0
    while True:
        cfg = load_sources()
        srcs = cfg["sources"]
        now = time.time()
        for s in srcs:
            if once or now >= due.get(s["id"], 0):
                check(c, s)
                iv = schedule.window_interval(s) or s["interval_s"]
                due[s["id"]] = time.time() + iv * random.uniform(0.9, 1.1)
            elif schedule.window_interval(s) and due[s["id"]] - now > schedule.window_interval(s) * 1.1:
                due[s["id"]] = now   # a drop window just opened: check now instead of waiting out the slow interval
        if once:
            export_dashboard(c, push="--push" in sys.argv)
            return
        telegram_poll(c)
        try:
            run_reminders(c, cfg.get("reminders", []))
        except Exception:
            traceback.print_exc()
        if time.time() - last_dash > DASH_EVERY_S:
            try:
                export_dashboard(c)
            except Exception:
                traceback.print_exc()
            last_dash = time.time()
        time.sleep(3)


if __name__ == "__main__":
    main()
