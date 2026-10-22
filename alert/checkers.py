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


def _match(text, kws):
    t = text.lower()
    return not kws or any(k.lower() in t for k in kws)


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
        newk = sorted(set(present) - set(json.loads(prev[1] or "[]")))
        if newk:
            i = text.find(newk[0])
            out.append(("SOON", f"'{newk[0]}' just appeared", src["url"], "..." + text[max(0, i - 80): i + 120] + "..."))
        elif prev[0] != digest and not out:
            out.append(("INFO", "Page changed", src["url"], ""))
    c.execute("INSERT INTO pages(source, digest, keywords, t) VALUES (?,?,?,?) ON CONFLICT(source) DO UPDATE SET digest=?, keywords=?, t=?",
              (src["id"], digest, json.dumps(present), now, digest, json.dumps(present), now))
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
            out.append(("SOON" if _match(title, src.get("keywords")) and src.get("keywords") else "INFO", title, link, "New post"))
    c.commit()
    return out


QUEUE_MARKS = ("queue-it", "queueit", "virtual waiting room", "you are now in line", "waitingroom.")   # specific markers only ("queue." matched ordinary page scripts)


def queue(c, src):
    """Drop is minutes away / live when a waiting room (e.g. Queue-it) appears on the homepage. We only LOOK at the
    homepage; we never join, skip or work around the queue."""
    try:
        status, htm = net.get(src["url"], accept="text/html")
        body = (htm or "").lower()
        up = any(m in body for m in QUEUE_MARKS)
    except net.Blocked:
        raise
    prev = c.execute("SELECT keywords FROM pages WHERE source=?", (src["id"],)).fetchone()
    was = prev is not None and prev[0] == "queue"
    now, out = time.time(), []
    if up and not was:
        out.append(("LIVE", "Waiting room is UP", src["url"], "A queue just appeared on the site: a drop is starting."))
    elif was and not up:
        out.append(("INFO", "Waiting room closed", src["url"], ""))
    state = "queue" if up else "open"
    c.execute("INSERT INTO pages(source, digest, keywords, t) VALUES (?,?,?,?) ON CONFLICT(source) DO UPDATE SET keywords=?, t=?",
              (src["id"], "", state, now, state, now))
    c.commit()
    return out


KINDS = {"shopify": shopify, "page": page, "rss": rss, "queue": queue}
