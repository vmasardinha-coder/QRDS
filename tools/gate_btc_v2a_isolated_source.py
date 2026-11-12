"""Validate current V2A evidence independently of unrelated LOCK continuity."""
import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def validate(root, now=None):
    now = now or datetime.now(timezone.utc)
    m = json.loads((root / 'outputs/v2a_run_manifest.json').read_text(encoding='utf-8-sig'))
    def require(ok, reason):
        if not ok:
            raise ValueError(reason)
    require(m['technical_status'] == 'PASS' and m['data_quality_status'] == 'PASS', 'quality not PASS')
    require(m['operational_status'] == 'NOT_APPROVED' and m['real_orders'] == 0 and m['capital_used'] == 0, 'authority changed')
    require(m['evidence_status'] == 'RESEARCH_ONLY_NOT_PROMOTED', 'research boundary changed')
    require(m['data_as_of'] == (now.date() - timedelta(days=1)).isoformat(), 'current close required; no backfill')
    require(datetime.fromisoformat(m['run_utc']).date() == now.date(), 'current capture required')
    for name in ('data/processed/qos_v2a_master_daily.csv', 'data/raw/coingecko_current_universe_v04.csv', 'outputs/download_failures_v2a.csv'):
        require(hashlib.sha256((root / name).read_bytes()).hexdigest() == m['input_files_sha256'][name], 'input hash mismatch: ' + name)
    require(hashlib.sha256((root / 'outputs/source_attempts_v2a.json').read_bytes()).hexdigest() == m['source_trace_sha256'], 'source trace hash mismatch')
    return m['data_as_of']


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    print(validate(ap.parse_args().root))
