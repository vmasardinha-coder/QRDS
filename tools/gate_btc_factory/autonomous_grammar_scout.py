#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

SCHEMA = "qrds.factory.grammar_scout.v1"
OPENALEX = "https://api.openalex.org/works"

CHANNELS = [
    {
        "channel_id": "B3_ADR_CROSS_LISTING_PRICE_DISCOVERY",
        "queries": [
            "Brazil ADR B3 price discovery",
            "Brazilian ADR lead lag Bovespa",
            "cross listed Brazilian stocks ADR information transmission",
        ],
        "mechanism": "Cross-listed Brazilian shares and their US ADRs may transmit information across non-overlapping and overlapping sessions, creating falsifiable lead-lag, overnight-gap, and relative-value hypotheses.",
        "required_new_data": ["B3 underlying share/ETF", "US ADR", "FX timing", "exchange calendars"],
        "official_free_source_candidates": ["B3", "CVM", "SEC EDGAR", "Federal Reserve/BCB FX references"],
    },
    {
        "channel_id": "B3_INDEX_FUTURES_CASH_PRICE_DISCOVERY",
        "queries": ["Brazil index futures cash price discovery B3", "Ibovespa futures lead lag cash market"],
        "mechanism": "Futures and cash markets may incorporate common information at different speeds around opens, closes, auctions, and macro announcements.",
        "required_new_data": ["B3 index futures", "B3 cash index/constituents", "auction/calendar metadata"],
        "official_free_source_candidates": ["B3", "CVM"],
    },
    {
        "channel_id": "B3_CROSS_ASSET_FX_COMMODITY_TRANSMISSION",
        "queries": ["Brazil equities exchange rate commodity price discovery", "Bovespa dollar futures cross market lead lag"],
        "mechanism": "Brazilian equities, BRL, rates, and commodity-linked assets may exhibit causal information transmission tied to distinct market clocks.",
        "required_new_data": ["B3 equities/futures", "BRL", "rates", "commodity reference"],
        "official_free_source_candidates": ["B3", "BCB", "CFTC", "EIA", "FRED"],
    },
]

TOKEN_RE = re.compile(r"[A-Z0-9_]{3,}")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _historical_tokens(results_dir: Path) -> set[str]:
    out: set[str] = set()
    for p in sorted(results_dir.glob("gate_btc_b3_h*_h*_result.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for fam in d.get("families", []):
            c = fam.get("contract") or fam
            for key in ("feature", "direction", "causal_standardization"):
                val = str(c.get(key, "")).upper()
                out.update(TOKEN_RE.findall(val))
    return out


def _existing_channel_ids(existing_dir: Path | None) -> set[str]:
    if not existing_dir or not existing_dir.exists():
        return set()
    ids: set[str] = set()
    for p in existing_dir.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for row in d.get("proposals", []):
            if row.get("channel_id"):
                ids.add(str(row["channel_id"]))
    return ids


def _openalex_search(query: str, per_page: int = 5) -> list[dict]:
    r = requests.get(
        OPENALEX,
        params={"search": query, "per-page": per_page, "select": "id,doi,title,publication_year,primary_location"},
        timeout=20,
        headers={"User-Agent": "QRDS-research-only-grammar-scout/1.0"},
    )
    r.raise_for_status()
    rows = []
    for w in r.json().get("results", []):
        source = (((w.get("primary_location") or {}).get("source") or {}).get("display_name"))
        rows.append({
            "openalex_id": w.get("id"),
            "doi": w.get("doi"),
            "title": w.get("title"),
            "publication_year": w.get("publication_year"),
            "source": source,
        })
    return rows


def scout(results_dir: Path, existing_dir: Path | None = None, fetcher=_openalex_search) -> dict:
    historical = _historical_tokens(results_dir)
    existing = _existing_channel_ids(existing_dir)
    proposals = []
    for ch in CHANNELS:
        evidence = []
        errors = []
        for q in ch["queries"]:
            try:
                evidence.extend(fetcher(q))
            except Exception as exc:
                errors.append(f"{type(exc).__name__}:{exc}")
        seen = set()
        unique = []
        for row in evidence:
            key = row.get("doi") or row.get("openalex_id") or row.get("title")
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(row)
        mechanism_tokens = set(TOKEN_RE.findall(ch["channel_id"].upper()))
        overlap = sorted(mechanism_tokens & historical)
        previously_proposed = ch["channel_id"] in existing
        status = "SCOUTED_NOT_PREREGISTERED"
        if previously_proposed:
            status = "DUPLICATE_CHANNEL_SUPPRESSED"
        elif not unique:
            status = "INSUFFICIENT_EXTERNAL_EVIDENCE_FAIL_CLOSED"
        proposal_id = hashlib.sha256((ch["channel_id"] + "|" + "|".join(sorted(str(x.get("doi") or x.get("openalex_id") or "") for x in unique))).encode()).hexdigest()[:16]
        proposals.append({
            "proposal_id": proposal_id,
            "channel_id": ch["channel_id"],
            "status": status,
            "mechanism": ch["mechanism"],
            "required_new_data": ch["required_new_data"],
            "official_free_source_candidates": ch["official_free_source_candidates"],
            "literature_evidence": unique[:12],
            "research_errors": errors,
            "historical_token_overlap": overlap,
            "historical_overlap_is_exclusion_input_not_performance_feedback": True,
            "requires_new_or_independent_unseen_data": True,
            "economics_read": False,
            "may_allocate_family_id": False,
            "may_change_existing_grammar": False,
            "may_test_threshold_grid": False,
        })
    return {
        "schema": SCHEMA,
        "generated_at_utc": _utcnow(),
        "mode": "IDEATION_ONLY_NO_ECONOMICS",
        "history_used_for": "DEDUPLICATION_AND_COVERAGE_ONLY",
        "history_used_for_selection": False,
        "b3_adr_scope_required": True,
        "evaluation_data_policy": "FORWARD_OR_INDEPENDENT_UNSEEN_ONLY_AFTER_SEPARATE_PREREGISTRATION",
        "root_cause_audit_dependency": "NONE_CAN_RUN_IN_PARALLEL",
        "proposals": proposals,
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "no_retune": True,
            "no_backfill": True,
            "no_counter_reset": True,
            "fail_closed": True,
            "h1_economics_read": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--existing-dir")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = scout(Path(args.results_dir), Path(args.existing_dir) if args.existing_dir else None)
    Path(args.output).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
