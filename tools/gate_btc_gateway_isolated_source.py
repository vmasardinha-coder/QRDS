"""Validate a daily Gateway artifact when LOCK valuation blocked the shared handoff.

This admits a *prospective Gateway snapshot only*. It never grants LOCK, QOS,
Delta, report delivery, trading or economic credit.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load(path: Path) -> dict:
    require(path.is_file(), f"missing source evidence: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate(root: Path, gateway_outputs: Path) -> str:
    qos_paths = list((root / "qos_daily").glob("QOS_ORCHESTRATION_MANIFEST_*.json"))
    require(len(qos_paths) == 1, "expected one QOS orchestration manifest")
    qos = load(qos_paths[0])
    upstream = load(root / "gateway_daily/GATE_BTC_GATEWAY_UPSTREAM_EQUIVALENCE.json")
    downstream = load(root / "gateway_reference_check/GATE_BTC_GATEWAY_V010_REPLAY.json")
    require(qos.get("status") in {"PASS", "PASS_WITH_GATEWAY_PENDING"}, "QOS orchestration not complete")
    require(qos.get("matched_component_close") is True and not qos.get("errors"), "QOS close/error mismatch")
    engines = {e.get("name"): e for e in qos.get("engines", [])}
    cutoff = qos.get("data_as_of")
    require(isinstance(cutoff, str) and len(cutoff) == 10, "invalid QOS cutoff")
    for name in ("V2A", "Delta"):
        require(engines.get(name, {}).get("status") == "PASS", f"{name} engine not PASS")
        require(engines[name].get("manifest", {}).get("data_as_of") == cutoff, f"{name} close mismatch")
    locks = qos.get("locks", {})
    require(locks.get("research_only") is True and locks.get("orders_generated") == 0
            and locks.get("real_capital_used") == 0 and locks.get("operational_status") == "NOT_APPROVED",
            "QOS safety lock invalid")

    capture = upstream.get("capture", {})
    replay = upstream.get("linux_replay", {})
    manifest = capture.get("gateway", {}).get("manifest", {})
    http_capture = capture.get("http", {})
    http_replay = replay.get("http", {})
    require(upstream.get("status") == "PASS" and capture.get("status") == "PASS"
            and replay.get("status") == "PASS", "Gateway upstream/capture/replay not PASS")
    require(str(upstream.get("public_source_acquisition_equivalence", "")).startswith("PASS")
            and str(upstream.get("feature_construction_equivalence", "")).startswith("PASS"),
            "Gateway equivalence missing")
    require(http_capture.get("capture_count", 0) > 0 and http_replay.get("replay_total") == http_replay.get("replay_consumed")
            and http_replay.get("replay_remaining") == 0, "Gateway HTTP cassette incomplete")
    gateway_close = manifest.get("data_as_of")
    require(gateway_close in {cutoff, (date.fromisoformat(cutoff) + timedelta(days=1)).isoformat()},
            "Gateway capture date outside daily source window")
    require(manifest.get("technical_status") == "PASS"
            and manifest.get("operational_status") == "NOT_APPROVED"
            and manifest.get("retrospective_performance_status") == "PROHIBITED_CURRENT_COMPOSITION"
            and manifest.get("errors") == [], "Gateway manifest not eligible")
    require(downstream.get("status") == "PASS", "Gateway downstream not PASS")
    for key in ("source_canonicality", "reference_integrity", "frozen_replay", "fixture_contract"):
        require(downstream.get(key, {}).get("status") == "PASS", f"Gateway {key} not PASS")
    for evidence in (upstream, downstream):
        require(evidence.get("research_only") is True and evidence.get("orders_generated") == 0
                and evidence.get("real_capital_used") == 0 and evidence.get("operational_status") == "NOT_APPROVED"
                and evidence.get("methodology_changes") == 0, "Gateway safety contract invalid")
    for name in ("v2a1_run_manifest.json", "scanner_snapshot_status.json", "strategy_compositions.csv",
                 "strategy_execution_profiles.csv"):
        require((gateway_outputs / name).is_file(), f"missing Gateway replay output: {name}")
    replay_manifest = load(gateway_outputs / "v2a1_run_manifest.json")
    require(replay_manifest.get("data_as_of") == gateway_close, "Gateway replay close mismatch")
    require(replay_manifest.get("technical_status") == "PASS", "Gateway replay technical status not PASS")
    require(replay_manifest.get("retrospective_performance_status") == "PROHIBITED_CURRENT_COMPOSITION",
            "Gateway replay retrospective prohibition missing")
    return gateway_close


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--daily-artifact", type=Path, required=True)
    p.add_argument("--gateway-outputs", type=Path, required=True)
    args = p.parse_args()
    close = validate(args.daily_artifact, args.gateway_outputs)
    print(f"GATEWAY_ISOLATED_SOURCE=PASS close={close} LOCK_CREDIT=0")


if __name__ == "__main__":
    main()
