"""Trigger a Render deploy of the current main branch and wait for it to go live.

Render auto-deploy is OFF for this service (repo connected as public URL, not via
GitHub app), so every code push needs a manual deploy. Run after `git push`.

Usage:  .venv/Scripts/python.exe scripts/deploy.py
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
env = {}
for line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k] = v

RK = env["RENDER_API_KEY"]
SID = env.get("RENDER_SERVICE_ID", "srv-dabib3ks728c73a0sq3g")


def api(method, path, body=None):
    req = urllib.request.Request(
        "https://api.render.com/v1" + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
    )
    req.add_header("Authorization", "Bearer " + RK)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode() or "{}")


def run_once():
    dep = api("POST", f"/services/{SID}/deploys", {"clearCache": "do_not_clear"})
    dep_id = dep["id"]
    print(f"triggered {dep_id} commit={dep.get('commit', {}).get('id', '')[:8]}")
    for _ in range(40):
        status = api("GET", f"/services/{SID}/deploys/{dep_id}")["status"]
        print(" ", status)
        if status == "live":
            return "live"
        if any(x in status for x in ("failed", "canceled", "deactivated")):
            return status
        time.sleep(15)
    return "timeout"


# Anonymous git clone on Render fails transiently (GitHub rate-limits it).
# Retry a failed build up to 3 times before giving up.
for attempt in range(1, 4):
    result = run_once()
    if result == "live":
        print("LIVE")
        sys.exit(0)
    print(f"attempt {attempt} ended: {result}")
    if attempt < 3:
        print("retrying...")
        time.sleep(5)

print("DEPLOY FAILED after 3 attempts")
sys.exit(1)
