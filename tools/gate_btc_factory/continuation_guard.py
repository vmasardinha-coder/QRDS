from __future__ import annotations

import glob
import json
import os
import re
from pathlib import Path

MIN_AUTONOMOUS_FRONTIER = 149


def generation_blocks() -> list[tuple[int, int, str]]:
    blocks: list[tuple[int, int, str]] = []
    patterns = [
        '.github/workflows/gate-btc-b3-h*-h*-*.yml',
        '.github/workflows/gate-btc-b3-h*-h*.yml',
        'tools/gate_btc_b3_h*_h*_prereg.md',
        'research/b3_h*_h*_*.md',
    ]
    for pattern in patterns:
        for path in glob.glob(pattern):
            name = os.path.basename(path).lower().replace('_', '-')
            match = re.search(r'h(\d+)-h(\d+)', name)
            if not match:
                continue
            start, end = int(match.group(1)), int(match.group(2))
            # The repository contains historical malformed/legacy filenames
            # (for example h95-h10) that are not canonical generation ranges.
            # They must not crash frontier discovery or become scientific state.
            if end < start:
                print(f'B3_FACTORY_IGNORED_LEGACY_RANGE={path}:H{start}-H{end}')
                continue
            # Only canonical decade blocks participate in autonomous frontier
            # progression; other named H-ranges remain visible elsewhere but
            # cannot silently redefine the production frontier.
            if end % 10 != 9 or start != end - 9:
                continue
            blocks.append((start, end, path))
    if not blocks:
        raise RuntimeError('NO_CANONICAL_B3_GENERATION_BLOCKS')
    return blocks


def canonical_frontier_block() -> tuple[int, int, str]:
    blocks = generation_blocks()
    return max(blocks, key=lambda row: (row[1], row[0], row[2]))


def canonical_result_path(start: int, end: int) -> Path:
    return Path(f'tools/gate_btc_b3_h{start}_h{end}_result.json')


def _assert_close_safety(payload: dict, path: Path) -> None:
    checks = {
        'h1_economics_read': False,
        'survivor_partial_economics_read': False,
        'engine_feed': False,
    }
    for key, expected in checks.items():
        if key in payload and payload[key] is not expected:
            raise RuntimeError(f'UNSAFE_CLOSE_RESULT:{path}:{key}={payload[key]!r}')
    for key in ('orders', 'orders_generated'):
        if key in payload and int(payload[key]) != 0:
            raise RuntimeError(f'UNSAFE_CLOSE_RESULT:{path}:{key}={payload[key]!r}')
    for key in ('capital', 'real_capital', 'real_capital_used'):
        if key in payload and float(payload[key]) != 0.0:
            raise RuntimeError(f'UNSAFE_CLOSE_RESULT:{path}:{key}={payload[key]!r}')


def classify_frontier(start: int, end: int) -> tuple[str, bool, str]:
    result_path = canonical_result_path(start, end)
    if not result_path.exists():
        if end == MIN_AUTONOMOUS_FRONTIER:
            return 'LEGACY_H149_BOOTSTRAP_REQUIRED', True, str(result_path)
        return 'WAITING_FOR_CANONICAL_TERMINAL_RESULT', False, str(result_path)

    try:
        payload = json.loads(result_path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise RuntimeError(f'INVALID_CANONICAL_CLOSE_RESULT:{result_path}:{exc}') from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f'INVALID_CANONICAL_CLOSE_RESULT:{result_path}:NOT_OBJECT')
    _assert_close_safety(payload, result_path)

    status = str(payload.get('status') or '')
    survivors = payload.get('survivors', [])
    if not isinstance(survivors, list):
        raise RuntimeError(f'INVALID_CANONICAL_CLOSE_RESULT:{result_path}:SURVIVORS_NOT_LIST')

    expected_closed = f'CLOSED_NO_H{start}_H{end}_SURVIVOR'
    if status == expected_closed and survivors == []:
        return 'TERMINAL_NO_SURVIVOR', True, str(result_path)
    if survivors or status.startswith('SURVIVORS_READY') or status.startswith('APPROVED_'):
        return 'TERMINAL_SURVIVOR_PRESENT', False, str(result_path)
    if 'DATA_GAP' in status or 'BLOCKED' in status or 'FAIL_CLOSED' in status:
        return 'FAIL_CLOSED_NON_SCIENTIFIC_CONTINUATION', False, str(result_path)
    return 'WAITING_FOR_TERMINAL_NO_SURVIVOR_OR_SURVIVOR_CLOSE', False, str(result_path)


def write_output(key: str, value: object) -> None:
    output = os.getenv('GITHUB_OUTPUT')
    if not output:
        return
    with open(output, 'a', encoding='utf-8') as handle:
        handle.write(f'{key}={str(value).lower() if isinstance(value, bool) else value}\n')


def main() -> int:
    start, end, source = canonical_frontier_block()
    if end < MIN_AUTONOMOUS_FRONTIER:
        raise RuntimeError(f'BLOCKED_INCOMPLETE_CANONICAL_HISTORY:H{end}')

    state, should_dispatch, result_path = classify_frontier(start, end)
    next_start, next_end = end + 1, end + 10
    frontier_key = f'H{end}-TO-H{next_start}-H{next_end}'

    print(f'B3_FACTORY_FRONTIER=H{start}-H{end}')
    print(f'B3_FACTORY_FRONTIER_SOURCE={source}')
    print(f'B3_FACTORY_STATUS={state}')
    print(f'B3_FACTORY_RESULT_PATH={result_path}')
    print(f'B3_FACTORY_NEXT_GENERATION=H{next_start}-H{next_end}')
    print(f'B3_FACTORY_FRONTIER_KEY={frontier_key}')
    print(f'B3_FACTORY_SHOULD_DISPATCH={str(should_dispatch).lower()}')
    print('B3_FACTORY_AUTOREPAIR_SCOPE=ORCHESTRATION_ONLY')
    print('B3_FACTORY_NO_CLONE_NO_RENAME=true')

    for key, value in {
        'frontier_start': start,
        'frontier_end': end,
        'frontier_key': frontier_key,
        'frontier_state': state,
        'result_path': result_path,
        'next_start': next_start,
        'next_end': next_end,
        'should_dispatch': should_dispatch,
    }.items():
        write_output(key, value)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
