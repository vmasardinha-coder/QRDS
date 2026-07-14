from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    write_json,
)
from crypto_decision_lab.scripts.phase213_regime_segmentation_audit_research_only import (
    build_phase213,
)


def test_phase213_covers_multiple_descriptive_regimes(tmp_path: Path):
    p209 = tmp_path / "phase209.json"
    p212 = tmp_path / "phase212.json"
    write_json(
        p209,
        {
            "historical_replay_passed": True,
            "results": [
                {
                    "realized_volatility": 0.01,
                    "normalized_mae": 0.01,
                    "directional_agreement": 0.4,
                },
                {
                    "realized_volatility": 0.02,
                    "normalized_mae": 0.02,
                    "directional_agreement": 0.5,
                },
                {
                    "realized_volatility": 0.03,
                    "normalized_mae": 0.03,
                    "directional_agreement": 0.6,
                },
            ],
        },
    )
    write_json(p212, {"stability_audit_passed": True})

    result = build_phase213(
        p209,
        p212,
        tmp_path / "phase213.json",
        tmp_path / "phase213.md",
        root=tmp_path,
    )

    assert result["regime_segmentation_passed"] is True
    assert result["covered_regimes"] >= 2
    assert result["locks"]["recommendation_generated"] is False
