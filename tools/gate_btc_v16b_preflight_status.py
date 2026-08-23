from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

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


def _find(root: Path, words: Iterable[str]) -> list[str]:
    words=tuple(w.lower() for w in words)
    out=[]
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        s=str(p).lower()
        if all(w in s for w in words):
            out.append(str(p))
    return out[:50]


def evaluate(root: Path) -> dict:
    checks=[]
    for name, words in REQUIRED_KEYWORDS.items():
        matches=_find(root, words)
        checks.append(Check(name, 'PASS_PRESENT' if matches else 'FAIL_MISSING', matches))
    rehearsal=(root/'tools/gate_btc_v16b_rehearsal.py').exists()
    checks.append(Check('REHEARSAL_TOOL', 'PASS_PRESENT' if rehearsal else 'FAIL_MISSING', ['tools/gate_btc_v16b_rehearsal.py'] if rehearsal else []))
    overall='PASS_PREFLIGHT_DISCOVERY' if all(c.status.startswith('PASS') for c in checks) else 'FAIL_PREFLIGHT_MISSING_INPUT'
    return {
        'schema':'gate_btc.v16b.preflight_status.v1',
        'status':overall,
        'signal_date':'2026-08-27',
        'entry_date':'2026-08-28',
        'complete_exit_date':'2026-09-04',
        'canonical_cycle_count':0,
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
    print(json.dumps(evaluate(Path('.')), indent=2, sort_keys=True))
