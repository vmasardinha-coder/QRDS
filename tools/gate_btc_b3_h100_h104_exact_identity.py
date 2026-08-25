#!/usr/bin/env python3
from __future__ import annotations

import hashlib, json
from pathlib import Path

import gate_btc_b3_h100_h109_cftc_probe as base

OUT=Path('artifacts/b3_h100_h109/B3_H100_H104_EXACT_IDENTITY.json')
YEARS=range(2020,2027)
TARGETS={
  'H100': {'kind':'financial','code':'13874A','name_tokens':['S&P','500']},
  'H101': {'kind':'financial','code':'098662','name_tokens':['DOLLAR','INDEX']},
  'H102': {'kind':'financial','code':'043602','name_tokens':['10','TREASURY']},
  'H103': {'kind':'disaggregated','code':'067651','name_tokens':['CRUDE','LIGHT']},
  'H104': {'kind':'disaggregated','code':'085692','name_tokens':['COPPER']},
}


def norm(s): return ' '.join(str(s or '').upper().replace('.',' ').replace(',',' ').split())

def get(row,key): return str(row.get(key,'')).strip()

def oi(row):
    try: return float(get(row,'Open_Interest_All').replace(',',''))
    except Exception: return -1.0

def pos_ok(kind,row):
    if kind=='financial':
        ks=('Lev_Money_Positions_Long_All','Lev_Money_Positions_Short_All')
    else:
        ks=('M_Money_Positions_Long_All','M_Money_Positions_Short_All')
    try:
        return all(get(row,k)!='' and float(get(row,k).replace(',',''))>=0 for k in ks)
    except Exception:
        return False


def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    rows_by_kind={'financial':[],'disaggregated':[]}; archives={}; errors=[]
    for kind,templ in base.SOURCES.items():
        for year in YEARS:
            url=base.BASE+templ.format(year=year)
            try:
                raw=base.fetch(url); member,data,fields,rows=base.parse_archive(raw)
                archives[f'{kind}_{year}']={'url':url,'raw_sha256':hashlib.sha256(raw).hexdigest(),'member':member,'member_sha256':hashlib.sha256(data).hexdigest(),'rows':len(rows)}
                for r in rows:
                    r['_year']=year; rows_by_kind[kind].append(r)
            except Exception as exc:
                errors.append({'kind':kind,'year':year,'error':str(exc)})

    fam={}
    for name,t in TARGETS.items():
        matches=[r for r in rows_by_kind[t['kind']] if get(r,'CFTC_Contract_Market_Code')==t['code']]
        years=sorted({r['_year'] for r in matches})
        names=sorted({get(r,'Market_and_Exchange_Names') for r in matches})
        name_ok=bool(names) and all(all(tok in norm(n) for tok in t['name_tokens']) for n in names)
        dates=[base.date_value(r) for r in matches if base.date_value(r)]
        unique_dates=(len(dates)==len(set(dates)))
        oi_ok=all(oi(r)>0 for r in matches)
        positions_ok=all(pos_ok(t['kind'],r) for r in matches)
        required=set(range(2020,2025))
        coverage_ok=required.issubset(set(years))
        status='SOURCE_IDENTITY_READY_EXACT_CODE' if (matches and name_ok and unique_dates and oi_ok and positions_ok and coverage_ok) else 'DATA_GAP_EXACT_CODE_OR_COVERAGE'
        fam[name]={
          'status':status,'kind':t['kind'],'contract_market_code':t['code'],'years':years,
          'market_names':names,'matched_rows':len(matches),'name_ok':name_ok,'unique_dates':unique_dates,
          'open_interest_positive':oi_ok,'position_fields_valid':positions_ok,'required_2020_2024_coverage':coverage_ok
        }
    report={
      'schema':'gate_btc.b3.h100_h104.exact_identity.v1','cutoff_exclusive':'2026-08-10',
      'source_provider':'U.S. Commodity Futures Trading Commission','families':fam,'archives':archives,'source_errors':errors,
      'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,
      'orders_generated':0,'real_capital_used':0,'engine_feed':False,'not_approved':True,
    }
    report['status']='PASS_ALL_EXACT_IDENTITIES_READY' if all(v['status'].startswith('SOURCE_IDENTITY_READY') for v in fam.values()) else 'PARTIAL_DATA_GAP_EXACT_IDENTITY'
    OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(report['status']); print({k:v['status'] for k,v in fam.items()})

if __name__=='__main__': main()
