#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github' / 'workflows'
REG = ROOT / 'ops' / 'workflow_operations_registry.json'

def main():
    reg = json.loads(REG.read_text(encoding='utf-8'))
    allow = set(reg['manual_allowlist'])
    rows = []
    for p in sorted(WF.glob('*.y*ml')):
        text = p.read_text(encoding='utf-8', errors='replace')
        has_dispatch = 'workflow_dispatch' in text
        rel = str(p.relative_to(ROOT)).replace('\\', '/')
        if has_dispatch:
            rows.append((rel, rel in allow))
    print('MANUAL_DISPATCH_SURFACES')
    for rel, allowed in rows:
        print(('ALLOWED   ' if allowed else 'LEGACY    ') + rel)
    legacy = [r for r, ok in rows if not ok]
    print(f'TOTAL_MANUAL={len(rows)}')
    print(f'ALLOWLISTED={len(rows)-len(legacy)}')
    print(f'LEGACY_REVIEW_REQUIRED={len(legacy)}')
    # Transitional mode: surface legacy buttons without breaking science/CI.
    # New manual entrypoints must be registered before merge.
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
