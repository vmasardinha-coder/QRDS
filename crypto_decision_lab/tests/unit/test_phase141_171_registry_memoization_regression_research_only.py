from __future__ import annotations

from crypto_decision_lab.scripts import (
    phase141_replay_validity_requirement_registry_research_only as phase141,
)
from crypto_decision_lab.scripts import (
    phase146_risk_requirement_registry_research_only as phase146,
)
from crypto_decision_lab.scripts import (
    phase151_shadow_decision_requirement_registry_research_only as phase151,
)
from crypto_decision_lab.scripts import (
    phase156_shadow_simulation_requirement_registry_research_only as phase156,
)
from crypto_decision_lab.scripts import (
    phase161_shadow_evidence_replay_requirement_registry_research_only as phase161,
)
from crypto_decision_lab.scripts import (
    phase166_shadow_score_requirement_registry_research_only as phase166,
)
from crypto_decision_lab.scripts import (
    phase171_shadow_readiness_requirement_registry_research_only as phase171,
)


CACHED_BUILDERS = [
    phase141.build_replay_validity_requirement_registry,
    phase146.build_risk_requirement_registry,
    phase151.build_shadow_decision_requirement_registry,
    phase156.build_shadow_simulation_requirement_registry,
    phase161.build_shadow_evidence_replay_requirement_registry,
    phase166.build_shadow_score_requirement_registry,
    phase171.build_shadow_readiness_requirement_registry,
]


def test_registry_builders_expose_process_local_cache_controls():
    for builder in CACHED_BUILDERS:
        assert callable(builder.cache_info)
        assert callable(builder.cache_clear)
        assert builder.cache_parameters()["maxsize"] == 16


def test_phase171_reuses_same_project_root_dependency(monkeypatch, tmp_path):
    calls = {"count": 0}

    def fake_checkpoint(project_root=None):
        calls["count"] += 1
        return {
            "gate": "FAKE_PHASE170_GATE",
            "checkpoint_pass": True,
            "shadow_score_status": (
                "SHADOW_SCORE_BATCH_READY_RESEARCH_ONLY_BLOCKED"
            ),
            "shadow_decision_allowed": False,
            "decision_layer_allowed": False,
            "trading_signal_generated": False,
            "recommendation_generated": False,
            "allocation_generated": False,
            "promotion_allowed": False,
            "canonical_data_writes": 0,
        }

    phase171.build_shadow_readiness_requirement_registry.cache_clear()
    monkeypatch.setattr(
        phase171,
        "build_shadow_score_checkpoint",
        fake_checkpoint,
    )

    first = phase171.build_shadow_readiness_requirement_registry(
        tmp_path
    )
    second = phase171.build_shadow_readiness_requirement_registry(
        tmp_path
    )

    assert first is second
    assert calls["count"] == 1
    assert first["registry_pass"] is True
    assert first["operational_status"] == "BLOCKED_RESEARCH_ONLY"

    info = (
        phase171
        .build_shadow_readiness_requirement_registry
        .cache_info()
    )
    assert info.misses == 1
    assert info.hits == 1

    phase171.build_shadow_readiness_requirement_registry.cache_clear()