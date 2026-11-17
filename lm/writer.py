"""Claude agents: (1) topic researcher with web search, (2) scriptwriter with structured output."""
from __future__ import annotations

import json
from datetime import date

import anthropic
from pydantic import BaseModel, Field

from .common import log

BETAS = ["server-side-fallback-2026-07-01"]


class Section(BaseModel):
    heading: str = Field(description="Short slide heading, max 6 words")
    bullets: list[str] = Field(description="2-4 on-screen bullet points, max 8 words each")
    narration: str = Field(description="Exactly what the voice says for this section")


class VideoPlan(BaseModel):
    topic: str
    why_now: str = Field(description="One sentence: why this topic is worth a video this week")
    title: str = Field(description="YouTube title, max 70 characters, no clickbait lies")
    thumbnail_text: str = Field(description="2-4 punchy words for the thumbnail")
    hook: str = Field(description="First 2 sentences of narration, also used as intro slide")
    sections: list[Section] = Field(description="6-9 sections; first is the intro/hook, last is the wrap-up + CTA")
    description: str = Field(description="YouTube description: 2 short paragraphs, then 'Sources:' list with URLs, then 3 hashtags")
    tags: list[str] = Field(description="10-15 search tags")
    sources: list[str] = Field(description="URLs actually used for facts in the script")


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _check(resp) -> None:
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined: {getattr(resp, 'stop_details', None)}")


def research(cfg: dict, niche_videos: list[dict], used_topics: list[str]) -> str:
    """Agent 1: finds 5 candidate topics from fresh news + what already performs on YouTube."""
    c = cfg["channel"]
    top = "\n".join(f"- {v['title']} ({v.get('views', 0):,} views, {v['channel']})" for v in niche_videos[:40]) or "(not available)"
    used = "\n".join(f"- {t}" for t in used_topics[-60:]) or "(none yet)"
    prompt = f"""You are the topic researcher for the YouTube channel "{c['name']}".
Niche: {c['niche']}
Audience: {c['audience']}
Today: {date.today().isoformat()}

Recent top videos in this niche on YouTube (what the audience already clicks):
{top}

Topics we already covered (do not repeat):
{used}

Search the web for news and launches from the last 14 days that matter to this audience:
new AI tools, price changes, big feature releases, practical how-tos that are trending.
Then propose 5 video topics. For each: a working title, why it would get clicks (link it to the
YouTube data above), why it is useful to a small-business owner, and 3-6 source URLs with the key
facts you found (numbers, prices, dates). Prefer topics where we can give concrete, checkable facts."""
    client = _client()
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": cfg["claude"]["web_search_max_uses"]}]
    messages = [{"role": "user", "content": prompt}]
    collected = []
    for _ in range(5):  # continue if the server pauses a long search turn
        resp = client.beta.messages.create(
            model=cfg["claude"]["model"], max_tokens=16000, betas=BETAS, fallbacks="default",
            output_config={"effort": cfg["claude"]["effort"]}, tools=tools, messages=messages,
        )
        _check(resp)
        collected.extend(resp.content)
        if resp.stop_reason != "pause_turn":
            break
        messages = [messages[0], {"role": "assistant", "content": collected}]
    notes = "\n".join(b.text for b in collected if getattr(b, "type", "") == "text")
    log(f"Research notes: {len(notes)} chars")
    return notes


def write_script(cfg: dict, research_notes: str, used_topics: list[str]) -> VideoPlan:
    """Agent 2: picks the best topic and writes the full video plan."""
    c = cfg["channel"]
    prompt = f"""You are the head writer of the YouTube channel "{c['name']}".
Niche: {c['niche']}. Audience: {c['audience']}.

Research notes from our researcher:
<research>
{research_notes}
</research>

Already covered (avoid): {json.dumps(used_topics[-60:])}

Pick the ONE topic with the best mix of search demand and usefulness, then write the video.
Rules:
- Narration about {cfg['channel']['target_words']} words total, spoken English, short sentences, no filler.
- Hook in the first 10 seconds: a concrete problem or number, not "In this video".
- Every fact (price, feature, date, number) must come from the research notes; if unsure, say so plainly.
  Never invent test results or personal experiences. Say "according to <source>" for key claims.
- Give a clear verdict: who should use it, who should skip it, and a cheaper/free alternative.
- Add original value: a simple framework, checklist, or cost math a small business can apply today.
- Last section: one-line summary + ask viewers to comment their use case + subscribe.
- No emojis in narration. Title max 70 chars, honest (the video must deliver what it promises)."""
    resp = _client().beta.messages.parse(
        model=cfg["claude"]["model"], max_tokens=16000, betas=BETAS, fallbacks="default",
        output_config={"effort": cfg["claude"]["effort"]},
        messages=[{"role": "user", "content": prompt}], output_format=VideoPlan,
    )
    _check(resp)
    plan = resp.parsed_output
    words = sum(len(s.narration.split()) for s in plan.sections)
    log(f"Script: '{plan.title}' — {len(plan.sections)} sections, {words} words")
    return plan
