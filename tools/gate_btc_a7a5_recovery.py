"""Bounded source recovery evidence only; never changes PIT counts or admission."""
import argparse,hashlib,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
import gate_btc_a7a5_swap_history as source

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    import requests
    now=datetime.now(timezone.utc);cutoff=(now.date()-timedelta(days=1)).isoformat()
    args.out.mkdir(parents=True,exist_ok=True)
    result={'schema':'qrds.pit150.a7a5_recovery.v1','cutoff':cutoff,'observed_at_utc':now.isoformat(),
            'collector_sha256':hashlib.sha256(Path(source.__file__).read_bytes()).hexdigest(),
            'physical_seed_sha256':source.SEED_SHA256,'runtime_admission':False,'prospective_credit':0,
            'historical_credit':0,'pit_counter_updated':False,'orders':0,'real_capital':0}
    try:
        with requests.Session() as session:
            session.headers['User-Agent']='QRDS-Research/1.0'
            rows,evidence=source.collect(session,cutoff,args.out,now)
        raw=(json.dumps(rows,sort_keys=True,indent=2)+'\n').encode();(args.out/'ROWS.json').write_bytes(raw)
        result.update(status='PASS_EXACT_200_PHYSICAL_DAYS',rows=len(rows),first=rows[0]['date'],last=rows[-1]['date'],
                      rows_sha256=hashlib.sha256(raw).hexdigest(),canonical_closes=evidence['canonical_closing_blocks_and_logs_verified'],
                      physical_seed_reused=evidence['pinned_physical_seed_reused'],
                      qualification_sha256=hashlib.sha256((args.out/'A7A5/qualification.json').read_bytes()).hexdigest())
    except Exception as error:
        result.update(status='BLOCKED_SOURCE',error=type(error).__name__+':'+str(error))
    result['completed_at_utc']=datetime.now(timezone.utc).isoformat()
    (args.out/'RESULT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
