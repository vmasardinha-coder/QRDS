"""Prospective source delivery only. No decisions, prices, outcomes or counters."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import uuid

from gate_btc_factory import crypto_745_basis_forward_capture as basis
from gate_btc_factory import xagent_spot_flow_signal_producer as spot
from gate_btc_factory import xagent_term_carry_signal_producer as carry
from gate_btc_factory import xagent_breadth_signal_producer as breadth

BASIS_ROOT='runtime/factory_sources/crypto_challenger_745/forward/basis_funding'
PRODUCER_ROOT='runtime/factory_autonomy/xagent_signal_producers'
SCOPES=(BASIS_ROOT+'/',PRODUCER_ROOT+'/')
MAX_INPUT_AGE_SECONDS=90*60
SAFETY={'orders':0,'real_capital':0,'economics_read':False,'decisions_created':0,
        'counter_reset':False,'historical_backfill_credit':0,'scientific_credit':0}

def encoded(d):return (json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(repo,*args,check=True):
 p=subprocess.run(['git','-c','core.autocrlf=false','-C',str(repo),*args],capture_output=True,text=True)
 if check and p.returncode:raise RuntimeError('LOCAL_SOURCE_GIT_FAILED:'+args[0])
 return p
def sealed(d,key='record_sha256'):
 raw={k:v for k,v in d.items() if k!=key}
 if d.get(key)!=sha(json.dumps(raw,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()):
  raise ValueError('SOURCE_PAYLOAD_SEAL_MISMATCH')
 return d
def immutable(path,d):
 raw=encoded(d)
 if path.exists():
  if json.loads(path.read_bytes())!=d:raise ValueError('APPEND_ONLY_SOURCE_CONFLICT')
 else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
def write(path,d):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encoded(d))

def apply_basis(root,packet,packet_id):
 if packet.get('attempted_window') is not True:return []
 sealed(packet,'attempt_sha256')
 if packet.get('channel_id')!=basis.CHANNEL_ID or packet.get('economics_read') is not False:
  raise ValueError('BASIS_SOURCE_AUTHORITY_CHANGED')
 folder=root/BASIS_ROOT
 existing=json.loads((folder/'MANIFEST.json').read_bytes())
 old_ids={x['observation_id'] for x in existing['partitions']}
 observation=packet['observation']
 # A second collector never awards a second observation or replaces an old seal.
 if observation['observation_id'] in old_ids:return []
 target=folder/'partitions'/('LOCAL_'+packet_id+'.json')
 immutable(target,packet)
 updated=basis.build_manifest(folder/'partitions')
 if updated['eligible_unique_observation_count']<existing['eligible_unique_observation_count']:
  raise ValueError('BASIS_EXISTING_OBSERVATIONS_LOST')
 write(folder/'MANIFEST.json',updated)
 return [target.relative_to(root).as_posix(),BASIS_ROOT+'/MANIFEST.json']

def check_producer(record,now_ms):
 sealed(record)
 if record.get('producer_id') not in ('S-XSPOT-FLOW-01','S-XTERM-CARRY-01','S-XBREADTH-01'):
  raise ValueError('UNDECLARED_PRODUCER')
 age=(now_ms-record['available_after_ms'])/1000
 if age<0 or age>MAX_INPUT_AGE_SECONDS:raise ValueError('SOURCE_STALE_OR_FUTURE_NO_PUBLICATION')
 if (record.get('economic_outcomes_read') is not False or record.get('engine_feed') is not False
     or record.get('orders')!=0 or record.get('real_capital')!=0):raise ValueError('PRODUCER_SAFETY_CHANGED')
 if record.get('signal') is not None and not -1<=record['signal']<=1:raise ValueError('SIGNAL_RANGE_CHANGED')
 return record

def apply_producers(root,packet,now_ms):
 genesis=packet['genesis'];breadth.validate_genesis(genesis)
 gp=root/PRODUCER_ROOT/'S-XBREADTH-01/GENESIS.json'
 if not gp.exists() or json.loads(gp.read_bytes())['genesis_sha256']!=genesis['genesis_sha256']:
  raise ValueError('EXISTING_IMMUTABLE_GENESIS_REQUIRED')
 # Validate every input before any mutation. Unavailable signals stay unavailable.
 records=[check_producer(d,now_ms) for d in packet['records']]
 if len(records)!=3 or len({d['producer_id'] for d in records})!=3:raise ValueError('THREE_DISTINCT_PRODUCERS_REQUIRED')
 paths=[]
 for d in records:
  pid=d['producer_id'];folder=root/PRODUCER_ROOT/pid
  key=d['close_time_ms'] if pid=='S-XSPOT-FLOW-01' else d['capture_time_ms']
  target=folder/(str(key)+'.json');immutable(target,d)
  paths.append(target.relative_to(root).as_posix())
  latest=folder/'LATEST.json'
  if latest.exists() and json.loads(latest.read_bytes())['available_after_ms']>d['available_after_ms']:continue
  write(latest,d);paths.append(latest.relative_to(root).as_posix())
  # Source-delivery receipt, explicitly not an eligibility or decision grant.
  status={'schema':'qrds.factory.local_producer_delivery.v1','producer_id':pid,
          'record_sha256':d['record_sha256'],'available_after_ms':d['available_after_ms'],
          'source_available':d['signal'] is not None,'decision_eligibility_requires_existing_contract':True,
          'input_max_age_seconds':MAX_INPUT_AGE_SECONDS,'safety':SAFETY}
  write(folder/'LOCAL_DELIVERY_STATUS.json',status)
  paths.append((folder/'LOCAL_DELIVERY_STATUS.json').relative_to(root).as_posix())
 return paths

def publish(repo,apply):
 """Rebuild only our disposable tree after a concurrent runtime push; reuse captures."""
 for attempt in range(4):
  git(repo,'fetch','origin','gate-btc-runtime')
  head=git(repo,'rev-parse','origin/gate-btc-runtime').stdout.strip()
  with tempfile.TemporaryDirectory(prefix='qrds-source-publication-') as temp:
   wt=Path(temp)/'worktree';added=False
   try:
    git(repo,'worktree','add','--no-checkout','--detach',str(wt),head);added=True
    git(wt,'sparse-checkout','set','--cone',BASIS_ROOT,PRODUCER_ROOT)
    git(wt,'checkout','HEAD')
    paths=apply(wt)
    if any(not p.startswith(SCOPES) for p in paths):raise ValueError('LOCAL_SOURCE_SCOPE_VIOLATION')
    if paths:git(wt,'add','--',*paths)
    staged=git(wt,'diff','--cached','--name-only').stdout.splitlines()
    if any(not p.startswith(SCOPES) for p in staged):raise ValueError('LOCAL_SOURCE_STAGED_SCOPE_VIOLATION')
    if not staged:return {'changed':False,'sha':head,'paths':[]}
    git(wt,'-c','user.name=gate-btc-research-bot','-c','user.email=gate-btc-research-bot@users.noreply.github.com',
        'commit','-m','Append prospective local factory source delivery; zero economic credit')
    new=git(wt,'rev-parse','HEAD').stdout.strip()
    if git(wt,'push','origin','HEAD:gate-btc-runtime',check=False).returncode==0:
     return {'changed':True,'sha':new,'paths':staged}
   finally:
    # This uniquely-created disposable worktree is owned by this invocation.
    if added:git(repo,'worktree','remove','--force',str(wt))
 raise RuntimeError('LOCAL_SOURCE_PUBLICATION_RETRY_EXHAUSTED_CAPTURE_RETAINED')

def capture_producers(runtime):
 gp=runtime/PRODUCER_ROOT/'S-XBREADTH-01/GENESIS.json'
 genesis=breadth.validate_genesis(json.loads(gp.read_bytes()))
 with ThreadPoolExecutor(max_workers=3) as pool:
  a=pool.submit(spot.collect);b=pool.submit(carry.collect);c=pool.submit(breadth.collect,genesis=genesis)
  br,same=c.result();records=[a.result(),b.result(),br]
 if same['genesis_sha256']!=genesis['genesis_sha256']:raise ValueError('GENESIS_CHANGED')
 now_ms=int(datetime.now(timezone.utc).timestamp()*1000)
 for d in records:check_producer(d,now_ms)
 return {'genesis':genesis,'records':records}

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['basis','xagent-producers'],required=True)
 p.add_argument('--runtime-repo',type=Path,required=True);p.add_argument('--spool',type=Path,required=True)
 p.add_argument('--validate-only',action='store_true');a=p.parse_args()
 basis.qualified_source_cost(a.runtime_repo/'runtime/factory_sources/crypto_challenger_745/SOURCE_COST.json')
 if a.validate_only:
  gp=a.runtime_repo/PRODUCER_ROOT/'S-XBREADTH-01/GENESIS.json'
  breadth.validate_genesis(json.loads(gp.read_bytes()))
  print(json.dumps({'status':'CONFIG_VALID','capture_executed':False,'mode':a.mode,'safety':SAFETY}));return
 started=datetime.now(timezone.utc).isoformat();packet_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:12]
 if a.mode=='basis':
  packet=basis.capture_attempt(a.runtime_repo/'runtime/factory_sources/crypto_challenger_745/SOURCE_COST.json',max_wait_seconds=2400)
 else:packet=capture_producers(a.runtime_repo)
 path=a.spool/(packet_id+'.json');write(path,packet)
 if a.mode=='basis' and packet.get('attempted_window') is not True:
  result={'changed':False,'status':packet['status'],'runtime_written':False}
 else:
  apply=(lambda root:apply_basis(root,packet,packet_id)) if a.mode=='basis' else (lambda root:apply_producers(root,packet,int(datetime.now(timezone.utc).timestamp()*1000)))
  result=publish(a.runtime_repo,apply)
 receipt={'mode':a.mode,'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
          'packet_path':str(path),'packet_sha256':sha(path.read_bytes()),'publication':result,'safety':SAFETY}
 write(a.spool/(packet_id+'.receipt.json'),receipt);print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__':main()
