"""ffmpeg montage: slide clips with slow zoom + voice + burned captions + watermark + optional music."""
from __future__ import annotations

import re
from pathlib import Path

from .common import ASSETS, log, media_duration, run

FPS = 30


def _ts(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def _chunks(text: str, max_words: int = 9) -> list[str]:
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", text.strip()):
        w = sent.split()
        for i in range(0, len(w), max_words):
            out.append(" ".join(w[i:i + max_words]))
    return [c for c in out if c]


def captions(sections: list[tuple[str, float]], path: Path, pad: float) -> None:
    """Approximate captions: split each section's narration over its audio by character length."""
    lines, n, t0 = [], 1, 0.0
    for text, dur in sections:
        parts = _chunks(text)
        total = sum(len(p) for p in parts) or 1
        t = t0
        for p in parts:
            dt = dur * len(p) / total
            lines.append(f"{n}\n{_ts(t)} --> {_ts(t + dt)}\n{p}\n")
            n += 1
            t += dt
        t0 += dur + pad
    path.write_text("\n".join(lines), encoding="utf-8")


def clip(slide_png: Path, seconds: float, out: Path) -> None:
    frames = int(seconds * FPS) + 1
    zoom = f"min(1+0.06*on/{frames},1.06)"
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(slide_png), "-vf",
         f"scale=3840:-1,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={FPS},format=yuv420p",
         "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(out)])


def build(work: Path, slides: list[Path], audios: list[Path], narrations: list[str], out: Path, pad: float = 0.5) -> Path:
    durs = [media_duration(a) for a in audios]
    clips = []
    for i, (s, d) in enumerate(zip(slides, durs)):
        c = work / f"clip_{i:02d}.mp4"
        clip(s, d + pad, c)
        clips.append(c)
        log(f"Clip {i + 1}/{len(slides)} ready")

    (work / "clips.txt").write_text("".join(f"file '{c.name}'\n" for c in clips))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(work / "clips.txt"), "-c", "copy", str(work / "video_raw.mp4")])

    # audio: each section + pad of silence, concatenated
    padded = []
    for i, a in enumerate(audios):
        p = work / f"voice_{i:02d}.wav"
        run(["ffmpeg", "-y", "-i", str(a), "-af", f"apad=pad_dur={pad}", "-ar", "44100", "-ac", "2", str(p)])
        padded.append(p)
    (work / "voices.txt").write_text("".join(f"file '{p.name}'\n" for p in padded))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(work / "voices.txt"), "-c", "copy", str(work / "voice.wav")])

    srt = work / "captions.srt"
    captions(list(zip(narrations, durs)), srt, pad)

    inputs = ["-i", str(work / "video_raw.mp4"), "-i", str(work / "voice.wav")]
    style = "FontName=Inter,FontSize=15,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=28"
    vf = f"[0:v]subtitles={srt.as_posix()}:force_style='{style}'[v1]"
    last = "v1"
    wm = ASSETS / "watermark.png"
    if wm.exists():
        inputs += ["-i", str(wm)]
        vf += f";[2:v]scale=110:110,format=rgba,colorchannelmixer=aa=0.8[wm];[{last}][wm]overlay=W-w-40:40[v2]"
        last = "v2"
    music = ASSETS / "music.mp3"
    if music.exists():
        idx = 3 if wm.exists() else 2
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        af = f"[{idx}:a]volume=0.08[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]"
        amap = "[a]"
        vf += ";" + af
    else:
        amap = "1:a"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", vf, "-map", f"[{last}]", "-map", amap,
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", str(out)])
    log(f"Final video: {out} ({media_duration(out) / 60:.1f} min)")
    return out
