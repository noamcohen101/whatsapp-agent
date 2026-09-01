"""One-time: get a Google refresh token for Calendar + Gmail (read-only)."""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]

flow = InstalledAppFlow.from_client_secrets_file("google_client_secret.json", SCOPES)

try:
    creds = flow.run_local_server(
        port=8765, access_type="offline", prompt="consent", open_browser=True
    )
except OSError as e:
    print(f"Local server failed ({e}); falling back to console mode.", file=sys.stderr)
    creds = flow.run_console(access_type="offline", prompt="consent")

if not creds.refresh_token:
    raise SystemExit(
        "No refresh_token. Go to https://myaccount.google.com/permissions, "
        "remove the app, and run again."
    )

print("=== COPY THESE ===")
print("GOOGLE_CLIENT_ID=" + flow.client_config["client_id"])
print("GOOGLE_CLIENT_SECRET=" + flow.client_config["client_secret"])
print("GOOGLE_REFRESH_TOKEN=" + creds.refresh_token)
