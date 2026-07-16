from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common import (
    LOCKS,
    canonical_hash,
    sha256_file,
    write_csv_gz,
    write_json,
)
from crypto_decision_lab.scripts.phase331_sealed_non_directional_hypothesis_templates_research_only import sealed_templates


def payload(phase: int, **values: Any) -> dict[str, Any]:
    item = {
        "phase": phase,
        "status": f"FIXTURE_PHASE_{phase}",
        "historical_result_authorizes_execution": False,
        "locks": dict(LOCKS),
        "artifact_fingerprint": f"fixture-{phase}",
    }
    item.update(values)
    return item


def patch_roots(monkeypatch: Any, root: Path) -> None:
    module_names = [
        "crypto_decision_lab.scripts.phase301_305_evidence_v2_common",
        "crypto_decision_lab.scripts.phase306_315_stability_common",
        "crypto_decision_lab.scripts.phase316_325_negative_evidence_common",
        "crypto_decision_lab.scripts.phase326_335_preregistration_common",
        "crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common",
        "crypto_decision_lab.scripts.phase336_finite_registry_opening_research_only",
        "crypto_decision_lab.scripts.phase337_asof_quality_feature_matrix_research_only",
        "crypto_decision_lab.scripts.phase338_frozen_h8_target_builder_research_only",
        "crypto_decision_lab.scripts.phase339_nested_walk_forward_abstention_research_only",
        "crypto_decision_lab.scripts.phase340_holm_calibration_null_comparison_research_only",
        "crypto_decision_lab.scripts.phase341_regime_provider_missingness_robustness_research_only",
        "crypto_decision_lab.scripts.phase342_abstention_coverage_reliability_tradeoff_research_only",
        "crypto_decision_lab.scripts.phase343_research_candidate_eligibility_research_only",
        "crypto_decision_lab.scripts.phase344_abstention_visual_interpretation_portal_research_only",
        "crypto_decision_lab.scripts.phase345_abstention_full_integration_checkpoint_research_only",
    ]
    import importlib

    for name in module_names:
        module = importlib.import_module(name)
        if hasattr(module, "ROOT"):
            monkeypatch.setattr(module, "ROOT", root)


def create_previous_state(root: Path, *, hours: int = 900) -> dict[int, Path]:
    fixture = root / "fixture_input"
    fixture.mkdir(parents=True, exist_ok=True)
    start = 1_700_000_000_000
    providers = ("binance", "bybit", "coinbase", "okx")
    datasets: dict[str, Any] = {}
    for provider_index, provider in enumerate(providers):
        rows = []
        for index in range(hours + 8):
            timestamp = start + index * 3_600_000
            base = 30_000 + index * 1.2 + 240 * math.sin(index / 33) + 45 * math.sin(index / 7)
            dynamic = (provider_index - 1.5) * (0.8 + 4.0 * (1 + math.sin(index / 19)))
            close = base + dynamic
            rows.append({"open_time_ms": timestamp, "close": close, "provider": provider.upper()})
        path = fixture / f"{provider}_candles.csv.gz"
        write_csv_gz(path, rows, ("open_time_ms", "close", "provider"))
        datasets[f"{provider}_candles"] = {"path": str(path), "rows": len(rows), "sha256": sha256_file(path)}

    for provider_index, provider in enumerate(("binance", "bybit")):
        rows = []
        for index in range(0, hours + 8, 8):
            timestamp = start + index * 3_600_000
            rows.append({"funding_time_ms": timestamp, "funding_rate": 0.00005 * math.sin(index / 17 + provider_index)})
        path = fixture / f"{provider}_funding.csv.gz"
        write_csv_gz(path, rows, ("funding_time_ms", "funding_rate"))
        datasets[f"{provider}_funding"] = {"path": str(path), "rows": len(rows), "sha256": sha256_file(path)}

    oi_rows = [
        {"timestamp_ms": start + index * 3_600_000, "open_interest": 100_000 + index * 15 + 800 * math.sin(index / 25)}
        for index in range(hours + 8)
    ]
    oi_path = fixture / "bybit_open_interest.csv.gz"
    write_csv_gz(oi_path, oi_rows, ("timestamp_ms", "open_interest"))
    datasets["bybit_open_interest"] = {"path": str(oi_path), "rows": len(oi_rows), "sha256": sha256_file(oi_path)}

    phase301 = payload(301, datasets=datasets, complete=True)
    p301 = fixture / "phase301.json"
    write_json(p301, phase301)

    feature_rows = []
    previous_close = None
    returns: list[float] = []
    for index in range(hours + 8):
        timestamp = start + index * 3_600_000
        close = 30_000 + index * 1.2 + 240 * math.sin(index / 33) + 45 * math.sin(index / 7)
        ret = 0.0 if previous_close is None else math.log(close / previous_close)
        previous_close = close
        returns.append(ret)
        window = returns[max(0, len(returns) - 24) :]
        mean = sum(window) / len(window)
        vol = math.sqrt(sum((value - mean) ** 2 for value in window) / len(window)) if window else 0.0
        feature_rows.append(
            {
                "open_time_ms": timestamp,
                "open_time_utc": f"fixture-{index}",
                "realized_vol_24h": vol,
                "return_24h": sum(returns[max(0, len(returns) - 24) :]),
            }
        )
    matrix = fixture / "phase302_matrix.csv.gz"
    write_csv_gz(matrix, feature_rows, ("open_time_ms", "open_time_utc", "realized_vol_24h", "return_24h"))
    p302 = fixture / "phase302.json"
    write_json(p302, payload(302, matrix_path=str(matrix), matrix_sha256=sha256_file(matrix)))

    p321 = fixture / "phase321.json"
    write_json(p321, payload(321, derivatives_context_usable=True))

    templates = sealed_templates()
    prior = {
        328: payload(328, family_definition_frozen=True),
        329: payload(
            329,
            target_label_frozen=True,
            target_contract={
                "target_id": "ABSTAIN_RELIABILITY_FAILURE_H8_V1",
                "forecast_horizon_hours": 8,
            },
        ),
        330: payload(330, budget_definition_frozen=True, maximum_hypothesis_budget=12),
        331: payload(
            331,
            sealed_template_count=12,
            sealed_templates=templates,
            sealed_registry_sha256=canonical_hash(templates),
            registry_open=False,
        ),
        332: payload(332, statistical_plan_frozen=True),
        335: payload(
            335,
            next_window_decision="FINITE_REGISTRY_OPENING_ELIGIBLE_NEXT_WINDOW_RESEARCH_ONLY",
            registry_opening_eligible_next_window=True,
        ),
    }
    paths = {301: p301, 302: p302, 321: p321}
    for phase, item in prior.items():
        path = fixture / f"phase{phase}.json"
        write_json(path, item)
        paths[phase] = path
    return paths


def run_chain(root: Path, paths: dict[int, Path], *, through: int = 344) -> dict[int, Path]:
    from crypto_decision_lab.scripts import phase336_finite_registry_opening_research_only as p336
    from crypto_decision_lab.scripts import phase337_asof_quality_feature_matrix_research_only as p337
    from crypto_decision_lab.scripts import phase338_frozen_h8_target_builder_research_only as p338
    from crypto_decision_lab.scripts import phase339_nested_walk_forward_abstention_research_only as p339
    from crypto_decision_lab.scripts import phase340_holm_calibration_null_comparison_research_only as p340
    from crypto_decision_lab.scripts import phase341_regime_provider_missingness_robustness_research_only as p341
    from crypto_decision_lab.scripts import phase342_abstention_coverage_reliability_tradeoff_research_only as p342
    from crypto_decision_lab.scripts import phase343_research_candidate_eligibility_research_only as p343
    from crypto_decision_lab.scripts import phase344_abstention_visual_interpretation_portal_research_only as p344

    out = root / "outputs"
    if through >= 336:
        d = out / "336"; p336.build(paths[328], paths[329], paths[330], paths[331], paths[332], paths[335], d); paths[336] = d / "phase336_finite_registry_opening.json"
    if through >= 337:
        d = out / "337"; p337.build(paths[301], paths[302], paths[321], paths[336], d, minimum_rows=500); paths[337] = d / "phase337_asof_quality_feature_matrix.json"
    if through >= 338:
        d = out / "338"; p338.build(paths[301], paths[329], paths[337], d, minimum_rows=500); paths[338] = d / "phase338_frozen_h8_target_builder.json"
    if through >= 339:
        d = out / "339"; p339.build(paths[336], paths[337], paths[338], d, minimum_train_hours=300, outer_hours=150, max_folds=3, logistic_iterations=5); paths[339] = d / "phase339_nested_walk_forward_abstention.json"
    if through >= 340:
        d = out / "340"; p340.build(paths[332], paths[339], d); paths[340] = d / "phase340_holm_calibration_null_comparison.json"
    if through >= 341:
        d = out / "341"; p341.build(paths[339], paths[340], d, minimum_stratum_rows=20); paths[341] = d / "phase341_regime_provider_missingness_robustness.json"
    if through >= 342:
        d = out / "342"; p342.build(paths[336], paths[339], paths[341], d); paths[342] = d / "phase342_abstention_coverage_reliability_tradeoff.json"
    if through >= 343:
        d = out / "343"; p343.build(paths[336], paths[337], paths[338], paths[339], paths[340], paths[341], paths[342], d); paths[343] = d / "phase343_research_candidate_eligibility.json"
    if through >= 344:
        d = out / "344"; p344.build(paths[337], paths[340], paths[342], paths[343], d); paths[344] = d / "phase344_abstention_visual_interpretation_portal.json"
    return paths
