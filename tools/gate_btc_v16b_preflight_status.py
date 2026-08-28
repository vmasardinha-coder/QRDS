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

REQUIRED_KEYWORDS = {
    'CMC_TOP150': ('cmc', 'top150'),
    'PROVENANCE_MANIFEST': ('manifest', 'sha'),
    'SHORTABILITY': ('shortability',),
    'EXECUTABILITY': ('executability',),
    'FUNDING': ('funding',),
    'PRICES': ('price',),
}

@dataclass
class Check:
    name: str
    status: str
    matches: list[str]


def _find(roots: list[Path], words: Iterable[str]) -> list[str]:
    words=tuple(w.lower() for w in words)
    out=[]
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob('*'):
            if not p.is_file():
                continue
            s=str(p).lower()
            if all(w in s for w in words):
                out.append(str(p))
                if len(out) >= 50:
                    return out
    return out


def evaluate(roots: list[Path], source_root: Path, signal_date: str = '2026-08-27') -> dict:
    window=window_from_signal(date.fromisoformat(signal_date))
    checks=[]
    for name, words in REQUIRED_KEYWORDS.items():
        matches=_find(roots, words)
        checks.append(Check(name, 'PASS_PRESENT' if matches else 'FAIL_MISSING', matches))
    rehearsal=(source_root/'tools/gate_btc_v16b_rehearsal.py').exists()
    checks.append(Check('REHEARSAL_TOOL', 'PASS_PRESENT' if rehearsal else 'FAIL_MISSING', [str(source_root/'tools/gate_btc_v16b_rehearsal.py')] if rehearsal else []))
    overall='PASS_PREFLIGHT_DISCOVERY' if all(c.status.startswith('PASS') for c in checks) else 'FAIL_PREFLIGHT_MISSING_INPUT'
    return {
        'schema':'gate_btc.v16b.preflight_status.v2',
        'status':overall,
        'signal_date':window.signal_date.isoformat(),
        'entry_date':window.entry_date.isoformat(),
        'complete_exit_date':window.complete_exit_date.isoformat(),
        'canonical_cycle_count':0,
        'calendar_authority':'FROZEN_WEEKLY_V16B_CLOCK',
        'roots':[str(r) for r in roots],
        'checks':[asdict(c) for c in checks],
        'RESEARCH_ONLY':RESEARCH_ONLY,
        'SHADOW_ONLY':SHADOW_ONLY,
        'NOT_APPROVED':NOT_APPROVED,
        'ENGINE_FEED':ENGINE_FEED,
        'ORDERS':ORDERS,
        'REAL_CAPITAL':REAL_CAPITAL,
        'NO_BACKFILL':True,
        'NO_LATE_SEAL':True,
    }

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', action='append', default=[])
    ap.add_argument('--source-root', default='.')
    ap.add_argument('--signal-date', default='2026-08-27')
    ns=ap.parse_args()
    roots=[Path(x) for x in (ns.root or ['.'])]
    print(json.dumps(evaluate(roots, Path(ns.source_root), ns.signal_date), indent=2, sort_keys=True))
