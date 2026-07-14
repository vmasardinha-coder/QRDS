from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    write_json,
)
from crypto_decision_lab.scripts.phase212_replay_stability_across_windows_research_only import (
    build_phase212,
)


def test_phase212_reports_variation_without_edge_claim(tmp_path: Path):
    p209 = tmp_path / "phase209.json"
    p211 = tmp_path / "phase211.json"
    write_json(
        p209,
        {
            "historical_replay_passed": True,
            "results": [
                {"normalized_mae": 0.01},
                {"normalized_mae": 0.012},
                {"normalized_mae": 0.011},
            ],
        },
    )
    write_json(p211, {"counterfactual_audit_passed": True})

    result = build_phase212(
        p209,
        p211,
        tmp_path / "phase212.json",
        tmp_path / "phase212.md",
        root=tmp_path,
    )

    assert result["stability_audit_passed"] is True
    assert result["variation_band"] in {
        "LOW_VARIATION",
        "MODERATE_VARIATION",
        "HIGH_VARIATION",
    }
    assert result["locks"]["edge_validated"] is False
