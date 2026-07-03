from __future__ import annotations
import argparse, json
from pathlib import Path
from crypto_decision_lab.reports.archive_manifest_repo_hygiene import build_archive_manifest_repo_hygiene

def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description='Build QRDS Archive Manifest / Repo Hygiene Index.')
    ap.add_argument('--output-dir', required=True); ap.add_argument('--repo-root', default='')
    a=ap.parse_args(argv)
    r=build_archive_manifest_repo_hygiene(output_dir=Path(a.output_dir), repo_root=a.repo_root or None)
    print(json.dumps({k:v for k,v in r.items() if k!='payload'},indent=2,sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())
