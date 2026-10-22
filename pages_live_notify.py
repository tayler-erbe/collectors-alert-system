"""One-shot (job queue, tick-style): when the GitHub Pages dashboard answers 200, tell Charles on Telegram once, then exit 0.
Exit 75 = not live yet, check again next tick."""
import sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from alert import notify
URL = "https://tayler-erbe.github.io/collectors-alert-system/"
try:
    with urllib.request.urlopen(URL, timeout=20) as r:
        live = r.status == 200 and b"Drop Radar" in r.read()
except Exception:
    live = False
if not live:
    print("not live yet"); sys.exit(75)
notify.load_env()
ok = notify.telegram("🌐 The Drop Radar website is live: " + URL + "\n\nIt shows every alert in one list (filter by Live now / Coming / Changes) "
                     "and every site I'm watching with how often it's checked and whether it's working. It refreshes every few minutes. "
                     "Alerts still come here instantly; the site is for looking back and seeing what's on the radar.")
print("sent", ok); sys.exit(0 if ok else 1)
