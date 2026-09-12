import json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_partial_triage_never_promotes_or_rejects_from_partial_performance(tmp_path):
    queue=tmp_path/"q.json"
    queue.write_text(json.dumps({"families":[
      {"original_family_id":"H2218","status":"WAITING_SOURCE_QUALIFICATION"},
      {"original_family_id":"H2474","status":"WAITING_SOURCE_QUALIFICATION"}
    ]}))
    evidence=tmp_path/"e.json"
    evidence.write_text(json.dumps({"valid_sessions_discovery":21,"valid_sessions_replication":52,"valid_sessions_total":73}))
    out=tmp_path/"out.json"
    subprocess.check_call([sys.executable,str(ROOT/"tools/gate_btc_factory/invalidated_partial_triage.py"),
      "--queue",str(queue),"--evidence",str(evidence),"--output",str(out)], cwd=ROOT)
    d=json.loads(out.read_text())
    assert d["strict_v2_unchanged"] is True
    assert d["promotion_allowed"] is False
    assert d["scientific_rejection_from_partial_performance_allowed"] is False
    assert d["counts"] == {"NOT_TRIAGEABLE_PARTIAL_CAPACITY": 2}
    assert {x["contract"]["standardization_lookback_sessions"] for x in d["families"]} == {200,252}
