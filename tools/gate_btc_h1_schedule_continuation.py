"""Add future structural opportunities without rewriting the frozen H1 calendars."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from gate_btc_h1_schedule_extension import EXTENSION_FILE, EXTENSION_SHA256, load_extension

CONTINUATION_FILE = Path(__file__).resolve().parent / 'gate_btc_factory/H1_PROSPECTIVE_CONTINUATION_20261101.v1.json'
CONTINUATION_SHA256 = '724397c30ffbe0add3732e9eb5a184f0414c9c281005816487cfaabdb16ce1b5'
FUTURE_SESSIONS = ('2026-11-03', '2026-11-04', '2026-11-05', '2026-11-06',
                   '2026-11-09', '2026-11-10', '2026-11-11', '2026-11-12',
                   '2026-11-13', '2026-11-16')


def load_continuation() -> dict:
    raw = CONTINUATION_FILE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONTINUATION_SHA256:
        raise RuntimeError('H1_CONTINUATION_HASH_MISMATCH')
    d = json.loads(raw)
    parent = load_extension()
    if (d.get('schema') != 'qrds.h1.prospective_schedule_continuation.v1'
            or d.get('parent_extension_sha256') != EXTENSION_SHA256
            or hashlib.sha256(EXTENSION_FILE.read_bytes()).hexdigest() != EXTENSION_SHA256):
        raise RuntimeError('H1_CONTINUATION_PARENT_SEAL_CHANGED')
    for field in ('parent_amendment_sha256', 'legacy_schedule_prefix_sha256',
                  'legacy_full_frozen_schedule_sha256', 'continuity_policy', 'qa_unchanged', 'safety'):
        if d.get(field) != parent[field]:
            raise RuntimeError('H1_CONTINUATION_FROZEN_BOUNDARY_CHANGED:' + field)
    if (d.get('canonical_counter_preserved') != 18
            or d.get('canonical_last_qualified_session') != '2026-10-23'
            or d.get('target') != 20):
        raise RuntimeError('H1_CONTINUATION_COUNTER_BOUNDARY_CHANGED')
    if (d.get('sessions') != [{'date': day, 'WIN': 'WINZ26', 'WDO': 'WDOZ26'} for day in FUTURE_SESSIONS]
            or d.get('first_eligible_session') != FUTURE_SESSIONS[0]
            or d.get('last_eligible_session') != FUTURE_SESSIONS[-1]
            or d.get('excluded_exchange_holidays') != ['2026-11-02']):
        raise RuntimeError('H1_CONTINUATION_SESSION_LIST_INVALID')
    registered = datetime.fromisoformat(d['preregistered_at_utc'].replace('Z', '+00:00'))
    first_open = datetime.fromisoformat(FUTURE_SESSIONS[0] + 'T09:00:00-03:00')
    if registered.tzinfo is None or not datetime.fromisoformat('2026-11-01T00:00:00+00:00') <= registered < first_open:
        raise RuntimeError('H1_CONTINUATION_NOT_FROZEN_BEFORE_FIRST_SESSION')
    if d.get('freeze_status') != 'FROZEN_BEFORE_SESSION_CONTINUATION_20261101_V1':
        raise RuntimeError('H1_CONTINUATION_FREEZE_STATUS_CHANGED')
    return d


def continuation_schedule() -> dict[str, dict[str, str]]:
    return {r['date']: {'WIN': r['WIN'], 'WDO': r['WDO']} for r in load_continuation()['sessions']}
