"""SQLite state: what we have already seen, so every alert fires once."""
import json
import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "state.db"


def conn():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS items(source TEXT, item TEXT, title TEXT, url TEXT, price TEXT,
                 available INTEGER, first_seen REAL, last_seen REAL, PRIMARY KEY(source, item))""")
    c.execute("""CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, t REAL, source TEXT, level TEXT,
                 title TEXT, url TEXT, detail TEXT)""")
    c.execute("CREATE TABLE IF NOT EXISTS pages(source TEXT PRIMARY KEY, digest TEXT, keywords TEXT, t REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS health(source TEXT PRIMARY KEY, ok_t REAL, err_t REAL, err TEXT, checks INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT)")
    return c


def event(c, source, level, title, url, detail=""):
    c.execute("INSERT INTO events(t, source, level, title, url, detail) VALUES (?,?,?,?,?,?)",
              (time.time(), source, level, title, url, detail))
    c.commit()


def health(c, source, err=None):
    now = time.time()
    if err:
        c.execute("INSERT INTO health(source, ok_t, err_t, err, checks) VALUES (?,NULL,?,?,1) ON CONFLICT(source) DO UPDATE "
                  "SET err_t=?, err=?, checks=checks+1", (source, now, err[:300], now, err[:300]))
    else:
        c.execute("INSERT INTO health(source, ok_t, err_t, err, checks) VALUES (?,?,NULL,NULL,1) ON CONFLICT(source) DO UPDATE "
                  "SET ok_t=?, err=NULL, checks=checks+1", (source, now, now))
    c.commit()


def kv_get(c, k, default=None):
    r = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return json.loads(r[0]) if r else default


def kv_set(c, k, v):
    c.execute("INSERT INTO kv(k, v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=?", (k, json.dumps(v), json.dumps(v)))
    c.commit()
