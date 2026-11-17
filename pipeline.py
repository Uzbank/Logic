"""LogikMedia autopilot.

  python pipeline.py produce            # research -> script -> voice -> video -> upload -> Telegram check
  python pipeline.py produce --dry-run  # no API keys needed: sample script, silent voice, no upload
  python pipeline.py produce --no-upload
  python pipeline.py check              # test all keys (GitHub: Actions -> Setup check)
  python pipeline.py review             # apply ✅/❌ presses from Telegram (run every hour)
"""
from __future__ import annotations

import argparse
import json
import traceback
from datetime import datetime
from pathlib import Path

from lm import assemble, telegram, visuals, voice
from lm.common import DATA, OUT, ROOT, load_config, log, next_publish_slot, read_json, write_json

USED = DATA / "topics_used.json"


def sample_plan() -> dict:
    return json.loads((ROOT / "data" / "sample_plan.json").read_text(encoding="utf-8"))


def produce(dry_run: bool, upload: bool) -> None:
    cfg = load_config()
    used = read_json(USED, [])
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    work = OUT / stamp
    work.mkdir(parents=True, exist_ok=True)

    # 1-2. Topic research + script (two Claude agents)
    if dry_run:
        plan = sample_plan()
    else:
        from lm import writer, youtube
        niche = []
        try:
            niche = youtube.niche_snapshot(youtube.client(), cfg["channel"]["seed_keywords"])
        except SystemExit:
            log("No YouTube credentials: skipping niche snapshot")
        notes = writer.research(cfg, niche, [u["topic"] for u in used])
        (work / "research.md").write_text(notes, encoding="utf-8")
        plan = writer.write_script(cfg, notes, [u["topic"] for u in used]).model_dump()
    write_json(work / "plan.json", plan)

    # 3. Voice + 4. slides
    secs = plan["sections"]
    slides, audios, narr = [], [], []
    for i, s in enumerate(secs, 1):
        png, mp3 = work / f"slide_{i:02d}.png", work / f"voice_{i:02d}.mp3"
        visuals.slide(png, s["heading"], s["bullets"], i, len(secs), cfg)
        voice.synthesize(s["narration"], mp3, cfg, dry_run=dry_run)
        slides.append(png); audios.append(mp3); narr.append(s["narration"])
    thumb = work / "thumbnail.png"
    visuals.thumbnail(thumb, plan["thumbnail_text"], cfg)

    # 5. Montage
    video = assemble.build(work, slides, audios, narr, work / "video.mp4")

    if dry_run or not upload:
        log(f"Done (not uploaded). Files in {work}")
        return

    # 6. Upload + schedule + human check
    from lm import youtube
    yt = youtube.client()
    slot = next_publish_slot(cfg)
    mode = cfg["review"]["mode"]
    if mode == "opt_in" and not telegram.enabled():
        log("review.mode=opt_in but Telegram is not configured: video will stay private until you publish it in Studio")
    vid = youtube.upload(yt, video, thumb, plan, cfg, publish_at=None if mode == "opt_in" else slot)
    if telegram.enabled() and mode != "off":
        telegram.send_review(vid, plan, thumb, slot, mode)
    used.append({"topic": plan["topic"], "title": plan["title"], "video_id": vid, "date": stamp})
    write_json(USED, used)


def review() -> None:
    from lm import youtube
    cfg = load_config()
    if not telegram.enabled():
        log("Telegram not configured; nothing to review")
        return
    decisions = telegram.pending_decisions()
    if not decisions:
        log("No new button presses")
        return
    yt = youtube.client()
    for action, vid, slot, cq in decisions:
        if action == "ok":
            youtube.set_schedule(yt, vid, cfg, slot)
            telegram.answer(cq, f"✅ Approved. Goes live {slot:%a %d %b %H:%M} UTC (or now if that time passed).")
        else:
            youtube.set_schedule(yt, vid, cfg, None)
            telegram.answer(cq, "❌ Stopped. The video stays private; edit or delete it in YouTube Studio.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["produce", "review", "check"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-upload", action="store_true")
    a = ap.parse_args()
    try:
        if a.command == "check":
            from lm.check import run_check
            raise SystemExit(0 if run_check() else 1)
        if a.command == "produce":
            produce(a.dry_run, upload=not a.no_upload)
        else:
            review()
    except Exception as e:
        try:
            telegram.notify(f"⚠️ LogikMedia autopilot failed ({a.command}): {e}")
        except Exception:
            pass
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
