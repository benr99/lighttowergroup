"""Ben Rohr's voice: prompts, story shapes and the banks the writer may draw on.

The prompt text lives in ``docs/voice/prompts/*.txt`` so it can be read and edited
without touching code. This module loads it and fills the templates.

Two banks keep depth honest. The writer is not allowed to reach for history,
culture or personal experience from memory:

* ``docs/voice/context-bank.json``: cultural, historical and macro context that a
  person has verified once, each entry with a source. The writer cites an id; the
  sentence may say nothing beyond the entry.
* ``docs/voice/ben-notes.json``: real experiences Ben supplies. First-person
  experience claims are only allowed when an entry backs them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VOICE_DIR = ROOT / "docs" / "voice"
PROMPT_DIR = VOICE_DIR / "prompts"

VOICE_PROMPT_VERSION = "voice-3-rehearsal-fixes"

LENSES = (
    "capital cycle", "time and patience", "trust and institutions", "home and belonging",
    "status and ambition", "work and cities", "power and politics", "technology and land",
    "climate and risk", "demographic change",
)

# name -> (when it fits, beats). Each shape is a way to arrange the same verified facts.
SHAPES: dict[str, tuple[str, str]] = {
    "The Number That Doesn't Fit": (
        "a figure contradicts the obvious reading (a price, rate, occupancy or spread that surprises)",
        "hook on the odd number; what the number means for a person; the obvious reading; the turn (what the number says instead); why it matters beyond this deal; kicker returns to the number",
    ),
    "The Clock": (
        "a maturity, deadline, rate lock, vote or construction window shapes every choice",
        "hook on the date or deadline; who is running out of time; the options each side had; the turn (what time cost or bought); the pattern; kicker asks what happens when the clock runs out",
    ),
    "The Price Tells the Truth": (
        "what someone paid or lent says more than what anyone said",
        "hook on the price or basis; who paid or lent and against what; the story the press release told; the turn (what the price admits); the pattern; kicker is the testable question",
    ),
    "Who Blinked": (
        "two parties wanted opposite things and one gave ground",
        "hook on the concession; what each side needed; the leverage; the turn (who really held the cards); what it signals; kicker on the next negotiation",
    ),
    "The Building as Character": (
        "a place, with a physical history the sources describe, is the subject",
        "hook on a physical detail from the sources; what the place has been and is asked to become; the capital it takes; the turn (what the building shows about its neighbourhood or era); meaning; kicker returns to the detail",
    ),
    "The Quiet Signal": (
        "a small deal that may be an early sign of something larger",
        "hook on the small, specific deal; why it is easy to miss; the turn (what it may be an early sign of, offered carefully); the evidence; the limits; kicker is what to watch",
    ),
    "The Rule Changed": (
        "a policy, ruling or regulation reallocates who wins and loses",
        "hook on the rule and the person it lands on; what changed; who gains, who pays, who waits; the turn (the second-order effect); the pattern; kicker on the next test",
    ),
    # The next two come from Codex's July voice modes ("lender's-eye memorandum" and "underwriting margin").
    "The Lender's Question": (
        "a loan, refinancing or credit decision where the terms the sources give answer a hard question",
        "hook on the loan term that matters; the question a credit committee would ask, as a voice line; the facts that answer it; the turn (what the terms protect against); who carries the risk; kicker is the question the reader should ask their own lender",
    ),
    "What Has to Be True": (
        "a purchase, development or recapitalisation whose plan depends on something the sources state (a lease-up, a rate, a completion date)",
        "hook on the plan's key number; what the sources say the plan needs; the turn (a take on what has to hold for it to work, framed as a reading); the evidence for and against in the sources; kicker on the date or figure that will settle it",
    ),
    "The Ritual": (
        "the deal reveals what people value: status, ownership, belonging, legacy",
        "hook on the human act; what the transaction is really about; what the numbers cannot show; the turn (the cultural reading, offered as a reading); meaning; kicker leaves one honest question",
    ),
}


def _read(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def system_prompt() -> str:
    return _read("system.txt")


def shapes_menu() -> str:
    return "\n".join(f"   - {name}: {when}" for name, (when, _) in SHAPES.items())


def shape_guide(name: str) -> str:
    when, beats = SHAPES.get(name) or next(iter(SHAPES.values()))
    return f"{name}. Use it when {when}. Beats: {beats}."


def _fill(template: str, **values: Any) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def load_bank(filename: str) -> list[dict[str, Any]]:
    path = VOICE_DIR / filename
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    entries = data.get("entries") if isinstance(data, dict) else data
    return [e for e in (entries or []) if isinstance(e, dict) and e.get("id") and e.get("text")]


def banks_block(context: list[dict[str, Any]], notes: list[dict[str, Any]]) -> str:
    """The text the writer sees for the two banks. Empty banks are stated plainly."""
    ctx = "\n".join(f'- {e["id"]}: {e["text"]}' for e in context) or "(none supplied: do not use any outside history or context)"
    nts = "\n".join(f'- {e["id"]}: {e["text"]}' for e in notes) or "(none supplied: make no experience claims)"
    return f"CONTEXT BANK (approved, cite by id with kind \"context\"):\n{ctx}\n\nBEN'S NOTES (real experiences, cite by id with kind \"ben\"):\n{nts}"


def brief_prompt(story: str, depth: str, sources_json: str) -> str:
    return _fill(_read("brief.txt"), STORY=story, DEPTH=depth, SOURCES=sources_json, SHAPES=shapes_menu())


def article_prompt(
    *, story: str, fmt: str, min_words: int, max_words: int, brief: dict[str, Any], sources_json: str,
    context: list[dict[str, Any]] | None = None, notes: list[dict[str, Any]] | None = None,
) -> str:
    target = (min_words + max_words) // 2
    flagship = fmt == "flagship"
    return _fill(
        _read("article.txt"),
        STORY=story, FORMAT=fmt, TARGET=target, MIN=min_words, MAX=max_words,
        BRIEF=json.dumps(brief, ensure_ascii=False, indent=1),
        SHAPE_GUIDE=shape_guide(str(brief.get("shape") or "")),
        SOURCES=sources_json, BANKS=banks_block(context or [], notes or []),
        MAX_TAKES=4 if flagship else 3, MAX_VOICE=3 if flagship else 2,
    )
