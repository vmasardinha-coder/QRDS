"""Deliver previously sealed exact-day Delta sources through the unchanged monitor."""
import argparse,json,shutil,tempfile
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from tools import gate_btc_delta_paper_monitor as monitor


def recover(contract,archive,runtime,target):
    contract=Path(contract);archive=Path(archive);runtime=Path(runtime)
    old=json.loads((runtime/'STATUS.json').read_text(encoding='utf-8-sig'))
    start=date.fromisoformat(old['data_as_of'])+timedelta(days=1);end=date.fromisoformat(target)
    plan=[];day=start
    # Validate the full delivery batch before modifying even a staged ledger.
    while day<=end:
        name=day.isoformat();rp=archive/(name+'.json');zp=archive/(name+'.zip')
        if not rp.is_file() or not zp.is_file():raise ValueError('EXACT_SEALED_SOURCE_MISSING:'+name)
        receipt=json.loads(rp.read_text(encoding='utf-8-sig'))
        if receipt['date']!=name or receipt['source_manifest_data_as_of']!=name or receipt['canonical_contract_sha256']!=monitor.h(contract.read_bytes()):raise ValueError('SOURCE_CONTRACT_OR_DATE_MISMATCH')
        flags={'source_only':True,'paper_nav_appended':False,'backfill_performed':False,'scientific_credit':0,'orders_generated':0,'real_capital_used':0,'engine_feed':False}
        if any(receipt.get(k)!=v for k,v in flags.items()):raise ValueError('SOURCE_RECEIPT_AUTHORITY_CHANGED')
        if monitor.h(zp.read_bytes())!=receipt['source_zip_sha256']:raise ValueError('SEALED_SOURCE_HASH_MISMATCH')
        source=monitor.load(contract,zp)
        captured=datetime.fromisoformat(source['manifest']['run_utc'].replace('Z','+00:00'))
        if source['manifest']['data_as_of']!=name or captured.date()!=day+timedelta(days=1):raise ValueError('SOURCE_NOT_CAPTURED_ON_ORIGINAL_DAILY_RUN')
        plan.append((name,zp,receipt));day+=timedelta(days=1)
    if not plan:return {'status':'UP_TO_DATE','data_as_of':old['data_as_of'],'observed_days':old['observed_days']}
    originals={p.name:monitor.read_csv(p) for p in runtime.glob('*.csv')}
    with tempfile.TemporaryDirectory(prefix='delta-sealed-delivery-') as td:
        staged=Path(td)/'monitor';shutil.copytree(runtime,staged)
        for name,zp,receipt in plan:
            monitor.process(contract,zp,staged,str(receipt['source_run_id']))
        for name,rows in originals.items():
            if monitor.read_csv(staged/name)[:len(rows)]!=rows:raise ValueError('ORIGINAL_LEDGER_PREFIX_CHANGED:'+name)
        new=json.loads((staged/'STATUS.json').read_text())
        if new['data_as_of']!=target or new['observed_days']!=old['observed_days']+len(plan):raise ValueError('DELIVERY_COUNTER_MISMATCH')
        result=dict(status='EXACT_SEALED_DELIVERY_RECOVERED',prior_data_as_of=old['data_as_of'],data_as_of=target,prior_observed_days=old['observed_days'],observed_days=new['observed_days'],original_ledger_prefix_preserved=True,source_captured_today_claim=False,source_returns_reconstructed=False,counter_reset=False,methodology_changed=False,orders_generated=0,real_capital_used=0,recovered=[dict(date=name,source_run_id=receipt['source_run_id'],source_zip_sha256=receipt['source_zip_sha256']) for name,_,receipt in plan])
        # The original engine is unchanged. Commit its completed batch only after all checks.
        files=sorted([p for p in staged.iterdir() if p.is_file()],key=lambda p:p.name=='STATUS.json')
        for p in files:
            if not (runtime/p.name).exists() or (runtime/p.name).read_bytes()!=p.read_bytes():shutil.copy2(p,runtime/p.name)
    (runtime/'DELIVERY_RECOVERY_LATEST.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--contract',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--target',required=True);a=p.parse_args()
    print(json.dumps(recover(a.contract,a.archive,a.runtime,a.target),indent=2))
