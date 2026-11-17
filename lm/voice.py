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
        _edge(text, out, v["edge_voice"], v["edge_rate"])
    d = media_duration(out)
    log(f"Voice {out.name}: {d:.1f}s")
    return d
