#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def apply_amendment(base: dict, amendment: dict) -> dict:
    if base.get("entry_count") != 137 or base.get("eligible_symbol_count") != 137:
        raise ValueError("base registry must be complete 137/137")
    if amendment.get("source_admitted") is not True or amendment.get("d0_started") is not False:
        raise ValueError("amendment boundary invalid")
    if any(amendment.get(k) != 0 for k in ("historical_credit", "scientific_credit", "prospective_credit_before_d0", "d0_credit")):
        raise ValueError("amendment cannot carry credit")

    out = copy.deepcopy(base)
    by_symbol = {e.get("symbol"): e for e in out.get("entries", [])}
    if len(by_symbol) != 137:
        raise ValueError("base registry symbols not unique")

    seen = set()
    for a in amendment.get("amendments", []):
        symbol = a.get("symbol")
        if symbol in seen or symbol not in by_symbol:
            raise ValueError(f"invalid amendment symbol {symbol}")
        seen.add(symbol)
        old = by_symbol[symbol]
        for key in ("source_identity", "source_symbol"):
            if old.get(key) != a.get("prior_" + key):
                raise ValueError(f"{symbol} prior {key} mismatch")
        old_prov = old.get("provenance_sha256") or old.get("raw_response_sha256")
        if isinstance(old_prov, list):
            old_prov = old_prov[0] if old_prov else None
        if old_prov != a.get("prior_provenance_sha256"):
            raise ValueError(f"{symbol} prior provenance mismatch")
        if a.get("source_identity") != "MEXC_SPOT" or a.get("source_symbol") != f"{symbol}USDT":
            raise ValueError(f"{symbol} amendment route mismatch")

        old["prior_source_identity"] = old["source_identity"]
        old["prior_source_symbol"] = old["source_symbol"]
        old["prior_source_provenance_sha256"] = a["prior_provenance_sha256"]
        old["source_identity"] = a["source_identity"]
        old["source_symbol"] = a["source_symbol"]
        old["qualification"] = "QUALIFIED_EXACT_SOURCE"
        old["qa_pass"] = True
        old["source_admitted"] = True
        old["evidence_stage"] = "MEXC4_PIT_RESIDUAL_RECOVERY_PR619"
        old["evidence_artifact_id"] = amendment["evidence_artifact_id"]
        old["evidence_artifact_sha256"] = amendment["evidence_artifact_sha256"]
        old["provenance_sha256"] = amendment["evidence_artifact_sha256"]
        old["historical_credit"] = 0
        old["d0_credit"] = 0

    if seen != {"HTX", "KAS", "KCS", "MNT"}:
        raise ValueError(f"unexpected amendment set: {sorted(seen)}")
    if len(out["entries"]) != 137 or len({e["symbol"] for e in out["entries"]}) != 137:
        raise ValueError("amended registry not 137 unique symbols")
    if any(e.get("qualification") != "QUALIFIED_EXACT_SOURCE" or e.get("qa_pass") is not True or e.get("source_admitted") is not True for e in out["entries"]):
        raise ValueError("amended registry contains unqualified entry")

    out["schema"] = "gate_btc.v2a_complete_qualified_source_registry.v1+amendment1"
    out["status"] = "COMPLETE_REGISTRY_ADMITTED_ZERO_D0_CREDIT_AMENDED_MEXC4"
    out["source_admission_changed"] = True
    out["d0_started"] = False
    out["historical_credit"] = 0
    out["scientific_credit"] = False
    out["prospective_credit"] = False
    out["d0_credit"] = 0
    out["amendment_evidence"] = {
        "physical_qualification_pr": amendment["physical_qualification_pr"],
        "physical_workflow_run_id": amendment["physical_workflow_run_id"],
        "evidence_artifact_id": amendment["evidence_artifact_id"],
        "evidence_artifact_sha256": amendment["evidence_artifact_sha256"],
        "symbols": sorted(seen),
    }
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--amendment", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    result = apply_amendment(load(a.base), load(a.amendment))
    Path(a.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "entries": len(result["entries"]), "d0_started": result["d0_started"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
