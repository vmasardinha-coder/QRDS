from pathlib import Path
import json

from crypto_decision_lab.scripts.phase44_research_hypothesis_backlog import READY_GATE, build_phase44


def test_phase44_builds_research_hypothesis_backlog(tmp_path):
    result = build_phase44(tmp_path / "phase44")
    out = Path(result["output_dir"])
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["page_count"] == 10
    assert result["hypothesis_count"] >= 6
    assert result["operational_hypotheses"] == 0
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0
    for name in [
        "index.html",
        "hypothesis_backlog.html",
        "polymarket_like_research.html",
        "portfolio_goal_context.html",
        "excluded_or_deferred.html",
        "research_hypothesis_backlog.csv",
        "research_hypothesis_registry.json",
        "phase44_checksums.json",
    ]:
        assert (out / name).exists(), name
    registry = json.loads((out / "research_hypothesis_registry.json").read_text(encoding="utf-8"))
    assert registry["trading_signal_generated"] is False
    assert registry["recommendation_generated"] is False
    assert registry["allocation_generated"] is False
    assert registry["shadow_decision_allowed"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["canonical_data_writes"] == 0
    assert all(h["operational_allowed"] is False for h in registry["hypotheses"])
