from pathlib import Path

from crypto_decision_lab.scripts.phase48_portfolio_context_schema_research_only import READY_GATE, build_phase48


def test_phase48_builds_portfolio_context_schema(tmp_path):
    result = build_phase48(tmp_path / "phase48")
    out = Path(result["output_dir"])
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["page_count"] == 10
    assert result["schema_ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["allocation_generated"] is False
    assert result["portfolio_recommendation_generated"] is False
    assert result["canonical_data_writes"] == 0
    for name in [
        "index.html",
        "capital_buckets.html",
        "crypto_high_risk_bucket.html",
        "portfolio_fields.html",
        "risk_context.html",
        "liquidity_context.html",
        "human_owned_inputs.html",
        "forbidden_outputs.html",
        "future_portfolio_review.html",
        "safety_lock.html",
        "portfolio_context_schema.json",
        "portfolio_context_example_research_only.json",
        "phase48_safety_status.json",
        "phase48_checksums.json",
    ]:
        assert (out / name).exists(), name
