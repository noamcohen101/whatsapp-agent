"""Phone-friendly Google OAuth: print an auth URL, then exchange a pasted redirect URL.

Usage:
  step 1:  python scripts/google_auth_manual.py            -> prints the auth URL
  step 2:  (user opens URL on phone, approves, copies the http://localhost/?... URL)
  step 3:  python scripts/google_auth_manual.py "<pasted redirect URL>"  -> prints tokens
"""
import sys
import urllib.parse

from google_auth_oauthlib.flow import Flow

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
]
REDIRECT = "http://localhost"

flow = Flow.from_client_secrets_file(
    "google_client_secret.json", scopes=SCOPES, redirect_uri=REDIRECT
)

if len(sys.argv) < 2:
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    # '+' as a scope separator gets corrupted when a long URL is copied on mobile;
    # force %20 which survives.
    auth_url = auth_url.replace("scope=" + "+".join(
        urllib.parse.quote(s, safe="") for s in SCOPES
    ), "scope=" + "%20".join(urllib.parse.quote(s, safe="") for s in SCOPES))
    print("\n=== פתח את הקישור הזה בטלפון, אשר, והעתק את הכתובת שאליה זה מפנה ===\n")
    print(auth_url)
    print()
else:
    pasted = sys.argv[1].strip()
    qs = urllib.parse.urlparse(pasted).query
    code = urllib.parse.parse_qs(qs).get("code", [None])[0]
    if not code:
        raise SystemExit("לא מצאתי code בכתובת שהודבקה.")
    flow.fetch_token(code=code)
    creds = flow.credentials
    if not creds.refresh_token:
        raise SystemExit("אין refresh_token. מחק את האפליקציה ב-myaccount.google.com/permissions ונסה שוב.")
    print("GOOGLE_CLIENT_ID=" + flow.client_config["client_id"])
    print("GOOGLE_CLIENT_SECRET=" + flow.client_config["client_secret"])
    print("GOOGLE_REFRESH_TOKEN=" + creds.refresh_token)
