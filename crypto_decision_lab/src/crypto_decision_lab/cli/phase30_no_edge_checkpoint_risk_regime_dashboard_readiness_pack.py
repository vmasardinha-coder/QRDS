from __future__ import annotations
import argparse,json
from pathlib import Path
from crypto_decision_lab.reports.phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack import build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description="Build QRDS Phase 30 No-Edge Checkpoint + Dashboard Readiness Pack")
    p.add_argument("--output-dir",required=True); p.add_argument("--repo-root",default="")
    a=p.parse_args(argv); r=build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack(Path(a.output_dir),a.repo_root or None)
    print(json.dumps({k:v for k,v in r.items() if k!="payload"},indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
