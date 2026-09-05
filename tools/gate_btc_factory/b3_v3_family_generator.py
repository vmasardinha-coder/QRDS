#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

DEFAULT_MANIFEST = Path("research/b3_h_autonomous_science_v3_family_manifest.json")
DEFAULT_SOURCE_CONTRACT = Path("research/b3_h_autonomous_science_v3_source_contract.json")


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    assert d["status"] == "PREREGISTERED_BEFORE_ANY_V3_ECONOMICS"
    assert d["data_dimension"] == "TICK_MICROSTRUCTURE"
    assert d["family_count"] == 160 and d["generation_size"] == 10
    assert d["first_family_number"] == 2730 and d["last_family_number"] == 2889
    assert d["economics_start_allowed"] is False
    return d


def identities(manifest: dict) -> list[tuple[str, str, int, float]]:
    rows = list(itertools.product(
        manifest["features"],
        manifest["directions"],
        manifest["decision_windows_minutes"],
        manifest["abs_z_thresholds"],
    ))
    if len(rows) != manifest["family_count"] or len(set(rows)) != len(rows):
        raise RuntimeError("V3_IDENTITY_MANIFEST_INVALID")
    return rows


def build_generation(start: int, manifest_path: Path = DEFAULT_MANIFEST, source_contract_path: Path = DEFAULT_SOURCE_CONTRACT) -> dict:
    manifest = load_manifest(manifest_path)
    lo, hi, size = manifest["first_family_number"], manifest["last_family_number"], manifest["generation_size"]
    if start < lo or start > hi or start % size:
        raise RuntimeError(f"NONCANONICAL_V3_START:{start}")
    if start + size - 1 > hi:
        raise RuntimeError("AUTONOMOUS_SCIENCE_V3_GRAMMAR_EXHAUSTED")
    source = json.loads(source_contract_path.read_text(encoding="utf-8"))
    if source["economics_allowed_before_qualification_pass"] is not False:
        raise RuntimeError("V3_SOURCE_CONTRACT_NOT_FAIL_CLOSED")
    rows = identities(manifest)
    offset = start - lo
    fams = []
    for i, (feature, direction, window, threshold) in enumerate(rows[offset:offset + size]):
        fid = start + i
        fams.append({
            "family_id": f"H{fid}",
            "protocol": "v3",
            "data_dimension": manifest["data_dimension"],
            "feature": feature,
            "direction": direction,
            "decision_window_minutes": int(window),
            "abs_z_threshold": float(threshold),
            "holding_horizons_minutes": list(manifest["holding_horizons_minutes"]),
            "standardization_lookback_sessions": int(manifest["standardization_lookback_sessions"]),
            "causal_standardization": "ROLLING_20_PRIOR_SESSIONS_MEDIAN_MAD",
        })
    if len(fams) != size:
        raise RuntimeError("V3_INCOMPLETE_GENERATION")
    return {
        "schema": "gate_btc.b3.autonomous_family_contract.v3",
        "generation": f"H{start}-H{start+size-1}",
        "protocol": "research/b3_h_autonomous_science_protocol_v3.md",
        "family_manifest": str(manifest_path),
        "source_contract": str(source_contract_path),
        "data_dimension": manifest["data_dimension"],
        "frozen_before_economics": True,
        "economics_authorized": False,
        "source_gate_required_before_economics": True,
        "discovery": "2022-01-01/2024-12-31",
        "replication": "2020-01-01/2021-12-31",
        "h1_cutoff_exclusive": "2026-08-10",
        "max_survivors": 2,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "h1_economics_read": False,
        "families": fams,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, type=int)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--source-contract", default=str(DEFAULT_SOURCE_CONTRACT))
    ap.add_argument("--out")
    args = ap.parse_args()
    d = build_generation(args.start, Path(args.manifest), Path(args.source_contract))
    text = json.dumps(d, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        p = Path(args.out); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
