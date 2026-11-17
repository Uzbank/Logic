"""Branded slides and thumbnail with Pillow (1920x1080 / 1280x720)."""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .common import ASSETS

FONT_CANDIDATES = {
    "bold": ["/usr/share/fonts/opentype/inter/Inter-Bold.otf", "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "regular": ["/usr/share/fonts/opentype/inter/Inter-Regular.otf", "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def font(kind: str, size: int):
    local = ASSETS / f"font-{kind}.ttf"
    for p in [str(local), *FONT_CANDIDATES[kind]]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def _rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _background(w: int, h: int, b: dict) -> Image.Image:
    top, bot = _rgb(b["bg"]), _rgb(b["bg2"])
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)))
    # subtle node-grid pattern (brand motif)
    acc = _rgb(b["accent"])
    dim = tuple(int(c * 0.18 + top[i] * 0.82) for i, c in enumerate(acc))
    step = w // 16
    for x in range(step, w, step):
        for y in range(step, h, step):
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=dim)
    return img


def _wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = f"{cur} {wd}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def slide(path: Path, heading: str, bullets: list[str], index: int, total: int, cfg: dict) -> None:
    b = cfg["brand"]
    W, H = 1920, 1080
    img = _background(W, H, b)
    d = ImageDraw.Draw(img)
    acc, txt, muted = _rgb(b["accent"]), _rgb(b["text"]), _rgb(b["muted"])
    x0 = 140
    # section counter + accent bar
    d.text((x0, 120), f"{index:02d} / {total:02d}", font=font("bold", 34), fill=acc)
    d.rectangle([x0, 175, x0 + 120, 183], fill=acc)
    fh = font("bold", 86)
    y = 230
    for line in _wrap(d, heading, fh, W - 2 * x0)[:3]:
        d.text((x0, y), line, font=fh, fill=txt)
        y += 104
    y += 50
    fb = font("regular", 48)
    for bullet in bullets[:4]:
        d.ellipse([x0, y + 18, x0 + 18, y + 36], fill=acc)
        for j, line in enumerate(_wrap(d, bullet, fb, W - 2 * x0 - 60)[:2]):
            d.text((x0 + 50, y + j * 60), line, font=fb, fill=muted if j else txt)
        y += 60 * min(2, len(_wrap(d, bullet, fb, W - 2 * x0 - 60))) + 34
    d.text((x0, H - 90), cfg["channel"]["name"], font=font("bold", 30), fill=muted)
    img.save(path)


def thumbnail(path: Path, text: str, cfg: dict) -> None:
    b = cfg["brand"]
    W, H = 1280, 720
    img = _background(W, H, b)
    d = ImageDraw.Draw(img)
    acc, txt = _rgb(b["accent"]), _rgb(b["text"])
    words = text.upper().split()
    size = 150
    while size > 70:
        f = font("bold", size)
        lines = _wrap(d, " ".join(words), f, W - 160)
        if len(lines) <= 3:
            break
        size -= 10
    y = (H - len(lines) * (size + 10)) // 2
    for i, line in enumerate(lines):
        # last line in accent colour for contrast
        d.text((80, y), line, font=f, fill=acc if i == len(lines) - 1 else txt,
               stroke_width=4, stroke_fill=_rgb(b["bg2"]))
        y += size + 10
    logo = ASSETS / "watermark.png"
    if logo.exists():
        lg = Image.open(logo).convert("RGBA").resize((120, 120))
        img.paste(lg, (W - 150, H - 150), lg)
    img.save(path)
