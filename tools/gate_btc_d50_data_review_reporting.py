"""Read-only documentary adjudication. Never imported by economic engines."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

REVIEW_SHA256 = '13d26b1c112dd45e0964212120a1d6141f7ad4cb835fc0bff74e0ecd89c52482'
SUBJECT_ZIP_SHA256 = 'f17a9e987930ef16f73f00d0f8c1a69fb1d10875cd32e1d176365a38f90911a5'
CONTRACT_SHA256 = 'f0b6a277053488def52fe730806d707b7746692fc5abeb868d27a34d7a8f76e0'
V32_ZIP_SHA256 = '38ce78be22bc64834018a0168c2076da7d05519443e4c00209523a30ce28c036'
CANDIDATE = 'D50_SLOW_NO_INTRADAY_STOP_7D_V2'
V32_ZIP_NAME = 'GATE_BTC_D50_7D_V32_RATIFICATION_2026-07-30.zip'
LEGACY_ROOT = Path(r'C:\GATE_BTC_PROJECT\RUNTIME\LEGACY_DATA_COLLECTION_V1\crypto_decision_lab')
DEFAULT_REVIEW_PATH = Path(r'C:\GATE_BTC_PROJECT\GOVERNANCE\D50_DATA_AUDIT_20261019\D50_PARECER.json')
ACCEPTED = {'CORRECTION_PASS_WINDOW_MAY_START', 'CORRECTION_PASS_WITH_NONBLOCKING_LIMITATIONS'}


def documentary_adjudication(review_path=None, *, contract_path=None, v32_zip_path=None,
                             prospective_status=None):
    """Verify frozen adjudication, optionally compare available original subjects.

    No rolling snapshot/current package hash comparison: the review binds the
    audited subject, not tomorrow's rolling window or AUTOPILOT V2 engine.
    """
    path = Path(review_path) if review_path is not None else DEFAULT_REVIEW_PATH
    result = {
        'status': 'MISSING', 'INDEPENDENT_DATA_AUDIT_COMPLETED': False,
        'WINDOW_MAY_START_DOCUMENTAL': False, 'WINDOW_MAY_START': False,
        'CAPITAL_REAL_ALLOWED': False, 'review_path': str(path),
        'scope': 'DOCUMENTARY_DATA_QUALIFICATION_ONLY',
        'production_attested': False, 'engine_feed': False, 'orders': 0,
        'audited_engine': 'V3.2_FROZEN_ARTIFACT_NOT_AUTOPILOT_V2',
        'subject_zip_sha256': SUBJECT_ZIP_SHA256,
        'data_qualification_at_audit': '7/7', 'required_complete_cycles': 12,
        'cycles_completion_inferred': False, 'subject_checks': {},
    }
    if prospective_status is not None:
        result['economic_observations_current'] = prospective_status.get('paired_prospective_observations')
        result['economic_next_checkpoint'] = prospective_status.get('next_checkpoint')
    try:
        if not path.is_file():
            result['reason'] = 'REVIEW_FILE_MISSING'
            return result
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        result['review_sha256'] = digest
        if digest != REVIEW_SHA256:
            raise ValueError('REVIEW_SHA256_MISMATCH')
        review = json.loads(raw.decode('utf-8-sig'))
        if review.get('schema') != 'gate_btc.d50_separate_agent_review.v1':
            raise ValueError('REVIEW_SCHEMA_MISMATCH')
        if review.get('subject_zip_sha256') != SUBJECT_ZIP_SHA256:
            raise ValueError('REVIEW_SUBJECT_MISMATCH')
        hashes = review.get('subject_hashes', {})
        def review_subject(name, expected):
            matches = [v for k,v in hashes.items() if k.replace('\\','/').split('/')[-1] == name]
            if matches != [expected]:
                raise ValueError('REVIEW_SUBJECT_HASH_MISMATCH:' + name)
        review_subject('candidate_contract_v32.json', CONTRACT_SHA256)
        review_subject(V32_ZIP_NAME, V32_ZIP_SHA256)
        if review.get('verdict') not in ACCEPTED:
            raise ValueError('REVIEW_VERDICT_NOT_ACCEPTED')
        if review.get('WINDOW_MAY_START') is not True or review.get('CAPITAL_REAL_ALLOWED') is not False:
            raise ValueError('REVIEW_FLAGS_INVALID')
        reviewer = review.get('reviewer', {})
        if reviewer.get('canonical_task') != '/root/revisao_d50' or reviewer.get('separate_context_from_discovery') is not True:
            raise ValueError('REVIEWER_MISMATCH')
        reqs = review.get('requirements', [])
        if len(reqs) != 7 or {r.get('id') for r in reqs} != set(range(1,8)) or any(
            r.get('decision') not in {'PASS','PASS_WITH_NONBLOCKING_LIMITATIONS'} or r.get('blocking') is not False for r in reqs
        ) or review.get('blocking_findings') != []:
            raise ValueError('REVIEW_REQUIREMENTS_INVALID')
        for label, subject_path, expected in [
            ('original_contract', Path(contract_path) if contract_path is not None else LEGACY_ROOT/'gate_btc_inputs/candidate_contract_v32.json', CONTRACT_SHA256),
            ('frozen_v32_zip', Path(v32_zip_path) if v32_zip_path is not None else LEGACY_ROOT/'gate_btc_inputs'/V32_ZIP_NAME, V32_ZIP_SHA256),
        ]:
            check = {'path': str(subject_path), 'status': 'UNAVAILABLE_NOT_ATTESTED'}
            result['subject_checks'][label] = check
            if subject_path.is_file():
                body = subject_path.read_bytes()
                check['sha256'] = hashlib.sha256(body).hexdigest()
                if check['sha256'] != expected:
                    check['status'] = 'MISMATCH'
                    raise ValueError('AVAILABLE_SUBJECT_MISMATCH:' + label)
                if label == 'original_contract':
                    contract = json.loads(body.decode('utf-8-sig'))
                    if contract.get('candidate_id') != CANDIDATE or contract.get('contract_version') != 'V3.2':
                        raise ValueError('AVAILABLE_CONTRACT_IDENTITY_MISMATCH')
                check['status'] = 'MATCH'
        result.update(status='VALID', INDEPENDENT_DATA_AUDIT_COMPLETED=True,
                      WINDOW_MAY_START_DOCUMENTAL=True, verdict=review['verdict'],
                      reviewer=reviewer['canonical_task'], reviewed_at_utc=review['reviewed_at_utc'],
                      candidate_id=CANDIDATE,
                      historical_qualification_status='PRE_REVIEW_ARCHIVE_UNCHANGED')
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result.update(status='INVALID', reason=str(exc))
    return result


def reporting_lines(adjudication):
    keys = ['INDEPENDENT_DATA_AUDIT_COMPLETED', 'WINDOW_MAY_START_DOCUMENTAL',
            'WINDOW_MAY_START', 'CAPITAL_REAL_ALLOWED']
    return ['D50_DATA_REVIEW_STATUS=' + str(adjudication['status'])] + [
        key + '=' + str(adjudication[key]) for key in keys
    ] + ['D50_DATA_REVIEW_VERDICT=' + str(adjudication.get('verdict', 'NOT_ACCEPTED')),
         'D50_DATA_REVIEW_SCOPE=DOCUMENTARY_DATA_QUALIFICATION_ONLY',
         'D50_PRODUCTION_ATTESTED=False',
         'D50_DATA_QUALIFICATION_AT_AUDIT=7/7',
         'D50_REQUIRED_COMPLETE_CYCLES=12',
         'D50_CYCLES_COMPLETION_INFERRED=False',
         'D50_ECONOMIC_OBSERVATIONS_CURRENT=' + str(adjudication.get('economic_observations_current', 'NOT_READ_BY_THIS_REPORT')),
         'D50_ECONOMIC_NEXT_CHECKPOINT=' + str(adjudication.get('economic_next_checkpoint', 'NOT_READ_BY_THIS_REPORT')),
         'D50_AUDITED_ENGINE=V3.2_FROZEN_ARTIFACT_NOT_AUTOPILOT_V2',
         'D50_DATA_REVIEW_SHA256=' + str(adjudication.get('review_sha256', 'UNAVAILABLE'))]
