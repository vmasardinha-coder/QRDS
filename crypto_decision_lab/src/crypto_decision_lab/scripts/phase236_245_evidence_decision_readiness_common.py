from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

OPERATIONAL_STATUS = "BLOCKED_RESEARCH_ONLY"

LOCKS: dict[str, Any] = {
    "operational_status": OPERATIONAL_STATUS,
    "data_trust_validated": False,
    "predictive_validity_established": False,
    "edge_validated": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

ACCEPTED_RESIDUAL_RISKS = [
    "RARE_NATIVE_PYTHON_WINDOWS_RUNTIME_CRASH",
    "FUTURE_REGRESSION_OUTSIDE_CURRENT_BATCH_SCOPE",
]

PRIOR_ARTIFACTS: tuple[tuple[int, str], ...] = (
    (
        216,
        "artifacts/phase216_225_robustness_trust/"
        "phase216_replay_provenance_completeness_audit.json",
    ),
    (
        217,
        "artifacts/phase216_225_robustness_trust/"
        "phase217_multi_source_agreement_diagnostics.json",
    ),
    (
        218,
        "artifacts/phase216_225_robustness_trust/"
        "phase218_outlier_contamination_sensitivity.json",
    ),
    (
        219,
        "artifacts/phase216_225_robustness_trust/"
        "phase219_window_boundary_perturbation_audit.json",
    ),
    (
        220,
        "artifacts/phase216_225_robustness_trust/"
        "phase220_robustness_batch_checkpoint.json",
    ),
    (
        221,
        "artifacts/phase216_225_robustness_trust/"
        "phase221_model_free_benchmark_comparison.json",
    ),
    (
        222,
        "artifacts/phase216_225_robustness_trust/"
        "phase222_calibration_uncertainty_diagnostics.json",
    ),
    (
        223,
        "artifacts/phase216_225_robustness_trust/"
        "phase223_cost_slippage_sensitivity.json",
    ),
    (
        224,
        "artifacts/phase216_225_robustness_trust/"
        "phase224_robustness_evidence_scorecard_v2.json",
    ),
    (
        225,
        "artifacts/phase216_225_robustness_trust/"
        "phase225_robustness_full_integration_checkpoint.json",
    ),
)

TECHNICAL_RELIABILITY_ARTIFACT = (
    "artifacts/phase226_235_technical_reliability/"
    "phase234_technical_reliability_scorecard.json"
)


def project_root(value: str | Path | None = None) -> Path:
    return (
        Path(value).resolve()
        if value is not None
        else Path.cwd().resolve()
    )


def base_payload(phase: int, status: str) -> dict[str, Any]:
    return {
        "phase": phase,
        "status": status,
        "passed": False,
        "accepted_residual_risks": copy.deepcopy(
            ACCEPTED_RESIDUAL_RISKS
        ),
        "locks": copy.deepcopy(LOCKS),
    }


def load_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object: {source}")
    return payload


def write_json(
    path: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, output)
    return output


def write_markdown(
    path: str | Path,
    title: str,
    payload: Mapping[str, Any],
    lines: Iterable[str],
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    body = [
        f"# {title}",
        "",
        f"- Phase: {payload['phase']}",
        f"- Status: `{payload['status']}`",
        f"- Passed: `{payload['passed']}`",
        f"- Operational: `{LOCKS['operational_status']}`",
        f"- Data trust validated: `{LOCKS['data_trust_validated']}`",
        f"- Predictive validity established: "
        f"`{LOCKS['predictive_validity_established']}`",
        f"- Edge validated: `{LOCKS['edge_validated']}`",
        f"- Decision layer allowed: "
        f"`{LOCKS['decision_layer_allowed']}`",
        f"- Canonical writes: `{LOCKS['canonical_data_writes']}`",
        "",
        *list(lines),
        "",
        "## Accepted residual risks",
        "",
        "- Rare native Python/Windows runtime crashes.",
        "- Future regressions outside the current batch scope.",
        "",
    ]
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text("\n".join(body), encoding="utf-8")
    os.replace(temporary, output)
    return output


def add_standard_output_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--documentation", required=True)
    parser.add_argument("--project-root")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_passed(payload: Mapping[str, Any]) -> bool:
    direct = payload.get("passed")
    if isinstance(direct, bool):
        return direct

    for key, value in payload.items():
        if not isinstance(value, bool):
            continue
        lowered = str(key).lower()
        if (
            lowered.endswith("_pass")
            or lowered.endswith("_passed")
            or lowered in {"checkpoint_pass", "audit_pass"}
        ):
            if value:
                return True

    return False


def historical_evidence_inventory(
    root: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for expected_phase, relative in PRIOR_ARTIFACTS:
        path = root / relative
        if not path.is_file():
            rows.append(
                {
                    "phase": expected_phase,
                    "relative_path": relative,
                    "exists": False,
                    "passed": False,
                }
            )
            continue

        payload = load_json(path)
        rows.append(
            {
                "phase": expected_phase,
                "reported_phase": payload.get("phase"),
                "relative_path": relative,
                "exists": True,
                "sha256": sha256_path(path),
                "passed": payload_passed(payload),
                "status": payload.get(
                    "status",
                    payload.get("checkpoint_status", ""),
                ),
                "operational_status": (
                    payload.get("locks", {}).get(
                        "operational_status"
                    )
                    if isinstance(payload.get("locks"), dict)
                    else payload.get("operational_status")
                ),
                "canonical_data_writes": (
                    payload.get("locks", {}).get(
                        "canonical_data_writes"
                    )
                    if isinstance(payload.get("locks"), dict)
                    else payload.get("canonical_data_writes")
                ),
                "score": payload.get("score"),
                "classification": payload.get("classification"),
            }
        )
    return rows


def criteria_registry() -> list[dict[str, Any]]:
    return [
        {
            "id": "SOURCE_IDENTITY",
            "required": True,
            "description": (
                "Every admitted observation names its source and "
                "acquisition method."
            ),
        },
        {
            "id": "LINEAGE",
            "required": True,
            "description": (
                "Every derived value can be traced to source records "
                "and deterministic transformations."
            ),
        },
        {
            "id": "FRESHNESS",
            "required": True,
            "description": (
                "Evidence carries an explicit observation timestamp "
                "and maximum accepted age."
            ),
        },
        {
            "id": "COMPLETENESS",
            "required": True,
            "description": (
                "Required fields and observation windows meet the "
                "declared completeness threshold."
            ),
        },
        {
            "id": "MULTI_SOURCE_AGREEMENT",
            "required": True,
            "description": (
                "Independent sources agree within a declared tolerance."
            ),
        },
        {
            "id": "OUTLIER_STABILITY",
            "required": True,
            "description": (
                "Results remain stable under contamination and outlier "
                "sensitivity checks."
            ),
        },
        {
            "id": "WINDOW_ROBUSTNESS",
            "required": True,
            "description": (
                "Results remain stable under reasonable window boundary "
                "perturbations."
            ),
        },
        {
            "id": "PREDICTIVE_VALIDITY",
            "required": True,
            "description": (
                "Out-of-sample walk-forward evidence beats declared "
                "model-free baselines."
            ),
        },
        {
            "id": "CALIBRATION",
            "required": True,
            "description": (
                "Predicted probabilities are calibrated and uncertainty "
                "is explicitly represented."
            ),
        },
        {
            "id": "NET_ECONOMIC_EDGE",
            "required": True,
            "description": (
                "Any claimed edge remains positive after realistic "
                "fees, spread, slippage and latency."
            ),
        },
    ]
