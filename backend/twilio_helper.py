"""
Twilio test helper — run locally to verify your trial credentials work.

Usage:
    export TWILIO_ACCOUNT_SID=ACxxxxxxxx
    export TWILIO_AUTH_TOKEN=xxxxxxxx
    export TWILIO_FROM_NUMBER=+1234567890
    python twilio_helper.py +91XXXXXXXXXX

On trial accounts, the destination number MUST be Twilio-verified first.
If env vars are missing, the helper runs in MOCK mode and just prints.
"""

import os
import sys
from datetime import datetime


def send(to_phone: str, body: str) -> dict:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    tok = os.getenv("TWILIO_AUTH_TOKEN", "")
    frm = os.getenv("TWILIO_FROM_NUMBER", "")

    if not (sid and tok and frm):
        print(f"[MOCK {datetime.now().isoformat(timespec='seconds')}] "
              f"→ {to_phone}\n{body}\n")
        return {"mode": "mock"}

    try:
        from twilio.rest import Client
    except ImportError:
        print("twilio not installed — run: pip install twilio")
        return {"mode": "error", "error": "twilio_not_installed"}

    client = Client(sid, tok)
    msg = client.messages.create(body=body, from_=frm, to=to_phone)
    print(f"[REAL] sent sid={msg.sid} status={msg.status}")
    return {"mode": "real", "sid": msg.sid, "status": msg.status}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    to = sys.argv[1]
    body = (
        "📚 LearnFlow test SMS — if you can read this, your Twilio setup works.\n"
        "Morning nudges arrive at 8 AM, night recaps at 9 PM."
    )
    send(to, body)
