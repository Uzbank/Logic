"""Text-to-speech. ElevenLabs if ELEVENLABS_API_KEY is set, else free edge-tts. Dry-run makes silence."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import requests

from .common import log, media_duration, run


def _edge(text: str, out: Path, voice: str, rate: str) -> None:
    import edge_tts

    async def go():
        await edge_tts.Communicate(text, voice, rate=rate).save(str(out))

    asyncio.run(go())


def _clean(text: str) -> str:
    import re
    text = text.replace("&", " and ").replace("<", " ").replace(">", " ")
    text = re.sub(r"[\u2018\u2019]", "'", text)
    text = re.sub(r"[\u201c\u201d]", '"', text)
    text = text.replace("\u2014", ", ").replace("\u2013", "-")
    return re.sub(r"\s+", " ", text).strip()


def _gtts(text: str, out: Path) -> None:
    from gtts import gTTS
    gTTS(text, lang="en", tld="com").save(str(out))


def _free(text: str, out: Path, v: dict) -> None:
    """edge-tts with retries and a backup voice, then Google TTS as last resort."""
    import time
    text = _clean(text)
    attempts = [(v["edge_voice"], v["edge_rate"]), (v["edge_voice"], "+0%"), ("en-US-GuyNeural", "+0%")]
    for i, (voice, rate) in enumerate(attempts):
        try:
            _edge(text, out, voice, rate)
            if out.exists() and out.stat().st_size > 1000:
                return
        except Exception as e:
            log(f"edge-tts attempt {i + 1} failed ({voice}): {e}")
        time.sleep(3 * (i + 1))
    log("edge-tts unavailable, using Google TTS fallback")
    _gtts(text, out)


def _eleven(text: str, out: Path, voice_id: str, model: str) -> None:
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "accept": "audio/mpeg"},
        json={"text": text, "model_id": model, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
        timeout=300,
    )
    r.raise_for_status()
    out.write_bytes(r.content)


def _silence(text: str, out: Path) -> None:
    secs = max(2.0, len(text.split()) / 2.6)
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{secs:.2f}",
         "-c:a", "libmp3lame", "-b:a", "128k", str(out)])


def synthesize(text: str, out: Path, cfg: dict, dry_run: bool = False) -> float:
    v = cfg["voice"]
    if dry_run:
        _silence(text, out)
    elif os.environ.get("ELEVENLABS_API_KEY"):
        _eleven(text, out, v["elevenlabs_voice_id"], v["elevenlabs_model"])
    else:
        _free(text, out, v)
    d = media_duration(out)
    log(f"Voice {out.name}: {d:.1f}s")
    return d
