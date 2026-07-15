from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import LOCKS
from crypto_decision_lab.scripts.phase303_finite_hypothesis_registry_v2_research_only import registry


def payload(phase: int, **fields: Any) -> dict[str, Any]:
    base = {
        "phase": phase,
        "project": "QRDS/QOS/GATE BTC",
        "status": f"PHASE_{phase}_TEST",
        "descriptive_only": True,
        "valid_for_decision": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "historical_result_authorizes_execution": False,
        "locks": dict(LOCKS),
        "gate": f"PHASE{phase}_TEST_GATE_RESEARCH_ONLY",
        "artifact_fingerprint": f"fingerprint-{phase}",
    }
    base.update(fields)
    return base


def write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def patch_roots(monkeypatch, root: Path, *modules: Any) -> None:
    import crypto_decision_lab.scripts.phase306_315_stability_common as common

    monkeypatch.setattr(common, "ROOT", root)
    for module in modules:
        monkeypatch.setattr(module, "ROOT", root)


def phase303_payload() -> dict[str, Any]:
    hypotheses = registry()
    return payload(
        303,
        experiment_budget=24,
        registered_hypotheses=24,
        registry_closed=True,
        hypotheses=hypotheses,
    )


def phase304_payload() -> dict[str, Any]:
    hypotheses = phase303_payload()["hypotheses"]
    ids = [item["hypothesis_id"] for item in hypotheses]
    selections = [
        "OI_MOM_H8_T005",
        "MOM_LB4_H4_T004",
        "OI_MOM_H8_T005",
        "TREND_SMA24_H4_T003",
    ]
    folds = []
    for fold_number, selected in enumerate(selections, start=1):
        results = {}
        for index, hypothesis_id in enumerate(ids):
            results[hypothesis_id] = {
                "mean_per_10000_brl": float(index + fold_number),
                "lower_95_per_10000_brl": float(index - 5),
                "pvalue_positive": 0.5,
                "trade_count": 10,
            }
        start = 300 + (fold_number - 1) * 100
        folds.append(
            {
                "fold": fold_number,
                "train_start": 168,
                "train_end": start - 30,
                "inner_start": start - 29,
                "inner_end": start - 1,
                "outer_start": start,
                "outer_end": start + 99,
                "embargo_hours": 24,
                "selected_hypothesis_id": selected,
                "selected_family": next(
                    item["family"] for item in hypotheses if item["hypothesis_id"] == selected
                ),
                "inner_selection": {
                    "results": results,
                    "multiple_testing": {"rejected_ids": []},
                    "selected_id": selected,
                },
                "outer_cost_metrics": {},
            }
        )
    return payload(
        304,
        selection_history=selections,
        modal_hypothesis_id="OI_MOM_H8_T005",
        modal_selection_share=0.5,
        selection_stable=False,
        modal_survives_multiple_testing=False,
        multiple_testing={"rejected_ids": [], "rejected_count": 0},
        robustness_pass=False,
        outer_metrics_10bps={
            "trade_count": 80,
            "mean_per_10000_brl": -10.4,
            "lower_95_per_10000_brl": -18.19,
        },
        regime_robustness={
            "HIGH_VOL": {
                "trade_count": 20,
                "mean_per_10000_brl": 2.0,
                "lower_95_per_10000_brl": -3.0,
            },
            "RANGE": {
                "trade_count": 45,
                "mean_per_10000_brl": -5.0,
                "lower_95_per_10000_brl": -9.0,
            },
            "TREND": {
                "trade_count": 15,
                "mean_per_10000_brl": 1.0,
                "lower_95_per_10000_brl": -4.0,
            },
        },
        fold_results=folds,
        strategy_approved=False,
        forward_shadow_eligible=False,
    )


def write_matrix(root: Path, rows: int = 800) -> str:
    relative = Path("artifacts/fixture/feature_matrix.csv.gz")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "open_time_ms",
        "close",
        "quote_volume",
        "return_24h",
        "realized_vol_24h",
        "funding_mean_3",
        "open_interest_change_24h",
        "sma_distance_24h",
        "sma_distance_168h",
    ]
    closes = []
    price = 100.0
    for index in range(rows):
        price *= 1.003 if (index // 12) % 2 == 0 else 0.997
        closes.append(price)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, close in enumerate(closes):
            return_24h = close / closes[index - 24] - 1 if index >= 24 else ""
            sma24 = sum(closes[max(0, index - 23) : index + 1]) / min(24, index + 1)
            sma168 = sum(closes[max(0, index - 167) : index + 1]) / min(168, index + 1)
            writer.writerow(
                {
                    "open_time_ms": index * 3_600_000,
                    "close": close,
                    "quote_volume": 1_000_000 + (index % 100) * 10_000,
                    "return_24h": return_24h,
                    "realized_vol_24h": 0.01,
                    "funding_mean_3": 0.0002 if index % 2 == 0 else -0.0002,
                    "open_interest_change_24h": 0.01 if return_24h == "" or float(return_24h) >= 0 else -0.01,
                    "sma_distance_24h": close / sma24 - 1,
                    "sma_distance_168h": close / sma168 - 1,
                }
            )
    return relative.as_posix()


def phase302_payload(matrix_path: str) -> dict[str, Any]:
    return payload(302, matrix_path=matrix_path, feature_count=18)


def write_junit(path: Path, tests: int = 10) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<testsuite name="batch306_315" tests="{tests}" failures="0" errors="0" skipped="0"></testsuite>\n',
        encoding="utf-8",
    )
    return path
