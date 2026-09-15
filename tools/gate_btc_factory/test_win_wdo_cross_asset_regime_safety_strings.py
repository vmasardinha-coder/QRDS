from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_boundary_pins_core_safety_flags_and_mt5_role():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_BOUNDARY_20260915.md").read_text(encoding="utf-8")
    for s in [
        "RESEARCH_ONLY=true", "SHADOW_ONLY=true", "NOT_APPROVED=true",
        "ENGINE_FEED=false", "ORDERS=0", "REAL_CAPITAL=0",
        "NO_RETUNE=true", "NO_BACKFILL=true", "NO_COUNTER_RESET=true", "FAIL_CLOSED=true",
        "INDEPENDENT_SECONDARY_SOURCE/CROSS_VALIDATION_ONLY"
    ]:
        assert s in t
