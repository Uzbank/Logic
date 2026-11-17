"""AI Battle format: plan a real test, run it on real models, judge blind, write the commentary.

Nothing shown in the video is invented: every answer on screen is the model's real output,
every timer is the measured latency, every price is computed from real token usage.
"""
from __future__ import annotations

import json
import os
import random
import time
from datetime import date

import anthropic
import requests
from pydantic import BaseModel, Field

from .common import log

BETAS = ["server-side-fallback-2026-07-01"]


# ---------- contestants ----------

def available_contestants(cfg: dict) -> list[dict]:
    """Contestants from config whose API key is present. Order is kept."""
    keys = {"anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}
    out = [c for c in cfg["battle"]["contestants"] if os.environ.get(keys[c["provider"]])]
    providers = {c["provider"] for c in out}
    if len(providers) < 2:
        # Only one company available: compare that company's cheap / mid / premium models.
        out = [c for c in cfg["battle"]["fallback_contestants"]]
    return out[: cfg["battle"]["max_contestants"]]


def _price(c: dict, tin: int, tout: int) -> float:
    return tin / 1e6 * c["price_in"] + tout / 1e6 * c["price_out"]


def ask(c: dict, prompt: str) -> dict:
    """Send one prompt to one contestant. Returns real text, latency, tokens and cost."""
    t0 = time.time()
    text, tin, tout = "", 0, 0
    try:
        if c["provider"] == "anthropic":
            r = anthropic.Anthropic().messages.create(
                model=c["model"], max_tokens=4000, messages=[{"role": "user", "content": prompt}])
            if r.stop_reason == "refusal":
                text = "(the model declined this request)"
            else:
                text = "\n".join(b.text for b in r.content if b.type == "text")
            tin, tout = r.usage.input_tokens, r.usage.output_tokens
        elif c["provider"] == "gemini":
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{c['model']}:generateContent",
                params={"key": os.environ["GEMINI_API_KEY"]},
                json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=180)
            r.raise_for_status()
            j = r.json()
            text = "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"])
            u = j.get("usageMetadata", {})
            tin, tout = u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
        elif c["provider"] == "openai":
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                json={"model": c["model"], "messages": [{"role": "user", "content": prompt}]}, timeout=180)
            r.raise_for_status()
            j = r.json()
            text = j["choices"][0]["message"]["content"]
            tin, tout = j["usage"]["prompt_tokens"], j["usage"]["completion_tokens"]
    except Exception as e:  # shown honestly on screen instead of hiding the failure
        text = f"(error: {type(e).__name__})"
        log(f"{c['name']} failed: {e}")
    secs = time.time() - t0
    return {"text": text.strip(), "seconds": round(secs, 1), "tokens_in": tin, "tokens_out": tout,
            "cost": round(_price(c, tin, tout), 5), "words": len(text.split())}


# ---------- planning ----------

class Variant(BaseModel):
    label: str = Field(description="Short column label, e.g. 'Lazy prompt' or 'Pro prompt'")
    prompt: str


class Round(BaseModel):
    name: str = Field(description="Round name, max 5 words, e.g. 'Cold email that books calls'")
    prompt: str = Field(description="Exact prompt sent to every AI (models mode). Must demand a short answer: max 110 words")
    variants: list[Variant] = Field(description="Prompts mode only: 3 prompt versions of rising quality for the same job. Empty in models mode")
    criteria: list[str] = Field(description="3 judging criteria, 1-3 words each")


class BattlePlan(BaseModel):
    mode: str = Field(description="'models' (AIs compete on the same prompt) or 'prompts' (one AI, prompt versions compete)")
    topic: str
    business: str = Field(description="The concrete small business used as the example, e.g. 'a 2-person plumbing company in Ohio'")
    rounds: list[Round] = Field(description="Exactly 3 rounds, escalating difficulty, each a real task a small business does weekly")


def plan(cfg: dict, contestants: list[dict], used: list[str], niche_titles: list[str]) -> BattlePlan:
    names = ", ".join(c["name"] for c in contestants)
    mode_hint = cfg["battle"].get("mode", "auto")
    prompt = f"""You design episodes for the YouTube channel "{cfg['channel']['name']}" — AI battles for US small-business owners.
Today: {date.today().isoformat()}.
Contestants available for a models battle: {names}.
Mode setting: {mode_hint} (auto = pick whichever makes the stronger episode; alternate with recent episodes).
Recent popular YouTube titles in the niche: {json.dumps(niche_titles[:25])}
Already done (do not repeat): {json.dumps(used[-40:])}

Design one episode: a concrete business, 3 rounds of real tasks it does every week (marketing copy, customer
replies, pricing, hiring posts, social captions, quotes, policies...). Rounds escalate: easy -> tricky -> hard
(a tricky constraint, an angry customer, numbers to calculate, a trap where AIs often fail).
Every prompt must ask for an answer of max 110 words so it fits on screen.
In 'prompts' mode, give 3 variants per round: a lazy one-line prompt, a decent prompt, an expert prompt
(role, context, constraints, format); keep 'prompt' equal to the expert one. In 'models' mode leave variants empty."""
    r = anthropic.Anthropic().beta.messages.parse(
        model=cfg["claude"]["model"], max_tokens=16000, betas=BETAS, fallbacks="default",
        output_config={"effort": cfg["claude"]["effort"]},
        messages=[{"role": "user", "content": prompt}], output_format=BattlePlan)
    p = r.parsed_output
    log(f"Battle plan: {p.mode} — {p.topic} ({len(p.rounds)} rounds)")
    return p


# ---------- running + judging ----------

class Score(BaseModel):
    label: str
    scores: list[int] = Field(description="One integer 1-10 per criterion, same order as the criteria")
    reason: str = Field(description="Max 14 words: the single most important strength or flaw")


class RoundJudgement(BaseModel):
    results: list[Score]
    winner_label: str


def run_battle(cfg: dict, p: BattlePlan, contestants: list[dict]) -> list[dict]:
    rounds = []
    for i, rd in enumerate(p.rounds, 1):
        if p.mode == "prompts" and rd.variants:
            cols = [{"name": v.label, "prompt": v.prompt, "contestant": cfg["battle"]["prompt_mode_model"]} for v in rd.variants]
        else:
            cols = [{"name": c["name"], "prompt": rd.prompt, "contestant": c} for c in contestants]
        for col in cols:
            col["result"] = ask(col["contestant"], col["prompt"])
            log(f"Round {i} — {col['name']}: {col['result']['seconds']}s, {col['result']['words']} words")
        rounds.append({"name": rd.name, "prompt": rd.prompt, "criteria": rd.criteria, "columns": cols})
        judge(cfg, p, rounds[-1])
    return rounds


def judge(cfg: dict, p: BattlePlan, rnd: dict) -> None:
    """Blind judging: answers are shuffled and labelled A/B/C so the judge cannot see who wrote what."""
    cols = rnd["columns"][:]
    random.shuffle(cols)
    letters = "ABCDE"
    blind = {letters[i]: c for i, c in enumerate(cols)}
    answers = "\n\n".join(f"Answer {k}:\n{c['result']['text']}" for k, c in blind.items())
    task = rnd["prompt"] if p.mode == "models" else f"The job: {rnd['name']} for {p.business}"
    prompt = f"""You are a strict, fair judge for a small-business AI test. Score each answer 1-10 on each criterion:
{json.dumps(rnd['criteria'])}. Use the full range; a generic answer is a 5, not an 8. Penalise invented facts,
ignored constraints, wrong math and fluff. Judge the answer, not its length.
Task: {task}

{answers}"""
    r = anthropic.Anthropic().beta.messages.parse(
        model=cfg["claude"]["model"], max_tokens=8000, betas=BETAS, fallbacks="default",
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": prompt}], output_format=RoundJudgement)
    j = r.parsed_output
    for s in j.results:
        c = blind.get(s.label.strip().upper()[:1])
        if c:
            c["scores"] = [max(1, min(10, int(x))) for x in s.scores][: len(rnd["criteria"])]
            c["total"] = sum(c["scores"])
            c["reason"] = s.reason
    for c in rnd["columns"]:
        c.setdefault("scores", [0] * len(rnd["criteria"]))
        c.setdefault("total", 0)
        c.setdefault("reason", "")
    best = max(rnd["columns"], key=lambda c: c["total"])
    rnd["winner"] = best["name"]
    log(f"Round winner: {best['name']} ({best['total']})")


# ---------- commentary ----------

class RoundTalk(BaseModel):
    intro: str = Field(description="Narration while the round title and prompt appear: 2-3 sentences")
    answers: str = Field(description="Narration while answers type out: compare what each AI actually wrote, quote short real phrases. 4-6 sentences")
    scores: str = Field(description="Narration for the score reveal: who won the round and the one reason why. 2-3 sentences")


class Commentary(BaseModel):
    title: str = Field(description="YouTube title max 70 chars, curiosity + honesty, e.g. 'I Made 3 AIs Run a Plumbing Business. One Failed Badly.'")
    thumbnail_text: str = Field(description="2-4 words, e.g. 'WHO WINS?'")
    hook: str = Field(description="First 15 seconds of narration: stakes + surprising real result teaser, no 'in this video'. 2-3 sentences")
    contestants: str = Field(description="Narration introducing the contestants (or prompt styles) and the rules: blind judge, real answers, real timers. 2-3 sentences")
    rounds: list[RoundTalk]
    scoreboard: str = Field(description="Short narration over the running scoreboard after the last round. 1-2 sentences")
    verdict: str = Field(description="Final verdict: overall winner, best value pick, who should use which. 3-5 sentences")
    outro: str = Field(description="CTA: ask viewers which battle to run next in the comments + subscribe. 1-2 sentences")
    description: str = Field(description="YouTube description: what was tested, the method (same prompts, blind AI judge, real outputs), results table in text, 3 hashtags")
    tags: list[str]


def commentary(cfg: dict, p: BattlePlan, contestants: list[dict], rounds: list[dict]) -> Commentary:
    data = {"mode": p.mode, "business": p.business, "topic": p.topic,
            "contestants": [c["name"] for c in contestants] if p.mode == "models" else [c["name"] for c in rounds[0]["columns"]],
            "rounds": [{"name": r["name"], "prompt": r["prompt"], "criteria": r["criteria"], "winner": r["winner"],
                        "answers": [{"by": c["name"], "text": c["result"]["text"], "seconds": c["result"]["seconds"],
                                     "words": c["result"]["words"], "cost_usd": c["result"]["cost"],
                                     "scores": c["scores"], "total": c["total"], "judge_note": c["reason"]}
                                    for c in r["columns"]]} for r in rounds]}
    totals = {}
    for r in rounds:
        for c in r["columns"]:
            totals[c["name"]] = totals.get(c["name"], 0) + c["total"]
    prompt = f"""You are the host of "{cfg['channel']['name']}", a fast, witty, honest YouTube show where AIs compete on
real small-business tasks. Write the narration for this episode from the REAL results below.
Rules: only state facts that are in the data (answers, seconds, costs, scores). Quote short real phrases from the
answers. Be energetic and specific, short spoken sentences, light humour, no hype words like 'game-changer'.
Total narration about {cfg['battle']['target_words']} words. Exactly {len(rounds)} items in 'rounds'.
Final totals: {json.dumps(totals)}

DATA:
{json.dumps(data, ensure_ascii=False)}"""
    r = anthropic.Anthropic().beta.messages.parse(
        model=cfg["claude"]["model"], max_tokens=16000, betas=BETAS, fallbacks="default",
        output_config={"effort": cfg["claude"]["effort"]},
        messages=[{"role": "user", "content": prompt}], output_format=Commentary)
    t = r.parsed_output
    log(f"Commentary: '{t.title}'")
    return t
