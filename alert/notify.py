"""Phone alerts. Secrets live in .env (never committed):
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID       alerts + the /add /list /remove commands (primary)
  PUSHOVER_TOKEN, PUSHOVER_USER               optional: loud LIVE alerts on iPhone (can break through silent mode)
  NTFY_TOPIC                                  optional: free push on Android
Levels: INFO (dashboard only), SOON (normal push), LIVE (loud push)."""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _post(url, data, as_json=False):
    body = json.dumps(data).encode() if as_json else urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json" if as_json else
                                                          "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read() or b"{}")


def telegram(text, chat_id=None, silent=False):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        return False
    _post(f"https://api.telegram.org/bot{tok}/sendMessage",
          {"chat_id": chat, "text": text, "disable_web_page_preview": False, "disable_notification": silent}, as_json=True)
    return True


def pushover(title, msg, url, live):
    tok, user = os.environ.get("PUSHOVER_TOKEN"), os.environ.get("PUSHOVER_USER")
    if not (tok and user):
        return False
    d = {"token": tok, "user": user, "title": title[:250], "message": msg[:1000], "url": url, "url_title": "Open"}
    if live:
        d.update(priority=2, retry=60, expire=900, sound="siren")   # repeats until he taps it, for 15 min
    _post("https://api.pushover.net/1/messages.json", d)
    return True


def ntfy(title, msg, url, live):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return False
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=msg.encode(),
                                 headers={"Title": title.encode("ascii", "replace").decode(), "Click": url,
                                          "Priority": "urgent" if live else "default", "Tags": "rotating_light" if live else "bell"})
    urllib.request.urlopen(req, timeout=15).read()
    return True


def send(level, source_name, title, url, detail=""):
    if level == "INFO":
        return
    live = level == "LIVE"
    head = ("LIVE NOW: " if live else "Coming: ") + title
    msg = f"{source_name}\n{detail}".strip()
    sent = []
    for fn, args in ((telegram, (f"{'🚨' if live else '🔔'} {head}\n{msg}\n{url}",)), (pushover, (head, msg, url, live)),
                     (ntfy, (head, msg, url, live))):
        try:
            if fn(*args):
                sent.append(fn.__name__)
        except Exception as e:  # one channel failing must not stop the others
            print("notify failed", fn.__name__, e, flush=True)
    print(f"[{level}] {source_name}: {title} -> {sent or 'no channel configured'}", flush=True)
