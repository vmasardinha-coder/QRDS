#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

INFRA_TOKENS = (
    'DATA_GAP', 'SOURCE', 'MISSING', 'SCHEMA', 'TIMESTAMP', 'COVERAGE',
    'OHLC', 'TICK', 'DOWNLOAD', 'PARSE', 'LATTICE', 'UNAVAILABLE',
)


def generation_start(name: str) -> int | None:
    m = re.search(r'_h(\d+)_h\d+_result\.json$', name.lower())
    return int(m.group(1)) if m else None


def reason_class(reason: str) -> str:
    r = reason.upper()
    if r == 'NO_TRADES':
        return 'NO_TRADES'
    if any(tok in r for tok in INFRA_TOKENS):
        return 'INFRASTRUCTURE_OR_DATA'
    return 'SCIENTIFIC_REJECTION'


def load(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        raise ValueError(f'expected object: {path}')
    return obj


def _all_no_trades(row: dict) -> bool:
    counts = row.get('class_counts') or {}
    return bool(counts.get('NO_TRADES', 0) > 0 and set(counts) == {'NO_TRADES'})


def _root_cause_override(root_cause: dict | None) -> tuple[set[str], str | None]:
    if not root_cause:
        return set(), None
    if root_cause.get('scientific_contract_changed') is not False:
        return set(), None
    if root_cause.get('historical_integrity_status') != 'HISTORICAL_RESULT_INVALIDATED_BY_MECHANICAL_DEFECT':
        return set(), None
    cls = str(root_cause.get('root_cause_classification') or '')
    if cls != 'SOURCE_DATA_GAP':
        return set(), None
    ids = {
        str(x) for x in ((root_cause.get('affected_scope') or {}).get('family_ids') or [])
        if str(x).startswith('H')
    }
    return ids, cls


def audit(results_dir: Path, root_cause: dict | None = None) -> dict:
    files = sorted(results_dir.glob('gate_btc_b3_h*_h*_result.json'), key=lambda p: generation_start(p.name) or -1)
    override_ids, override_class = _root_cause_override(root_cause)
    reasons = Counter()
    classes = Counter()
    features = Counter()
    directions = Counter()
    generation_rows = []
    survivors = []
    near_gate = []
    families_total = 0
    cells_total = 0
    discovery_qualified_families = 0
    replication_attempted_families = 0
    overridden_cells = 0

    for path in files:
        obj = load(path)
        gen = str(obj.get('generation', path.stem))
        gen_reasons = Counter()
        gen_classes = Counter()
        gen_survivors = list(obj.get('survivors') or [])
        survivors.extend(str(x) for x in gen_survivors)
        families = obj.get('families') or []
        for fam in families:
            if not isinstance(fam, dict):
                continue
            families_total += 1
            fid = str(fam.get('family_id', 'UNKNOWN'))
            contract = fam.get('contract') or {}
            if contract.get('feature'):
                features[str(contract['feature'])] += 1
            if contract.get('direction'):
                directions[str(contract['direction'])] += 1
            disc = fam.get('discovery') or {}
            rep = fam.get('replication') or {}
            dq = int(disc.get('qualified_cells', 0) or 0)
            rq = int(rep.get('qualified_cells', 0) or 0)
            if dq > 0:
                discovery_qualified_families += 1
            rep_cells = rep.get('cells') or []
            if rep_cells:
                replication_attempted_families += 1
            if dq > 0 and not fam.get('replicated', False):
                near_gate.append({
                    'family_id': fid,
                    'generation': gen,
                    'discovery_qualified_cells': dq,
                    'replication_qualified_cells': rq,
                    'replication_not_run_reason': rep.get('not_run_reason'),
                })
            for stage in (disc, rep):
                for cell in stage.get('cells') or []:
                    if not isinstance(cell, dict):
                        continue
                    cells_total += 1
                    metrics = cell.get('metrics') or {}
                    cell_reasons = list(metrics.get('reasons') or [])
                    if not cell_reasons and cell.get('qualified') is False:
                        cell_reasons = ['UNSPECIFIED_REJECTION']
                    if fid in override_ids and set(cell_reasons) == {'NO_TRADES'}:
                        cell_reasons = ['SOURCE_DATA_GAP']
                        overridden_cells += 1
                    for raw in cell_reasons:
                        reason = str(raw)
                        cls = reason_class(reason)
                        reasons[reason] += 1
                        classes[cls] += 1
                        gen_reasons[reason] += 1
                        gen_classes[cls] += 1
        generation_rows.append({
            'generation': gen,
            'status': obj.get('status'),
            'family_count': len(families),
            'survivors': gen_survivors,
            'reason_counts': dict(gen_reasons.most_common()),
            'class_counts': dict(gen_classes),
        })

    post_h31 = []
    for fid in survivors:
        m = re.fullmatch(r'H(\d+)', fid.upper())
        if m and int(m.group(1)) > 31:
            post_h31.append(fid)

    judged = sum(classes.values())
    infra = classes['INFRASTRUCTURE_OR_DATA']
    no_trades = classes['NO_TRADES']
    scientific = classes['SCIENTIFIC_REJECTION']
    latest_20 = generation_rows[-20:]
    recent_no_trades_streak = []
    for row in reversed(generation_rows):
        if not _all_no_trades(row):
            break
        recent_no_trades_streak.append(row['generation'])
    recent_no_trades_streak.reverse()
    latest_20_all_no_trades = bool(len(latest_20) == 20 and all(_all_no_trades(row) for row in latest_20))
    no_trades_concentration = bool(judged and no_trades / judged >= 0.50)
    anomaly_detected = bool(latest_20_all_no_trades or no_trades_concentration)
    override_applied = bool(overridden_cells)
    root_cause_work_required = bool(anomaly_detected and not override_applied)

    return {
        'schema': 'qrds.factory.scientific_mortality.v2',
        'generated_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'results_authority': 'gate-btc-runtime/runtime/autonomous_science/results',
        'generations_scanned': len(files),
        'first_generation': generation_rows[0]['generation'] if generation_rows else None,
        'latest_generation': generation_rows[-1]['generation'] if generation_rows else None,
        'families_scanned': families_total,
        'cells_scanned': cells_total,
        'discovery_qualified_families': discovery_qualified_families,
        'replication_attempted_families': replication_attempted_families,
        'survivors': sorted(set(survivors)),
        'post_h31_survivors': sorted(set(post_h31)),
        'near_gate_families': near_gate[-100:],
        'near_gate_family_count': len(near_gate),
        'anomaly_detected': anomaly_detected,
        'root_cause_unresolved': root_cause_work_required,
        'root_cause_work_required': root_cause_work_required,
        'root_cause_rule': 'ANOMALY_DETECTED && ROOT_CAUSE_UNRESOLVED => ROOT_CAUSE_WORK_REQUIRED',
        'root_cause_override': {
            'classification': override_class,
            'affected_family_count': len(override_ids),
            'overridden_no_trade_cells': overridden_cells,
            'historical_results_mutated': False,
        },
        'mortality': {
            'reason_counts': dict(reasons.most_common()),
            'class_counts': dict(classes),
            'judged_cell_reasons': judged,
            'no_trades_fraction': (no_trades / judged) if judged else None,
            'infrastructure_or_data_fraction': (infra / judged) if judged else None,
            'scientific_rejection_fraction': (scientific / judged) if judged else None,
        },
        'family_grammar_distribution': {
            'features': dict(features.most_common()),
            'directions': dict(directions.most_common()),
        },
        'latest_20_generations': latest_20,
        'recent_all_no_trades_streak': {
            'generation_count': len(recent_no_trades_streak),
            'generations': recent_no_trades_streak,
        },
        'interpretation': {
            'infrastructure_bottleneck_flag': bool(judged and infra / judged >= 0.20),
            'no_trades_concentration_flag': no_trades_concentration,
            'latest_20_all_no_trades_flag': latest_20_all_no_trades,
            'post_h31_survivor_found': bool(post_h31),
            'root_cause_override_applied': override_applied,
        },
        'safety': {
            'research_only': True,
            'shadow_only': True,
            'scientific_change_allowed': False,
            'backfill_allowed': False,
            'retune_allowed': False,
            'counter_reset_allowed': False,
            'engine_feed': False,
            'orders': 0,
            'real_capital': 0,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--results-dir', type=Path, required=True)
    ap.add_argument('--root-cause', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    ns = ap.parse_args()
    root_cause = load(ns.root_cause) if ns.root_cause and ns.root_cause.exists() else None
    report = audit(ns.results_dir, root_cause=root_cause)
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'generations': report['generations_scanned'],
        'families': report['families_scanned'],
        'survivors': report['survivors'],
        'post_h31_survivors': report['post_h31_survivors'],
        'mortality': report['mortality']['class_counts'],
        'root_cause_work_required': report['root_cause_work_required'],
        'root_cause_override': report['root_cause_override'],
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
