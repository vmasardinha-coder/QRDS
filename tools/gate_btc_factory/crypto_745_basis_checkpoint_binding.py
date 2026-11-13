"""Outcome-blind binding of the original first 60 legacy-eligible Basis records."""
import argparse
import hashlib
import json
from pathlib import Path
from tools.gate_btc_factory.crypto_745_basis_forward_capture import (
    CHANNEL_ID, SAFETY, select_latest_predecision, select_latest_funding_before,
    select_first_postclock,
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bind(root, source_ref):
    raw = (root / 'MANIFEST.json').read_bytes()
    manifest = json.loads(raw)
    if manifest['channel_id'] != CHANNEL_ID or manifest['economics_read'] is not False:
        raise ValueError('MANIFEST_AUTHORITY_MISMATCH')
    items = sorted((x for x in manifest['partitions'] if x['eligible']), key=lambda x: int(x['observation_id']))
    if len({x['observation_id'] for x in items}) != len(items):
        raise ValueError('DUPLICATE_OBSERVATION_ID')
    original = items[:60]
    records = []
    for item in original:
        name = item['file']
        if Path(name).name != name or not name.endswith('.json'):
            raise ValueError('INVALID_PARTITION_NAME')
        raw = (root / 'partitions' / name).read_bytes()
        if sha(raw) != item['sha256']:
            raise ValueError('PARTITION_BYTES_CHANGED:' + name)
        d = json.loads(raw)
        if d['channel_id'] != CHANNEL_ID or d['economics_read'] is not False or d['scientific_credit'] != 0:
            raise ValueError('PARTITION_AUTHORITY_MISMATCH')
        o = d['observation']; decision = o['decision_ms']; settlement = o['settlement_ms']
        if str(settlement) != item['observation_id'] or o['eligible_for_future_evaluation'] is not True:
            raise ValueError('PARTITION_IDENTITY_MISMATCH')
        checks = {
            'decision_exact_5m': decision == settlement - 300000,
            'predecision_received_before_deadline': o['predecision_pair'] is not None and select_latest_predecision(d['quote_samples_decision_window'], decision) == o['predecision_pair'],
            'funding_received_before_deadline': o['funding_bound'] is not None and select_latest_funding_before(d['funding_samples_decision_window'], decision, settlement) == o['funding_bound'],
            'entry_reproduced': o['entry_pair'] is not None and select_first_postclock(d['quote_samples_decision_window'], decision) == o['entry_pair'],
            'entry_before_settlement': o['entry_pair'] is not None and max(o['entry_pair']['spot']['ts_ms'], o['entry_pair']['perp']['ts_ms']) < settlement,
            'exit_reproduced': o['exit_pair'] is not None and select_first_postclock(d['quote_samples_exit_window'], settlement, 60000) == o['exit_pair'],
        }
        records.append(dict(file=name, sha256=item['sha256'], observation_id=item['observation_id'], decision_ms=decision, settlement_ms=settlement, checks=checks, admissible=all(checks.values())))
    passed = sum(x['admissible'] for x in records)
    return dict(schema='qrds.factory.basis_original_n60_binding.v1', channel_id=CHANNEL_ID,
                source_ref=source_ref, checkpoint=60, selection='ORIGINAL_FIRST60_LEGACY_ELIGIBLE_ORDERED_BY_SETTLEMENT_NO_REPLACEMENT',
                original_record_count=len(records), causally_admissible_count=passed,
                status='BOUND_ORIGINAL_N60' if len(records)==passed==60 else 'ORIGINAL_N60_NOT_ADMISSIBLE' if len(records)==60 else 'WAIT_ORIGINAL_N60',
                records=records, source_cost_evidence_sha256=manifest['source_cost_evidence_sha256'],
                first_settlement_ms=records[0]['settlement_ms'] if records else None,
                last_settlement_ms=records[-1]['settlement_ms'] if records else None,
                endpoints=['https://www.okx.com/api/v5/market/ticker','https://www.okx.com/api/v5/public/funding-rate'],
                raw_http_bodies_preserved=False, sealed_partition_bytes_bound=True,
                economics_read=False, economics_read_allowed=False, outcome_metrics_computed=False,
                scientific_credit=0, historical_backfill_credit=0, counter_reset=False, original_population_replaced=False, safety=SAFETY)


def write_once(path, value):
    payload=(json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
    if path.exists():
        if path.read_bytes()!=payload:
            raise ValueError('IMMUTABLE_BINDING_CHANGED')
    else:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)


if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--source-ref',required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();ref=json.loads(a.out.read_bytes())['source_ref'] if a.out.exists() else a.source_ref;value=bind(a.root,ref);write_once(a.out,value)
    print(json.dumps({k:v for k,v in value.items() if k in ['status','original_record_count','causally_admissible_count','economics_read_allowed']}))
