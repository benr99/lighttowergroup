#!/usr/bin/env python3
"""Audit a rehearsal (or any v4 run folder) after the fact.

For every published story in <run>/v4-evidence/: rebuild the exact source text the writer
saw from <run>/v3-candidates.json, then
  1. re-check deterministically that every fact quote is verbatim in the source and every
     figure in the sentence appears in its quotes;
  2. have an independent reasoning pass (fresh prompt, no knowledge of the gate's verdict)
     judge every kept fact sentence against the source;
  3. print every opinion ("take") and "voice" line beside the facts it cites, for a human read.

Run: python rehearsal_audit.py <run folder>
Writes <run>/audit.json and prints a summary.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))

import claim_verifier as cv  # noqa: E402
import v4_generation as v4  # noqa: E402
from accuracy_audit import audit, auditor  # noqa: E402
from intelligence_object import IntelligenceObject  # noqa: E402
from model_router import provider_config  # noqa: E402
from readability import unsupported_numbers  # noqa: E402


def main() -> int:
    run = Path(sys.argv[1])
    from model_router import configure_state_dir
    configure_state_dir(run)  # provider diagnostics stay with the run, never in the repository
    candidates = json.loads((run / "v3-candidates.json").read_text(encoding="utf-8"))["candidates"]
    by_id = {c["object_id"]: c for c in candidates}
    llm = auditor(provider_config("deepseek", for_writing=True))
    stories = []
    for path in sorted((run / "v4-evidence").glob("*.json")):
        ev = json.loads(path.read_text(encoding="utf-8"))
        obj = IntelligenceObject.from_dict(by_id[ev["object_id"]])
        source = cv.source_text_from_dossier(v4._safe_dossier(obj))
        stories.append((ev, source))

    def one(pair):
        ev, source = pair
        items = [i for p in ev["paragraphs"] for i in p]
        facts = [i for i in items if i["kind"] == "fact"]
        mechanical = []
        for f in facts:
            for q in f.get("quotes") or []:
                if not cv.quote_in_source(q, source):
                    mechanical.append(f"quote not in source: {q[:90]}")
            extra = unsupported_numbers(f["text"], " ".join(f.get("quotes") or []))
            if extra:
                mechanical.append(f"figures not in quotes {extra}: {f['text'][:90]}")
        flagged = audit([f["text"] for f in facts], source, {"auditor": llm})
        views = [{"kind": i["kind"], "text": i["text"], "rests_on": i.get("because_text", [])}
                 for i in items if i["kind"] != "fact"]
        return {"title": ev["title"], "mode": ev.get("mode"), "facts": len(facts), "cut": len(ev.get("rejected") or []),
                "mechanical": mechanical, "flagged": flagged, "views": views}

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(one, stories))
    (run / "audit.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    total = sum(r["facts"] for r in results)
    flagged = sum(len(r["flagged"]) for r in results)
    mech = sum(len(r["mechanical"]) for r in results)
    print(f"{len(results)} stories, {total} kept fact sentences: {mech} mechanical problems, {flagged} flagged by the auditor")
    for r in results:
        print(f"\n## {r['title']} ({r['mode']}; {r['facts']} facts kept, {r['cut']} cut)")
        for m in r["mechanical"]:
            print("  MECHANICAL:", m)
        for text, why in r["flagged"].items():
            print("  FLAGGED:", text, "<-", "; ".join(why))
        for v in r["views"]:
            print(f"  [{v['kind']}] {v['text']}")
            for f in v["rests_on"]:
                print(f"        rests on: {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
