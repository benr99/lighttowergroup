#!/usr/bin/env python3
"""Independent audit of a preview run's kept sentences.

Reads a run's state directory (``--state-dir`` of insights_v3.py): the drafts, the
per-article evidence files, and the candidates (which carry each source's retrieved
text). Every kept fact sentence is re-checked against its sources by a reasoning-mode
model with the strict fact rules. Writes ``preview_audit.json`` into the state dir.

Run: python outputs/readability/audit_preview.py <state_dir>
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))

from accuracy_audit import audit, auditor  # noqa: E402
from model_router import provider_config  # noqa: E402


def main() -> None:
    state = Path(sys.argv[1])
    drafts = json.loads((state / "v3-drafts.json").read_text(encoding="utf-8"))["drafts"]
    candidates = {c["object_id"]: c for c in json.loads((state / "v3-candidates.json").read_text(encoding="utf-8"))["candidates"]}
    evidence = {}
    for path in (state / "v4-evidence").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        evidence[data["object_id"]] = data

    statuses = Counter(d.get("status") for d in drafts)
    print("draft outcomes:", dict(statuses))
    for d in drafts:
        diag = d.get("diagnostics") or {}
        print(f"  - {d.get('status'):9s} {d.get('depth') or '':6s} {str(d.get('title'))[:70]}"
              + (f"  [{d.get('skipped_reason')}]" if d.get("skipped_reason") else "")
              + (f"  errors={d.get('errors')}" if d.get("errors") else "")
              + (f"  fact_check={diag.get('fact_check')}" if diag.get("fact_check") else ""))

    ds = provider_config("deepseek", for_writing=True)
    if not ds:
        sys.exit("Needs DEEPSEEK_API_KEY.")
    auditors = {"deepseek-reasoning-audit": auditor(ds)}
    results = []
    for oid, ev in evidence.items():
        obj = candidates.get(oid)
        if not obj:
            print(f"  ! no candidate record for {oid}")
            continue
        source = "\n\n".join(f"[Source {n}: {s.get('source_name', '')}]\n{(s.get('retrieved_text') or '')[:5000]}"
                             for n, s in enumerate(obj.get("sources") or [], 1) if s.get("retrieved_text"))
        facts = [i["text"] for p in ev["paragraphs"] for i in p if i.get("kind") == "fact"]
        flagged = audit(facts, source, auditors) if facts else {}
        results.append({"object_id": oid, "title": ev.get("title"), "facts": len(facts),
                        "rejected_by_gate": len(ev.get("rejected") or []), "flagged": flagged})
        print(f"  audit {ev.get('title', '')[:60]!r}: {len(facts)} facts kept, {len(flagged)} flagged")
        for sentence, why in flagged.items():
            print(f"      FLAG: {sentence[:150]}  <- {why[0][:150]}")
    total = sum(r["facts"] for r in results)
    flagged = sum(len(r["flagged"]) for r in results)
    print(f"\nkept fact sentences audited: {total}; flagged: {flagged}")
    (state / "preview_audit.json").write_text(json.dumps({"outcomes": dict(statuses), "articles": results},
                                                         indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
