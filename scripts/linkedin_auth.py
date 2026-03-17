#!/usr/bin/env python3
"""
Light Tower Group — LinkedIn OAuth Setup Helper
────────────────────────────────────────────────
Run this ONCE to authorise the daily news agent to post on LinkedIn.

Steps:
  1. This script opens the LinkedIn authorization page.
  2. Click "Allow" on LinkedIn.
  3. LinkedIn will try to redirect to localhost and show an error — that's fine.
  4. Copy the full URL from your browser's address bar and paste it here.
  5. The script exchanges the code for a token and saves it to scripts/.env.

Pre-requisites (LinkedIn Developer portal):
  1. Create an app at https://www.linkedin.com/developers/apps
  2. Products tab → add "Share on LinkedIn"
  3. Auth tab → OAuth 2.0 settings → add redirect URL: http://localhost:8000/callback
  4. Copy Client ID + Client Secret into scripts/.env

Token validity: ~60 days. Re-run this script when the token expires.
"""

import sys
import secrets
import webbrowser
import requests
from urllib.parse import urlparse, parse_qs, urlencode
from pathlib import Path

ENV_PATH     = Path(__file__).parent / ".env"
REDIRECT_URI = "http://localhost:8000/callback"
SCOPES       = "w_member_social"


# ── Helpers ──────────────────────────────────────────────────────────────────

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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\nLight Tower Group — LinkedIn OAuth Setup")
    print("=" * 50)

    env           = load_env()
    client_id     = env.get("LINKEDIN_CLIENT_ID", "")
    client_secret = env.get("LINKEDIN_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print(
            "\nAdd your LinkedIn credentials to scripts/.env first:\n\n"
            "  LINKEDIN_CLIENT_ID=your_client_id_here\n"
            "  LINKEDIN_CLIENT_SECRET=your_client_secret_here\n"
        )
        sys.exit(1)

    state    = secrets.token_urlsafe(16)
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

    print(f"\nOpening LinkedIn in your browser...")
    print(f"\nIf it doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print("=" * 50)
    print("INSTRUCTIONS:")
    print("  1. Click 'Allow' on the LinkedIn page")
    print("  2. Your browser will show an error (can't connect to localhost) — that's OK")
    print("  3. Copy the FULL URL from your browser's address bar")
    print("     It will look like: http://localhost:8000/callback?code=XXX&state=YYY")
    print("  4. Paste it below and press Enter")
    print("=" * 50)

    callback_url = input("\nPaste the redirect URL here: ").strip()

    parsed = urlparse(callback_url)
    params = parse_qs(parsed.query)

    error = params.get("error", [None])[0]
    if error:
        desc = params.get("error_description", [""])[0]
        print(f"\nLinkedIn returned an error: {error}\n{desc}")
        sys.exit(1)

    auth_code = params.get("code", [None])[0]
    if not auth_code:
        print("\nNo authorization code found in that URL. Make sure you copied the full address bar URL.")
        sys.exit(1)

    # Exchange auth code for access token
    print("\nExchanging code for access token...")
    token_resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type":    "authorization_code",
            "code":          auth_code,
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
        print(f"\nFailed to get access token.\nResponse: {token_data}")
        sys.exit(1)

    expiry_days = expires_in // 86400
    print(f"Access token received (expires in ~{expiry_days} days)")

    # Fetch LinkedIn person ID — try OpenID userinfo first, fall back to v2/me
    person_id, name = "", ""
    for endpoint, id_key, fn_key, ln_key in [
        ("https://api.linkedin.com/v2/userinfo",   "sub",  "given_name",          "family_name"),
        ("https://api.linkedin.com/v2/me",          "id",   "localizedFirstName",  "localizedLastName"),
    ]:
        try:
            r = requests.get(
                endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            d = r.json()
            if d.get(id_key):
                person_id = d[id_key]
                name = f"{d.get(fn_key, '')} {d.get(ln_key, '')}".strip()
                break
        except Exception:
            continue

    if not person_id:
        print("Warning: could not fetch LinkedIn person ID. Enter it manually.")
        person_id = input("Paste your LinkedIn person ID (or press Enter to skip): ").strip()
        if not person_id:
            print("Skipping person URN — LinkedIn posting may not work.")
            person_urn = ""
        else:
            person_urn = f"urn:li:person:{person_id}"
    else:
        person_urn = f"urn:li:person:{person_id}"
        print(f"Authenticated as: {name} ({person_urn})")

    # Save to .env
    print()
    save_env_key("LINKEDIN_ACCESS_TOKEN", access_token)
    if person_urn:
        save_env_key("LINKEDIN_PERSON_URN", person_urn)

    print(
        f"\nAll done! The daily agent will now post to LinkedIn as {name or 'you'}.\n"
        f"Token expires in ~{expiry_days} days. Re-run this script to refresh it.\n\n"
        f"Test with:\n"
        f"  python daily_news_agent.py --dry-run\n"
    )


if __name__ == "__main__":
    main()
