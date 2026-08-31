from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from tools.gate_btc_factory.factory_activity_status import build


def write(root: Path, rel: str, obj: dict):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding="utf-8")


def test_activity_status_consolidates_native_loops(tmp_path: Path):
    now = datetime(2026, 8, 31, 1, 0, tzinfo=timezone.utc)
    root = tmp_path / "runtime"
    write(root, "factory_autonomy/GRAMMAR_SCOUT_RUNTIME.json", {"generated_at_utc": (now - timedelta(hours=4)).isoformat(), "mode": "IDEATION_ONLY_NO_ECONOMICS"})
    write(root, "factory_autonomy/invalidated_requalification/SOURCE_SEARCH_RUNTIME.json", {"generated_at_utc": (now - timedelta(hours=2)).isoformat(), "status": "ACTIVE_SEARCHING_QUALIFICATION"})
    write(root, "factory_autonomy/invalidated_requalification/QUEUE.json", {"updated_at_utc": (now - timedelta(hours=1)).isoformat(), "source_gate_status": "SOURCE_GATE_NOT_GREEN:qualified", "affected_family_count": 768, "source_gate_green": False})
    out = build(root, now=now)
    assert out["overall_status"] == "ACTIVE"
    assert out["monitor_cadence_minutes"] == 15
    assert out["components"]["grammar_scout"]["active"] is True
    assert out["components"]["source_qualification_search"]["active"] is True
    assert out["components"]["invalidated_family_requalification"]["affected_family_count"] == 768
    s = out["safety"]
    assert s["orders"] == 0 and s["real_capital"] == 0 and s["engine_feed"] is False


def test_stale_source_search_degrades_status(tmp_path: Path):
    now = datetime(2026, 8, 31, 20, 0, tzinfo=timezone.utc)
    root = tmp_path / "runtime"
    write(root, "factory_autonomy/invalidated_requalification/SOURCE_SEARCH_RUNTIME.json", {"generated_at_utc": (now - timedelta(hours=13)).isoformat(), "status": "ACTIVE_SEARCHING_QUALIFICATION"})
    write(root, "factory_autonomy/invalidated_requalification/QUEUE.json", {"updated_at_utc": (now - timedelta(hours=2)).isoformat(), "source_gate_status": "WAITING", "affected_family_count": 768})
    out = build(root, now=now)
    assert out["overall_status"] == "DEGRADED_WARMUP_OR_STALE"
    assert out["components"]["source_qualification_search"]["freshness"] == "STALE_OR_UNDATED"
