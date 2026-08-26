from __future__ import annotations

import glob
import os
import re
import sys


def canonical_frontier() -> int:
    blocks = []
    pats = [
        '.github/workflows/gate-btc-b3-h*-h*-*.yml',
        '.github/workflows/gate-btc-b3-h*-h*.yml',
        'tools/gate_btc_b3_h*_h*_prereg.md',
    ]
    for pat in pats:
        for path in glob.glob(pat):
            name = os.path.basename(path).lower().replace('_', '-')
            m = re.search(r'h(\d+)-h(\d+)', name)
            if m:
                blocks.append((int(m.group(1)), int(m.group(2)), path))
    if not blocks:
        raise RuntimeError('No canonical B3 generation blocks found')
    return max(end for _, end, _ in blocks)


def main() -> int:
    frontier = canonical_frontier()
    print(f'B3_FACTORY_FRONTIER=H{frontier}')
    if frontier < 149:
        print('B3_FACTORY_STATUS=BLOCKED_INCOMPLETE_CANONICAL_HISTORY')
        return 2
    if frontier == 149:
        print('B3_FACTORY_STATUS=STALLED_AFTER_H149')
        print('B3_FACTORY_ACTION=REQUIRES_NEW_SCIENTIFIC_BATCH_CONTRACT')
        print('B3_FACTORY_AUTOREPAIR_SCOPE=ORCHESTRATION_ONLY')
        return 3
    print('B3_FACTORY_STATUS=CONTINUATION_PRESENT')
    return 0


if __name__ == '__main__':
    sys.exit(main())
