"""Materialize exact Git blobs for the local H1 collector; never execute it."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from gate_btc_h1_schedule_continuation import CONTINUATION_SHA256
from gate_btc_h1_schedule_extension import EXTENSION_SHA256, PARENT_SHA256

FILES = (
    'tools/gate_btc_b3_h1_daily.py',
    'tools/gate_btc_b3_h1_parser.py',
    'tools/gate_btc_factory/H1_PROSPECTIVE_SCHEDULE_AMENDMENT_20261007.v1.json',
    'tools/gate_btc_h1_schedule_extension.py',
    'tools/gate_btc_factory/H1_PROSPECTIVE_SCHEDULE_EXTENSION_20261022.v1.json',
    'tools/gate_btc_h1_schedule_continuation.py',
    'tools/gate_btc_factory/H1_PROSPECTIVE_CONTINUATION_20261101.v1.json',
)
SEALS = {FILES[2]: PARENT_SHA256, FILES[4]: EXTENSION_SHA256, FILES[6]: CONTINUATION_SHA256}


def git(root: Path, *args: str) -> bytes:
    p = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    if p.returncode:
        raise RuntimeError('H1_MATERIALIZATION_GIT_FAILED:' + args[0])
    return p.stdout


def materialize(source: Path, out: Path, verify_only: bool = False) -> dict:
    if out.resolve().is_relative_to(source.resolve()):
        raise RuntimeError('H1_MATERIALIZATION_OUTPUT_INSIDE_SOURCE_REPO')
    head = git(source, 'rev-parse', 'HEAD').decode().strip()
    blobs = {name: git(source, 'show', head + ':' + name) for name in FILES}
    for name, expected in SEALS.items():
        if hashlib.sha256(blobs[name]).hexdigest() != expected:
            raise RuntimeError('H1_FROZEN_CONTRACT_GIT_BLOB_HASH_MISMATCH:' + name)
    files = []
    # Verify all pinned inputs before touching any destination file.
    for name, raw in blobs.items():
        target = out / Path(name).relative_to('tools')
        previous = target.read_bytes() if target.exists() else None
        digest = hashlib.sha256(raw).hexdigest()
        if not verify_only and previous != raw:
            target.parent.mkdir(parents=True, exist_ok=True)
            candidate = target.with_suffix(target.suffix + '.partial')
            candidate.write_bytes(raw)
            candidate.replace(target)
        if not verify_only and target.read_bytes() != raw:
            raise RuntimeError('H1_LOCAL_BLOB_MATERIALIZATION_MISMATCH:' + name)
        files.append({'path': name, 'sha256': digest, 'changed': previous != raw,
                      'previous_sha256': hashlib.sha256(previous).hexdigest() if previous is not None else None})
    return {'status': 'PASS', 'main_head': head, 'collector': str(out / 'gate_btc_b3_h1_daily.py'),
            'collector_executed': False, 'counter_changed': False, 'verify_only': verify_only,
            'amendment_sha256': PARENT_SHA256, 'extension_sha256': EXTENSION_SHA256,
            'continuation_sha256': CONTINUATION_SHA256, 'files': files}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path(r'C:\actions-runner\qrds-local-shadow\code_canonical'))
    p.add_argument('--out', type=Path, default=Path(r'C:\GATE_BTC_PROJECT\RUNTIME\B3_H1_CANONICAL\canonical_collector'))
    p.add_argument('--verify-only', action='store_true')
    a = p.parse_args()
    print(json.dumps(materialize(a.source, a.out, a.verify_only), sort_keys=True))
