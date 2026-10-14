"""Sealed H31 source continuation; input-only warmup has zero observation credit."""
import argparse, hashlib, io, json, math, zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from gate_btc_b3_h1_daily import fetch_raw, recompute_m5
from gate_btc_b3_h1_parser import process_zip, time_ms, brnum, CHUNK

CONTRACT = Path(__file__).resolve().parent / 'gate_btc_factory/H31_SOURCE_CONTINUATION_20261015.v1.json'
CALENDAR_EXTENSION = CONTRACT.with_name('H31_SOURCE_CALENDAR_EXTENSION_20261021.v1.json')
CALENDAR_EXTENSION_SHA256 = 'd668fa662548719128772886530938e3cef2914075d0c21c82cd965ffa13e08c'
INPUT_QUALIFICATION = CONTRACT.with_name('H31_SOURCE_INPUT_QUALIFICATION_20261015.v1.json')
INPUT_QUALIFICATION_SHA256 = '096c2c764807506ff2cf74501823b16abba115730154595ba1b78bb65ca8f7a2'
CONTRACT_SHA256 = '613a94bc8ceeb9067add0a0b5ec324f1ce5d2f599d51a0316a42102021ae89e7'

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def load_contract():
    raw = CONTRACT.read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(raw).hexdigest() != CONTRACT_SHA256:
        raise RuntimeError('H31_CONTINUATION_SEAL_MISMATCH')
    c = json.loads(raw)
    if c['first_eligible_session'] != '2026-10-15' or len(c['warmup_dates']) != 20:
        raise RuntimeError('H31_CONTINUATION_BOUNDARY_MISMATCH')
    if datetime.fromisoformat(c['sealed_at_utc'].replace('Z','+00:00')) >= datetime.fromisoformat('2026-10-15T12:00:00+00:00'):
        raise RuntimeError('H31_CONTINUATION_NOT_PRESEALED')
    extension_raw=CALENDAR_EXTENSION.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(extension_raw).hexdigest()!=CALENDAR_EXTENSION_SHA256:
        raise RuntimeError('H31_CALENDAR_EXTENSION_SEAL_MISMATCH')
    extension=json.loads(extension_raw)
    if extension['base_continuation_sha256']!=CONTRACT_SHA256 or extension['freeze_rule_hash_sha256']!=c['freeze_rule_hash_sha256']:
        raise RuntimeError('H31_CALENDAR_EXTENSION_BINDING_MISMATCH')
    extra=extension['sessions']; dates=[r['date'] for r in extra]
    if len(extra)!=36 or dates!=sorted(set(dates)) or dates[0]!='2026-10-21' or dates[-1]!='2026-12-11' or any(d in dates for d in ['2026-11-02','2026-11-20']):
        raise RuntimeError('H31_CALENDAR_EXTENSION_DATES_INVALID')
    if datetime.fromisoformat(extension['sealed_at_utc'].replace('Z','+00:00'))>=datetime.fromisoformat(dates[0]+'T12:00:00+00:00'):
        raise RuntimeError('H31_CALENDAR_EXTENSION_NOT_PRESEALED')
    c['sessions']=c['sessions']+extra
    c['calendar_extension_sha256']=CALENDAR_EXTENSION_SHA256
    qraw=INPUT_QUALIFICATION.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(qraw).hexdigest()!=INPUT_QUALIFICATION_SHA256: raise RuntimeError('H31_INPUT_QUALIFICATION_SEAL_MISMATCH')
    q=json.loads(qraw)
    if q['base_continuation_sha256']!=CONTRACT_SHA256 or q['frozen_h31_m5_qa_unchanged'] is not True: raise RuntimeError('H31_INPUT_QUALIFICATION_BINDING_MISMATCH')
    if datetime.fromisoformat(q['sealed_at_utc'].replace('Z','+00:00'))>=datetime.fromisoformat('2026-10-15T12:00:00+00:00'): raise RuntimeError('H31_INPUT_QUALIFICATION_NOT_PRESEALED')
    c['warmup_dates']=sorted(q['supplemental_prior_candidate_dates']+c['warmup_dates'])
    c['input_qualification_sha256']=INPUT_QUALIFICATION_SHA256
    return c

def source_schedule(legacy):
    c = load_contract()
    return dict(legacy, **{r['date']: {'WIN':r['WIN'], 'WDO':r['WDO'], **({'WDO_candidates':r['WDO_candidates']} if 'WDO_candidates' in r else {})} for r in c['sessions']})

def choose_wdo(raw):
    """Rank only new WDO executions in 09:00-09:30; no WIN/outcome reads."""
    totals = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members = [x for x in z.infolist() if not x.is_dir()]
        if len(members)!=1 or '_NEGOCIOSAVISTA.TXT' not in members[0].filename.upper():
            raise RuntimeError('H31_WARMUP_ZIP_SCHEMA')
        with z.open(members[0]) as f:
            for ch in pd.read_csv(f, sep=';', encoding='iso-8859-1', dtype=str, chunksize=CHUNK,
                                  usecols=['CodigoInstrumento','AcaoAtualizacao','QuantidadeNegociada','HoraFechamento','TipoSessaoPregao']):
                sym = ch.CodigoInstrumento.str.strip().str.upper()
                act = pd.to_numeric(ch.AcaoAtualizacao, errors='coerce')
                sess = pd.to_numeric(ch.TipoSessaoPregao, errors='coerce')
                x = ch.loc[sym.str.fullmatch(r'WDO[FGHJKMNQUVXZ]\d{2}') & act.eq(0) & sess.eq(1)].copy()
                if x.empty: continue
                t = time_ms(x.HoraFechamento)
                x = x.loc[(t>=540*60000)&(t<570*60000)].copy()
                if x.empty: continue
                x['symbol'] = x.CodigoInstrumento.str.strip().str.upper()
                x['qty'] = brnum(x.QuantidadeNegociada)
                if not (x.qty > 0).all(): raise RuntimeError('H31_WARMUP_BAD_QUANTITY')
                for symbol, qty in x.groupby('symbol').qty.sum().items():
                    totals[symbol] = totals.get(symbol,0.0)+float(qty)
    if not totals: raise RuntimeError('H31_WARMUP_NO_WDO_EXECUTIONS')
    return sorted(totals, key=lambda s:(-totals[s],s))[0], totals

def validate_bars(day, symbol, m1, m5):
    bars=[]
    for df, n, freq in [(m1,30,'min'),(m5,6,'5min')]:
        if df.empty: raise RuntimeError('H31_WARMUP_EMPTY_BARS')
        ts=pd.to_datetime(df.timestamp).dt.tz_convert('America/Sao_Paulo')
        x=df.loc[(ts>=pd.Timestamp(day+' 09:00',tz='America/Sao_Paulo')) & (ts<pd.Timestamp(day+' 09:30',tz='America/Sao_Paulo'))].copy()
        x['timestamp']=ts.loc[x.index]
        x=x.sort_values('timestamp').reset_index(drop=True)
        expected=pd.date_range(day+' 09:00', periods=n, freq=freq,tz='America/Sao_Paulo')
        got=pd.DatetimeIndex(x.timestamp)
        if got.has_duplicates or len(got)==0 or len(got.difference(expected)) or (n==6 and not got.equals(expected)):
            raise RuntimeError('H31_WARMUP_LATTICE_MISMATCH '+str({'rows':len(x),'expected':n,'missing':[str(v) for v in expected.difference(got)],'extra':[str(v) for v in got.difference(expected)]}))
        if set(x.symbol)!={symbol} or set(x.root)!={'WDO'}: raise RuntimeError('H31_WARMUP_IDENTITY_MISMATCH')
        vals=x[['open','high','low','close','volume','trades']]
        if not all(math.isfinite(float(v)) for v in vals.to_numpy().flat): raise RuntimeError('H31_WARMUP_NONFINITE')
        if not ((x.low<=x.open)&(x.low<=x.close)&(x.high>=x.open)&(x.high>=x.close)&(x.low>0)&(x.volume>0)&(x.trades>0)).all(): raise RuntimeError('H31_WARMUP_BAD_OHLC')
        for field in ['open','high','low','close']:
            if not ((x[field]/.5-(x[field]/.5).round()).abs()<1e-7).all(): raise RuntimeError('H31_WARMUP_OFF_TICK')
        bars.append(x)
    rebuilt=recompute_m5(bars[0]).reset_index(drop=True)
    for field in ['open','high','low','close','volume','trades']:
        if not ((rebuilt[field].astype(float)-bars[1][field].astype(float)).abs()<=1e-6).all(): raise RuntimeError('H31_WARMUP_M1_M5_MISMATCH')
    return bars[1]

def validate_receipt(rec, day):
    payload=dict(rec); seal=payload.pop('receipt_sha256', None)
    if digest(payload)!=seal or rec.get('date')!=day or rec.get('contract_sha256')!=CONTRACT_SHA256:
        raise RuntimeError('H31_WARMUP_RECEIPT_SEAL_MISMATCH')
    if rec.get('structural_qa')!='PASS' or rec.get('prospective_scored') is not False or not math.isfinite(float(rec['ret30_bps'])):
        raise RuntimeError('H31_WARMUP_RECEIPT_INVALID')
    if rec.get('eligible_observation_increment')!=0 or len(rec.get('source_sha256',''))!=64:
        raise RuntimeError('H31_WARMUP_CREDIT_OR_SOURCE_MISMATCH')
    return rec

def prepare(day, ledger_dir):
    c=load_contract()
    allowed=c['warmup_dates']+[r['date'] for r in c['sessions']]
    if day not in allowed: raise RuntimeError('H31_WARMUP_DATE_UNBOUND')
    now=datetime.now(ZoneInfo('America/Sao_Paulo'))
    if day>now.date().isoformat() or (day==now.date().isoformat() and (now.hour,now.minute)<(18,30)):
        raise RuntimeError('H31_WARMUP_SESSION_NOT_CLOSED')
    p=Path(ledger_dir)/'source_continuation'/ 'warmup'/ (day+'.json')
    if p.exists(): return validate_receipt(json.loads(p.read_text()),day)
    raw, source=fetch_raw(day)
    if raw is None: raise RuntimeError('H31_WARMUP_SOURCE_NOT_READY '+json.dumps(source))
    symbol, volumes=choose_wdo(raw)
    fixed={r['date']:r['WDO'] for r in c['sessions']}
    candidates={r['date']:r.get('WDO_candidates') for r in c['sessions']}
    if candidates.get(day):
        if symbol not in candidates[day]: raise RuntimeError('H31_FUTURE_WDO_CANDIDATE_MISMATCH')
    elif day in fixed and symbol!=fixed[day]: raise RuntimeError('H31_FUTURE_WDO_BINDING_MISMATCH')
    m1,m5,stats,member=process_zip(raw,day,{'WIN':'__H31_NO_WIN_WARMUP__','WDO':symbol})
    first=validate_bars(day,symbol,m1,m5)
    rec={'schema':'qrds.h31.recent_official_warmup.v1','date':day,'contract_sha256':CONTRACT_SHA256,'input_qualification_sha256':INPUT_QUALIFICATION_SHA256,
         'source_sha256':source['sha256'],'source_url':source['url'],'source_bytes':source['bytes'],
         'source_member':member,'WDO':symbol,'selection_first30_new_execution_volume':volumes,
         'ret30_bps':(float(first.iloc[-1]['close'])/float(first.iloc[0]['open'])-1)*10000,
         'first30_m5':json.loads(first.to_json(orient='records',date_format='iso')),
         'engine_stats':stats,'structural_qa':'PASS','m1_to_m5_exact':True,
         'prospective_scored':False,'eligible_observation_increment':0,'h1_economics_read':False,
         'orders':0,'real_capital':0,'engine_feed':False}
    rec['receipt_sha256']=digest(rec)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n')
    return rec

def qualify(day, ledger_dir):
    """Quality-only exclusion mirrors frozen historical loader; never a scored event."""
    qpath=Path(ledger_dir)/'source_continuation'/'unqualified_warmup'/(day+'.json')
    if day<'2026-10-15' and qpath.exists():
        old=json.loads(qpath.read_text())
        if old.get('input_qualification_sha256')==INPUT_QUALIFICATION_SHA256:
            return None
    try:
        return prepare(day,ledger_dir)
    except RuntimeError as exc:
        if 'SESSION_NOT_CLOSED' in str(exc): return None
        rec={'date':day,'input_qualification_sha256':INPUT_QUALIFICATION_SHA256,'structural_qa':'FAIL_CLOSED','error':str(exc),'prospective_scored':False,'eligible_observation_increment':0,'canonical_counter_mutated':False,'h1_economics_read':False}
        qpath.parent.mkdir(parents=True,exist_ok=True);qpath.write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n')
        return None

def trailing(target, ledger_dir):
    c=load_contract()
    dates=sorted(d for d in c['warmup_dates']+[r['date'] for r in c['sessions']] if d<target)
    selected=[]
    for day in reversed(dates):
        rec=qualify(day,ledger_dir)
        if rec is not None:
            selected.append({'date':day,'ret30_bps':rec['ret30_bps'],'source':'RECENT_OFFICIAL_B3_INPUT_ONLY','receipt_sha256':rec['receipt_sha256']})
        if len(selected)==20: break
    if len(selected)!=20: raise RuntimeError('H31_RECENT_WARMUP_NEEDS_20_STRUCTURAL_PASS_INPUTS got='+str(len(selected)))
    return list(reversed(selected))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--date',required=True);ap.add_argument('--ledger-dir',required=True)
    a=ap.parse_args();r=prepare(a.date,a.ledger_dir)
    print(json.dumps({'date':r['date'],'status':r['structural_qa'],'WDO':r['WDO'],'receipt_sha256':r['receipt_sha256'],'eligible_observation_increment':0}))
