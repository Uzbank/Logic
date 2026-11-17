"""Animated scenes for the AI Battle format, rendered frame by frame with Pillow and piped to ffmpeg."""
from __future__ import annotations

import math
import random
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .visuals import _rgb, _wrap, font

W, H, FPS = 1920, 1080, 24
COLORS = ["#22D3EE", "#FB923C", "#A78BFA", "#4ADE80", "#F472B6"]


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def back(x: float) -> float:
    x = max(0.0, min(1.0, x))
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def prog(t: float, a: float, b: float) -> float:
    return 0.0 if t <= a else 1.0 if t >= b else (t - a) / (b - a)


class Ctx:
    def __init__(self, cfg: dict):
        b = cfg["brand"]
        self.bg, self.bg2 = _rgb(b["bg"]), _rgb(b["bg2"])
        self.acc, self.txt, self.muted = _rgb(b["accent"]), _rgb(b["text"]), _rgb(b["muted"])
        self.name = cfg["channel"]["name"]
        self.base = self._base()

    def _base(self) -> Image.Image:
        big = Image.new("RGB", (W + 120, H + 120))
        d = ImageDraw.Draw(big)
        for y in range(H + 120):
            k = y / (H + 120)
            d.line([(0, y), (W + 120, y)], fill=tuple(int(self.bg[i] * (1 - k) + self.bg2[i] * k) for i in range(3)))
        dim = tuple(int(self.acc[i] * 0.16 + self.bg[i] * 0.84) for i in range(3))
        for x in range(0, W + 120, 60):
            for y in range(0, H + 120, 60):
                d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=dim)
        return big

    def frame(self, t: float) -> Image.Image:
        off = int(t * 12) % 60  # slow drifting grid
        im = self.base.crop((off, off, off + W, off + H)).copy()
        d = ImageDraw.Draw(im)
        d.text((60, H - 70), self.name, font=font("bold", 26), fill=self.muted)
        return im


def col(i: int):
    return _rgb(COLORS[i % len(COLORS)])


def center_text(d, y, text, f, fill, stroke=0, sf=None):
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=sf)


def rr(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def mix(a, b, k):
    return tuple(int(a[i] * (1 - k) + b[i] * k) for i in range(3))


# ---------------- scenes ----------------

def s_hook(cx: Ctx, im, t, D, s):
    d = ImageDraw.Draw(im)
    words = s["text"].split()
    f = font("bold", 78)
    shown = int(len(words) * ease(prog(t, 0.1, max(0.6, D * 0.55))) + 0.999)
    lines = _wrap(d, " ".join(words), f, W - 300)
    y = 260 - max(0, len(lines) - 4) * 45
    n = 0
    for line in lines[:6]:
        lw = line.split()
        x = (W - d.textlength(line, font=f)) / 2
        for w in lw:
            if n < shown:
                hot = any(ch.isdigit() for ch in w) or w.isupper() and len(w) > 2
                d.text((x, y), w, font=f, fill=cx.acc if hot else cx.txt)
            x += d.textlength(w + " ", font=f)
            n += 1
        y += 96
    names = s.get("names", [])
    if names:
        fc = font("bold", 34)
        total = sum(d.textlength(nm, font=fc) + 80 for nm in names) + 70 * (len(names) - 1)
        x = (W - total) / 2
        for i, nm in enumerate(names):
            k = back(prog(t, 0.4 + i * 0.25, 0.9 + i * 0.25))
            yy = 860 + (1 - k) * 260
            w = d.textlength(nm, font=fc) + 80
            rr(d, [x, yy, x + w, yy + 74], 37, fill=col(i))
            d.text((x + 40, yy + 16), nm, font=fc, fill=cx.bg2)
            x += w
            if i < len(names) - 1:
                d.text((x + 12, yy + 14), "VS", font=font("bold", 38), fill=cx.txt)
                x += 70


def s_contestants(cx: Ctx, im, t, D, s):
    d = ImageDraw.Draw(im)
    center_text(d, 110, s.get("heading", "TODAY'S CONTESTANTS"), font("bold", 54), cx.txt)
    cards = s["cards"]
    n = len(cards)
    cw, gap = min(520, (W - 200 - 40 * (n - 1)) // n), 40
    x0 = (W - (cw * n + gap * (n - 1))) / 2
    for i, c in enumerate(cards):
        k = back(prog(t, 0.3 + i * 0.35, 0.9 + i * 0.35))
        x = x0 + i * (cw + gap)
        y = 270 + (1 - k) * 700
        rr(d, [x, y, x + cw, y + 520], 28, fill=mix(cx.bg2, (0, 0, 0), 0.25), outline=col(i), width=4)
        rr(d, [x, y, x + cw, y + 18], 9, fill=col(i))
        fy = y + 60
        for line in _wrap(d, c["name"], font("bold", 50), cw - 60)[:2]:
            d.text((x + 30, fy), line, font=font("bold", 50), fill=cx.txt)
            fy += 62
        ini = "".join(w[0] for w in c["name"].replace("Claude ", "").split()[:2]).upper()
        cyc = y + 400
        rr(d, [x + cw / 2 - 70, cyc - 70, x + cw / 2 + 70, cyc + 70], 70, fill=col(i))
        fi = font("bold", 64)
        d.text((x + cw / 2 - d.textlength(ini, font=fi) / 2, cyc - 40), ini, font=fi, fill=cx.bg2)
        fy += 20
        for line in c.get("lines", []):
            for wl in _wrap(d, line, font("regular", 30), cw - 60)[:3]:
                d.text((x + 30, fy), wl, font=font("regular", 30), fill=cx.muted)
                fy += 42
            fy += 14


def s_round(cx: Ctx, im, t, D, s):
    d = ImageDraw.Draw(im)
    k = back(prog(t, 0.0, 0.6))
    size = int(40 + 110 * k)
    center_text(d, 120 + (150 - size) // 2, f"ROUND {s['n']}", font("bold", max(10, size)), cx.acc)
    a = ease(prog(t, 0.5, 1.0))
    if a > 0:
        center_text(d, 300, s["name"], font("bold", 62), mix(cx.bg, cx.txt, a))
    box = [200, 430, W - 200, 900]
    if t > 0.9:
        rr(d, box, 24, fill=mix(cx.bg2, (0, 0, 0), 0.3), outline=cx.muted, width=2)
        d.text((240, 455), "THE PROMPT", font=font("bold", 28), fill=cx.acc)
        txt = s["prompt"]
        n = int(len(txt) * prog(t, 1.0, max(1.5, D * 0.7)))
        fp = font("regular", 34)
        y = 510
        lines = _wrap(d, txt[:n] + ("▌" if n < len(txt) and int(t * 4) % 2 == 0 else ""), fp, box[2] - box[0] - 80)
        for line in lines[-9:]:
            d.text((240, y), line, font=fp, fill=cx.txt)
            y += 44


def s_answers(cx: Ctx, im, t, D, s):
    d = ImageDraw.Draw(im)
    cols = s["columns"]
    n = len(cols)
    gap, top, bottom = 30, 90, 900
    cw = (W - 120 - gap * (n - 1)) // n
    maxsec = max(c["result"]["seconds"] for c in cols) or 1
    fsz = 26 if n <= 2 else 24
    ft = font("regular", fsz)
    for i, c in enumerate(cols):
        x = 60 + i * (cw + gap)
        rr(d, [x, top, x + cw, bottom], 22, fill=mix(cx.bg2, (0, 0, 0), 0.3), outline=col(i), width=3)
        rr(d, [x, top, x + cw, top + 70], 22, fill=col(i))
        d.rectangle([x, top + 40, x + cw, top + 70], fill=col(i))
        d.text((x + 24, top + 14), c["name"][:28], font=font("bold", 34), fill=cx.bg2)
        r = c["result"]
        start, finish = 0.6, 0.6 + (D * 0.75 - 0.6) * (0.35 + 0.65 * r["seconds"] / maxsec)
        p = prog(t, start, finish)
        timer = r["seconds"] * p
        d.text((x + 24, top + 86), f"TIME  {timer:4.1f}s", font=font("bold", 28), fill=cx.acc if p < 1 else cx.txt)
        txt = r["text"]
        shown = txt[: int(len(txt) * p)]
        y = top + 140
        lines = []
        for para in shown.split("\n"):
            lines += _wrap(d, para, ft, cw - 48) or [""]
        maxl = (bottom - 80 - y) // (fsz + 9)
        for line in lines[-maxl:]:
            d.text((x + 24, y), line, font=ft, fill=cx.txt)
            y += fsz + 9
        if p >= 1:
            k = ease(prog(t, finish, finish + 0.4))
            badge = f"{r['seconds']}s · {r['words']} words · ${r['cost']:.4f}"
            fb = font("bold", 24)
            bw = d.textlength(badge, font=fb) + 30
            by = bottom - 56 + (1 - k) * 30
            rr(d, [x + 20, by, x + 20 + bw, by + 40], 20, fill=mix(cx.bg2, col(i), 0.35 * k))
            d.text((x + 35, by + 7), badge, font=fb, fill=cx.txt)


def s_scores(cx: Ctx, im, t, D, s):
    d = ImageDraw.Draw(im)
    center_text(d, 70, f"ROUND {s['n']} — SCORES", font("bold", 52), cx.txt)
    crit = s["criteria"]
    cols = s["columns"]
    rowh = min(220, 760 // len(cols))
    for i, c in enumerate(cols):
        y = 180 + i * rowh
        win = c["name"] == s["winner"] and t > D * 0.65
        glow = 0.5 + 0.5 * math.sin(t * 6) if win else 0
        rr(d, [80, y, W - 80, y + rowh - 24], 20, fill=mix(cx.bg2, col(i), 0.12 + 0.12 * glow),
           outline=col(i) if win else None, width=4)
        d.text((120, y + 22), c["name"][:24], font=font("bold", 40), fill=col(i))
        for line in _wrap(d, c.get("reason", ""), font("regular", 24), 560)[:2]:
            d.text((120, y + 80), line, font=font("regular", 24), fill=cx.muted)
            y += 30
        y = 180 + i * rowh
        for j, cr in enumerate(crit):
            bx = 760 + j * 300
            k = ease(prog(t, 0.4 + i * 0.3 + j * 0.15, 1.2 + i * 0.3 + j * 0.15))
            val = c["scores"][j] if j < len(c["scores"]) else 0
            d.text((bx, y + 20), cr[:18], font=font("regular", 24), fill=cx.muted)
            rr(d, [bx, y + 58, bx + 250, y + 82], 12, fill=mix(cx.bg2, (0, 0, 0), 0.3))
            if k > 0:
                rr(d, [bx, y + 58, bx + max(24, int(250 * val / 10 * k)), y + 82], 12, fill=col(i))
            d.text((bx + 200, y + 92), f"{val * k:.0f}/10", font=font("bold", 26), fill=cx.txt)
        tot = c["total"] * ease(prog(t, 1.0 + i * 0.3, 2.2 + i * 0.3))
        d.text((W - 230, y + 30), f"{tot:.0f}", font=font("bold", 78), fill=cx.txt)
        if win:
            k = back(prog(t, D * 0.65, D * 0.65 + 0.5))
            stamp = Image.new("RGBA", (420, 90), (0, 0, 0, 0))
            sd = ImageDraw.Draw(stamp)
            rr(sd, [0, 0, 419, 89], 18, outline=cx.acc + (255,), width=6)
            sd.text((26, 16), "ROUND WINNER", font=font("bold", 48), fill=cx.acc + (255,))
            stamp = stamp.rotate(-8, expand=True, resample=Image.BICUBIC)
            sz = max(1, int(stamp.width * (0.4 + 0.6 * k))), max(1, int(stamp.height * (0.4 + 0.6 * k)))
            stamp = stamp.resize(sz)
            im.paste(stamp, (W - 720, y + 10), stamp)


def s_board(cx: Ctx, im, t, D, s):
    d = ImageDraw.Draw(im)
    center_text(d, 90, s.get("heading", "SCOREBOARD"), font("bold", 60), cx.txt)
    rows = s["totals"]  # list of (name, total, color_index)
    mx = max(v for _, v, _ in rows) or 1
    for i, (name, v, ci) in enumerate(rows):
        y = 250 + i * 150
        k = ease(prog(t, 0.3 + i * 0.25, 1.6 + i * 0.25))
        d.text((120, y + 18), f"#{i + 1}", font=font("bold", 54), fill=cx.muted)
        d.text((260, y + 22), name[:24], font=font("bold", 44), fill=col(ci))
        bx, bw = 860, 820
        rr(d, [bx, y + 26, bx + bw, y + 86], 30, fill=mix(cx.bg2, (0, 0, 0), 0.3))
        rr(d, [bx, y + 26, bx + max(60, int(bw * v / mx * k)), y + 86], 30, fill=col(ci))
        d.text((bx + bw + 30, y + 22), f"{v * k:.0f}", font=font("bold", 52), fill=cx.txt)


def _crown(d, cx, cy, s, fill):
    pts = [(cx - s, cy + s * 0.6), (cx - s, cy - s * 0.4), (cx - s * 0.5, cy + s * 0.1), (cx, cy - s * 0.7),
           (cx + s * 0.5, cy + s * 0.1), (cx + s, cy - s * 0.4), (cx + s, cy + s * 0.6)]
    d.polygon(pts, fill=fill)
    for px, py in pts[1:6:2] + [pts[3]]:
        d.ellipse([px - s * 0.12, py - s * 0.12, px + s * 0.12, py + s * 0.12], fill=fill)


def s_verdict(cx: Ctx, im, t, D, s):
    d = ImageDraw.Draw(im)
    rnd = random.Random(7)
    for _ in range(140):  # confetti
        x0, sp, ph, ci = rnd.uniform(0, W), rnd.uniform(160, 380), rnd.uniform(0, 6), rnd.randint(0, 4)
        y = (t * sp + rnd.uniform(-H, 0)) % (H + 60) - 30
        x = x0 + 30 * math.sin(t * 2 + ph)
        d.rectangle([x, y, x + 12, y + 20], fill=col(ci))
    k = back(prog(t, 0.2, 1.0))
    _crown(d, W / 2, 260, 90 * k + 1, cx.acc)
    center_text(d, 360, "THE WINNER", font("bold", 46), cx.muted)
    f = font("bold", max(10, int(120 * k)))
    center_text(d, 430, s["winner"], f, col(s.get("color", 0)), stroke=6, sf=cx.bg2)
    a = ease(prog(t, 1.5, 2.3))
    if a > 0:
        y = 640
        for line in s.get("lines", [])[:3]:
            center_text(d, y, line, font("regular", 40), mix(cx.bg, cx.txt, a))
            y += 60


def s_outro(cx: Ctx, im, t, D, s):
    d = ImageDraw.Draw(im)
    center_text(d, 300, s.get("line1", "Which AIs should fight next?"), font("bold", 70), cx.txt)
    center_text(d, 400, s.get("line2", "Tell me in the comments."), font("regular", 48), cx.muted)
    pulse = 1 + 0.06 * math.sin(t * 5)
    bw, bh = int(520 * pulse), int(110 * pulse)
    x, y = (W - bw) // 2, 560
    rr(d, [x, y, x + bw, y + bh], bh // 2, fill=(229, 57, 53))
    center_text(d, y + bh // 2 - 34, "SUBSCRIBE", font("bold", int(58 * pulse)), (255, 255, 255))


SCENES = {"hook": s_hook, "contestants": s_contestants, "round": s_round, "answers": s_answers,
          "scores": s_scores, "board": s_board, "verdict": s_verdict, "outro": s_outro}


def render(cfg: dict, scene: dict, seconds: float, out: Path, cx: Ctx | None = None) -> Path:
    cx = cx or Ctx(cfg)
    frames = max(1, int(seconds * FPS))
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                          "-crf", "20", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    fn = SCENES[scene["type"]]
    for i in range(frames):
        t = i / FPS
        im = cx.frame(t)
        fn(cx, im, t, seconds, scene)
        # quick fade in/out between scenes
        fade = min(1.0, t / 0.25, (seconds - t) / 0.25)
        if fade < 1:
            im = Image.blend(Image.new("RGB", (W, H), cx.bg2), im, max(0.0, fade))
        p.stdin.write(im.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed rendering {scene['type']}")
    return out
