"""Shared helpers: config, paths, logging, ffmpeg wrappers."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
OUT = Path(os.environ.get("LM_OUT_DIR", ROOT / "out"))


def load_config() -> dict:
    with open(ROOT / "config.toml", "rb") as f:
        return tomllib.load(f)


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def env(name: str, required: bool = True) -> str | None:
    val = os.environ.get(name)
    if required and not val:
        sys.exit(f"Missing environment variable {name}. See README.md, section 'Keys'.")
    return val


def run(cmd: list[str]) -> None:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd[:6])}...\n{res.stderr[-2000:]}")


def media_duration(path: Path) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(res.stdout.strip())


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def next_publish_slot(cfg: dict, min_hours_ahead: float = 4.0) -> datetime:
    """Next configured weekday/hour in the channel timezone, as an aware UTC datetime."""
    s = cfg["schedule"]
    tz = ZoneInfo(s["timezone"])
    now = datetime.now(tz)
    wanted = {DAY_NAMES.index(d) for d in s["days"]}
    for add in range(0, 15):
        day = (now + timedelta(days=add)).replace(hour=s["hour"], minute=0, second=0, microsecond=0)
        if day.weekday() in wanted and day - now >= timedelta(hours=min_hours_ahead):
            return day.astimezone(ZoneInfo("UTC"))
    raise RuntimeError("No publish slot found; check [schedule] in config.toml")
