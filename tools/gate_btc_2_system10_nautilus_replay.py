#!/usr/bin/env python3
"""Read-only Stage 9 admission replay through a real NautilusTrader BacktestEngine.

This proves routing and state parity for admitted capture metadata only. The ledger
has no order-book ticks or fill observations; no trading/economic claim follows.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from tools.gate_btc_2_stage9_admission_ledger import parse_ledger, validate_ledger
from tools.gate_btc_2_stage9_exit_gate import verify_status
from tools.gate_btc_2_system10_event_envelope import build_event_envelope

SCHEMA = "gate_btc.2_0.system10.nautilus_metadata_replay.v1"


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError(reason)


def timestamp_ns(value: str) -> int:
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    delta = t - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000


def digest_events(events: list[tuple[int, int, str]]) -> str:
    state = "GENESIS"
    for seq, run_id, event_hash in events:
        state = hashlib.sha256(
            json.dumps([state, seq, run_id, event_hash], separators=(",", ":")).encode()
        ).hexdigest()
    return state


@dataclass(frozen=True)
class AdmissionEvent:
    sequence: int
    run_id: int
    event_sha256: str
    ts_event: int
    ts_init: int


def replay(ledger: Path, head_path: Path, completion_path: Path) -> dict:
    head = json.loads(head_path.read_text())
    require(head.get("schema") == "gate_btc.2_0.stage9_canonical_ledger_head.v1", "head schema")
    rows = parse_ledger(ledger)
    validate_ledger(rows)
    require(len(rows) == head["record_count"] and bool(rows), "head count mismatch")
    require(rows[-1]["record_sha256"] == head["tip_sha256"], "head tip mismatch")
    require(rows[-1]["captured_at_utc"] == head["latest_captured_at_utc"], "head clock mismatch")
    completion = json.loads(completion_path.read_text())
    verify_status(completion)
    require(completion["decision"] == "PASS_STAGE9_EXIT_GATE", "Stage 9 incomplete")
    require(completion["original_stage9_canonical_counter"] <= len(rows), "completion after head")

    envelope = build_event_envelope(rows)
    source = envelope["events"]
    require(len(source) > 0, "empty replay forbidden")
    expected = [(e["sequence"], e["run_id"], e["event_sha256"]) for e in source]

    import nautilus_trader
    from nautilus_trader.backtest import BacktestEngine
    from nautilus_trader.common import DataActor
    from nautilus_trader.config import BacktestEngineConfig, DataActorConfig
    from nautilus_trader.model import CustomData, DataType

    data_type = DataType("Stage9AdmittedCapture", metadata={"source": "QRDS_STAGE9"})
    class Observer(DataActor):
        def __init__(self):
            super().__init__(DataActorConfig(actor_id="STAGE9-PARITY-OBSERVER"))
            self.observed = []

        def on_start(self):
            self.subscribe_data(data_type)

        def on_data(self, data):
            if data.data_type == data_type:
                item = data.data
                self.observed.append((item.sequence, item.run_id, item.event_sha256))

    actor = Observer()
    engine = BacktestEngine(BacktestEngineConfig())
    engine.add_actor(actor)
    wrapped = [
        CustomData(data_type, AdmissionEvent(
            e["sequence"], e["run_id"], e["event_sha256"],
            timestamp_ns(e["event_time_utc"]), timestamp_ns(e["event_time_utc"]),
        ))
        for e in source
    ]
    engine.add_data(wrapped)
    engine.run()
    observed = actor.observed
    require(observed == expected, "Nautilus event routing/order mismatch")
    expected_state = digest_events(expected)
    observed_state = digest_events(observed)
    require(observed_state == expected_state, "Nautilus state digest mismatch")
    result = {
        "schema": SCHEMA,
        "decision": "PASS_ADMISSION_METADATA_REPLAY_PARITY",
        "nautilus_version": nautilus_trader.__version__,
        "ledger_run_id": head["ledger_run_id"],
        "ledger_record_count": len(rows),
        "ledger_tip_sha256": head["tip_sha256"],
        "source_envelope_sha256": envelope["envelope_sha256"],
        "event_count": len(expected),
        "reference_state_sha256": expected_state,
        "nautilus_observed_state_sha256": observed_state,
        "engine_instantiated": True,
        "engine_run": True,
        "system10_complete": False,
        "scope": "ADMISSION_METADATA_ONLY_NO_LOB_OR_FILL_PARITY",
        "research_only": True,
        "shadow_only": True,
        "economics_allowed": False,
        "orders": 0,
        "real_capital_brl": 0,
    }
    result["receipt_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--head", type=Path, required=True)
    p.add_argument("--completion", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = replay(args.ledger, args.head, args.completion)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("SYSTEM10_METADATA_REPLAY="+result["decision"])
    print("EVENTS="+str(result["event_count"])+" ORDERS=0 CAPITAL=0")


if __name__ == "__main__":
    main()
