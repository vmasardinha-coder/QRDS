from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts import phase366_375_remediation_evaluation_common as common

PROVIDERS = ("BINANCE", "BYBIT", "COINBASE", "OKX")


def payload(phase: int, **updates: Any) -> dict[str, Any]:
    value = {
        "project": "QRDS/QOS/GATE BTC",
        "phase": phase,
        "status": "TEST_RESEARCH_ONLY",
        "locks": dict(common.LOCKS),
        "strategy_approved": False,
        "forward_shadow_eligible": False,
        "forward_shadow_started": False,
        "paper_trading_started": False,
    }
    value.update(updates)
    return value


def write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    return path


def patch_roots(monkeypatch: Any, repo: Path, project: Path, *modules: Any) -> None:
    monkeypatch.setattr(common, "ROOT", project)
    monkeypatch.setattr(common, "GIT_ROOT", repo)
    for module in modules:
        if hasattr(module, "ROOT"):
            monkeypatch.setattr(module, "ROOT", project)
        if hasattr(module, "GIT_ROOT"):
            monkeypatch.setattr(module, "GIT_ROOT", repo)


def create_prior_state(base: Path) -> dict[str, Path]:
    repo = base / "repo"
    project = repo / "crypto_decision_lab"
    project.mkdir(parents=True, exist_ok=True)
    (repo / "QRDS_START_HERE.md").write_text(
        "# QRDS Start\n\n"
        "<!-- QRDS_CURRENT_STATUS_BEGIN -->\n"
        "- Existing launcher: `C:\\QRDS\\ABRIR_QRDS.ps1`\n"
        "<!-- QRDS_CURRENT_STATUS_END -->\n",
        encoding="utf-8",
    )

    datasets: dict[str, Any] = {}
    start = 1_700_000_000_000 // 3_600_000 * 3_600_000
    for provider_index, provider in enumerate(PROVIDERS):
        rows = []
        for hour in range(800):
            if provider == "OKX" and hour in {10, 20, 30}:
                continue
            timestamp = start + hour * 3_600_000
            close = 40_000.0 + hour * 2.0 + provider_index * 0.25
            rows.append(
                {
                    "provider": provider,
                    "market_type": "TEST",
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "open_time_ms": timestamp,
                    "open_time_utc": common.iso_from_ms(timestamp),
                    "open": close - 1.0,
                    "high": close + 2.0,
                    "low": close - 2.0,
                    "close": close,
                    "volume": 1000 + hour,
                    "quote_volume": (1000 + hour) * close,
                    "complete": True,
                }
            )
        relative = f"data/{provider.lower()}_candles.csv.gz"
        path = project / relative
        common.write_deterministic_csv_gz(
            path,
            rows,
            (
                "provider",
                "market_type",
                "symbol",
                "interval",
                "open_time_ms",
                "open_time_utc",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_volume",
                "complete",
            ),
        )
        datasets[f"{provider.lower()}_candles"] = {
            "name": f"{provider.lower()}_candles",
            "path": relative,
            "sha256": common.sha256_file(path),
            "rows": len(rows),
        }

    p301 = write_json(
        base / "phase301.json",
        payload(
            301,
            datasets=datasets,
            successful_candle_providers=list(PROVIDERS),
            max_candle_rows=800,
            complete=True,
        ),
    )
    success_criteria = {
        "minimum_provider_count": 3,
        "no_forward_shift": True,
        "no_interpolation": True,
        "valid_hour_ratio_not_lower_than_baseline": True,
        "timestamp_mismatch_count_must_decrease": True,
    }
    contract = {
        "selected_remediation_id": "TIMESTAMP_CONSENSUS_ALIGNMENT_REMEDIATION_V1",
        "preregistration_fingerprint": "test-preregistration",
        "future_experiment_budget": 1,
        "success_criteria": success_criteria,
        "primary_metrics": list(common.QUALITY_METRIC_NAMES),
        "one_evaluation_only": True,
        "closed_family_metrics_prohibited": True,
        "execution_metrics_prohibited": True,
    }
    contract_fingerprint = common.fingerprint(contract)
    p360 = write_json(
        base / "phase360.json",
        payload(
            360,
            future_experiment_budget=1,
            active_experiment_budget=0,
            success_criteria=success_criteria,
            primary_metrics=list(common.QUALITY_METRIC_NAMES),
            stop_rule="ONE_EVALUATION_THEN_CLOSE_OR_MANUAL_REVIEW",
        ),
    )
    p363 = write_json(
        base / "phase363.json",
        payload(
            363,
            contract=contract,
            contract_frozen=True,
            contract_fingerprint=contract_fingerprint,
            real_data_remediation_evaluation_started=False,
        ),
    )
    global_suite = {
        "passed": True,
        "test_file_count": 604,
        "totals": {"tests": 1511, "failures": 0, "errors": 0, "skipped": 0},
        "manifest_stable": True,
    }
    p365 = write_json(
        base / "phase365.json",
        payload(
            365,
            contract_frozen=True,
            active_hypotheses=0,
            global_full_suite=global_suite,
            real_data_remediation_evaluation_started=False,
        ),
    )
    return {
        "repo": repo,
        "project": project,
        "phase301": p301,
        "phase360": p360,
        "phase363": p363,
        "phase365": p365,
    }


def write_junit(path: Path, tests: int = 10) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="targeted" tests="{tests}" failures="0" errors="0" skipped="0"></testsuite></testsuites>',
        encoding="utf-8",
    )
    return path


def run_chain(monkeypatch: Any, base: Path, decision: str = "APPROVE_ONE_FROZEN_REMEDIATION_EVALUATION") -> dict[str, Any]:
    from crypto_decision_lab.scripts import phase366_manual_frozen_remediation_execution_review_research_only as p366m
    from crypto_decision_lab.scripts import phase367_one_real_data_remediation_evaluation_research_only as p367m
    from crypto_decision_lab.scripts import phase368_raw_vs_remediated_data_quality_comparison_research_only as p368m
    from crypto_decision_lab.scripts import phase369_no_closed_family_performance_metric_proof_research_only as p369m
    from crypto_decision_lab.scripts import phase370_public_recollection_need_decision_research_only as p370m
    from crypto_decision_lab.scripts import phase371_remediation_lineage_and_hash_audit_research_only as p371m
    from crypto_decision_lab.scripts import phase372_remediation_reproducibility_audit_research_only as p372m
    from crypto_decision_lab.scripts import phase373_remediation_stop_rule_and_budget_audit_research_only as p373m
    from crypto_decision_lab.scripts import phase374_data_quality_remediation_result_portal_research_only as p374m
    from crypto_decision_lab.scripts import phase375_data_quality_remediation_integrated_checkpoint_research_only as p375m

    state = create_prior_state(base)
    patch_roots(
        monkeypatch,
        state["repo"],
        state["project"],
        p366m,
        p367m,
        p368m,
        p369m,
        p370m,
        p371m,
        p372m,
        p373m,
        p374m,
        p375m,
    )

    artifacts = state["project"] / "artifacts"
    p366 = p366m.build(state["phase363"], state["phase365"], decision, "Victor Sardinha", artifacts / "366")
    p366_path = write_json(base / "phase366.json", p366)
    p367 = p367m.build(state["phase301"], state["phase363"], p366_path, artifacts / "367", project_root=state["project"])
    p367_path = write_json(base / "phase367.json", p367)
    p368 = p368m.build(state["phase363"], p367_path, artifacts / "368")
    p368_path = write_json(base / "phase368.json", p368)
    p369 = p369m.build(p367_path, p368_path, artifacts / "369")
    p369_path = write_json(base / "phase369.json", p369)
    p370 = p370m.build(p367_path, p368_path, p369_path, artifacts / "370")
    p370_path = write_json(base / "phase370.json", p370)
    p371 = p371m.build(state["phase301"], state["phase363"], p367_path, artifacts / "371", project_root=state["project"])
    p371_path = write_json(base / "phase371.json", p371)
    p372 = p372m.build(state["phase301"], state["phase363"], p367_path, artifacts / "372", project_root=state["project"])
    p372_path = write_json(base / "phase372.json", p372)
    p373 = p373m.build(
        state["phase360"],
        p366_path,
        p367_path,
        p368_path,
        p369_path,
        p370_path,
        p371_path,
        p372_path,
        artifacts / "373",
    )
    p373_path = write_json(base / "phase373.json", p373)
    p374 = p374m.build(
        state["phase365"],
        p366_path,
        p367_path,
        p368_path,
        p369_path,
        p370_path,
        p373_path,
        artifacts / "374",
        project_root=state["project"],
        git_root=state["repo"],
    )
    p374_path = write_json(base / "phase374.json", p374)
    junit = write_junit(base / "targeted.xml")
    p375 = p375m.build_checkpoint(
        {
            365: state["phase365"],
            366: p366_path,
            367: p367_path,
            368: p368_path,
            369: p369_path,
            370: p370_path,
            371: p371_path,
            372: p372_path,
            373: p373_path,
            374: p374_path,
        },
        targeted_junit_path=junit,
        artifact_path=artifacts / "375" / "phase375.json",
        documentation_path=state["project"] / "docs/reports/integration/phase375_summary.md",
        tracking_dir=state["project"] / "docs/reports/project_tracking",
    )
    return {
        **state,
        "phase366_payload": p366,
        "phase366": p366_path,
        "phase367_payload": p367,
        "phase367": p367_path,
        "phase368_payload": p368,
        "phase368": p368_path,
        "phase369_payload": p369,
        "phase369": p369_path,
        "phase370_payload": p370,
        "phase370": p370_path,
        "phase371_payload": p371,
        "phase371": p371_path,
        "phase372_payload": p372,
        "phase372": p372_path,
        "phase373_payload": p373,
        "phase373": p373_path,
        "phase374_payload": p374,
        "phase374": p374_path,
        "phase375_payload": p375,
    }
