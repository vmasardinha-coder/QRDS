#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_PATH = Path(__file__).with_name('grammar_008_industrial_evaluator.py')
_spec = importlib.util.spec_from_file_location('g008_base', BASE_PATH)
base = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(base)

HOUR = base.HOUR
UA = base.UA
_ORIGINAL_BACKTEST = base.backtest_partition
GAP_AUDIT: dict[str, dict] = {}


def fetch_coinbase_sparse(product: str, start: int, end: int, chunk_hours: int = 240) -> list[dict]:
    """Fetch physical Coinbase bars and preserve gaps as absent observations.

    Grammar 008 froze missing_bar_policy=INELIGIBLE_NO_IMPUTATION. Missing physical
    bars therefore cannot be synthesized and must not turn expected source sparsity
    into an infrastructure exception. Duplicate conflicting timestamps still fail closed.
    """
    endpoint = f'https://api.exchange.coinbase.com/products/{product}/candles'
    rows: dict[int, dict] = {}
    cur = start
    while cur < end:
        stop = min(end, cur + chunk_hours * HOUR)
        q = urllib.parse.urlencode({'granularity': 3600, 'start': base.iso(cur), 'end': base.iso(stop)})
        err = None
        for attempt in range(5):
            try:
                req = urllib.request.Request(endpoint + '?' + q, headers=UA)
                with urllib.request.urlopen(req, timeout=30) as response:
                    obj = json.loads(response.read().decode())
                if not isinstance(obj, list):
                    raise RuntimeError('COINBASE_NONLIST_RESPONSE')
                for z in obj:
                    if len(z) < 6:
                        continue
                    t = int(z[0])
                    if cur <= t < stop:
                        bar = {
                            'time': t,
                            'low': float(z[1]),
                            'high': float(z[2]),
                            'open': float(z[3]),
                            'close': float(z[4]),
                            'volume': float(z[5]),
                        }
                        if t in rows and rows[t] != bar:
                            raise RuntimeError(f'DUPLICATE_TIMESTAMP_CONFLICT_{product}_{t}')
                        rows[t] = bar
                err = None
                break
            except Exception as exc:
                err = exc
                time.sleep(2 ** attempt)
        if err is not None:
            raise err
        cur = stop
        time.sleep(.05)

    out = [rows[k] for k in sorted(rows)]
    expected = set(range(start, end, HOUR))
    got = {b['time'] for b in out}
    missing = sorted(expected - got)
    GAP_AUDIT[product] = {
        'requested_start': base.iso(start),
        'requested_end_exclusive': base.iso(end),
        'physical_bar_count': len(out),
        'missing_hour_count': len(missing),
        'first_missing_hour': base.iso(missing[0]) if missing else None,
        'policy': 'INELIGIBLE_NO_IMPUTATION',
        'imputed_bar_count': 0,
    }
    return out


def contiguous_segments(bars: list[dict]) -> list[list[dict]]:
    if not bars:
        return []
    segments = [[bars[0]]]
    for bar in bars[1:]:
        if bar['time'] != segments[-1][-1]['time'] + HOUR:
            segments.append([])
        segments[-1].append(bar)
    return segments


def gap_safe_backtest_partition(bars, spec, prereg, start, end):
    """Run the frozen evaluator only inside physically contiguous hourly segments.

    Indicators are re-warmed after every physical gap and open positions are discarded
    at the segment boundary. This prevents signals, indicator state, entries or exits
    from jumping across missing observations while retaining every physical bar.
    """
    if not spec['executable']:
        return _ORIGINAL_BACKTEST(bars, spec, prereg, start, end)

    trades = []
    discarded = False
    eligible_segments = 0
    for segment in contiguous_segments(bars):
        if len(segment) < 2:
            continue
        seg_start = max(start, segment[0]['time'])
        seg_end = min(end, segment[-1]['time'])
        if seg_start > seg_end:
            continue
        part = _ORIGINAL_BACKTEST(segment, spec, prereg, seg_start, seg_end)
        if part.get('ineligible'):
            return part
        eligible_segments += 1
        trades.extend(part.get('trades', []))
        discarded = discarded or bool(part.get('open_trade_discarded_at_partition_end'))

    return {
        'started': True,
        'ineligible': False,
        'open_trade_discarded_at_partition_end': discarded,
        'trades': trades,
        'physical_contiguous_segments': eligible_segments,
        'gap_policy': 'INELIGIBLE_NO_IMPUTATION',
    }


def execute(prereg, semantics, fetcher=fetch_coinbase_sparse):
    GAP_AUDIT.clear()
    original = base.backtest_partition
    base.backtest_partition = gap_safe_backtest_partition
    try:
        result = base.execute(prereg, semantics, fetcher=fetcher)
    finally:
        base.backtest_partition = original
    result['source_gap_audit'] = dict(sorted(GAP_AUDIT.items()))
    result['missing_bar_policy_applied'] = 'INELIGIBLE_NO_IMPUTATION'
    result['imputed_bar_count'] = 0
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prereg', type=Path, required=True)
    ap.add_argument('--semantics', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    load = lambda p: json.loads(p.read_text())
    result = execute(load(args.prereg), load(args.semantics))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({
        'status': result['status'],
        'discovery_pass': result['discovery_pass_count'],
        'validation_pass': result['validation_pass_count'],
        'survivors': result['historical_survivors'],
        'validation_source_opened': result['validation_source_opened'],
        'holdout_source_opened': result['holdout_source_opened'],
        'source_gap_audit': result['source_gap_audit'],
    }, sort_keys=True))


if __name__ == '__main__':
    main()
