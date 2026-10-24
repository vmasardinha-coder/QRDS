"""Publish existing H31 evidence and freeze blinded crypto data; never collect/trade."""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def safety(d, upper=True):
    names = ('ORDERS', 'REAL_CAPITAL', 'ENGINE_FEED') if upper else ('orders', 'real_capital', 'engine_feed')
    if any(d.get(k) != v for k, v in zip(names, (0, 0, False))):
        raise ValueError('SAFETY_MISMATCH')


def publish_h31(spool: Path, target: Path):
    """Plan fully before writing. Existing immutable events are never replaced."""
    source_status = spool / 'INTRADAY_STATUS.json'
    d = read(source_status)
    if d.get('schema') != 'gate_btc.b3.h31.intraday_shadow_status.v1':
        raise ValueError('BAD_H31_STATUS_SCHEMA')
    safety(d)
    if d.get('SHADOW_CREDIT_TO_CANONICAL') != 0 or d.get('CANONICAL_COUNTER_CHANGED') is not False:
        raise ValueError('CANONICAL_BOUNDARY')
    session = d['H31_INTRADAY_SESSION']
    datetime.strptime(session, '%Y-%m-%d')
    destination_status = target / 'INTRADAY_STATUS.json'
    old = read(destination_status) if destination_status.exists() else {}
    if old.get('H31_INTRADAY_SESSION', '') > session:
        return {'status': 'REMOTE_NEWER_PRESERVED', 'events_added': 0}
    for key in ('H31_SHADOW_SESSIONS', 'H31_SHADOW_TRIGGERED_SESSIONS', 'H31_SHADOW_CLOSED_TRADES'):
        if int(d.get(key, -1)) < int(old.get(key, 0)):
            raise ValueError('COUNTER_REGRESSION:' + key)
    writes = []
    latest_events = []
    for source in sorted((spool / 'intraday_events').glob('*/*.json')):
        e = read(source)
        if e.get('schema') != 'gate_btc.b3.h31.intraday_shadow_event.v1':
            raise ValueError('BAD_EVENT_SCHEMA')
        safety(e)
        if e.get('SHADOW_CREDIT_TO_CANONICAL') != 0:
            raise ValueError('EVENT_CANONICAL_CREDIT')
        digest = e.get('event_hash_sha256')
        if sha(canonical({k: v for k, v in e.items() if k != 'event_hash_sha256'})) != digest:
            raise ValueError('EVENT_HASH_MISMATCH')
        if source.stem != digest or source.parent.name != e.get('session'):
            raise ValueError('EVENT_PATH_MISMATCH')
        destination = target / 'intraday_events' / source.parent.name / source.name
        if destination.exists():
            if read(destination) != e:
                raise ValueError('IMMUTABLE_EVENT_CONFLICT')
        else:
            writes.append((destination, source.read_bytes()))
        if e['session'] == session:
            latest_events.append(e)
    if not latest_events:
        raise ValueError('SESSION_EVENT_EVIDENCE_MISSING')
    if d.get('H31_PAPER_POSITION') == 'CLOSED' and not any(e.get('event_type') == 'PAPER_CLOSE' for e in latest_events):
        raise ValueError('CLOSE_EVIDENCE_MISSING')
    # A later same-session remote status is preserved; archived missing events may still append.
    replace_status = d.get('updated_at', '') > old.get('updated_at', '')
    for destination, raw in writes:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    if replace_status:
        target.mkdir(parents=True, exist_ok=True)
        destination_status.write_bytes(source_status.read_bytes())
    return {'status': 'EXISTING_LOCAL_EVIDENCE_PUBLISHED', 'session': session,
            'events_added': len(writes), 'status_updated': replace_status,
            'canonical_credit': 0, 'orders': 0, 'real_capital': 0}


def freeze_crossvenue(root: Path, prereg: Path, capture_code: Path):
    """Bind bytes and metadata only. No price arithmetic or outcome selection."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('crossvenue_capture', capture_code)
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)
    output = root / 'DATASET_BINDING_N1440.json'
    if output.exists():
        binding = read(output)
        if sha(canonical({k: v for k, v in binding.items() if k != 'binding_payload_sha256'})) != binding.get('binding_payload_sha256'):
            raise ValueError('FROZEN_BINDING_CHANGED')
        for row in binding['partitions']:
            if sha((root / 'partitions' / row['file']).read_bytes()) != row['sha256']:
                raise ValueError('FROZEN_PARTITION_CHANGED')
        return {'status': 'FROZEN_BINDING_PRESERVED', 'record_count': binding['record_count']}
    protocol = read(prereg)
    admission = root.parent.parent / 'SOURCE_COST.json'
    _, evidence = capture.qualified_source_cost(admission)
    manifest = capture.build_manifest(root / 'partitions')
    published = read(root / 'MANIFEST.json')
    for key in ('partitions', 'eligible_unique_observation_count', 'first_observation_id', 'last_observation_id'):
        if published.get(key) != manifest[key]:
            raise ValueError('PUBLISHED_MANIFEST_MISMATCH:' + key)
    if manifest['source_cost_evidence_sha256'] != evidence:
        raise ValueError('ADMISSION_EVIDENCE_MISMATCH')
    minimum = protocol['evaluation']['minimum_observation_count_before_first_economics']
    if minimum != 1440 or protocol.get('economics_read') is not False:
        raise ValueError('FROZEN_PROTOCOL_MISMATCH')
    if manifest['eligible_unique_observation_count'] < minimum:
        return {'status': 'WAITING_CHECKPOINT', 'record_count': manifest['eligible_unique_observation_count']}
    stamp = lambda value: datetime.fromtimestamp(int(value) / 1000, timezone.utc).isoformat()
    binding = {
        'schema': 'qrds.factory.crypto_745_crossvenue_dataset_binding.v1',
        'channel_id': capture.CHANNEL_ID, 'checkpoint': minimum,
        'bound_at_utc': datetime.now(timezone.utc).isoformat(),
        'selection_rule': 'ALL_SEALED_PARTITIONS_AT_FIRST_BINDING_NO_OUTCOME_SELECTION',
        'record_count': manifest['eligible_unique_observation_count'],
        'first_eligible_timestamp_utc': stamp(manifest['first_observation_id']),
        'last_eligible_timestamp_utc': stamp(manifest['last_observation_id']),
        'source_metadata': {
            'coinbase': {'endpoint': 'https://api.exchange.coinbase.com/products/BTC-USD/trades', 'version': 'Exchange REST'},
            'okx': {'endpoint': 'https://www.okx.com/api/v5/market/trades', 'version': 'v5', 'instrument': 'BTC-USDT-SWAP'},
            'partition_schemas': sorted({p['schema'] for p in manifest['partitions']})},
        'prereg_sha256': sha(prereg.read_bytes()),
        'capture_code_sha256': sha(capture_code.read_bytes()),
        'source_cost_file_sha256': sha(admission.read_bytes()),
        'source_cost_evidence_sha256': evidence,
        'partitions': manifest['partitions'],
        'duplicate_observation_ids_zero_credit': manifest['duplicate_observation_ids_zero_credit'],
        'economics_read': False, 'economics_computed': False,
        'scientific_credit': 0, 'historical_backfill_credit': 0,
        'next_action': 'IMPLEMENT_OR_RUN_FROZEN_ECONOMIC_EVALUATION_WITH_BINDING_VERIFICATION',
        'safety': capture.SAFETY}
    binding['binding_payload_sha256'] = sha(canonical(binding))
    output.write_text(json.dumps(binding, indent=2, sort_keys=True) + '\n')
    return {'status': 'BLINDED_DATASET_BOUND', 'record_count': binding['record_count'],
            'partition_count': len(binding['partitions']), 'economics_read': False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['h31', 'crossvenue'], required=True)
    ap.add_argument('--runtime', type=Path, required=True)
    ap.add_argument('--spool', type=Path)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    if args.mode == 'h31':
        if not args.spool:
            ap.error('--spool required')
        result = publish_h31(args.spool, args.runtime / 'runtime/ledgers/b3_h31_shadow_paper')
    else:
        result = freeze_crossvenue(args.runtime / 'runtime/factory_sources/crypto_challenger_745/forward/cross_venue',
                                  here / 'gate_btc_factory/crypto_challenger_prereg/CRYPTO_CROSS_VENUE_PRICE_DISCOVERY_PREREG.v1.json',
                                  here / 'gate_btc_factory/crypto_745_crossvenue_forward_capture.py')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
