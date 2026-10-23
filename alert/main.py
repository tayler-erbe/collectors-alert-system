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

from . import checkers, discord_feed, net, notify, schedule, store

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
        found = checkers.gate(src, fn(c, src))
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
    if cmd == "/mute":
        dur = {"m": 60, "h": 3600, "d": 86400}
        until = None
        if args:
            a = args[0].lower()
            if a[:-1].isdigit() and a[-1] in dur:
                until = time.time() + int(a[:-1]) * dur[a[-1]]
            elif a.isdigit():
                until = time.time() + int(a) * 3600
            else:
                return "Use /mute (until /unmute), or /mute 30m, /mute 2h, /mute 1d"
        notify.set_mute_state(muted=True, until=until)
        when = schedule.pt_now(__import__("datetime").datetime.fromtimestamp(until, __import__("datetime").timezone.utc)).strftime("%a %I:%M %p PT") if until else "you send /unmute"
        return f"🔕 Muted until {when}. Alerts still arrive here, just without sound."
    if cmd == "/unmute":
        notify.set_mute_state(muted=False, until=None)
        q = notify.mute_state().get("quiet", notify.QUIET)
        return "🔔 Unmuted: alerts will buzz again." + (f" (Nightly quiet hours {q} PT still apply; /quiet off removes them.)" if q else "")
    if cmd == "/quiet":
        if not args:
            q = notify.mute_state().get("quiet", notify.QUIET)
            return f"Quiet hours: {q or 'off'} (Pacific). Change with /quiet 21-3 or /quiet off."
        a = args[0].lower()
        if a == "off":
            notify.set_mute_state(quiet="")
            return "Nightly quiet hours are OFF: alerts buzz at any hour (unless you /mute)."
        import re as _re
        m = _re.match(r"^(\d{1,2})(?::(\d\d))?-(\d{1,2})(?::(\d\d))?$", a)
        if not m:
            return "Use /quiet 21-3 (9 pm to 3 am), /quiet 22:30-6, or /quiet off"
        q = f"{int(m.group(1)):02d}:{m.group(2) or '00'}-{int(m.group(3)):02d}:{m.group(4) or '00'}"
        notify.set_mute_state(quiet=q)
        return f"🌙 Quiet hours set to {q} Pacific: alerts in that window arrive silently."
    if cmd == "/picks":
        send_picks(notify.os.environ.get("TELEGRAM_CHAT_ID"))
        return "Tap to choose, then Save."
    if cmd == "/list":
        return "\n".join(f"{s['id']}: {s['name']} " + ("(paused)" if s.get("enabled") is False else f"({s['interval_s'] // 60 or 1} min)") for s in d["sources"])
    if cmd == "/status":
        c = store.conn()
        rows = c.execute("SELECT source, ok_t, err FROM health").fetchall()
        bad = [f"{r[0]}: {r[2]}" for r in rows if r[2]]
        return f"{len(rows)} sources checked. " + ("Problems:\n" + "\n".join(bad) if bad else "All fine.")
    return ("Commands:\n/add <url> [keyword ...]  watch a site (use_underscores for multi-word keywords)\n"
            "/remove <id>\n/list\n/status\n/remind <time> <what>   e.g. /remind 9:30 Topps timer (Pacific)\n/reminders\n"
            "/picks   choose which suggested items to follow\n"
            "/mute  /mute 2h  /unmute   silence alerts (they still arrive, no sound)\n/quiet 21-3  /quiet off   nightly quiet hours (Pacific)\n"
            "Anything else you type or dictate is saved as a note: a site to add, a problem, an idea.")


def save_attachments(tok, m):
    """Download any photo / screenshot / file / voice note / video in a message to feedback/attachments/. Returns paths."""
    want = []
    if m.get("photo"):
        want.append((m["photo"][-1]["file_id"], ".jpg"))          # last = largest size
    for k, ext in (("document", ""), ("voice", ".ogg"), ("audio", ""), ("video", ".mp4"), ("video_note", ".mp4")):
        if m.get(k):
            name = m[k].get("file_name", "")
            want.append((m[k]["file_id"], Path(name).suffix if name else ext))
    out = []
    d = ROOT / "feedback" / "attachments"
    for fid, ext in want:
        try:
            with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/getFile?file_id={fid}", timeout=20) as r:
                fp = json.loads(r.read())["result"]["file_path"]
            ext = ext or Path(fp).suffix
            d.mkdir(parents=True, exist_ok=True)
            dest = d / f"{time.strftime('%Y%m%d_%H%M%S')}_{len(out) + 1}{ext}"
            with urllib.request.urlopen(f"https://api.telegram.org/file/bot{tok}/{fp}", timeout=60) as r:
                dest.write_bytes(r.read())
            out.append(str(dest.relative_to(ROOT)).replace("\\", "/"))
        except Exception as e:   # bot API max download is 20 MB
            print("attachment download failed", e, flush=True)
            out.append(f"(could not download: {e})")
    return out


PICKS = ROOT / "data" / "picks.json"


def _picks():
    return json.loads(PICKS.read_text(encoding="utf-8")) if PICKS.exists() else {"picks": []}


def picks_keyboard(sel):
    rows = [[{"text": ("✅ " if p["id"] in sel else "⬜ ") + p["label"], "callback_data": "pk:" + p["id"]}] for p in _picks()["picks"]]
    rows.append([{"text": "All", "callback_data": "pk:*all"}, {"text": "None", "callback_data": "pk:*none"}, {"text": "💾 Save", "callback_data": "pk:*save"}])
    return {"inline_keyboard": rows}


def send_picks(chat):
    sel = [p["id"] for p in _picks()["picks"]]          # everything starts ticked (already on the radar); untick what he doesn't want
    notify.set_mute_state(picks_sel=sel)
    tok = notify.os.environ["TELEGRAM_BOT_TOKEN"]
    notify._post(f"https://api.telegram.org/bot{tok}/sendMessage", {"chat_id": chat, "reply_markup": picks_keyboard(sel),
                 "text": "🎯 Pick what to follow. Tap to switch on/off, then Save. ✅ = on your radar."}, as_json=True)


def apply_picks(sel):
    """Unticked picks: their keywords and reminders come off the radar. Ticked: put back on if they were removed."""
    d, pk = load_sources(), _picks()
    for p in pk["picks"]:
        on = p["id"] in sel
        for s in d["sources"]:
            key = "_pk_" + p["id"]          # keywords this pick removed from this source, so Save can put exactly those back
            kws = set(s.get("keywords", []))
            if on and key in s:
                kws |= set(s.pop(key))
            elif not on and key not in s:
                gone = sorted(kws & set(p.get("keywords", [])))
                if gone:
                    s[key] = gone
                    kws -= set(gone)
            s["keywords"] = sorted(kws)
        for r in d.get("reminders", []):
            if r["id"] in p.get("reminders", []):
                r["enabled"] = on
    save_sources(d)
    with (ROOT / "feedback" / "done.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "text": "picks selection", "done": "following: " + ", ".join(sel), "at": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False) + "\n")
    chosen = [p["label"] for p in pk["picks"] if p["id"] in sel]
    return chosen


def handle_callback(tok, cq):
    data, chat = cq.get("data", ""), str(cq["message"]["chat"]["id"])
    mid = cq["message"]["message_id"]
    sel = list(notify.mute_state().get("picks_sel", []))
    ids = [p["id"] for p in _picks()["picks"]]
    k = data[3:]
    if k == "*all":
        sel = ids
    elif k == "*none":
        sel = []
    elif k == "*save":
        chosen = apply_picks(sel)
        notify._post(f"https://api.telegram.org/bot{tok}/editMessageText", {"chat_id": chat, "message_id": mid,
                     "text": "✅ Saved. Following: " + ("; ".join(chosen) or "none of these") + "\nSend /picks to change it any time."}, as_json=True)
        notify._post(f"https://api.telegram.org/bot{tok}/answerCallbackQuery", {"callback_query_id": cq["id"], "text": "Saved"}, as_json=True)
        return
    elif k in ids:
        sel = [x for x in sel if x != k] if k in sel else sel + [k]
    notify.set_mute_state(picks_sel=sel)
    notify._post(f"https://api.telegram.org/bot{tok}/editMessageReplyMarkup", {"chat_id": chat, "message_id": mid, "reply_markup": picks_keyboard(sel)}, as_json=True)
    notify._post(f"https://api.telegram.org/bot{tok}/answerCallbackQuery", {"callback_query_id": cq["id"]}, as_json=True)


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
        if u.get("callback_query"):
            cq = u["callback_query"]
            if str(cq.get("message", {}).get("chat", {}).get("id", "")) in allowed and cq.get("data", "").startswith("pk:"):
                try:
                    handle_callback(tok, cq)
                except Exception as e:
                    print("picks callback failed", e, flush=True)
            continue
        m = u.get("message") or {}
        chat = str(m.get("chat", {}).get("id", ""))
        text = (m.get("text") or m.get("caption") or "").strip()
        files = save_attachments(tok, m) if chat in allowed else []
        if not text and not files:
            continue
        if chat not in allowed:
            print("ignored message from chat", chat, flush=True)   # first-time setup: put this id in TELEGRAM_CHAT_ID
            continue
        parts = text.split() or [""]
        if files or not parts[0].startswith("/"):
            # Anything that isn't a command is feedback: a site to add, a problem with an alert or the website, an idea,
            # with any screenshot/photo/file/voice note saved next to it. Kept LOCAL only (feedback/ is git-ignored: the
            # repo is public). notes_watcher.py queues the same-day Claude review that reads and acts on it.
            fb = ROOT / "feedback" / "inbox.jsonl"
            fb.parent.mkdir(exist_ok=True)
            with fb.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "from": chat, "text": text, "files": files},
                                   ensure_ascii=False) + "\n")
            n = sum(1 for _ in fb.open(encoding="utf-8"))
            got = f" with {len(files)} attachment{'s' if len(files) > 1 else ''}" if files else ""
            notify.telegram(f"Got it, saved as note #{n}{got}. Claude replies within about 15-30 minutes. "
                            "(To add a site right away: /add <url>)", chat_id=chat)
            continue
        try:
            reply = handle(parts[0].split("@")[0].lower(), parts[1:])
        except Exception as e:
            reply = f"Sorry, that failed: {e}"
        notify.telegram(reply, chat_id=chat)


def run_reminders(c, fixed):
    now = schedule.pt_now()
    sent = set(store.kv_get(c, "fixed_sent", []))
    urls = {r["id"]: r.get("url", "") for r in fixed}
    for key, text in schedule.due_reminders(fixed, sent, now):
        notify.send("SOON", "Reminder", text, urls.get(key.split("|")[0], ""), "")
        sent.add(key)
    store.kv_set(c, "fixed_sent", sorted(sent)[-200:])
    rem, keep = store.kv_get(c, "reminders", []), []
    import datetime as dt
    for r in rem:
        at = dt.datetime.fromisoformat(r["at"])
        if not r["warned"] and now >= at - dt.timedelta(minutes=10):
            notify.send("SOON", "Reminder", f"In 10 min: {r['text']}", r.get("url", ""), f"{at:%I:%M %p} PT", force=True)
            r["warned"] = True
        if now >= at:
            notify.send("LIVE", "Reminder", f"NOW: {r['text']}", r.get("url", ""), "", force=True)
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
            "sources": [{"id": s["id"], "name": s["name"], "kind": s["kind"], "url": s.get("link") or s["url"],   # a page to open, never a feed file (Charles, note #5)
                         "group": s.get("group", ""), "interval_s": s["interval_s"], "paused": s.get("enabled") is False,
                         "note": s.get("note", "") if s.get("enabled") is False else "", **health.get(s["id"], {})} for s in srcs]}
    DASH.write_text(json.dumps(data, indent=1), encoding="utf-8")
    if push:
        g = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
        g("add", "docs/data.json", "sources.json")
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
    next_discord = 0
    while True:
        cfg = load_sources()
        srcs = cfg["sources"]
        now = time.time()
        for s in srcs:
            if s.get("enabled") is False:
                continue
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
        if discord_feed.configured() and time.time() >= next_discord:
            try:
                for level, sname, title, url, detail in discord_feed.check(c):
                    store.event(c, "discord", level, title, url, f"{sname}: {detail}"[:500])
                    notify.send(level, sname, title, url, detail)
                store.health(c, "discord")
            except Exception as e:
                store.health(c, "discord", f"{type(e).__name__}: {e}")
                print("discord check failed", e, flush=True)
            next_discord = time.time() + 10   # every 10 s (Discord allows far more)
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
