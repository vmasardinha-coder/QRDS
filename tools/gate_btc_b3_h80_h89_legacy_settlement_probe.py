#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path('artifacts/b3_h80_h89_legacy_settlement/B3_H80_H89_LEGACY_SETTLEMENT_QA.json')
URL = 'https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-ajustes-do-pregao-ptBR.asp'
DATES = ['03/01/2020', '01/07/2020', '04/01/2021', '01/07/2021']
PREFIXES = ('WDO', 'DOL', 'WIN', 'IND', 'DI1')


def fetch(session: requests.Session, date_str: str):
    errors = []
    for attempt in range(1, 4):
        try:
            r = session.post(URL, data={'dData1': date_str}, timeout=(10, 45), allow_redirects=True)
            return r, errors
        except (requests.Timeout, requests.ConnectionError) as exc:
            errors.append({'attempt': attempt, 'error': type(exc).__name__ + ': ' + str(exc)[:200]})
            if attempt < 3:
                time.sleep(2 * attempt)
    return None, errors


def inspect(raw: bytes, requested: str):
    soup = BeautifulSoup(raw, 'html.parser', from_encoding='iso-8859-1')
    table = soup.find('table', id='tblDadosAjustes')
    date_input = soup.find('input', id='dData1')
    returned_date = date_input.get('value') if date_input else None
    if table is None:
        return {
            'table_found': False,
            'returned_date': returned_date,
            'date_match': returned_date == requested,
            'headers': [],
            'rows': 0,
            'prefix_hits': {p: 0 for p in PREFIXES},
        }
    headers = [x.get_text(' ', strip=True) for x in table.find_all('th')]
    trs = table.find_all('tr')[1:]
    texts = [tr.get_text(' ', strip=True).upper() for tr in trs]
    hits = {p: sum(1 for text in texts if p in text) for p in PREFIXES}
    return {
        'table_found': True,
        'returned_date': returned_date,
        'date_match': returned_date == requested,
        'headers': headers,
        'rows': len(trs),
        'prefix_hits': hits,
    }


def main() -> int:
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 GATE-BTC-H80-LegacySettlement-QA/1.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.5',
        'Origin': 'https://www2.bmf.com.br',
        'Content-Type': 'application/x-www-form-urlencoded',
    })
    rows = []
    for d in DATES:
        r, errors = fetch(s, d)
        if r is None:
            rows.append({'requested_date': d, 'status': 'DATA_GAP_TRANSIENT_DELIVERY', 'errors': errors})
            continue
        raw = r.content
        qa = inspect(raw, d)
        useful = (
            r.status_code == 200
            and qa['table_found']
            and qa['date_match']
            and qa['rows'] > 0
            and any(qa['prefix_hits'][p] > 0 for p in PREFIXES)
        )
        rows.append({
            'requested_date': d,
            'status': 'PASS' if useful else 'DATA_GAP_LEGACY_SETTLEMENT_SOURCE',
            'http_status': r.status_code,
            'final_url': str(r.url),
            'content_type': r.headers.get('content-type'),
            'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'errors': errors,
            **qa,
        })
    passed = sum(1 for row in rows if row.get('status') == 'PASS')
    all_prefixes = {p: sum(row.get('prefix_hits', {}).get(p, 0) for row in rows) for p in PREFIXES}
    payload = {
        'schema': 'qrds.b3.h80_h89.legacy_settlement_qa.v1',
        'source_provider': 'B3',
        'source_url': URL,
        'source_kind': 'observed_official_legacy_settlement_table',
        'community_code_used_as_data': False,
        'status': 'PASS_LEGACY_SETTLEMENT_SAMPLE' if passed == len(DATES) else 'DATA_GAP_LEGACY_SETTLEMENT_SOURCE',
        'sample_dates': DATES,
        'passed': passed,
        'total': len(DATES),
        'prefix_hits_total': all_prefixes,
        'rows': rows,
        'economics_run': False,
        'h1_economics_read': False,
        'survivor_partial_economics_read': False,
        'cutoff_exclusive': '2026-08-10',
        'research_only': True,
        'shadow_only': True,
        'not_approved': True,
        'orders': 0,
        'real_capital': 0,
        'engine_feed': False,
        'next_gate': 'FREEZE_PARSER_AND_FULL_CAUSAL_2020_2021_COVERAGE_PER_SUPPORTED_FAMILY' if passed == len(DATES) else 'KEEP_DEPENDENT_FAMILIES_DATA_GAP_AND_CONTINUE_SOURCE_DISCOVERY',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': payload['status'], 'passed': passed, 'total': len(DATES), 'prefix_hits_total': all_prefixes}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
