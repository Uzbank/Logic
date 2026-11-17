"""Telegram bot for the 1-minute human check: ✅ publish / ❌ cancel buttons."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from .common import env, log


def _api(method: str, **kw):
    token = env("TELEGRAM_BOT_TOKEN")
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", timeout=60, **kw)
    r.raise_for_status()
    return r.json()["result"]


def enabled() -> bool:
    import os
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def send_review(video_id: str, plan: dict, thumb: Path | None, slot: datetime, mode: str) -> None:
    when = slot.strftime("%a %d %b, %H:%M UTC")
    ts = int(slot.timestamp())
    if mode == "opt_in":
        head = f"🆕 New video is ready and PRIVATE.\nPress ✅ to publish it on {when}."
        buttons = [[{"text": "✅ Publish", "callback_data": f"ok|{video_id}|{ts}"},
                    {"text": "❌ Reject", "callback_data": f"no|{video_id}|0"}]]
    else:
        head = f"🆕 New video is SCHEDULED for {when}.\nPress ❌ if you want to stop it."
        buttons = [[{"text": "❌ Cancel publishing", "callback_data": f"no|{video_id}|0"}]]
    caption = (f"{head}\n\n<b>{plan['title']}</b>\n\nWhy now: {plan.get('why_now', '')}\n\n"
               f"Watch: https://youtu.be/{video_id}\nEdit: https://studio.youtube.com/video/{video_id}/edit")
    data = {"chat_id": env("TELEGRAM_CHAT_ID"), "caption": caption[:1000], "parse_mode": "HTML",
            "reply_markup": json.dumps({"inline_keyboard": buttons})}
    if thumb and thumb.exists():
        with open(thumb, "rb") as f:
            _api("sendPhoto", data=data, files={"photo": f})
    else:
        data["text"] = data.pop("caption")
        _api("sendMessage", data=data)
    log("Telegram review message sent")


def notify(text: str) -> None:
    if enabled():
        _api("sendMessage", data={"chat_id": env("TELEGRAM_CHAT_ID"), "text": text[:4000]})


def pending_decisions() -> list[tuple[str, str, datetime | None, dict]]:
    """Read button presses. Returns (action, video_id, slot, callback) and confirms them to Telegram."""
    updates = _api("getUpdates", data={"timeout": 0, "allowed_updates": json.dumps(["callback_query"])})
    chat = str(env("TELEGRAM_CHAT_ID"))
    out = []
    for u in updates:
        cq = u.get("callback_query")
        if not cq or str(cq["message"]["chat"]["id"]) != chat:
            continue
        action, vid, ts = cq["data"].split("|")
        slot = datetime.fromtimestamp(int(ts), tz=timezone.utc) if int(ts) else None
        out.append((action, vid, slot, cq))
    if updates:
        _api("getUpdates", data={"offset": updates[-1]["update_id"] + 1, "timeout": 0})
    return out


def answer(cq: dict, text: str) -> None:
    _api("answerCallbackQuery", data={"callback_query_id": cq["id"], "text": text[:190]})
    _api("editMessageReplyMarkup", data={"chat_id": cq["message"]["chat"]["id"],
                                         "message_id": cq["message"]["message_id"],
                                         "reply_markup": json.dumps({"inline_keyboard": []})})
    _api("sendMessage", data={"chat_id": cq["message"]["chat"]["id"], "text": text,
                              "reply_to_message_id": cq["message"]["message_id"]})
