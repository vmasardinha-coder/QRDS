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


def test_zero_incremental_transport_preserves_cumulative_intake(tmp_path: Path):
    root = tmp_path / "runtime"
    write(root, "factory_autonomy/GRAMMAR_PREREG_TRANSPORT_RUNTIME.json", {"transported_count": 0})
    write(root, "factory_autonomy/GRAMMAR_SOURCE_COST_INTAKE_RUNTIME.json", {"transported_count": 12})
    out = build(root)
    counts = out["executive_counters"]["grammar_pipeline"]
    assert counts["transported_current"] == 12
    assert counts["transported_incremental_last_handoff"] == 0


def rejected_queue():
    return {'affected_family_count':2,'completed_family_count':2,
            'survivor_count':0,'waiting_source_count':0,'inconclusive_count':0,
            'source_gate_green':False,'source_gate_status':'SOURCE_GATE_NOT_GREEN:qualified',
            'updated_at_utc':'2026-09-19T17:19:59+00:00',
            'families':[{'original_family_id':'A','status':'SCIENTIFIC_REJECTION'},
                        {'original_family_id':'B','status':'SCIENTIFIC_REJECTION'}]}

def healthy_loops(root, now):
    write(root,'factory_autonomy/GRAMMAR_SCOUT_RUNTIME.json',{'generated_at_utc':now.isoformat()})
    write(root,'factory_autonomy/invalidated_requalification/SOURCE_SEARCH_RUNTIME.json',{'generated_at_utc':now.isoformat()})

def test_closed_rejected_queue_is_historical_not_stale(tmp_path):
    now=datetime(2026,10,12,tzinfo=timezone.utc)
    root=tmp_path/'runtime';healthy_loops(root,now);q=rejected_queue()
    write(root,'factory_autonomy/invalidated_requalification/QUEUE.json',q)
    out=build(root,now)
    assert out['overall_status']=='ACTIVE_WITH_CLOSED_LEGACY'
    queue=out['components']['invalidated_family_requalification']
    assert queue['freshness']=='NOT_APPLICABLE_CLOSED'
    assert queue['active'] is False
    assert queue['lifecycle']=='COMPLETED_NO_SURVIVORS'
    assert queue['source_gate_green'] is False
    assert queue['status']==q['source_gate_status']
    assert out['executive_counters']['legacy_requalification']['survivors']==0
    assert out['safety']['scientific_change_allowed'] is False

def test_closed_queue_does_not_hide_stale_active_source(tmp_path):
    now=datetime(2026,10,12,tzinfo=timezone.utc)
    root=tmp_path/'runtime';healthy_loops(root,now)
    write(root,'factory_autonomy/invalidated_requalification/QUEUE.json',rejected_queue())
    write(root,'factory_autonomy/invalidated_requalification/SOURCE_SEARCH_RUNTIME.json',
          {'generated_at_utc':(now-timedelta(hours=13)).isoformat()})
    assert build(root,now)['overall_status']=='DEGRADED_WARMUP_OR_STALE'

def test_unverified_completion_cannot_hide_stale_queue(tmp_path):
    from copy import deepcopy
    from tools.gate_btc_factory.factory_activity_status import terminal_rejected_queue
    cases=[]
    q=rejected_queue();q.pop('families');cases.append(q)
    q=rejected_queue();q['completed_family_count']=1;cases.append(q)
    q=rejected_queue();q['families'][1]['original_family_id']='A';cases.append(q)
    q=rejected_queue();q['families'][1]['status']='WAITING_SOURCE';cases.append(q)
    q=rejected_queue();q['waiting_source_count']=1;cases.append(q)
    q=rejected_queue();q['survivor_count']=1;cases.append(q)
    q=rejected_queue();q['inconclusive_count']=1;cases.append(q)
    q=rejected_queue();q['affected_family_count']=0;q['families']=[];cases.append(q)
    for q in cases:
        assert terminal_rejected_queue(q) is False
        now=datetime(2026,10,12,tzinfo=timezone.utc)
        root=tmp_path/'runtime';healthy_loops(root,now)
        write(root,'factory_autonomy/invalidated_requalification/QUEUE.json',q)
        assert build(root,now)['overall_status']=='DEGRADED_WARMUP_OR_STALE'
