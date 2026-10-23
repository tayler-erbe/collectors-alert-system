"""Pacific time, drop windows and reminders (no tzdata needed: US DST rule computed here).
A window makes a source check faster during the hours a store usually drops, e.g.
  "windows": [{"days": "Mon-Thu", "start": "08:00", "end": "11:00", "interval_s": 60}]
Fixed reminders live in sources.json "reminders"; one-off reminders come from the bot's /remind command."""
import datetime as dt
import re

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _nth_sunday(year, month, n):
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(6 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def pt_now(utc=None):
    utc = utc or dt.datetime.now(dt.timezone.utc)
    y = utc.year
    start = dt.datetime.combine(_nth_sunday(y, 3, 2), dt.time(10), dt.timezone.utc)   # 2am PST = 10:00 UTC
    end = dt.datetime.combine(_nth_sunday(y, 11, 1), dt.time(9), dt.timezone.utc)     # 2am PDT = 09:00 UTC
    off = -7 if start <= utc < end else -8
    return (utc + dt.timedelta(hours=off)).replace(tzinfo=None)


def day_set(spec):
    out = set()
    for part in str(spec).lower().replace(" ", "").split(","):
        if part in ("daily", "every", "all", ""):
            return set(range(7))
        if "-" in part:
            a, b = (DAYS.index(x[:3]) for x in part.split("-"))
            out |= set(range(a, b + 1)) if a <= b else set(range(a, 7)) | set(range(0, b + 1))
        else:
            out.add(DAYS.index(part[:3]))
    return out


def _hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def window_interval(src, now=None):
    now = now or pt_now()
    mins = now.hour * 60 + now.minute
    for w in src.get("windows", []):
        if now.weekday() in day_set(w.get("days", "daily")) and _hm(w["start"]) <= mins < _hm(w["end"]):
            return w["interval_s"]
    return None


def due_reminders(reminders, sent, now=None):
    """Fixed weekly reminders: each fires once per day at its time (PT). sent = set of 'id|date' already sent."""
    now = now or pt_now()
    out = []
    for r in reminders:
        key = f"{r['id']}|{now.date()}"
        if r.get("enabled") is False or key in sent or now.weekday() not in day_set(r.get("days", "daily")) or (r.get("once_on") and r["once_on"] != str(now.date())):
            continue
        if 0 <= (now.hour * 60 + now.minute) - _hm(r["time"]) < 5:
            out.append((key, r["text"]))
    return out


def parse_remind(args, now=None):
    """'/remind 9:30 Topps Chrome' (today, or tomorrow if past) or '/remind 10/24 9:30pm Lorcana preorder'. PT times."""
    now = now or pt_now()
    s = " ".join(args)
    m = re.match(r"^(?:(\d{1,2})/(\d{1,2})\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+(.+)$", s, re.I)
    if not m:
        return None
    mo, dy, h, mi, ap, text = m.groups()
    h, mi = int(h), int(mi or 0)
    if ap:
        h = h % 12 + (12 if ap.lower() == "pm" else 0)
    d = dt.date(now.year, int(mo), int(dy)) if mo else now.date()
    when = dt.datetime.combine(d, dt.time(h, mi))
    if not mo and when <= now:
        when += dt.timedelta(days=1)
    return when, text
