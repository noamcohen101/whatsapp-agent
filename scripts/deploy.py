"""Wait for the latest Render deploy to go live (GitHub push auto-triggers it).

Run after `git push`. If no fresh deploy appears within ~30s it triggers one.

Usage:  .venv/Scripts/python.exe scripts/deploy.py
"""
import json
import subprocess
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
HEAD = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=BASE, text=True).strip()


def api(method, path, body=None):
    req = urllib.request.Request(
        "https://api.render.com/v1" + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
    )
    req.add_header("Authorization", "Bearer " + RK)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        raw = r.read().decode()
    return json.loads(raw) if raw.strip() else {}


def latest():
    d = api("GET", f"/services/{SID}/deploys?limit=1")[0]["deploy"]
    return d["status"], (d.get("commit") or {}).get("id", "")


print(f"HEAD {HEAD[:8]}")
triggered = False
for i in range(60):
    status, commit = latest()
    print(f"  [{i}] {status} {commit[:8]}")
    if commit.startswith(HEAD[:8]) or HEAD[:8].startswith(commit[:8]):
        if status == "live":
            print("LIVE")
            sys.exit(0)
        if any(x in status for x in ("failed", "canceled", "deactivated")):
            if not triggered:
                print("failed once, retriggering...")
                try:
                    api("POST", f"/services/{SID}/deploys", {"commitId": HEAD})
                except Exception:
                    pass
                triggered = True
            else:
                print("DEPLOY FAILED")
                sys.exit(1)
    elif i >= 2 and not triggered:
        print("no auto-deploy for HEAD, triggering...")
        try:
            api("POST", f"/services/{SID}/deploys", {"commitId": HEAD})
        except Exception:
            pass
        triggered = True
    time.sleep(15)

print("timeout")
sys.exit(1)
