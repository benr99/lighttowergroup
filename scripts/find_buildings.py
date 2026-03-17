#!/usr/bin/env python3
"""
Light Tower Group — Qualifying Building Finder
───────────────────────────────────────────────
Scans NYC PLUTO + ACRIS to find free-market multifamily buildings in
Manhattan and Brooklyn matching ALL criteria:

  1. Free-market multifamily (elevator apartment, post-1990 construction)
  2. 100+ residential units
  3. Built 1990 or later
  4. Outstanding mortgage likely maturing 2026–2028

Maturity logic: mortgages filed 2016–2023 with typical 5/7/10-year terms
would mature 2021–2033. The intersection with our 2026–2028 window:
  - 5-year term  → filed 2021–2023
  - 7-year term  → filed 2019–2021
  - 10-year term → filed 2016–2018
We search 2016–2023 and exclude buildings where a satisfaction was
filed in 2024 or later (debt already retired).

Output: qualified_buildings.txt  →  feed to generate_building.py --batch

Usage:
  python find_buildings.py
  python find_buildings.py --limit 100   # cap results for a test run
  python find_buildings.py --borough manhattan
  python find_buildings.py --borough brooklyn
"""

import requests
import json
import time
import os
import sys
import argparse
from pathlib import Path
from datetime import date

# ── Load .env ─────────────────────────────────────────────────────────────────
_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Config ────────────────────────────────────────────────────────────────────
PLUTO_API    = "https://data.cityofnewyork.us/resource/64uk-42ks.json"
ACRIS_LEGALS = "https://data.cityofnewyork.us/resource/8h5j-fqxa.json"
ACRIS_MASTER = "https://data.cityofnewyork.us/resource/bnx9-e6tj.json"

SCRIPT_DIR   = Path(__file__).parent

# Mortgage date window for maturity 2026-2028
MTGE_FROM = "2016-01-01"
MTGE_TO   = "2023-06-01"

BOROUGH_CODES = {"manhattan": "1", "brooklyn": "3", "both": "('1','3')"}

# Owners that signal government/affordable/NYCHA — exclude these
EXCLUDED_OWNERS = (
    "NYCHA", "N.Y.C.H.A", "NEW YORK CITY HOUSING",
    "NYC HOUSING", "CITY OF NEW YORK", "NYC HPD",
    "HOUSING PRESERVATION", "HUD ", "U.S. DEPT",
    "SECTION 8", "AFFORDABLE",
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get(url, params, timeout=15):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json() or []
    except Exception:
        return []


def fmt_money(v):
    try:
        n = int(float(v))
        return f"${n/1_000_000:.1f}M" if n >= 1_000_000 else f"${n:,}"
    except Exception:
        return str(v)


# ── PLUTO Bulk Query ──────────────────────────────────────────────────────────

def fetch_pluto_candidates(borough_code: str) -> list:
    """
    Pull all qualifying buildings from PLUTO in one (paginated) query.
    Criteria: elevator multifamily, 100+ units, built 1990+, Manhattan or Brooklyn.
    """
    if borough_code == "both":
        boro_clause = "borocode IN ('1','3')"
    else:
        boro_clause = f"borocode='{borough_code}'"

    where = (
        f"{boro_clause} "
        f"AND yearbuilt >= 1990 "
        f"AND unitsres >= 100 "
        f"AND (bldgclass LIKE 'D%' OR bldgclass LIKE 'R%')"
        # D = elevator apartments (D0-D9), R = condos (R0-R9)
        # Excludes C (walk-ups), which rarely hit 100 units post-1990
    )

    print(f"  Querying PLUTO: {boro_clause}, 100+ units, built >= 1990, elevator/condo class...")

    all_results = []
    offset = 0
    page   = 1000

    while True:
        batch = get(PLUTO_API, {
            "$where":  where,
            "$select": (
                "address,borocode,borough,bbl,block,lot,"
                "yearbuilt,unitsres,numfloors,bldgclass,ownername,assesstot"
            ),
            "$order":  "unitsres DESC",
            "$limit":  page,
            "$offset": offset,
        })
        if not batch:
            break

        # Filter out government / affordable housing by owner name
        kept = []
        for b in batch:
            owner = (b.get("ownername") or "").upper()
            if not any(ex in owner for ex in EXCLUDED_OWNERS):
                kept.append(b)

        all_results.extend(kept)
        print(f"    Page {offset//page + 1}: {len(batch)} records, {len(kept)} kept  "
              f"(running total: {len(all_results)})")

        if len(batch) < page:
            break
        offset += page
        time.sleep(0.15)

    print(f"  PLUTO result: {len(all_results)} candidates pass physical + ownership filters\n")
    return all_results


# ── ACRIS Maturity Check ──────────────────────────────────────────────────────

def check_acris(b: dict) -> tuple:
    """
    Returns (qualifies: bool, loan_info: dict | None)

    Qualifies = has at least one mortgage in MTGE_FROM..MTGE_TO window
                with no satisfaction filed 2024+.
    """
    boro  = str(b.get("borocode") or "").strip()
    block = str(int(float(b.get("block") or 0)))
    lot   = str(int(float(b.get("lot")   or 0)))

    if not (boro and block != "0" and lot != "0"):
        return False, None

    # Step 1 — get all doc_ids for this BBL
    legals = get(ACRIS_LEGALS, {
        "$where": f"borough='{boro}' AND block='{block}' AND lot='{lot}'",
        "$select": "document_id",
        "$limit": 200,
    })
    if not legals:
        return False, None

    doc_ids = list({l["document_id"] for l in legals if l.get("document_id")})
    if not doc_ids:
        return False, None

    id_clause = ",".join(f"'{d}'" for d in doc_ids[:100])   # Socrata IN limit

    # Step 2 — mortgages in our date window
    mortgages = get(ACRIS_MASTER, {
        "$where": (
            f"document_id IN ({id_clause}) "
            f"AND doc_type IN ('MTGE','SMTG','AMTG','CONV D') "
            f"AND document_date >= '{MTGE_FROM}' "
            f"AND document_date <= '{MTGE_TO}'"
        ),
        "$select": "document_id,doc_type,document_date,document_amt",
        "$order": "document_date DESC",
        "$limit": 10,
    })
    if not mortgages:
        return False, None

    # Step 3 — recent satisfactions (debt already retired)
    satisfactions = get(ACRIS_MASTER, {
        "$where": (
            f"document_id IN ({id_clause}) "
            f"AND doc_type IN ('SATS','SAT') "
            f"AND document_date >= '2024-01-01'"
        ),
        "$select": "document_id",
        "$limit": 20,
    })
    satisfied_ids = {s["document_id"] for s in satisfactions}

    # Active = mortgages not yet satisfied
    active = [m for m in mortgages if m["document_id"] not in satisfied_ids]
    if not active:
        return False, None

    best = active[0]
    return True, {
        "amount":   int(float(best.get("document_amt") or 0)),
        "date":     (best.get("document_date") or "")[:10],
        "doc_type": best.get("doc_type", ""),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Find qualifying LTG building biography targets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python find_buildings.py\n"
            "  python find_buildings.py --limit 50\n"
            "  python find_buildings.py --borough brooklyn\n"
        ),
    )
    parser.add_argument(
        "--borough",
        choices=["manhattan", "brooklyn", "both"],
        default="both",
        help="Which borough(s) to scan (default: both)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Max number of qualifying buildings to output (default: 500)",
    )
    parser.add_argument(
        "--out",
        default=str(SCRIPT_DIR / "qualified_buildings.txt"),
        help="Output file path",
    )
    args = parser.parse_args()

    borough_code = args.borough   # pass the name, not the translated code
    print(f"\nLight Tower Group — Building Finder")
    print(f"{'='*50}")
    print(f"Borough:      {args.borough.title()}")
    print(f"Criteria:     100+ units | built 1990+ | elevator/condo class | free-market owners")
    print(f"Debt window:  mortgages filed {MTGE_FROM} to {MTGE_TO}")
    print(f"Max output:   {args.limit} buildings")
    print(f"{'='*50}\n")

    # Step 1: PLUTO
    candidates = fetch_pluto_candidates(borough_code)
    if not candidates:
        print("No candidates found. Check query parameters.")
        return

    # Step 2: ACRIS loan check
    total      = len(candidates)
    qualified  = []
    no_debt    = 0
    errors     = 0

    print(f"Checking ACRIS for {total} candidates (est. {total * 0.8 / 60:.1f} min)...\n")

    for i, b in enumerate(candidates):
        addr      = (b.get("address") or "").title().strip()
        boro_name = "Manhattan" if str(b.get("borocode")) == "1" else "Brooklyn"
        full_addr = f"{addr}, {boro_name}"
        units     = b.get("unitsres", "?")
        yr        = b.get("yearbuilt", "?")

        try:
            ok, loan = check_acris(b)
        except Exception as e:
            errors += 1
            print(f"  [{i+1:>4}/{total}] {full_addr:<50}  ERROR: {e}")
            time.sleep(0.4)
            continue

        if ok:
            qualified.append({
                "address":    full_addr,
                "year_built": yr,
                "units":      units,
                "floors":     b.get("numfloors", "?"),
                "bldgclass":  b.get("bldgclass", ""),
                "assesstot":  b.get("assesstot", ""),
                "loan_amt":   loan["amount"],
                "loan_date":  loan["date"],
                "loan_type":  loan["doc_type"],
            })
            tag = f"QUALIFIED  {fmt_money(loan['amount'])} {loan['doc_type']} filed {loan['date'][:7]}"
        else:
            no_debt += 1
            tag = "no qualifying debt"

        print(f"  [{i+1:>4}/{total}] {addr:<42} {units} units {yr}  {tag}")

        if len(qualified) >= args.limit:
            print(f"\n  Limit of {args.limit} reached — stopping ACRIS scan.")
            break

        time.sleep(0.4)   # polite rate-limiting

    # Step 3: Write output
    out_path = Path(args.out)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Light Tower Group — Qualifying Building Targets\n")
        f.write(f"# Generated: {date.today().isoformat()}\n")
        f.write(f"# Borough: {args.borough.title()} | Min units: 100 | Built: 1990+ | Likely loan maturing 2026-2028\n")
        f.write(f"# Total qualifying: {len(qualified)}\n")
        f.write("#\n")
        f.write("# HOW TO USE:\n")
        f.write("#   cd scripts\n")
        f.write("#   python generate_building.py --batch qualified_buildings.txt\n")
        f.write("#\n")
        f.write("# Format: address line preceded by a comment with key stats\n")
        f.write("#" + "-"*65 + "\n\n")

        for q in qualified:
            loan_str = fmt_money(q['loan_amt']) if q['loan_amt'] else "unknown"
            f.write(
                f"# {q['year_built']} | {q['units']} units | "
                f"{loan_str} {q['loan_type']} filed {q['loan_date'][:7]}\n"
            )
            f.write(f"{q['address']}\n\n")

    # Summary
    print(f"\n{'='*60}")
    print(f"SCAN COMPLETE")
    print(f"  Candidates checked:  {min(i+1, total)}")
    print(f"  Qualified:           {len(qualified)}")
    print(f"  No qualifying debt:  {no_debt}")
    print(f"  Errors:              {errors}")
    print(f"  Output:              {out_path}")
    print(f"\nNext step:")
    print(f"  python generate_building.py --batch {out_path.name}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
