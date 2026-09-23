from pathlib import Path


def test_xagent_fallback_workflow_is_stale_only_and_safe():
    text = Path('.github/workflows/gate-btc-xagent-schedule-fallback.yml').read_text()
    assert "TARGET_WORKFLOW: gate-btc-xagent-disagree-transform.yml" in text
    assert "FRESHNESS_SECONDS: '5400'" in text
    assert "actions: write" in text
    assert "contents: read" in text
    assert "RESEARCH_ONLY: 'true'" in text
    assert "SHADOW_ONLY: 'true'" in text
    assert "ENGINE_FEED: 'false'" in text
    assert "ORDERS: '0'" in text
    assert "REAL_CAPITAL: '0'" in text
    assert "NO_RETUNE: 'true'" in text
    assert "NO_BACKFILL: 'true'" in text
