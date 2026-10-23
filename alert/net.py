"""Polite HTTP: one request at a time per host, conditional GET (ETag / Last-Modified), backoff on 429/403/5xx.
We never try to get around a block: a site that pushes back is simply checked less often."""
import gzip
import random
import time
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar

UA = "Mozilla/5.0 (compatible; collectors-alert-system/1.0; personal drop alerts; +https://github.com/tayler-erbe/collectors-alert-system)"
_validators = {}      # url -> (etag, last_modified)
_last_body = {}       # url -> body from the last 200, returned again on 304
_host_next = {}       # host -> earliest time we may hit it again
_host_penalty = {}    # host -> current backoff seconds
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))   # accept cookies like a browser
MIN_GAP_S = 5         # never two requests to the same host closer than this


class Blocked(Exception):
    pass


def host(url):
    return urllib.parse.urlsplit(url).netloc.lower()


def penalty(url):
    return _host_penalty.get(host(url), 0)


def get(url, timeout=20, accept="*/*"):
    """Returns (status, text). Raises Blocked when the site says slow down; the caller reschedules."""
    h = host(url)
    wait = _host_next.get(h, 0) - time.time()
    if wait > 0:
        time.sleep(wait)
    hdr = {"User-Agent": UA, "Accept": accept, "Accept-Encoding": "gzip"}
    et, lm = _validators.get(url, (None, None))
    if et:
        hdr["If-None-Match"] = et
    if lm:
        hdr["If-Modified-Since"] = lm
    req = urllib.request.Request(url, headers=hdr)
    try:
        with _opener.open(req, timeout=timeout) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            text = raw.decode(r.headers.get_content_charset() or "utf-8", errors="replace")
            _validators[url] = (r.headers.get("ETag"), r.headers.get("Last-Modified"))
            _last_body[url] = text
            _host_penalty[h] = max(0, _host_penalty.get(h, 0) // 2)
            _host_next[h] = time.time() + MIN_GAP_S
            return r.status, text
    except urllib.error.HTTPError as e:
        if e.code == 304:
            _host_next[h] = time.time() + MIN_GAP_S
            return 304, _last_body.get(url, "")
        if e.code in (429, 403, 503):
            retry = e.headers.get("Retry-After")
            base = max(int(retry), 60) if retry and retry.isdigit() else 60   # some sites send Retry-After: 0
            pen = min(max(base, _host_penalty.get(h, 0) * 2 or base), 3600)
            _host_penalty[h] = pen
            _host_next[h] = time.time() + pen + random.uniform(0, 10)
            raise Blocked(f"{h} answered {e.code}; backing off {pen}s")
        raise
