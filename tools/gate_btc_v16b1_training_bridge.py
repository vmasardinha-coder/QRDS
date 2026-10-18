"""Derived model-only universe from hash-verified, matured prospective weeks.

Never rewrites source weeks, creates missing identities, credits missed cycles,
or lowers the frozen 52-prior-week model gate. External authoritative history
retains priority in the publisher; this is the prospective corpus alternative.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tools.gate_btc_v16b1_prospective_training import FEATURES

BASE = Path('runtime/evidence/v16b1/prospective_training/weeks')
COLUMNS = ['signal_date', 'symbol', 'evidence_class', 'snapshot_effective_date',
           'retrieved_at_utc', 'source_ref', 'snapshot_sha256']
MODEL_ONLY = 'HISTORICAL_OFFICIAL_SNAPSHOT_MODEL_ONLY'
MIN_WEEKS = 52


def sha(raw): return hashlib.sha256(raw).hexdigest()


def verified(path, expected):
    raw = path.read_bytes()
    if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected) or sha(raw) != expected:
        raise ValueError('training corpus hash mismatch: ' + str(path))
    return raw


def prepare(runtime, signal_date, output, now=None):
    source_root = (Path(runtime)/BASE).resolve()
    if Path(output).name == 'HISTORICAL_WEEKLY_UNIVERSE_MODEL_ONLY.csv' or Path(output).resolve().is_relative_to(source_root):
        raise ValueError('training bridge cannot overwrite external history or source corpus')
    current = date.fromisoformat(signal_date)
    if current.weekday() != 3:
        raise ValueError('training bridge requires a Thursday signal')
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError('training bridge requires aware clock')
    rows, receipts = [], []
    for directory in sorted((Path(runtime)/BASE).glob('20??-??-??')):
        matured = directory/'MATURED.json'
        if not matured.exists():
            continue
        meta = json.loads(matured.read_bytes())
        week_raw = (directory/'WEEK.json').read_bytes()
        week = json.loads(week_raw)
        d = date.fromisoformat(directory.name)
        if d >= current:
            continue
        exit_day = d + timedelta(days=8)
        # The model uses only prior dates whose frozen exit is already closed.
        if exit_day >= current or datetime.combine(exit_day + timedelta(days=1), datetime.min.time(), timezone.utc) > clock:
            continue
        if (d < date(2026, 10, 1) or d.weekday() != 3 or week.get('signal_date') != d.isoformat()
                or week.get('entry_date') != (d+timedelta(days=1)).isoformat()
                or week.get('exit_date') != exit_day.isoformat()
                or meta.get('label_status') != 'SEALED_AFTER_FROZEN_EXIT'):
            raise ValueError('training corpus frozen dates/status mismatch')
        for key, value in week.items():
            if key != 'label_status' and meta.get(key) != value:
                raise ValueError('matured metadata differs from frozen week: ' + key)
        for key, value in {'RESEARCH_ONLY':True, 'SHADOW_ONLY':True, 'NOT_APPROVED':True,
                           'ENGINE_FEED':False, 'ORDERS':0, 'REAL_CAPITAL':0,
                           'NO_BACKFILL':True, 'NO_RETUNE':True, 'scientific_credit':0}.items():
            if meta.get(key) != value:
                raise ValueError('unsafe training corpus: ' + key)
        fraw = verified(directory/'FEATURES.csv', meta['features_sha256'])
        verified(directory/'EXCLUSIONS.csv', meta['exclusions_sha256'])
        labels_raw = verified(directory/'LABELS.csv', meta['labels_sha256'])
        evidence_raw = verified(directory/'LABEL_EVIDENCE.json', meta['label_evidence_sha256'])
        evidence = json.loads(evidence_raw)
        if (evidence.get('week_sha256') != sha(week_raw)
                or evidence.get('features_sha256') != meta['features_sha256']
                or evidence.get('labels_sha256') != meta['labels_sha256']
                or evidence.get('signal_date') != d.isoformat()
                or evidence.get('source') != 'BINANCE_SPOT_DAILY_KLINE_DATA_VISION_CHECKSUM'):
            raise ValueError('training label evidence binding mismatch')
        features = list(csv.DictReader(io.StringIO(fraw.decode())))
        labels = list(csv.DictReader(io.StringIO(labels_raw.decode())))
        symbols = [r['symbol'] for r in features]
        if (not symbols or len(symbols) != len(set(symbols)) or len(symbols) != meta['eligible_feature_rows']
                or len(labels) != len(symbols) or sorted(r['symbol'] for r in labels) != sorted(symbols)
                or any(not math.isfinite(float(r['fwd_ret'])) for r in labels)):
            raise ValueError('training labels/membership mismatch')
        for r in features:
            retrieved = datetime.fromisoformat(r['retrieved_at_utc'].replace('Z', '+00:00'))
            if (r['signal_date'] != d.isoformat() or r['snapshot_effective_date'] != d.isoformat()
                    or r['evidence_class'] != 'CURRENT_PROSPECTIVE_PIT'
                    or r['feature_ok'].lower() != 'true'
                    or retrieved.tzinfo is None
                    or retrieved > datetime.combine(d+timedelta(days=1), datetime.min.time(), timezone.utc)
                    or not r['universe_source_ref'].strip()
                    or not re.fullmatch('[0-9a-f]{64}', r['universe_snapshot_sha256'])
                    or any(not math.isfinite(float(r[name])) for name in FEATURES)):
                raise ValueError('invalid frozen prospective feature provenance')
            rows.append({'signal_date':d.isoformat(), 'symbol':r['symbol'],
                'evidence_class':MODEL_ONLY, 'snapshot_effective_date':d.isoformat(),
                'retrieved_at_utc':r['retrieved_at_utc'], 'source_ref':r['universe_source_ref'],
                'snapshot_sha256':r['universe_snapshot_sha256']})
        receipts.append({'signal_date':d.isoformat(), 'matured_sha256':sha(matured.read_bytes()),
                         'features_sha256':meta['features_sha256'], 'labels_sha256':meta['labels_sha256'],
                         'label_evidence_sha256':meta['label_evidence_sha256'], 'rows':len(features)})
    ready = len(receipts) >= MIN_WEEKS
    result = {'schema':'gate_btc.v16b1.training_corpus_bridge.v1', 'signal_date':signal_date,
        'status':'READY_HASH_VERIFIED_MODEL_ONLY_UNIVERSE' if ready else 'WAITING_52_MATURED_PRIOR_WEEKS',
        'matured_prior_weeks':len(receipts), 'required_prior_weeks':MIN_WEEKS,
        'remaining_prior_weeks':max(0, MIN_WEEKS-len(receipts)), 'source_weeks':receipts,
        'training_rows':len(rows), 'model_input_created':ready,
        'recomputed_features_and_model_still_require_frozen_pipeline_validation':True,
        'scientific_credit':0, 'prospective_credit':0, 'orders':0, 'real_capital':0,
        'source_corpus_modified':False, 'historical_file_overwritten':False}
    out = Path(output)
    if ready:
        buffer = io.StringIO(newline=''); writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator='\n')
        writer.writeheader(); writer.writerows(sorted(rows, key=lambda r:(r['signal_date'],r['symbol'])))
        raw = buffer.getvalue().encode()
        out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(raw)
        result['model_input_sha256'] = sha(raw)
    elif out.exists():
        # Never let an obsolete derived CSV survive a now-invalid readiness state.
        raise ValueError('stale derived training view must not bypass readiness')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--signal-date', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--status', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.runtime_root, args.signal_date, args.output)
    args.status.parent.mkdir(parents=True, exist_ok=True)
    args.status.write_bytes((json.dumps(result, indent=2, sort_keys=True)+'\n').encode())
    print(json.dumps({k:v for k,v in result.items() if k != 'source_weeks'}, sort_keys=True))


if __name__ == '__main__': main()
