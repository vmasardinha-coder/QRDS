from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from gate_btc_b3_h150_h159_focus_source_qa import CUTOFF, INDICATORS, START, fetch_indicator

OUT = Path("artifacts/b3_h150_h159_focus_causality_qa.json")
PRIMARY_BASE_CALCULO = 0
CAUSAL_POLICY = "ONE_FULL_COMPLETED_B3_SESSION_LAG"
ANCHOR_DATE = "2025-06-13"
ANCHOR_REF = "2025"
ANCHOR_SOURCE = "https://www.bcb.gov.br/content/focus/focus/R20250613.pdf"
ANCHORS = {
    "IPCA": {0: {"Mediana": 5.25, "numeroRespondentes": 151}, 1: {"Mediana": 5.24, "numeroRespondentes": 115}},
    "PIB Total": {0: {"Mediana": 2.20, "numeroRespondentes": 115}, 1: {"Mediana": 2.26, "numeroRespondentes": 69}},
    "Câmbio": {0: {"Mediana": 5.77, "numeroRespondentes": 125}, 1: {"Mediana": 5.75, "numeroRespondentes": 84}},
    "Selic": {0: {"Mediana": 14.75, "numeroRespondentes": 146}, 1: {"Mediana": 14.75, "numeroRespondentes": 102}},
}


def as_year(value: object) -> int | None:
    text = str(value or "").strip()
    if len(text) == 4 and text.isdigit():
        return int(text)
    return None


def close(a: object, b: float, tol: float = 1e-9) -> bool:
    try:
        return abs(float(a) - b) <= tol
    except (TypeError, ValueError):
        return False


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "qrds.b3_h150_h159.focus_causality_horizon_qa.v1",
        "historical_start_inclusive": START,
        "historical_cutoff_exclusive": CUTOFF,
        "official_focus_anchor": ANCHOR_SOURCE,
        "anchor_date": ANCHOR_DATE,
        "anchor_reference_year": ANCHOR_REF,
        "primary_base_calculo": PRIMARY_BASE_CALCULO,
        "base_calculo_rule": "baseCalculo=0 must match official Focus 30-day aggregate; baseCalculo=1 must match official 5-business-day aggregate",
        "fixed_horizon_rule": "for each source Data, choose the minimum annual DataReferencia year >= calendar year(Data), using only baseCalculo=0",
        "causal_policy": CAUSAL_POLICY,
        "causal_policy_reason": "API historical rows have dates but no release timestamp adequate for same-session admission; preregistered conservative fallback is one full completed B3-session lag",
        "economics_executed": False,
        "h1_economics_read": False,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "indicators": {},
        "failures": [],
    }

    for indicator in INDICATORS:
        try:
            _raw, obj = fetch_indicator(indicator)
            rows = obj["payload"]["value"]

            anchor_rows = {
                int(r["baseCalculo"]): r
                for r in rows
                if str(r.get("Data"))[:10] == ANCHOR_DATE
                and str(r.get("DataReferencia")) == ANCHOR_REF
                and r.get("baseCalculo") in (0, 1)
            }
            if set(anchor_rows) != {0, 1}:
                raise RuntimeError(f"anchor baseCalculo rows missing: {sorted(anchor_rows)}")
            anchor_check = {}
            for base, expected in ANCHORS[indicator].items():
                row = anchor_rows[base]
                ok = close(row.get("Mediana"), expected["Mediana"]) and int(row.get("numeroRespondentes")) == expected["numeroRespondentes"]
                anchor_check[str(base)] = {
                    "observed_mediana": row.get("Mediana"),
                    "expected_mediana": expected["Mediana"],
                    "observed_numero_respondentes": row.get("numeroRespondentes"),
                    "expected_numero_respondentes": expected["numeroRespondentes"],
                    "match": ok,
                }
                if not ok:
                    raise RuntimeError(f"official Focus anchor mismatch baseCalculo={base}: {anchor_check[str(base)]}")

            primary = [r for r in rows if r.get("baseCalculo") == PRIMARY_BASE_CALCULO]
            by_date: dict[str, list[dict]] = defaultdict(list)
            for row in primary:
                d = str(row.get("Data") or "")[:10]
                if START <= d < CUTOFF:
                    by_date[d].append(row)

            chosen = []
            offsets = Counter()
            missing_dates = []
            ambiguous_dates = []
            for d, day_rows in sorted(by_date.items()):
                obs_year = date.fromisoformat(d).year
                candidates = [(as_year(r.get("DataReferencia")), r) for r in day_rows]
                candidates = [(y, r) for y, r in candidates if y is not None and y >= obs_year]
                if not candidates:
                    missing_dates.append(d)
                    continue
                chosen_year = min(y for y, _r in candidates)
                selected = [r for y, r in candidates if y == chosen_year]
                if len(selected) != 1:
                    ambiguous_dates.append({"date": d, "year": chosen_year, "rows": len(selected)})
                    continue
                chosen.append(selected[0])
                offsets[chosen_year - obs_year] += 1

            if missing_dates:
                raise RuntimeError(f"fixed annual horizon unavailable on {len(missing_dates)} dates; first={missing_dates[:5]}")
            if ambiguous_dates:
                raise RuntimeError(f"fixed annual horizon ambiguous on {len(ambiguous_dates)} dates; first={ambiguous_dates[:5]}")
            if not chosen:
                raise RuntimeError("zero fixed-horizon observations")

            chosen_dates = [str(r["Data"])[:10] for r in chosen]
            coverage = {
                "replication_2020_22": any("2020-" <= d < "2022-" for d in chosen_dates),
                "replication_2022_24": any("2022-" <= d < "2024-" for d in chosen_dates),
                "discovery_2024_26": any("2024-" <= d < CUTOFF for d in chosen_dates),
            }
            if not all(coverage.values()):
                raise RuntimeError(f"fixed-horizon coverage block missing: {coverage}")

            report["indicators"][indicator] = {
                "base_calculo_anchor": anchor_check,
                "primary_rows": len(primary),
                "distinct_source_dates": len(by_date),
                "fixed_horizon_observations": len(chosen),
                "fixed_horizon_offset_years": {str(k): v for k, v in sorted(offsets.items())},
                "first_fixed_horizon_date": min(chosen_dates),
                "last_fixed_horizon_date": max(chosen_dates),
                "coverage_blocks_present": coverage,
                "publication_time_same_session_admitted": False,
                "causal_admission": "RULE_FROZEN_ONE_FULL_COMPLETED_B3_SESSION_LAG__B3_JOIN_COVERAGE_PENDING",
            }
        except Exception as exc:
            report["failures"].append(f"{indicator}: {exc}")

    report["status"] = (
        "CAUSALITY_HORIZON_QA_PASS_ADAPTER_JOIN_PENDING"
        if not report["failures"]
        else "CAUSALITY_HORIZON_QA_FAIL_CLOSED"
    )
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "failures": report["failures"]}, ensure_ascii=False))
    return 0 if not report["failures"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
