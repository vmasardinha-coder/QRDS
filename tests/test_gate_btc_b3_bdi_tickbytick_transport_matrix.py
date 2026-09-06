from __future__ import annotations
import importlib.util
from pathlib import Path

P=Path(__file__).parents[1]/'tools'/'gate_btc_factory'/'b3_bdi_tickbytick_transport_matrix.py'
s=importlib.util.spec_from_file_location('m',P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)

class R:
    def __init__(self,status=500,raw=b''): self.status_code=status; self.content=raw; self.headers={'content-type':'application/json'}
    def json(self):
        import json
        return json.loads(self.content) if self.content else None
class S:
    def __init__(self): self.calls=[]
    def post(self,url,**kw): self.calls.append((url,kw)); return R()

def test_matrix_is_finite_and_fail_closed():
    s=S(); out=m.run_probe(s,'2026-09-04')
    assert len(s.calls)==5
    assert any('/2026-09-04/2026-09-04/' in u for u,_ in s.calls)
    assert any('/04-09-2026/04-09-2026/' in u for u,_ in s.calls)
    assert any('/20260904/20260904/' in u for u,_ in s.calls)
    assert out['strict_source_gate_green'] is False
    assert out['source_gate_credit']==0 and out['historical_backfill_credit']==0 and out['prospective_credit']==0
    assert out['economics_read'] is False
    assert out['status']=='BDI_SPECIAL_TRANSPORT_NOT_RESOLVED_FAIL_CLOSED'
    z=out['safety']; assert z['research_only'] and z['shadow_only'] and z['not_approved'] and z['fail_closed']; assert z['orders']==0 and z['real_capital']==0 and z['engine_feed'] is False
