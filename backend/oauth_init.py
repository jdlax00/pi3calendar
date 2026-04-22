"""One-shot OAuth bootstrap. Run once on the Pi (with a keyboard attached)
after dropping your Google Desktop credentials.json into ~/.config/picalendar/.

    python -m backend.oauth_init
"""

from __future__ import annotations

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

from .google_calendar import (
    CONFIG_DIR,
    CREDENTIALS_PATH,
    SCOPES,
    TOKEN_PATH,
    has_valid_token,
)


def main() -> int:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CREDENTIALS_PATH.exists():
        print(f"Missing {CREDENTIALS_PATH}.")
        print("Create a Desktop-app OAuth client at")
        print("  https://console.cloud.google.com/apis/credentials")
        print(f"and save the JSON to {CREDENTIALS_PATH}.")
        return 1

    if has_valid_token():
        print(f"Token already exists at {TOKEN_PATH}. Delete it to re-auth.")
        return 0

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=8765, prompt="consent", access_type="offline")
    TOKEN_PATH.write_text(creds.to_json())
    print(f"Wrote {TOKEN_PATH}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
