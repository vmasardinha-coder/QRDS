from __future__ import annotations

import json
from pathlib import Path

P = Path(__file__).with_name("CROSS_ASSET_REGIME_GATE_PREREG.v1.json")


def main() -> None:
    z = json.loads(P.read_text(encoding="utf-8"))
    assert z["schema_version"] == "1.0"
    assert z["family_id"] == "H-XREGIME-01"
    assert z["family_name"] == "cross_asset_regime_gate"
    assert z["status"] == "REGISTERED_FOR_FACTORY_RESEARCH"
    assert z["research_only"] is True
    assert z["shadow_only"] is True
    assert z["engine_weight"] == 0
    assert z["auto_promote"] is False
    assert z["external_performance_imported"] is False
    assert z["winning_external_parameters_seeded"] is False
    assert z["promotion_boundary"]["candidate_on_registration"] is True
    assert z["promotion_boundary"]["survivor_on_registration"] is False
    assert z["promotion_boundary"]["may_modify_existing_factory_families"] is False
    assert z["promotion_boundary"]["requires_independent_factory_validation"] is True
    assert z["promotion_boundary"]["requires_separate_promotion_decision"] is True
    required = set(z["required_validation"])
    for item in {
        "point_in_time_alignment",
        "leakage_audit",
        "walk_forward",
        "costs_and_slippage",
        "cross_asset_replication",
        "multiple_hypothesis_control",
        "shadow_validation_before_any_promotion",
    }:
        assert item in required
    assert z["external_provenance"]["interpretation"].startswith("Evidence supports a candidate")
    print("CROSS_ASSET_REGIME_GATE_PREREG: PASS")


if __name__ == "__main__":
    main()
