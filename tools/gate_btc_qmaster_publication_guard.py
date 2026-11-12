"""Reject QMASTER publication regressions and same-cutoff source revisions."""
import argparse,hashlib,json,re
from datetime import date
from pathlib import Path


def validate(value):
    date.fromisoformat(value['data_as_of'])
    if value['status']!='PASS' or value['operational_status']!='NOT_APPROVED' or value['orders_generated']!=0 or value['real_capital_used']!=0:
        raise ValueError('QMASTER_AUTHORITY_CHANGED')
    if not re.fullmatch('[0-9a-f]{64}',value['csv_sha256']):
        raise ValueError('INVALID_CSV_SHA256')


def assess(candidate,published=None):
    validate(candidate)
    if published is None:return 'ADVANCE'
    validate(published)
    if candidate['data_as_of']<published['data_as_of']:return 'REFUSED_SOURCE_REGRESSION'
    if candidate['data_as_of']==published['data_as_of']:
        if candidate['csv_sha256']!=published['csv_sha256']:
            raise ValueError('SAME_CUTOFF_CHANGED_SOURCE_REVIEW_REQUIRED')
        return 'UNCHANGED'
    return 'ADVANCE'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--candidate-csv',type=Path,required=True);p.add_argument('--published',type=Path,required=True);a=p.parse_args()
    c=json.loads(a.candidate.read_text(encoding='utf-8-sig'))
    if hashlib.sha256(a.candidate_csv.read_bytes()).hexdigest()!=c['csv_sha256']:
        raise ValueError('CANDIDATE_CSV_HASH_MISMATCH')
    old=json.loads(a.published.read_text(encoding='utf-8-sig')) if a.published.is_file() else None
    print(assess(c,old))
