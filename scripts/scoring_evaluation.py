"""
Scoring evaluation: compare deterministic and LLM scoring systems.

Usage:  python scripts/scoring_evaluation.py
Output: data/scoring-evaluation.json + stdout report.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
RUNS_DIR = SITE_ROOT / "data" / "editorial_runs"
OUTPUT_PATH = SITE_ROOT / "data" / "scoring-evaluation.json"


def _pearson_r(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2 or len(ys) != n:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom = math.sqrt(
        sum((x - mean_x) ** 2 for x in xs)
        * sum((y - mean_y) ** 2 for y in ys)
    )
    if denom == 0:
        return 0.0
    return num / denom


def _load_editorial_runs() -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    if not RUNS_DIR.is_dir():
        return runs
    for path in sorted(RUNS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            runs.append(data)
    return runs


def main() -> None:
    runs = _load_editorial_runs()
    det_scores: list[float] = []
    llm_scores: list[float] = []
    score_pairs: list[dict[str, Any]] = []

    for run in runs:
        candidates = run.get("scored_candidates") or []
        for c in candidates:
            det = c.get("deterministic_score")
            llm = c.get("model_score") or c.get("score")
            if det is not None and llm is not None:
                try:
                    det_val = float(det)
                    llm_val = float(llm)
                except (ValueError, TypeError):
                    continue
                det_scores.append(det_val)
                llm_scores.append(llm_val)
                score_pairs.append({
                    "index": c.get("index"),
                    "title": (c.get("candidate") or {}).get("title", ""),
                    "date": run.get("date") or run.get("today", ""),
                    "deterministic_score": det_val,
                    "llm_score": llm_val,
                })

    if not det_scores:
        print("=" * 60)
        print("  SCORING EVALUATION")
        print("=" * 60)
        print("  Insufficient data — run the pipeline in")
        print("  shadow mode with --save-scores flag first.")
        print("=" * 60)

        output = {
            "status": "insufficient_data",
            "message": (
                "No scored candidates with both deterministic_score and "
                "model_score found in editorial runs. Run the pipeline in "
                "shadow mode with --save-scores flag first."
            ),
            "pairs_found": 0,
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(
            json.dumps(output, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"  Report saved to: {OUTPUT_PATH}")
        return

    pearson = _pearson_r(det_scores, llm_scores)

    det_publish = sum(1 for s in det_scores if s >= 56)
    llm_publish = sum(1 for s in llm_scores if s >= 70)
    both_publish = sum(
        1 for d, m in zip(det_scores, llm_scores) if d >= 56 and m >= 70
    )
    both_reject = sum(
        1 for d, m in zip(det_scores, llm_scores) if d < 56 and m < 70
    )
    agreement_pct = (
        (both_publish + both_reject) / len(det_scores) * 100
    )

    det_only_publish = sum(
        1 for d, m in zip(det_scores, llm_scores) if d >= 56 and m < 70
    )
    llm_only_publish = sum(
        1 for d, m in zip(det_scores, llm_scores) if d < 56 and m >= 70
    )

    if pearson is not None and pearson >= 0.50:
        recommendation = (
            "Moderate to strong correlation between deterministic and LLM "
            "scores. The LLM scoring layer adds signal beyond the deterministic "
            "baseline. Retain LLM scoring but continue periodic evaluation."
        )
    elif pearson is not None and pearson >= 0.30:
        recommendation = (
            "Weak to moderate correlation. LLM scoring provides some additional "
            "signal but may increase volatility. Consider widening the blending "
            "window or reducing LLM weight in the blended score."
        )
    elif pearson is not None:
        recommendation = (
            "Low correlation between deterministic and LLM scores. The LLM "
            "scoring layer may be adding noise rather than signal. Consider "
            "increasing reliance on deterministic scoring or recalibrating "
            "the LLM scoring prompt."
        )
    else:
        recommendation = (
            f"Agreement rate: {agreement_pct:.1f}% on publish/don't-publish "
            f"decisions. Review the disagreement cases to determine whether "
            f"LLM scoring is catching important signal the deterministic "
            f"layer misses."
        )

    output = {
        "total_pairs": len(det_scores),
        "pearson_r": round(pearson, 4) if pearson is not None else None,
        "agreement_pct": round(agreement_pct, 1),
        "both_publish": both_publish,
        "both_reject": both_reject,
        "det_only_publish": det_only_publish,
        "llm_only_publish": llm_only_publish,
        "det_mean": round(sum(det_scores) / len(det_scores), 2),
        "llm_mean": round(sum(llm_scores) / len(llm_scores), 2),
        "recommendation": recommendation,
        "score_pairs": score_pairs,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print("=" * 60)
    print("  SCORING EVALUATION")
    print("=" * 60)
    print(f"  Candidate pairs evaluated:        {len(det_scores)}")
    if pearson is not None:
        print(f"  Pearson correlation:              {pearson:.4f}")
    print(f"  Agreement (publish/don't-publish): {agreement_pct:.1f}%")
    print(f"  Both publish:                     {both_publish}")
    print(f"  Both reject:                      {both_reject}")
    print(f"  Deterministic only publish:       {det_only_publish}")
    print(f"  LLM only publish:                 {llm_only_publish}")
    print(f"  Deterministic score mean:         {sum(det_scores)/len(det_scores):.1f}")
    print(f"  LLM score mean:                   {sum(llm_scores)/len(llm_scores):.1f}")
    print("-" * 60)
    print(f"  Recommendation: {recommendation}")
    print("=" * 60)
    print(f"  Report saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
