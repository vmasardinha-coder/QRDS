#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import statistics
from pathlib import Path
from typing import Callable

GAP_PATH = Path(__file__).with_name('grammar_008_industrial_gap_safe.py')
_spec = importlib.util.spec_from_file_location('g008_gap_safe_for_xregime', GAP_PATH)
gap = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gap)

HOUR = gap.HOUR
WARMUP_HOURS = 1000


def ts(s: str) -> int:
    return gap.base.ts(s)


def sample_sd(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def rolling_sma(values: list[float], n: int) -> list[float | None]:
    return gap.base.sma(values, n)


def rolling_rv24(closes: list[float]) -> list[float | None]:
    rets: list[float | None] = [None]
    for i in range(1, len(closes)):
        rets.append(math.log(closes[i] / closes[i - 1]))
    out: list[float | None] = [None] * len(closes)
    for i in range(24, len(closes)):
        window = [x for x in rets[i - 23:i + 1] if x is not None]
        if len(window) == 24:
            out[i] = sample_sd(window)
    return out


def prior_rolling_median(values: list[float | None], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    for i in range(len(values)):
        prior = [x for x in values[max(0, i - n):i] if x is not None]
        if len(prior) == n:
            out[i] = statistics.median(prior)
    return out


def synchronized_segments(btc: list[dict], eth: list[dict]) -> tuple[list[list[dict]], dict]:
    bm = {b['time']: b for b in btc}
    em = {b['time']: b for b in eth}
    common = sorted(set(bm) & set(em))
    paired = [
        {
            'time': t,
            'btc_open': bm[t]['open'], 'btc_close': bm[t]['close'],
            'eth_open': em[t]['open'], 'eth_close': em[t]['close'],
        }
        for t in common
    ]
    segments: list[list[dict]] = []
    for row in paired:
        if not segments or row['time'] != segments[-1][-1]['time'] + HOUR:
            segments.append([])
        segments[-1].append(row)
    audit = {
        'btc_physical_bars': len(btc),
        'eth_physical_bars': len(eth),
        'synchronized_physical_bars': len(paired),
        'btc_only_timestamps': len(set(bm) - set(em)),
        'eth_only_timestamps': len(set(em) - set(bm)),
        'synchronized_contiguous_segments': len(segments),
        'imputed_bar_count': 0,
        'policy': 'INELIGIBLE_NO_IMPUTATION',
    }
    return segments, audit


def feature_flags(segment: list[dict]) -> dict[str, list[bool | None]]:
    btc = [x['btc_close'] for x in segment]
    eth = [x['eth_close'] for x in segment]
    btc_sma168 = rolling_sma(btc, 168)
    eth_sma72 = rolling_sma(eth, 72)
    rv24 = rolling_rv24(btc)
    rv24_med720 = prior_rolling_median(rv24, 720)

    n = len(segment)
    states: dict[str, list[bool | None]] = {
        'BTC_TREND_168H': [None] * n,
        'BTC_RETURN_24H': [None] * n,
        'BTC_LOW_VOL_24H_VS_720H_MEDIAN': [None] * n,
        'BTC_DRAWDOWN_720H_GT_MINUS10PCT': [None] * n,
    }
    signals: dict[str, list[bool | None]] = {
        'ETH_TREND_TRANSITION_72H': [None] * n,
        'ETH_TREND_STATE_72H': [None] * n,
        'ETH_MOMENTUM_24H': [None] * n,
    }

    for i in range(n):
        if btc_sma168[i] is not None:
            states['BTC_TREND_168H'][i] = btc[i] > btc_sma168[i]
        if i >= 24:
            states['BTC_RETURN_24H'][i] = btc[i] / btc[i - 24] - 1 > 0
        if rv24[i] is not None and rv24_med720[i] is not None:
            states['BTC_LOW_VOL_24H_VS_720H_MEDIAN'][i] = rv24[i] <= rv24_med720[i]
        if i >= 719:
            peak = max(btc[i - 719:i + 1])
            states['BTC_DRAWDOWN_720H_GT_MINUS10PCT'][i] = btc[i] / peak - 1 >= -0.10

        if eth_sma72[i] is not None:
            signals['ETH_TREND_STATE_72H'][i] = eth[i] > eth_sma72[i]
        if i >= 1 and eth_sma72[i] is not None and eth_sma72[i - 1] is not None:
            signals['ETH_TREND_TRANSITION_72H'][i] = eth[i] > eth_sma72[i] and eth[i - 1] <= eth_sma72[i - 1]
        if i >= 24:
            signals['ETH_MOMENTUM_24H'][i] = eth[i] / eth[i - 24] - 1 > 0

    return {'states': states, 'signals': signals}


def simulate_fixed_hold(
    segment: list[dict], enter_flags: list[bool | None], start: int, end: int, prereg: dict
) -> list[dict]:
    trades: list[dict] = []
    next_allowed_signal_i = 0
    hold = int(prereg['interaction']['holding_period_hours'])
    pside = prereg['costs']['primary_bps_per_side'] / 10000
    sside = prereg['costs']['stress_bps_per_side'] / 10000
    for i, flag in enumerate(enter_flags):
        if i < next_allowed_signal_i or flag is not True:
            continue
        decision_t = segment[i]['time']
        entry_i = i + 1
        exit_i = entry_i + hold
        if decision_t < start or entry_i >= len(segment) or exit_i >= len(segment):
            continue
        entry_t = segment[entry_i]['time']
        exit_t = segment[exit_i]['time']
        if entry_t > end or exit_t > end:
            continue
        entry = segment[entry_i]['eth_open']
        exitp = segment[exit_i]['eth_open']
        gross = exitp / entry - 1
        trades.append({
            'decision_time': decision_t,
            'entry_time': entry_t,
            'exit_time': exit_t,
            'gross_return': gross,
            'net_primary': gross - 2 * pside,
            'net_stress': gross - 2 * sside,
        })
        next_allowed_signal_i = exit_i
    return trades


def raw_metrics(trades: list[dict], minimum: int) -> dict:
    n = len(trades)
    if n < minimum:
        return {'n': n, 'available': False, 'reason': 'MINIMUM_TRADES_FAIL_CLOSED'}
    primary = [x['net_primary'] for x in trades]
    stress = [x['net_stress'] for x in trades]
    sd = sample_sd(primary)
    if sd == 0:
        return {'n': n, 'available': False, 'reason': 'ZERO_VARIANCE_FAIL_CLOSED'}
    mp = statistics.mean(primary)
    ms = statistics.mean(stress)
    return {'n': n, 'available': True, 'mean_net_primary': mp, 'mean_net_stress': ms, 'effect': mp / sd}


def evaluate_partition(segments: list[list[dict]], prereg: dict, start: int, end: int, minimum: int) -> dict:
    state_ids = [x['state_id'] for x in prereg['benchmark_states']]
    signal_ids = [x['signal_id'] for x in prereg['target_signals']]
    candidate_trades = {(s, q): [] for s in state_ids for q in signal_ids}
    baseline_trades = {q: [] for q in signal_ids}

    for segment in segments:
        if len(segment) < 2:
            continue
        f = feature_flags(segment)
        for signal_id in signal_ids:
            sig = f['signals'][signal_id]
            baseline_trades[signal_id].extend(simulate_fixed_hold(segment, sig, start, end, prereg))
            for state_id in state_ids:
                state = f['states'][state_id]
                gated = [True if a is True and b is True else False if a is not None and b is not None else None for a, b in zip(sig, state)]
                candidate_trades[(state_id, signal_id)].extend(simulate_fixed_hold(segment, gated, start, end, prereg))

    baselines: dict[str, dict] = {}
    for signal_id, trades in baseline_trades.items():
        # Baseline is a comparator, not a candidate gate. Two observations are enough to
        # define its effect; if it cannot be defined, incremental comparison fails closed.
        baselines[signal_id] = raw_metrics(trades, 2)

    cases = {}
    for (state_id, signal_id), trades in candidate_trades.items():
        cid = f'{state_id}::{signal_id}::GATE'
        gated = raw_metrics(trades, minimum)
        baseline = baselines[signal_id]
        passed = False
        reason = None
        if not gated.get('available'):
            reason = gated.get('reason')
        elif not baseline.get('available'):
            reason = 'BASELINE_METRICS_UNAVAILABLE_FAIL_CLOSED'
        else:
            passed = (
                gated['effect'] > 0
                and gated['mean_net_primary'] > 0
                and gated['mean_net_stress'] >= 0
                and gated['mean_net_primary'] > baseline['mean_net_primary']
                and gated['effect'] >= baseline['effect']
            )
            if not passed:
                reason = 'FROZEN_INCREMENTAL_GATE_FAIL'
        cases[cid] = {
            'candidate_id': cid,
            'state_id': state_id,
            'signal_id': signal_id,
            'gated': gated,
            'ungated_baseline': baseline,
            'pass': passed,
            'reason': reason,
        }
    return {'cases': cases, 'baselines': baselines}


def fetch_phase(prereg: dict, phase: str, fetcher: Callable, audit: dict) -> tuple[list[list[dict]], int, int]:
    p = prereg['partitions'][phase]
    start, end = ts(p['start']), ts(p['end_inclusive'])
    earliest = ts(prereg['market_data']['download_start_utc'])
    fetch_start = max(earliest, start - WARMUP_HOURS * HOUR)
    fetch_end = end + HOUR
    btc = fetcher('BTC-USD', fetch_start, fetch_end)
    btc_audit = dict(gap.GAP_AUDIT.get('BTC-USD', {}))
    eth = fetcher('ETH-USD', fetch_start, fetch_end)
    eth_audit = dict(gap.GAP_AUDIT.get('ETH-USD', {}))
    segments, sync_audit = synchronized_segments(btc, eth)
    audit[phase] = {'BTC-USD': btc_audit, 'ETH-USD': eth_audit, 'synchronization': sync_audit}
    return segments, start, end


def execute(prereg: dict, fetcher: Callable = gap.fetch_coinbase_sparse) -> dict:
    assert prereg['family_id'] == 'H-XREGIME-01'
    assert prereg['status'] == 'FROZEN_BEFORE_BATCH_OUTCOME_READ'
    assert prereg['candidate_construction']['candidate_count'] == 12
    assert prereg['interaction']['form'] == 'GATE'
    assert prereg['scientific_boundary']['batch_outcomes_read_before_freeze'] is False
    assert prereg['decision_rule']['promotion_authority'] is False
    gap.GAP_AUDIT.clear()
    audit: dict[str, dict] = {}
    mins = prereg['decision_rule']['minimum_trades']

    dseg, ds, de = fetch_phase(prereg, 'discovery', fetcher, audit)
    discovery = evaluate_partition(dseg, prereg, ds, de, mins['discovery'])
    discovery_passers = [cid for cid, x in discovery['cases'].items() if x['pass']]

    validation = {'cases': {}, 'baselines': {}}
    validation_passers: list[str] = []
    validation_opened = bool(discovery_passers)
    if validation_opened:
        vseg, vs, ve = fetch_phase(prereg, 'validation', fetcher, audit)
        all_v = evaluate_partition(vseg, prereg, vs, ve, mins['validation'])
        validation = {
            'cases': {cid: all_v['cases'][cid] for cid in discovery_passers},
            'baselines': all_v['baselines'],
        }
        validation_passers = [cid for cid, x in validation['cases'].items() if x['pass']]

    holdout = {'cases': {}, 'baselines': {}}
    historical_triage_passes: list[str] = []
    holdout_opened = bool(validation_passers)
    if holdout_opened:
        hseg, hs, he = fetch_phase(prereg, 'holdout', fetcher, audit)
        all_h = evaluate_partition(hseg, prereg, hs, he, mins['holdout'])
        holdout = {
            'cases': {cid: all_h['cases'][cid] for cid in validation_passers},
            'baselines': all_h['baselines'],
        }
        historical_triage_passes = [cid for cid, x in holdout['cases'].items() if x['pass']]

    terminal = {}
    for cid in discovery['cases']:
        if cid not in discovery_passers:
            terminal[cid] = 'REJECTED_DISCOVERY_NO_RETUNE'
        elif cid not in validation_passers:
            terminal[cid] = 'REJECTED_VALIDATION_NO_RETUNE'
        elif cid not in historical_triage_passes:
            terminal[cid] = 'REJECTED_HOLDOUT_NO_RETUNE'
        else:
            terminal[cid] = 'HISTORICAL_TRIAGE_PASS_PROSPECTIVE_REQUIRED_ZERO_CREDIT'

    return {
        'schema': 'qrds.factory.xregime_01.historical_eval.v1',
        'family_id': 'H-XREGIME-01',
        'batch_id': prereg['batch_id'],
        'status': 'HISTORICAL_TRIAGE_COMPLETE_PASSES_EXIST' if historical_triage_passes else 'HISTORICAL_TRIAGE_COMPLETE_NO_PASS',
        'registered_candidate_count': 12,
        'discovery_pass_count': len(discovery_passers),
        'validation_pass_count': len(validation_passers),
        'historical_triage_pass_count': len(historical_triage_passes),
        'historical_triage_passes': historical_triage_passes,
        'validation_source_opened': validation_opened,
        'holdout_source_opened': holdout_opened,
        'discovery': discovery,
        'validation': validation,
        'holdout': holdout,
        'terminal_status': terminal,
        'source_gap_audit': audit,
        'missing_bar_policy_applied': 'INELIGIBLE_NO_IMPUTATION',
        'imputed_bar_count': 0,
        'historical_survivor_credit': 0,
        'prospective_credit': 0,
        'promotion_authority': False,
        'next_gate': 'SEPARATE_PROSPECTIVE_ACTIVATION_PREREG_REQUIRED' if historical_triage_passes else 'XREGIME01_BATCH_A_CLOSE_NO_HISTORICAL_TRIAGE_PASS',
        'safety': prereg['safety'],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--prereg', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    prereg = json.loads(args.prereg.read_text(encoding='utf-8'))
    result = execute(prereg)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': result['status'],
        'discovery_pass': result['discovery_pass_count'],
        'validation_pass': result['validation_pass_count'],
        'historical_triage_passes': result['historical_triage_passes'],
    }, sort_keys=True))


if __name__ == '__main__':
    main()
