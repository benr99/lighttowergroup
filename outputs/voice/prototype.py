#!/usr/bin/env python3
"""Prototype of the two-step voice engine on real cached stories.

brief (find the story) -> article (write in Ben's voice) -> gate (facts + voice layer).
Writes samples.json and samples.md beside this file. Needs DEEPSEEK_API_KEY.

Run: python prototype.py [slug fragment ...]
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "outputs" / "readability"))

import ben_voice as bv  # noqa: E402
import claim_verifier as cv  # noqa: E402
import v4_generation as v4  # noqa: E402
import voice_gate as vg  # noqa: E402
from accuracy_audit import load_objects  # noqa: E402
from measure import metrics  # noqa: E402
from model_router import provider_config  # noqa: E402

DEFAULT = ["tpg-ag-redfearn", "ejs-group-jv", "brookfield-asset", "feds-cook", "uwm-2-05b", "tishman-speyer"]


def chat(provider, system, user, temperature, *, thinking=False, max_tokens=6000):
    payload = {"model": provider["model"], "temperature": temperature, "max_tokens": max_tokens,
               "response_format": {"type": "json_object"},
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if provider["provider"] == "deepseek":
        payload["thinking"] = {"type": "enabled" if thinking else "disabled"}
    for attempt in range(4):
        try:
            r = requests.post(provider["url"], headers={"Authorization": f"Bearer {provider['api_key']}",
                              "Content-Type": "application/json"}, json=payload, timeout=240)
        except requests.RequestException:
            time.sleep(3 * (attempt + 1)); continue
        if r.status_code in (429, 500, 502, 503):
            time.sleep(4 * (attempt + 1)); continue
        r.raise_for_status()
        return str(r.json()["choices"][0]["message"]["content"]).strip()
    raise RuntimeError("provider unavailable")


def parse(raw):
    t = raw.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I | re.S).strip()
    return json.loads(t)


def run(story, provider, verifier, *, context=None, notes=None):
    obj = story["obj"]
    dossier = v4._safe_dossier(obj)
    sources_json = json.dumps(dossier, ensure_ascii=False, separators=(",", ":"))
    source_text = cv.source_text_from_dossier(dossier)
    spec = v4.DEPTH_SPEC[story["tier"]]
    system = bv.system_prompt()
    out = {"slug": story["slug"], "tier": story["tier"]}

    brief = parse(chat(provider, system, bv.brief_prompt(obj.title, story["tier"], sources_json), 0.7))
    out["brief"] = brief
    prompt = bv.article_prompt(story=obj.title, fmt=spec["format"], min_words=spec["min_words"], max_words=spec["max_words"],
                               brief=brief, sources_json=sources_json, context=context, notes=notes)
    best = None
    feedback = ""
    for attempt in range(2):
        note = ("\n\nYour previous draft was checked. These sentences were rejected and deleted. Write a complete "
                "replacement in the same JSON shape. Keep every fact plain and single-claim, put all colour in "
                "separate take/voice sentences, and copy quotes exactly.\n" + feedback) if feedback else ""
        attempt_prompt = prompt + note
        try:
            draft = parse(chat(provider, system, attempt_prompt, 0.7))
            vd = vg.verify_voice_draft(draft, source_text, verifier, context=context, notes=notes)
        except Exception as exc:  # noqa: BLE001
            out["draft_error"] = f"{type(exc).__name__}: {exc}"[:160]
            continue
        score = (vd.fact_count + 2 * vd.take_count + vd.voice_count) - len(vd.rejected)
        if best is None or score > best[0]:
            best = (score, draft, vd)
        rejected = len(vd.rejected)
        total = rejected + vd.fact_count + vd.take_count + vd.voice_count
        if rejected <= max(2, 0.2 * total) and vd.take_count >= 1:
            break
        feedback = "\n".join(f"- [{i.kind}] {i.text[:140]} <- {i.reason[:140]}" for i in vd.rejected[:14])
    if best is None:
        return out
    _, draft, vd = best
    out["draft"] = draft
    out["attempts"] = attempt + 1
    paras = vd.text_paragraphs()
    out["verified"] = {
        "title": vd.title if vd.title_ok else obj.title, "excerpt": vd.excerpt if vd.excerpt_ok else "",
        "paragraphs": [{"role": r, "items": [{"kind": i.kind, "text": i.text} for i in its]} for r, its in vd.paragraphs],
        "facts": vd.fact_count, "takes": vd.take_count, "voice": vd.voice_count,
        "rejected": [{"kind": i.kind, "text": i.text[:160], "why": i.reason[:200]} for i in vd.rejected],
        "metrics": metrics(paras, vd.title, vd.excerpt) if paras else {},
    }
    return out


def to_markdown(results):
    lines = ["# Voice engine prototype samples\n"]
    for r in results:
        v = r.get("verified")
        lines.append(f"\n---\n\n## {r['slug']} ({r['tier']})\n")
        b = r.get("brief", {})
        lines.append(f"**Brief:** shape *{b.get('shape')}*, lens *{b.get('lens')}*. Protagonist: {b.get('protagonist')}. Tension: {b.get('tension')}\n")
        if not v:
            lines.append(f"_no verified draft ({r.get('draft_error')})_"); continue
        lines.append(f"### {v['title']}\n*{v['excerpt']}*\n")
        for p in v["paragraphs"]:
            lines.append(" ".join(("" if i["kind"] == "fact" else f"[{i['kind']}] ") + i["text"] for i in p["items"]) + "\n")
        m = v["metrics"]
        lines.append(f"\n_facts {v['facts']} · takes {v['takes']} · voice {v['voice']} · rejected {len(v['rejected'])} · "
                     f"{m.get('words')} words · {m.get('words_per_sentence_mean')} w/sentence · grade {m.get('fk_grade')}_\n")
        for x in v["rejected"][:6]:
            lines.append(f"- rejected {x['kind']}: {x['text']} ← {x['why']}")
    return "\n".join(lines)


def main():
    frags = sys.argv[1:] or DEFAULT
    provider = provider_config("deepseek", for_writing=True)
    verifier = v4._make_verifier(provider)
    stories = [s for s in load_objects() if any(f in s["slug"] for f in frags)]
    print(f"{len(stories)} stories")
    results = []
    for s in stories:
        t = time.time()
        try:
            res = run(s, provider, verifier, context=bv.load_bank("context-bank.json"), notes=bv.load_bank("ben-notes.json"))
        except Exception as exc:  # noqa: BLE001
            res = {"slug": s["slug"], "tier": s["tier"], "draft_error": f"{type(exc).__name__}: {exc}"[:200]}
        v = res.get("verified")
        print(f"- {s['slug'][:40]:40s} {round(time.time() - t)}s " + (f"facts {v['facts']} takes {v['takes']} voice {v['voice']} rejected {len(v['rejected'])}" if v else res.get("draft_error", "")))
        results.append(res)
    (HERE / "samples.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "samples.md").write_text(to_markdown(results), encoding="utf-8")


if __name__ == "__main__":
    main()
