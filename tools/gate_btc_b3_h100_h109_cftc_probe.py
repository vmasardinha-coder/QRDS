#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, io, json, re, time, zipfile
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

OUT=Path('artifacts/b3_h100_h109/B3_H100_H109_CFTC_SOURCE_QA.json')
YEARS=range(2020, 2027)
BASE='https://www.cftc.gov/files/dea/history/'
SOURCES={
  'financial': 'fut_fin_txt_{year}.zip',
  'disaggregated': 'fut_disagg_txt_{year}.zip',
}
TARGETS={
  'H100': ('financial', [r'E[- ]?MINI.*S&P', r'S&P 500']),
  'H101': ('financial', [r'U\.?S\.? DOLLAR INDEX', r'DOLLAR INDEX']),
  'H102': ('financial', [r'10[- ]?YEAR.*TREASURY', r'10 YEAR.*TREASURY']),
  'H103': ('disaggregated', [r'CRUDE OIL.*LIGHT', r'WTI']),
  'H104': ('disaggregated', [r'COPPER']),
}

def fetch(url: str) -> bytes:
    err=None
    for attempt in range(3):
        try:
            req=Request(url, headers={'User-Agent':'QRDS-research-source-QA/1.0'})
            with urlopen(req, timeout=45) as r:
                body=r.read()
            if len(body)<100:
                raise RuntimeError('response too small')
            return body
        except Exception as exc:
            err=exc
            time.sleep(2*(attempt+1))
    raise RuntimeError(f'fetch failed: {url}: {err}')

def parse_archive(raw: bytes):
    z=zipfile.ZipFile(io.BytesIO(raw))
    members=[n for n in z.namelist() if not n.endswith('/')]
    if not members:
        raise RuntimeError('empty zip')
    member=members[0]
    data=z.read(member)
    text=data.decode('latin-1')
    reader=csv.DictReader(io.StringIO(text))
    rows=list(reader)
    return member, data, reader.fieldnames or [], rows

def market_name(row: dict) -> str:
    for k in row:
        if 'Market_and_Exchange' in k or 'Market and Exchange' in k or k.strip().startswith('Market_and_Exchange'):
            return str(row.get(k,'')).strip()
    if row:
        return str(next(iter(row.values()))).strip()
    return ''

def date_value(row: dict) -> str:
    for key in ('Report_Date_as_MM_DD_YYYY','As_of_Date_In_Form_YYMMDD','Report Date as YYYY-MM-DD'):
        if key in row and row[key]: return str(row[key]).strip()
    for k,v in row.items():
        if 'Report_Date' in k or 'As_of_Date' in k:
            if v: return str(v).strip()
    return ''

def has_oi(fields):
    return any('Open_Interest_All' in x or 'Open Interest' in x for x in fields)

def has_position_fields(kind, fields):
    joined=' '.join(fields)
    if kind=='financial':
        return ('Lev_Money_Positions_Long_All' in joined and 'Lev_Money_Positions_Short_All' in joined)
    return (('M_Money_Positions_Long_All' in joined and 'M_Money_Positions_Short_All' in joined)
            or ('NonComm_Positions_Long_All' in joined and 'NonComm_Positions_Short_All' in joined))

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    archives={}
    rows_by_kind=defaultdict(list)
    source_errors=[]
    for kind,templ in SOURCES.items():
        for year in YEARS:
            url=BASE+templ.format(year=year)
            try:
                raw=fetch(url)
                member,data,fields,rows=parse_archive(raw)
                archives[f'{kind}_{year}']={
                    'url':url,'raw_sha256':hashlib.sha256(raw).hexdigest(),
                    'member':member,'member_sha256':hashlib.sha256(data).hexdigest(),
                    'rows':len(rows),'schema':fields,
                    'has_open_interest':has_oi(fields),
                    'has_position_fields':has_position_fields(kind,fields),
                }
                for row in rows:
                    row['_year']=year; rows_by_kind[kind].append(row)
            except Exception as exc:
                source_errors.append({'kind':kind,'year':year,'url':url,'error':str(exc)})

    families={}
    identities={}
    for fam,(kind,patterns) in TARGETS.items():
        matches=[]
        for row in rows_by_kind[kind]:
            name=market_name(row)
            if any(re.search(p,name,re.I) for p in patterns):
                matches.append((row['_year'],name,date_value(row)))
        years=sorted({x[0] for x in matches})
        names=sorted({x[1] for x in matches})
        required_years=set(range(2020,2025))
        archive_schema_ok=all(
            archives.get(f'{kind}_{y}',{}).get('has_open_interest') and
            archives.get(f'{kind}_{y}',{}).get('has_position_fields')
            for y in required_years
        )
        identity_ok=bool(matches) and required_years.issubset(set(years))
        status='SOURCE_IDENTITY_READY_PUBLICATION_LAG_PENDING' if identity_ok and archive_schema_ok else 'DATA_GAP_CFTC_IDENTITY_OR_COVERAGE'
        families[fam]={'status':status,'kind':kind,'years':years,'market_names':names[:30],'matched_rows':len(matches)}
        identities[fam]=names

    # Composite families cannot proceed until their primitive dependencies and a publication-availability contract pass.
    primitive_ready=all(families[x]['status'].startswith('SOURCE_IDENTITY_READY') for x in ('H100','H101','H102','H103','H104'))
    for fam in ('H105','H106','H107','H108','H109'):
        families[fam]={'status':'DEPENDENCY_SOURCE_READY_PUBLICATION_LAG_PENDING' if primitive_ready else 'DATA_GAP_DEPENDENCY'}

    report={
      'schema':'gate_btc.b3.h100_h109.cftc_source_qa.v1',
      'generation':'H100_H109_V1',
      'source_provider':'U.S. Commodity Futures Trading Commission',
      'source_surface':'Historical Compressed COT yearly futures-only archives',
      'cutoff_exclusive':'2026-08-10',
      'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,
      'orders_generated':0,'real_capital_used':0,'engine_feed':False,'not_approved':True,
      'archives':archives,'source_errors':source_errors,'families':families,
      'publication_lag_gate':{
        'status':'PENDING_FAIL_CLOSED',
        'reason':'Historical compressed rows expose report/as-of date but this probe does not yet prove exact historical public-release timestamp. No economics may run until a conservative auditable availability rule is frozen and delayed-release anomalies are handled.'
      }
    }
    report['status']='SOURCE_QA_PARTIAL_READY_PUBLICATION_LAG_PENDING' if primitive_ready else 'SOURCE_QA_DATA_GAPS'
    OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(report['status'])
    print({k:v['status'] for k,v in families.items()})

if __name__=='__main__': main()
