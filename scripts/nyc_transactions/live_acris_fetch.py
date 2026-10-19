"""Live NYC Open Data ACRIS + PLUTO Full Dossier Builder for the Latest 30 >$10M Sales."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_PATH = REPO_ROOT / "config" / "nyc_latest_30_acris.json"

BORO_NAMES = {
    "1": "Manhattan",
    "2": "Bronx",
    "3": "Brooklyn",
    "4": "Queens",
    "5": "Staten Island",
}

EXCLUDED_SINGLE_RES_TYPES = {"SC", "SP", "CC", "CP", "D2"}  # Single res condo/co-op/1-2 fam


def _get_json(url: str, timeout: int = 25) -> list[dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": "LightTowerNYCDesk/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data if isinstance(data, list) else []


def fetch_and_enrich_latest_30(limit: int = 30) -> list[dict[str, Any]]:
    master_url = "https://data.cityofnewyork.us/resource/bnx9-e6tj.json?" + urllib.parse.urlencode(
        {
            "$where": "document_amt > 10000000 AND doc_type in ('DEED','DEEDO') AND percent_trans >= 50",
            "$order": "document_date DESC",
            "$limit": "220",
        }
    )
    masters = _get_json(master_url)
    doc_ids = [m["document_id"] for m in masters if m.get("document_id")]

    leg_by_doc: dict[str, list[dict[str, Any]]] = {}
    pty_by_doc: dict[str, list[dict[str, Any]]] = {}

    for i in range(0, len(doc_ids), 60):
        chunk = doc_ids[i : i + 60]
        in_clause = ",".join(f"'{d}'" for d in chunk)
        legals = _get_json(
            "https://data.cityofnewyork.us/resource/8h5j-fqxa.json?"
            + urllib.parse.urlencode({"$where": f"document_id in ({in_clause})", "$limit": "1000"})
        )
        for l in legals:
            leg_by_doc.setdefault(l["document_id"], []).append(l)

        parties = _get_json(
            "https://data.cityofnewyork.us/resource/636b-3b5g.json?"
            + urllib.parse.urlencode({"$where": f"document_id in ({in_clause})", "$limit": "1500"})
        )
        for p in parties:
            pty_by_doc.setdefault(p["document_id"], []).append(p)

    raw_deals: list[dict[str, Any]] = []
    seen_bbls: set[str] = set()

    for m in masters:
        did = m["document_id"]
        ls = leg_by_doc.get(did, [])
        if not ls:
            continue
        l0 = ls[0]
        prop_type = str(l0.get("property_type") or "").upper()
        lot_num = int(l0.get("lot", "0") or 0)
        if prop_type in EXCLUDED_SINGLE_RES_TYPES and len(ls) == 1:
            continue
        if prop_type == "AP" and len(ls) == 1:
            continue
        if 1000 <= lot_num <= 9999 and len(ls) == 1 and prop_type not in {"CB", "CM", "CO", "CR", "IB"}:
            continue

        boro = str(l0.get("borough") or "")
        block_int = int(l0.get("block") or 0)
        lot_int = int(l0.get("lot") or 0)
        bbl = f"{boro}-{block_int:05d}-{lot_int:04d}"
        if bbl in seen_bbls:
            continue

        addr = f"{l0.get('street_number', '')} {l0.get('street_name', '')}".strip()
        if not addr or len(addr) < 4 or addr.upper().startswith("N/A"):
            continue

        ptys = pty_by_doc.get(did, [])
        sellers = [str(p.get("name") or "").strip() for p in ptys if p.get("party_type") == "1" and p.get("name")]
        buyers = [str(p.get("name") or "").strip() for p in ptys if p.get("party_type") == "2" and p.get("name")]
        if not buyers or not sellers:
            continue

        seen_bbls.add(bbl)
        raw_deals.append(
            {
                "document_id": did,
                "crfn": m.get("crfn", ""),
                "closing_date": str(m.get("document_date") or m.get("recorded_datetime") or "")[:10],
                "recorded_date": str(m.get("recorded_datetime") or "")[:10],
                "sale_price_usd": float(m.get("document_amt") or 0.0),
                "borough_code": boro,
                "borough": BORO_NAMES.get(boro, "Manhattan"),
                "block": str(block_int),
                "lot": str(lot_int),
                "bbl": bbl,
                "property_type": prop_type,
                "address": addr.title(),
                "buyer": buyers[0],
                "seller": sellers[0],
                "parcel_count": len(ls),
            }
        )
        if len(raw_deals) >= limit:
            break

    # Enrich each deal with PLUTO and ACRIS parcel history (mortgages + prior deed)
    for d in raw_deals:
        boro = d["borough_code"]
        block = d["block"]
        lot = d["lot"]
        # For condo lots (1000+), PLUTO often stores billing lot 7501/7502 or base lot 1
        pluto_rows = _get_json(
            "https://data.cityofnewyork.us/resource/64uk-42ks.json?"
            + urllib.parse.urlencode({"borocode": boro, "block": block, "lot": lot, "$limit": "1"})
        )
        if not pluto_rows and int(lot) >= 1000:
            pluto_rows = _get_json(
                "https://data.cityofnewyork.us/resource/64uk-42ks.json?"
                + urllib.parse.urlencode({"borocode": boro, "block": block, "$limit": "1"})
            )
        p0 = pluto_rows[0] if pluto_rows else {}
        d["pluto"] = {
            "bldgclass": p0.get("bldgclass") or d["property_type"] or "O4",
            "bldgarea": int(float(p0.get("bldgarea") or 0)),
            "lotarea": int(float(p0.get("lotarea") or 0)),
            "unitstotal": int(float(p0.get("unitstotal") or 0)),
            "unitsres": int(float(p0.get("unitsres") or 0)),
            "numfloors": int(float(p0.get("numfloors") or 0)),
            "yearbuilt": int(float(p0.get("yearbuilt") or 0)),
            "zonedist1": p0.get("zonedist1") or "C6-4",
            "zipcode": p0.get("zipcode") or "",
        }

        # Fetch all ACRIS legal docs on this borough/block/lot to find same-closing mortgage & prior deed
        parcel_legals = _get_json(
            "https://data.cityofnewyork.us/resource/8h5j-fqxa.json?"
            + urllib.parse.urlencode({"borough": boro, "block": block, "lot": lot, "$limit": "60"})
        )
        p_doc_ids = [pl["document_id"] for pl in parcel_legals if pl.get("document_id") and pl["document_id"] != d["document_id"]]
        d["mortgage"] = None
        d["prior_sale"] = None
        if p_doc_ids:
            in_p = ",".join(f"'{x}'" for x in p_doc_ids[:50])
            p_masters = _get_json(
                "https://data.cityofnewyork.us/resource/bnx9-e6tj.json?"
                + urllib.parse.urlencode(
                    {
                        "$where": f"document_id in ({in_p}) AND document_amt > 1000000",
                        "$order": "recorded_datetime DESC",
                        "$limit": "50",
                    }
                )
            )
            # Find mortgage recorded within 14 days of deed
            for pm in p_masters:
                dt_type = str(pm.get("doc_type") or "").upper()
                rec_d = str(pm.get("recorded_datetime") or "")[:10]
                amt = float(pm.get("document_amt") or 0.0)
                if dt_type in {"MTGE", "AGMT", "M&CON"} and rec_d[:7] == d["recorded_date"][:7] and amt <= d["sale_price_usd"]:
                    # Fetch lender party (party_type 2 on MTGE/AGMT)
                    m_ptys = _get_json(
                        "https://data.cityofnewyork.us/resource/636b-3b5g.json?"
                        + urllib.parse.urlencode({"document_id": pm["document_id"], "$limit": "10"})
                    )
                    lenders = [mp.get("name") for mp in m_ptys if mp.get("party_type") == "2" and mp.get("name")]
                    d["mortgage"] = {
                        "document_id": pm["document_id"],
                        "doc_type": dt_type,
                        "amount_usd": amt,
                        "recorded_date": rec_d,
                        "lender": (lenders[0] if lenders else "Senior Commercial Lender"),
                    }
                    break
            # Find prior deed before this closing
            for pm in p_masters:
                dt_type = str(pm.get("doc_type") or "").upper()
                doc_d = str(pm.get("document_date") or pm.get("recorded_datetime") or "")[:10]
                amt = float(pm.get("document_amt") or 0.0)
                if dt_type in {"DEED", "DEEDO"} and doc_d < d["closing_date"][:7] and amt > 1_000_000:
                    d["prior_sale"] = {
                        "document_id": pm["document_id"],
                        "closing_date": doc_d,
                        "price_usd": amt,
                    }
                    break

    CACHE_PATH.write_text(json.dumps(raw_deals, indent=2), encoding="utf-8")
    return raw_deals


if __name__ == "__main__":
    deals = fetch_and_enrich_latest_30(30)
    print(f"Saved {len(deals)} enriched real ACRIS+PLUTO transactions to {CACHE_PATH}")
    for i, d in enumerate(deals, 1):
        m_str = f"Loan: ${d['mortgage']['amount_usd']:,.0f} ({d['mortgage']['lender'][:25]})" if d.get("mortgage") else "All-Cash / Unrecorded Debt"
        p_str = f"Prior: ${d['prior_sale']['price_usd']:,.0f} ({d['prior_sale']['closing_date']})" if d.get("prior_sale") else "No prior deed"
        print(f"{i:2d}. {d['closing_date']} | ${d['sale_price_usd']:>11,.0f} | {d['borough']:10s} | {d['address']:28s} | GSF: {d['pluto']['bldgarea']:>7,d} | {m_str} | {p_str}")
