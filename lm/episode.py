"""Turns a judged battle + commentary into scenes, voice, video and thumbnail."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from . import assemble, scenes, voice
from .common import ASSETS, log
from .visuals import _background, _rgb, _wrap, font


def build_scenes(mode: str, contestants: list[dict], rounds: list[dict], talk: dict) -> list[dict]:
    names = [c["name"] for c in rounds[0]["columns"]]
    if mode == "models":
        cards = [{"name": c["name"], "lines": [c.get("tag", ""),
                  f"${c['price_in']:g} in / ${c['price_out']:g} out per 1M tokens"]} for c in contestants]
        heading = "TODAY'S CONTESTANTS"
    else:
        model = rounds[0]["columns"][0]["contestant"]["name"]
        cards = [{"name": c["name"], "lines": [f"\"{c['prompt'][:110]}{'...' if len(c['prompt']) > 110 else ''}\""]}
                 for c in rounds[0]["columns"]]
        heading = f"SAME AI ({model}), 3 PROMPTS"
    out = [{"type": "hook", "text": talk["hook"], "names": names, "say": talk["hook"]},
           {"type": "contestants", "cards": cards, "heading": heading, "say": talk["contestants"]}]
    totals = {n: 0 for n in names}
    for i, (r, rt) in enumerate(zip(rounds, talk["rounds"]), 1):
        out.append({"type": "round", "n": i, "name": r["name"], "prompt": r["columns"][-1]["prompt"], "say": rt["intro"]})
        out.append({"type": "answers", "columns": r["columns"], "say": rt["answers"]})
        out.append({"type": "scores", "n": i, "columns": r["columns"], "criteria": r["criteria"],
                    "winner": r["winner"], "say": rt["scores"]})
        for c in r["columns"]:
            totals[c["name"]] += c["total"]
    board = sorted(((n, v, names.index(n)) for n, v in totals.items()), key=lambda x: -x[1])
    out.append({"type": "board", "totals": board, "heading": "FINAL SCOREBOARD", "say": talk["scoreboard"]})
    win = board[0]
    lines = [f"{n}: {v} points" for n, v, _ in board]
    out.append({"type": "verdict", "winner": win[0], "color": win[2], "lines": lines, "say": talk["verdict"]})
    out.append({"type": "outro", "say": talk["outro"]})
    return out


def thumbnail(path: Path, text: str, names: list[str], cfg: dict) -> None:
    b = cfg["brand"]
    im = _background(1280, 720, b)
    d = ImageDraw.Draw(im)
    n = len(names)
    w = 1280 // n
    for i, nm in enumerate(names):
        c = scenes.col(i)
        d.rectangle([i * w, 0, (i + 1) * w, 300], fill=c)
        f = font("bold", 64)
        lines = _wrap(d, nm.upper(), f, w - 40)[:2]
        y = 150 - len(lines) * 38
        for line in lines:
            d.text((i * w + (w - d.textlength(line, font=f)) / 2, y), line, font=f, fill=_rgb(b["bg2"]))
            y += 76
        if i:
            d.ellipse([i * w - 70, 80, i * w + 70, 220], fill=_rgb(b["bg2"]))
            d.text((i * w - 48, 112), "VS", font=font("bold", 66), fill=(255, 255, 255))
    f = font("bold", 130)
    lines = _wrap(d, text.upper(), f, 1180)[:2]
    y = 330 + (2 - len(lines)) * 70
    for i, line in enumerate(lines):
        d.text(((1280 - d.textlength(line, font=f)) / 2, y), line, font=f,
               fill=_rgb(b["accent"]) if i == len(lines) - 1 else (255, 255, 255), stroke_width=5, stroke_fill=_rgb(b["bg2"]))
        y += 145
    logo = ASSETS / "watermark.png"
    if logo.exists():
        lg = Image.open(logo).convert("RGBA").resize((96, 96))
        im.paste(lg, (1280 - 120, 720 - 120), lg)
    im.save(path)


def produce_video(work: Path, scene_list: list[dict], cfg: dict, dry_run: bool) -> Path:
    cx = scenes.Ctx(cfg)
    clips, audios, narr = [], [], []
    for i, sc in enumerate(scene_list, 1):
        mp3 = work / f"voice_{i:02d}.mp3"
        dur = voice.synthesize(sc["say"], mp3, cfg, dry_run=dry_run)
        clip = work / f"clip_{i:02d}.mp4"
        extra = 1.2 if sc["type"] in ("answers", "scores", "verdict") else 0.6
        scenes.render(cfg, sc, dur + extra, clip, cx)
        clips.append(clip); audios.append(mp3); narr.append(sc["say"])
        log(f"Scene {i}/{len(scene_list)} ({sc['type']}) rendered")
    return assemble.build_from_clips(work, clips, audios, narr, work / "video.mp4", cfg)
