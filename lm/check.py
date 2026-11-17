"""Setup check: tests every key and tells you in plain words what is missing."""
from __future__ import annotations

import os

import requests

NAMES = ["ANTHROPIC_API_KEY", "YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN",
         "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]


def run_check() -> bool:
    ok = True
    print("=== 1. Secrets present ===")
    for n in NAMES:
        has = bool(os.environ.get(n))
        print(f"  {'OK ' if has else 'MISSING'}  {n}")
        ok &= has or n == "TELEGRAM_CHAT_ID"

    print("=== 2. Claude (Anthropic) ===")
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            anthropic.Anthropic().models.retrieve("claude-opus-5-5")
            print("  OK  key works")
        except Exception as e:
            ok = False
            print(f"  FAIL  {e}")

    print("=== 3. YouTube ===")
    if all(os.environ.get(n) for n in NAMES[1:4]):
        try:
            from lm import youtube
            res = youtube.client().channels().list(part="snippet", mine=True).execute()
            names = [c["snippet"]["title"] for c in res.get("items", [])]
            print(f"  OK  connected channel: {names or 'NONE (log in with the account that owns the channel)'}")
            ok &= bool(names)
        except Exception as e:
            ok = False
            print(f"  FAIL  {e}")

    print("=== 4. Telegram ===")
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    if tok:
        try:
            me = requests.get(f"https://api.telegram.org/bot{tok}/getMe", timeout=30).json()
            print(f"  bot: @{me['result']['username']}")
            ups = requests.get(f"https://api.telegram.org/bot{tok}/getUpdates", timeout=30).json()["result"]
            chats = {str(u["message"]["chat"]["id"]): u["message"]["chat"].get("first_name", "")
                     for u in ups if "message" in u}
            for cid, name in chats.items():
                print(f"  >>> TELEGRAM_CHAT_ID for {name}: {cid}")
            if not chats and not os.environ.get("TELEGRAM_CHAT_ID"):
                print("  Send /start to your bot in Telegram, then run this check again to see your chat ID.")
            cid = os.environ.get("TELEGRAM_CHAT_ID")
            if cid:
                requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", timeout=30,
                              data={"chat_id": cid, "text": "✅ LogikMedia autopilot: setup check passed for Telegram."}).raise_for_status()
                print("  OK  test message sent")
            else:
                ok = False
        except Exception as e:
            ok = False
            print(f"  FAIL  {e}")
    print("\nRESULT:", "ALL GOOD — run 'Produce video' now." if ok else "Something is missing — see above.")
    return ok
