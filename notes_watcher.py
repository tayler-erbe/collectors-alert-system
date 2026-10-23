"""Hourly watcher (job queue, cpu lane, tick-style): when Charles has open notes, or a source has failed for 24 h,
queue ONE drop-radar Claude review job, at most twice a day. Free when there is nothing to do.
Exit 75 = run me again next tick (the queue's tick-style contract)."""
import datetime as dt
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OPS = Path("C:/dev/skyrule-fresh/.opencode/ops")
STATE = ROOT / "data" / "watcher_state.json"
MAX_PER_DAY = 8   # Tayler 22 Oct 2026: Claude should read and answer Telegram more often
AGAIN = 75

PROMPT = ("You are the drop-radar agent, working unattended. First read C:/Users/tayle/.claude/agents/drop-radar.md (your role and "
          "hard rules) and C:/dev/collectors-alert-system/KNOWLEDGE.md, and follow them exactly. Task: the DAILY REVIEW. In "
          "C:/dev/collectors-alert-system: process every open note in feedback/inbox.jsonl that is not yet in feedback/done.jsonl "
          "(add sites, fix reported problems with alerts or the dashboard, tune keywords/windows; ignore greetings like 'hi' but "
          "still mark them done), check data/state.db health for sources failing more than 24 h and fix or retire them, test with "
          "`python -X utf8 -m alert.main --once`, commit and push, update KNOWLEDGE.md, and send Charles a plain Telegram "
          "confirmation (alert.notify.load_env() then alert.notify.telegram(text)) that names EACH of his notes by number and a few of "
          "his words and says what you did ('Note #3 (add Zoomies): done, watching zoomies.com every 15 min') or why not; he must always "
          "get a 'processed' confirmation for every note, even greetings ('Note #1 (Hi): nothing to do'). "
          "sources.json changes are picked up live; if you changed code, restart with `schtasks /End /TN CollectorsAlert` then "
          "`schtasks /Run /TN CollectorsAlert`. Report what you changed.")


def open_notes():
    inbox, done = ROOT / "feedback" / "inbox.jsonl", ROOT / "feedback" / "done.jsonl"
    rows = [json.loads(l) for l in inbox.read_text(encoding="utf-8").splitlines() if l.strip()] if inbox.exists() else []
    seen = set()
    if done.exists():
        for l in done.read_text(encoding="utf-8").splitlines():
            if l.strip():
                d = json.loads(l)
                seen.add((d.get("t"), d.get("text")))
    return [r for r in rows if (r.get("t"), r.get("text")) not in seen]


def failing_sources():
    db = ROOT / "data" / "state.db"
    if not db.exists():
        return []
    c = sqlite3.connect(db)
    day = time.time() - 86400
    return [r[0] for r in c.execute("SELECT source FROM health WHERE err IS NOT NULL AND (ok_t IS NULL OR ok_t < ?) AND err_t > ?",
                                    (day, day))]


def main():
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    today = dt.date.today().isoformat()
    launched = [x for x in st.get("launched", []) if x.startswith(today)]
    notes, bad = open_notes(), failing_sources()
    reason = []
    if notes and len(notes) != st.get("notes_at_last_launch"):
        reason.append(f"{len(notes)} open note(s)")
    if bad and today not in st.get("health_days", []):
        reason.append(f"failing >24h: {', '.join(bad)}")
    if not reason or len(launched) >= MAX_PER_DAY:
        print("nothing to do" if not reason else f"daily cap reached ({MAX_PER_DAY})", reason)
        return AGAIN
    jid = f"radar-daily-{dt.datetime.now():%Y%m%dT%H%M}"
    job = [{"id": jid, "title": f"drop-radar: daily review ({'; '.join(reason)})", "lane": "claude", "model": "sonnet",
            "cwd": str(ROOT).replace("\\", "/"), "priority": 9, "max_attempts": 1, "prompt": PROMPT,
            "approved_by": "Founder 22 Oct 2026: notes 'need to be read probably daily ... those issues need to be addressed daily'"}]
    f = ROOT / "data" / f"{jid}.json"
    f.write_text(json.dumps(job), encoding="utf-8")
    r = subprocess.run([sys.executable, "-X", "utf8", str(OPS / "jobqueue.py"), "add", str(f)], capture_output=True, text=True)
    print(r.stdout.strip(), r.stderr.strip()[:300])
    if r.returncode == 0:
        st.setdefault("launched", []).append(dt.datetime.now().isoformat())
        st["notes_at_last_launch"] = len(notes)
        if bad:
            st.setdefault("health_days", []).append(today)
        STATE.write_text(json.dumps(st), encoding="utf-8")
    return AGAIN


if __name__ == "__main__":
    sys.exit(main())
