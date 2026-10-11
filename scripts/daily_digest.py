#!/usr/bin/env python3
"""Build the daily digest and health note from one run's folder.

The digest is the page Ben reads to check a day's work: every published sentence
beside the source quote it rests on, the opinion lines and the facts they cite,
and everything the checker cut, with the reason. The health note is the same day
in five lines. Both are built offline from files the pipeline already writes:

    <run>/v3-run.json        the run report (counts, spend, warnings, errors)
    <run>/v3-drafts.json     every story's outcome, including withheld and skipped
    <run>/v4-evidence/*.json one file per published story: kept and cut sentences

Usage:  python daily_digest.py <run folder> [--out <folder>]
Writes: digest.html and health.txt into --out (default: the run folder).
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

KIND_LABEL = {"fact": "Fact", "take": "Ben's read", "voice": "Voice", "context": "Context", "ben": "Ben's note"}


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_run(run_dir: Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    report = _load(run_dir / "v3-run.json") or {}
    drafts = (_load(run_dir / "v3-drafts.json") or {}).get("drafts", [])
    evidence = []
    for path in sorted((run_dir / "v4-evidence").glob("*.json")):
        data = _load(path)
        if isinstance(data, dict):
            evidence.append(data)
    def text(name: str) -> str:
        try:
            return (run_dir / name).read_text(encoding="utf-8")
        except OSError:
            return ""
    return {"report": report, "drafts": drafts, "evidence": evidence,
            "linkedin": text("linkedin-post.txt"), "linkedin_comment": text("linkedin-comment.txt")}


def summary(run: dict[str, Any]) -> dict[str, Any]:
    report, drafts = run["report"], run["drafts"]
    generation = report.get("generation") or {}
    spend = report.get("spend") or {}
    counts = {status: sum(1 for d in drafts if d.get("status") == status)
              for status in ("completed", "withheld", "skipped", "failed")}
    voiced = sum(1 for d in drafts if (d.get("article") or {}).get("voice") == "ben")
    kept = cut = takes = 0
    for ev in run["evidence"]:
        for para in ev.get("paragraphs") or []:
            for item in para:
                kept += 1
                takes += item.get("kind") == "take"
        cut += len(ev.get("rejected") or [])
    problems = list(report.get("errors") or [])
    if generation.get("stop_reason"):
        problems.append(f"writing stopped early: {generation['stop_reason']}")
    if counts["failed"]:
        problems.append(f"{counts['failed']} stor{'y' if counts['failed'] == 1 else 'ies'} failed")
    return {
        "date": str(report.get("run_at") or "")[:10], "mode": report.get("mode", ""),
        "written": counts["completed"], "voiced": voiced, "withheld": counts["withheld"],
        "skipped": counts["skipped"], "failed": counts["failed"],
        "selected": report.get("publication_candidates", len(drafts)),
        "sentences_kept": kept, "sentences_cut": cut, "takes_kept": takes,
        "spend_run": float(spend.get("spent_this_run_usd") or generation.get("spend_usd") or 0.0),
        "spend_today": float(spend.get("spent_today_usd") or 0.0),
        "spend_cap": float(spend.get("daily_limit_usd") or 0.0),
        "minutes": round(float(report.get("elapsed_seconds") or 0.0) / 60, 1),
        "warnings": list(report.get("warnings") or []),
        "problems": problems,
        "status": "NEEDS A LOOK" if problems else "OK",
    }


def health_note(run: dict[str, Any]) -> str:
    s = summary(run)
    lines = [
        f"Light Tower daily health: {s['date']} ({s['mode']})  {s['status']}",
        f"Stories: {s['written']} written ({s['voiced']} in Ben's voice), {s['withheld']} withheld as "
        f"unverifiable, {s['skipped']} skipped, {s['failed']} failed, of {s['selected']} selected",
        f"Checker: {s['sentences_kept']} sentences kept ({s['takes_kept']} opinion lines), {s['sentences_cut']} cut",
        f"Spend: ${s['spend_run']:.2f} this run, ${s['spend_today']:.2f} today of a ${s['spend_cap']:.2f} cap",
        f"Time: {s['minutes']} minutes",
    ]
    lines += [f"Problem: {p}" for p in s["problems"]]
    lines += [f"Note: {w}" for w in s["warnings"][:6]]
    return "\n".join(lines) + "\n"


def _e(text: Any) -> str:
    return html.escape(str(text or ""), quote=True)


def _story(ev: dict[str, Any]) -> str:
    rows = []
    for para in ev.get("paragraphs") or []:
        for item in para:
            kind = str(item.get("kind") or "fact")
            support = item.get("quotes") or []
            if kind == "take":
                cited = item.get("because_text") or []
                support_html = ('<span class="muted">Ben\'s reading of these published facts:</span>'
                                + "".join(f"<blockquote>{_e(t)}</blockquote>" for t in cited)) if cited else \
                    f'<span class="muted">rests on {_e(", ".join(item.get("because") or []))}</span>'
            elif kind == "voice":
                support_html = '<span class="muted">a reaction or transition; states no fact</span>'
            else:
                support_html = "".join(f"<blockquote>{_e(q)}</blockquote>" for q in support) or \
                    '<span class="muted">no quote</span>'
            rows.append(f'<tr><td><span class="kind k-{_e(kind)}">{_e(KIND_LABEL.get(kind, kind))}</span></td>'
                        f"<td>{_e(item.get('text'))}</td><td>{support_html}</td></tr>")
        rows.append('<tr class="gap"><td colspan="3"></td></tr>')
    cut = "".join(
        f'<li><span class="kind k-{_e(r.get("kind"))}">{_e(KIND_LABEL.get(r.get("kind"), r.get("kind")))}</span> '
        f"{_e(r.get('text'))}<div class=\"why\">{_e(r.get('reason'))}</div></li>"
        for r in ev.get("rejected") or [])
    sources = " · ".join(f'<a href="{_e(u)}">{_e(u.split("/")[2] if "//" in u else u)}</a>'
                         for u in ev.get("sources") or [])
    mode = "Ben's voice" if ev.get("mode") == "voice" else "Facts only"
    return f"""<section class="story">
<h2>{_e(ev.get('title'))}</h2>
<p class="meta">{_e(ev.get('sector', '').replace('_', ' '))} · {_e(ev.get('depth', ''))} · {mode} · {sources}</p>
<p class="excerpt">{_e(ev.get('excerpt'))}</p>
<table><thead><tr><th>Kind</th><th>Published sentence</th><th>What it rests on</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<details><summary>{len(ev.get('rejected') or [])} sentences cut by the checker</summary><ul class="cut">{cut or '<li>none</li>'}</ul></details>
</section>"""


def _linkedin(run: dict[str, Any]) -> str:
    post, comment = run.get("linkedin") or "", run.get("linkedin_comment") or ""
    if not post:
        return ""
    return f"""<section class="story linkedin">
<h2>Today's LinkedIn post</h2>
<p class="muted">Every line was checked again against the stories' verified sentences. Paste the post, then the first comment.</p>
<button type="button" onclick="navigator.clipboard.writeText(document.getElementById('li-post').textContent)">Copy post</button>
<pre id="li-post">{_e(post)}</pre>
<button type="button" onclick="navigator.clipboard.writeText(document.getElementById('li-comment').textContent)">Copy first comment</button>
<pre id="li-comment">{_e(comment)}</pre>
</section>"""


def digest_html(run: dict[str, Any]) -> str:
    s = summary(run)
    others = [d for d in run["drafts"] if d.get("status") != "completed"]
    other_rows = "".join(
        f"<li><b>{_e(d.get('status'))}</b>: {_e(d.get('title'))}"
        f"<div class=\"why\">{_e(d.get('skipped_reason') or '; '.join(d.get('errors') or []))}</div></li>"
        for d in others)
    notes = "".join(f"<li>{_e(x)}</li>" for x in s["problems"] + s["warnings"])
    stories = "".join(_story(ev) for ev in run["evidence"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Digest {_e(s['date'])}</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e4e1d8; --card:#fff;
  --fact:#e8f0e6; --take:#f6ead7; --voice:#e9e7f3; --bad:#b3261e; --ok:#2e6b3a; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#161614; --fg:#ecebe6; --muted:#a3a19a; --line:#34332f;
  --card:#1f1e1b; --fact:#22311f; --take:#3a2e1c; --voice:#2a2838; --bad:#f2b8b5; --ok:#9fd5a8; }} }}
body {{ background:var(--bg); color:var(--fg); font:16px/1.5 Georgia, 'Times New Roman', serif; margin:0; }}
main {{ max-width:1080px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ font-size:28px; margin:0 0 4px; }} h2 {{ font-size:21px; margin:0 0 4px; }}
.status {{ font:600 13px system-ui, sans-serif; padding:2px 8px; border-radius:4px; }}
.s-OK {{ color:var(--ok); border:1px solid var(--ok); }} .s-NEEDS {{ color:var(--bad); border:1px solid var(--bad); }}
.numbers {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:8px; margin:16px 0; }}
.numbers div {{ background:var(--card); border:1px solid var(--line); border-radius:6px; padding:10px; font-family:system-ui, sans-serif; }}
.numbers b {{ display:block; font-size:22px; }}
.story {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:16px; margin:20px 0; }}
.meta, .muted, .why {{ color:var(--muted); font:13px system-ui, sans-serif; }}
.excerpt {{ font-style:italic; }}
table {{ width:100%; border-collapse:collapse; font-size:15px; }}
th {{ text-align:left; font:600 12px system-ui, sans-serif; color:var(--muted); border-bottom:1px solid var(--line); padding:6px; }}
td {{ vertical-align:top; padding:6px; border-bottom:1px solid var(--line); }}
td:nth-child(2) {{ width:45%; }} tr.gap td {{ border:0; padding:2px; }}
blockquote {{ margin:0 0 4px; padding-left:8px; border-left:3px solid var(--line); font-size:14px; }}
.kind {{ font:600 11px system-ui, sans-serif; padding:2px 6px; border-radius:4px; white-space:nowrap; }}
.k-fact {{ background:var(--fact); }} .k-take {{ background:var(--take); }} .k-voice {{ background:var(--voice); }}
pre {{ white-space:pre-wrap; font:15px/1.5 system-ui, sans-serif; background:var(--bg); border:1px solid var(--line); border-radius:6px; padding:12px; }}
button {{ font:600 13px system-ui, sans-serif; padding:6px 12px; border-radius:6px; border:1px solid var(--line); background:var(--card); color:var(--fg); cursor:pointer; }}
details {{ margin-top:10px; font-size:14px; }} .cut li {{ margin:6px 0; }}
@media (max-width:640px) {{ table, thead, tbody, tr, td {{ display:block; width:auto !important; }} thead {{ display:none; }}
  td {{ border:0; padding:2px 0; }} tr {{ border-bottom:1px solid var(--line); padding:6px 0; }} }}
</style></head><body><main>
<h1>Daily digest: {_e(s['date'])} <span class="status s-{s['status'].split()[0]}">{_e(s['status'])}</span></h1>
<p class="muted">Mode: {_e(s['mode'])}. Every published sentence is shown beside the source quote it rests on.
Opinion lines show the facts they cite. Everything the checker cut is listed under each story.</p>
<div class="numbers">
<div><b>{s['written']}</b>written</div><div><b>{s['voiced']}</b>in Ben's voice</div>
<div><b>{s['withheld']}</b>withheld</div><div><b>{s['skipped'] + s['failed']}</b>skipped or failed</div>
<div><b>{s['sentences_kept']}</b>sentences kept</div><div><b>{s['sentences_cut']}</b>sentences cut</div>
<div><b>${s['spend_run']:.2f}</b>spent</div><div><b>{s['minutes']}</b>minutes</div></div>
{_linkedin(run)}
{f'<h3>Notes</h3><ul>{notes}</ul>' if notes else ''}
{stories or '<p>No stories were published in this run.</p>'}
{f'<h3>Not published</h3><ul class="cut">{other_rows}</ul>' if other_rows else ''}
</main></body></html>
"""


def build(run_dir: Path, out_dir: Path | None = None) -> tuple[Path, Path]:
    run = load_run(run_dir)
    out = Path(out_dir or run_dir)
    out.mkdir(parents=True, exist_ok=True)
    digest, health = out / "digest.html", out / "health.txt"
    digest.write_text(digest_html(run), encoding="utf-8")
    health.write_text(health_note(run), encoding="utf-8")
    return digest, health


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    digest, health = build(args.run_dir, args.out)
    print(health.read_text(encoding="utf-8"), end="")
    print(f"Digest: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
