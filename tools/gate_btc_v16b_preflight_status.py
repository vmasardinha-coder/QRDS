from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Iterable

try:
    from tools.gate_btc_v16b_calendar import window_from_signal
except ModuleNotFoundError:  # direct script execution from tools/
    from gate_btc_v16b_calendar import window_from_signal

RESEARCH_ONLY = True
SHADOW_ONLY = True
NOT_APPROVED = True
ENGINE_FEED = False
ORDERS = 0
REAL_CAPITAL = 0

# D-2/D-1 preflight must not demand evidence that can only exist causally at
# SIGNAL or ENTRY.  It proves those producers are armed; the downstream seal
# builders still require the exact contemporaneous immutable artifacts.
PRODUCER_REQUIREMENTS = {
    'CMC_TOP150': (
        '.github/workflows/gate-btc-v16b-cmc-snapshot.yml',
        'tools/gate_btc_v16b_cmc_snapshot.py',
    ),
    'EXECUTABILITY': (
        '.github/workflows/gate-btc-v16b-executability-snapshot.yml',
        'tools/gate_btc_v16b_executability_snapshot.py',
    ),
}

DISCOVERABLE_REQUIREMENTS = {
    'PROVENANCE_MANIFEST': ('manifest', 'sha'),
    'SHORTABILITY': ('shortability',),
    'FUNDING': ('funding',),
    'PRICES': ('price',),
}

STAGE_SEMANTICS = {
    'CMC_TOP150': 'PRODUCER_READY_AT_PREFLIGHT__EXACT_IMMUTABLE_SNAPSHOT_REQUIRED_AT_SIGNAL',
    'EXECUTABILITY': 'PRODUCER_READY_AT_PREFLIGHT__POST_SIGNAL_PRE_ENTRY_BINANCE_EVIDENCE_REQUIRED_AT_ENTRY',
}


@dataclass
class Check:
    name: str
    status: str
    matches: list[str]


def _find(roots: list[Path], words: Iterable[str]) -> list[str]:
    words = tuple(w.lower() for w in words)
    out = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob('*'):
            if not p.is_file():
                continue
            s = str(p).lower()
            if all(w in s for w in words):
                out.append(str(p))
                if len(out) >= 50:
                    return out
    return out


def _producer_check(source_root: Path, name: str, required_paths: tuple[str, ...]) -> Check:
    paths = [source_root / rel for rel in required_paths]
    present = [str(p) for p in paths if p.is_file()]
    status = 'PASS_PRODUCER_READY' if len(present) == len(paths) else 'FAIL_PRODUCER_MISSING'
    return Check(name, status, present)


def evaluate(roots: list[Path], source_root: Path, signal_date: str = '2026-08-27') -> dict:
    window = window_from_signal(date.fromisoformat(signal_date))
    checks = []

    for name, required_paths in PRODUCER_REQUIREMENTS.items():
        checks.append(_producer_check(source_root, name, required_paths))

    for name, words in DISCOVERABLE_REQUIREMENTS.items():
        matches = _find(roots, words)
        checks.append(Check(name, 'PASS_PRESENT' if matches else 'FAIL_MISSING', matches))

    rehearsal = (source_root / 'tools/gate_btc_v16b_rehearsal.py').exists()
    checks.append(Check(
        'REHEARSAL_TOOL',
        'PASS_PRESENT' if rehearsal else 'FAIL_MISSING',
        [str(source_root / 'tools/gate_btc_v16b_rehearsal.py')] if rehearsal else [],
    ))

    overall = 'PASS_PREFLIGHT_DISCOVERY' if all(c.status.startswith('PASS') for c in checks) else 'FAIL_PREFLIGHT_MISSING_INPUT'
    return {
        'schema': 'gate_btc.v16b.preflight_status.v3',
        'status': overall,
        'signal_date': window.signal_date.isoformat(),
        'entry_date': window.entry_date.isoformat(),
        'complete_exit_date': window.complete_exit_date.isoformat(),
        'canonical_cycle_count': 0,
        'calendar_authority': 'FROZEN_WEEKLY_V16B_CLOCK',
        'preflight_scope': 'PRODUCER_READINESS_ONLY_FOR_FUTURE_CAUSAL_STAGE_INPUTS',
        'stage_semantics': STAGE_SEMANTICS,
        'roots': [str(r) for r in roots],
        'checks': [asdict(c) for c in checks],
        'RESEARCH_ONLY': RESEARCH_ONLY,
        'SHADOW_ONLY': SHADOW_ONLY,
        'NOT_APPROVED': NOT_APPROVED,
        'ENGINE_FEED': ENGINE_FEED,
        'ORDERS': ORDERS,
        'REAL_CAPITAL': REAL_CAPITAL,
        'NO_BACKFILL': True,
        'NO_LATE_SEAL': True,
    }


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', default=[])
    ap.add_argument('--source-root', default='.')
    ap.add_argument('--signal-date', default='2026-08-27')
    ns = ap.parse_args()
    roots = [Path(x) for x in (ns.root or ['.'])]
    print(json.dumps(evaluate(roots, Path(ns.source_root), ns.signal_date), indent=2, sort_keys=True))
