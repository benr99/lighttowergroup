#!/usr/bin/env python3
"""
Light Tower Group \u2014 LinkedIn OAuth Setup Helper
\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
Run this ONCE to authorise the daily news agent to post on LinkedIn.
It opens a browser OAuth flow, catches the callback on localhost, and
saves LINKEDIN_ACCESS_TOKEN + LINKEDIN_PERSON_URN to scripts/.env.

Pre-requisites (do these in the LinkedIn Developer portal first):
  1. Go to https://www.linkedin.com/developers/apps and create an app.
     - App name: "Light Tower Group News Agent" (or similar)
     - Company: your LinkedIn company page (or create one)
     - Logo: upload LTG logo
  2. Under the app \u2192 Products tab, add:
       "Share on LinkedIn"
  3. Under Auth tab \u2192 OAuth 2.0 settings, add redirect URL:
       http://localhost:8000/callback
  4. Copy the Client ID and Client Secret into scripts/.env:
       LINKEDIN_CLIENT_ID=your_client_id
       LINKEDIN_CLIENT_SECRET=your_client_secret

Then run:
  cd scripts
  python linkedin_auth.py

Token validity: ~60 days. Re-run this script when the token expires.
The daily_news_agent.py will warn you when it hits a 401 error.
"""

import os
import sys
import json
import secrets
import webbrowser
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
from pathlib import Path

ENV_PATH     = Path(__file__).parent / ".env"
REDIRECT_URI = "http://localhost:8000/callback"
SCOPES       = "r_liteprofile w_member_social"

_auth_code   = None   # set by the callback handler


# \u2500\u2500 Helpers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def load_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def save_env_key(key: str, value: str):
    """Update or append a key=value pair in scripts/.env."""
    text  = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    lines = text.splitlines()
    new_lines, found = [], False
    for line in lines:
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    print(f"  Saved {key} to .env")


# \u2500\u2500 OAuth Callback Server \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        params     = parse_qs(urlparse(self.path).query)
        _auth_code = params.get("code", [None])[0]
        error      = params.get("error", [None])[0]

        if error:
            body = f"<h2>Authorization failed: {error}</h2><p>You can close this window.</p>"
        elif _auth_code:
            body = "<h2>Authorization successful!</h2><p>You can close this window.</p>"
        else:
            body = "<h2>No code received.</h2><p>You can close this window.</p>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            f"<html><body style='font-family:sans-serif;padding:2rem'>{body}</body></html>"
            .encode()
        )

    def log_message(self, *args):
        pass   # silence access log


# \u2500\u2500 Main \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def main():
    print("\nLight Tower Group \u2014 LinkedIn OAuth Setup")
    print("=" * 50)

    env           = load_env()
    client_id     = env.get("LINKEDIN_CLIENT_ID", "")
    client_secret = env.get("LINKEDIN_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print(
            "\nBefore running this script, add your LinkedIn app credentials to scripts/.env:\n\n"
            "  LINKEDIN_CLIENT_ID=your_client_id_here\n"
            "  LINKEDIN_CLIENT_SECRET=your_client_secret_here\n\n"
            "Get these from: https://www.linkedin.com/developers/apps\n"
            "See the top of this file for full setup instructions.\n"
        )
        sys.exit(1)

    # Build the authorization URL
    state   = secrets.token_urlsafe(16)
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization?"
        + urlencode({
            "response_type": "code",
            "client_id":     client_id,
            "redirect_uri":  REDIRECT_URI,
            "scope":         SCOPES,
            "state":         state,
        })
    )

    print(f"\nOpening LinkedIn authorization in your browser...")
    print(f"If it doesn't open automatically, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # Start a one-request local server to catch the redirect
    print("Waiting for authorization callback on http://localhost:8000/callback ...")
    server = HTTPServer(("localhost", 8000), _CallbackHandler)
    server.handle_request()    # blocks until one request arrives

    if not _auth_code:
        print("\nNo authorization code received. Aborting.")
        sys.exit(1)

    # Exchange auth code for access token
    print("\nExchanging authorization code for access token...")
    token_resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type":    "authorization_code",
            "code":          _auth_code,
            "redirect_uri":  REDIRECT_URI,
            "client_id":     client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )

    token_data   = token_resp.json()
    access_token = token_data.get("access_token")
    expires_in   = token_data.get("expires_in", 0)

    if not access_token:
        print(f"\nFailed to obtain access token.\nResponse: {token_data}")
        sys.exit(1)

    expiry_days = expires_in // 86400
    print(f"Access token received (expires in ~{expiry_days} days)")

    # Fetch the person's LinkedIn ID
    me_resp  = requests.get(
        "https://api.linkedin.com/v2/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    me_data   = me_resp.json()
    person_id = me_data.get("id", "")
    first     = me_data.get("localizedFirstName", "")
    last      = me_data.get("localizedLastName",  "")
    name      = f"{first} {last}".strip()

    if not person_id:
        print(f"\nCould not retrieve LinkedIn person ID.\nResponse: {me_data}")
        sys.exit(1)

    person_urn = f"urn:li:person:{person_id}"
    print(f"Authenticated as: {name} ({person_urn})")

    # Persist to .env
    print()
    save_env_key("LINKEDIN_ACCESS_TOKEN", access_token)
    save_env_key("LINKEDIN_PERSON_URN",   person_urn)

    print(
        f"\nAll done! The daily agent will now post to LinkedIn as {name}.\n"
        f"Token expires in ~{expiry_days} days. Re-run this script to refresh it.\n\n"
        f"Test the agent with:\n"
        f"  python daily_news_agent.py --dry-run\n"
    )


if __name__ == "__main__":
    main()
