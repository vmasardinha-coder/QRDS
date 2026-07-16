from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase356_365_data_remediation_common import LOCKS

def payload(phase:int,**updates:Any)->dict[str,Any]:
    value={"project":"QRDS/QOS/GATE BTC","phase":phase,"status":"TEST_RESEARCH_ONLY","locks":dict(LOCKS),"strategy_approved":False,"forward_shadow_eligible":False,"forward_shadow_started":False,"paper_trading_started":False}
    value.update(updates); return value

def write_json(path:Path,value:dict[str,Any])->Path:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value),encoding="utf-8"); return path

def patch_roots(monkeypatch,tmp_path:Path,*modules:Any)->None:
    project=tmp_path/"crypto_decision_lab"; project.mkdir(parents=True,exist_ok=True); repo=tmp_path
    for module in modules:
        if hasattr(module,"ROOT"): monkeypatch.setattr(module,"ROOT",project)
        if hasattr(module,"GIT_ROOT"): monkeypatch.setattr(module,"GIT_ROOT",repo)
