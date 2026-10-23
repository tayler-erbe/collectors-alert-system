"""One checker per source kind. Each returns a list of (level, title, url, detail) and updates the store.
The first check of a new source only records what is there (a baseline) and sends nothing."""
import hashlib
import html
import json
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET

from . import net


def _match(text, kws, also=None):
    t = " " + text.lower() + " "
    ok = not kws or any(k.lower() in t for k in kws)
    return ok and (not also or any(a.lower() in t for a in also))


LIVE_WORDS = ["restock", "in stock", "back in stock", "live now", "is live", "queue is open", "queue open", "available now",
              "drops today", "dropping today", "on sale now", "pre-order now", "preorders open", "pre-orders open"]


def gate(src, found):
    """Sources marked phone:false (news sites, trackers) send to the dashboard only, unless the text says it is live/restocking.
    Charles, 22 Oct 2026: alerts must be things he can act on, linking to a store or waiting room."""
    if src.get("phone", True):
        return found
    out = []
    for level, title, url, detail in found:
        txt = (title + " " + detail).lower()
        out.append((level if any(w in txt for w in LIVE_WORDS) else "INFO", title, url, detail))
    return out


def shopify(c, src):
    base = src["url"].rstrip("/")
    status, text = net.get(f"{base}/products.json?limit=250", accept="application/json")
    products = json.loads(text).get("products", []) if text else []
    first = c.execute("SELECT COUNT(*) FROM items WHERE source=?", (src["id"],)).fetchone()[0] == 0
    out, now = [], time.time()
    for p in products:
        avail = any(v.get("available") for v in p.get("variants", []))
        price = min((v.get("price") for v in p.get("variants", []) if v.get("price")), default="")
        url = f"{base}/products/{p['handle']}"
        title = p.get("title", "")
        hay = " ".join([title, p.get("vendor", ""), p.get("product_type", ""), " ".join(p.get("tags", []) if isinstance(p.get("tags"), list) else [str(p.get("tags", ""))])])
        row = c.execute("SELECT available FROM items WHERE source=? AND item=?", (src["id"], str(p["id"]))).fetchone()
        if row is None:
            c.execute("INSERT INTO items VALUES (?,?,?,?,?,?,?,?)", (src["id"], str(p["id"]), title, url, price, int(avail), now, now))
            if not first:
                lvl = ("LIVE" if avail else "SOON") if _match(hay, src.get("keywords")) else "INFO"
                out.append((lvl, title, url, f"New product, ${price}, {'IN STOCK' if avail else 'not buyable yet'}"))
        else:
            c.execute("UPDATE items SET last_seen=?, available=?, price=? WHERE source=? AND item=?", (now, int(avail), price, src["id"], str(p["id"])))
            if avail and not row[0]:
                lvl = "LIVE" if _match(hay, src.get("keywords")) else "INFO"
                out.append((lvl, title, url, f"Back in stock / now buyable, ${price}"))
    c.commit()
    return out


_TAG = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.S | re.I)
_A = re.compile(r"<a\b[^>]*href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", re.S | re.I)


def _visible(htm):
    t = _TAG.sub(" ", htm)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def page(c, src):
    """Alerts on NEW links whose text or address contains a keyword (a new product or news item appearing), and on a
    keyword appearing in the page text that was not there before. Plain layout changes go to the dashboard only."""
    status, htm = net.get(src["url"], accept="text/html")
    kws = [k.lower() for k in src.get("keywords", [])]
    links = {}
    for href, label in _A.findall(htm):
        lab = _visible(label)[:120]
        full = urllib.parse.urljoin(src["url"], href)
        if lab and (not kws or any(k in (lab + " " + full).lower() for k in kws)):
            links[full] = lab
    text = _visible(htm).lower()
    present = sorted(k for k in kws if k in text)
    digest = hashlib.sha1(text.encode()).hexdigest()
    prev = c.execute("SELECT digest, keywords FROM pages WHERE source=?", (src["id"],)).fetchone()
    seen = {r[0] for r in c.execute("SELECT item FROM items WHERE source=?", (src["id"],))}
    now, out = time.time(), []
    for full, lab in links.items():
        if full not in seen:
            c.execute("INSERT OR IGNORE INTO items VALUES (?,?,?,?,?,?,?,?)", (src["id"], full, lab, full, "", 0, now, now))
            if prev is not None:
                out.append(("SOON", lab, full, "New link on the page"))
    if prev is not None:
        pv = json.loads(prev[1] or "[]")
        prev_present, prev_cfg = (pv.get("present", []), pv.get("cfg", kws)) if isinstance(pv, dict) else (pv, kws)
        # a keyword added to the config since the last check is NOT news (22 Oct bug: adding '30th celebration' fired 6 alerts)
        newk = sorted((set(present) - set(prev_present)) & set(prev_cfg))
        if newk:
            i = text.find(newk[0])
            out.append(("SOON", f"'{newk[0]}' just appeared", src["url"], "..." + text[max(0, i - 80): i + 120] + "..."))
        elif prev[0] != digest and not out:
            out.append(("INFO", "Page changed", src["url"], ""))
    stv = json.dumps({"present": present, "cfg": kws})
    c.execute("INSERT INTO pages(source, digest, keywords, t) VALUES (?,?,?,?) ON CONFLICT(source) DO UPDATE SET digest=?, keywords=?, t=?",
              (src["id"], digest, stv, now, digest, stv, now))
    c.commit()
    return out


def rss(c, src):
    status, text = net.get(src["url"], accept="application/rss+xml, application/atom+xml, text/xml")
    root = ET.fromstring(text.encode()) if text else None
    if root is None:
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = [(i.findtext("link") or "", i.findtext("title") or "") for i in root.iter("item")]
    entries += [((e.find("a:link", ns).get("href") if e.find("a:link", ns) is not None else ""), e.findtext("a:title", "", ns))
                for e in root.iter("{http://www.w3.org/2005/Atom}entry")]
    first = c.execute("SELECT COUNT(*) FROM items WHERE source=?", (src["id"],)).fetchone()[0] == 0
    now, out = time.time(), []
    for link, title in entries:
        if not link:
            continue
        if c.execute("SELECT 1 FROM items WHERE source=? AND item=?", (src["id"], link)).fetchone():
            continue
        c.execute("INSERT INTO items VALUES (?,?,?,?,?,?,?,?)", (src["id"], link, title, link, "", 0, now, now))
        if not first:
            out.append(("SOON" if src.get("keywords") and _match(title, src.get("keywords"), src.get("also")) else "INFO", title, link, "New post"))
    c.commit()
    return out


QUEUE_MARKS = ("queue-it", "queueit", "virtual waiting room", "you are now in line", "waitingroom.")   # specific markers only ("queue." matched ordinary page scripts)


def _pt(iso):
    import datetime as dt
    from . import schedule
    u = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return schedule.pt_now(u)


def queue(c, src):
    """Waiting-room watch (Queue-it). Many stores keep an always-on 'safety net' queue that real visitors pass straight
    through, while a script is always shown the queue page, so "queue page seen" is NOT a drop signal (22 Oct bug: Bear
    Walker alerts flapped 9 times in 30 min). Instead we read the queue page itself:
      - a NEW event id (e.g. 'kaido1023') -> one COMING alert with the event name and its start time in Pacific;
      - its start time arriving -> one LIVE alert;
      - no alerts for a queue 'closing', and never more than one alert per event per kind.
    Sites without Queue-it details: alert only after 3 checks in a row see a queue, at most once per 12 h.
    We only LOOK; we never join, skip or work around the queue."""
    import datetime as dt
    from . import schedule
    status, htm = net.get(src["url"], accept="text/html")
    body = htm or ""
    low = body.lower()
    up = any(m in low for m in QUEUE_MARKS)
    st_row = c.execute("SELECT keywords FROM pages WHERE source=?", (src["id"],)).fetchone()
    st = json.loads(st_row[0]) if st_row and st_row[0] and st_row[0].startswith("{") else {}
    st.setdefault("events", {})
    out, now_pt = [], schedule.pt_now()
    ev = re.search(r"eventId:\s*'([^']+)'", body)
    if up and ev:
        eid = ev.group(1)
        vis = _visible(body)
        title = re.search(r"You are in line for (.{3,120}?)\s+(?:You are in line|When it is your turn)", vis)
        title = title.group(1).strip() if title else eid
        starts = [x for x in re.findall(r"20\d\d-\d\d-\d\dT\d\d:\d\d:00Z", body)]
        start_pt = _pt(starts[0]) if starts else None
        e = st["events"].setdefault(eid, {"title": title, "start": start_pt.isoformat() if start_pt else None})
        when = f"{start_pt:%a %b %d, %I:%M %p} PT" if start_pt else "start time not shown"
        if not e.get("announced"):
            state = "opened" if start_pt and start_pt <= now_pt else "opens"
            out.append(("SOON", f"Waiting room set up: {title}", src["url"], f"The queue {state} {when}."))
            e["announced"] = True
            if start_pt and start_pt <= now_pt:
                e["live_sent"] = True   # it already started before we saw it: no LIVE alert for a start in the past
        elif start_pt and not e.get("live_sent") and now_pt >= start_pt:
            out.append(("LIVE", f"Waiting room OPEN NOW: {title}", src["url"], f"Started {when}."))
            e["live_sent"] = True
    elif up:
        st["streak"] = st.get("streak", 0) + 1
        if st["streak"] >= 3 and time.time() - st.get("last_alert", 0) > 12 * 3600:
            out.append(("LIVE", "Waiting room is UP", src["url"], "A queue has been showing for 3 checks in a row: a drop may be starting."))
            st["last_alert"] = time.time()
    if not up:
        st["streak"] = 0
    now = time.time()
    c.execute("INSERT INTO pages(source, digest, keywords, t) VALUES (?,?,?,?) ON CONFLICT(source) DO UPDATE SET keywords=?, t=?",
              (src["id"], "", json.dumps(st), now, json.dumps(st), now))
    c.commit()
    return out


KINDS = {"shopify": shopify, "page": page, "rss": rss, "queue": queue}
