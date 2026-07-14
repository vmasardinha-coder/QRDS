from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase236_245_evidence_decision_readiness_common import (
    add_standard_output_arguments,
    base_payload,
    write_json,
    write_markdown,
)


def build_economic_edge_acceptance_protocol(
    root: Path | None = None,
) -> dict[str, Any]:
    _ = root
    requirements = {
        "gross_edge_positive_required": True,
        "net_edge_positive_required": True,
        "fees_included": True,
        "spread_included": True,
        "slippage_included": True,
        "latency_included": True,
        "tail_loss_budget_required": True,
        "benchmark_superiority_required": True,
        "independent_replication_required": True,
        "real_capital_required_for_protocol_pass": False,
    }
    passed = bool(
        requirements["net_edge_positive_required"]
        and requirements["fees_included"]
        and requirements["spread_included"]
        and requirements["slippage_included"]
        and requirements["latency_included"]
        and requirements["independent_replication_required"]
        and requirements["real_capital_required_for_protocol_pass"]
        is False
    )
    payload = base_payload(
        242,
        (
            "ECONOMIC_EDGE_ACCEPTANCE_PROTOCOL_PASS_RESEARCH_ONLY"
            if passed
            else "ECONOMIC_EDGE_ACCEPTANCE_PROTOCOL_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "requirements": requirements,
            "protocol_ready": passed,
            "edge_validated": False,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_economic_edge_acceptance_protocol(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 242 Economic Edge Acceptance Protocol",
        payload,
        [
            "- Requires positive edge after fees, spread, slippage "
            "and latency.",
            "- Requires tail-loss controls and independent replication.",
            "- Protocol ready: `True`; economic edge validated: `False`.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
