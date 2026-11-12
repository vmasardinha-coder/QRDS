"""Read canonical Git objects without changing a dirty or detached worktree."""
import hashlib,json,os,subprocess
from datetime import datetime,timezone
from pathlib import Path
try:
    from .gate_btc_qmaster_publication_guard import assess
except ImportError:
    from gate_btc_qmaster_publication_guard import assess


def git(repo,*args):
    try:
        p=subprocess.run(['git','-C',str(repo),*args],capture_output=True,timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('QMASTER_CANONICAL_GIT_TIMEOUT') from exc
    if p.returncode:raise RuntimeError('QMASTER_CANONICAL_GIT_READ_FAILED:'+args[0])
    return p.stdout


def refresh(repo,cache,reader=git):
    repo=Path(repo);cache=Path(cache)
    reader(repo,'fetch','--no-tags','origin','gate-btc-runtime')
    ref=reader(repo,'rev-parse','FETCH_HEAD').decode().strip()
    meta_raw=reader(repo,'show',ref+':runtime/GATE_BTC_QMASTER_LATEST.txt')
    csv_raw=reader(repo,'show',ref+':runtime/GATE_BTC_QMASTER_LATEST.csv')
    meta=json.loads(meta_raw);digest=hashlib.sha256(csv_raw).hexdigest()
    if digest!=meta['csv_sha256']:raise ValueError('CANONICAL_CSV_HASH_MISMATCH')
    if meta.get('csv_path')!='GATE_BTC_QMASTER_LATEST.csv':raise ValueError('UNEXPECTED_CSV_NAME')
    current=cache/'CURRENT.json';prior=None
    if current.exists():
        old=json.loads(current.read_bytes());prior=json.loads((cache/old['snapshot']/'GATE_BTC_QMASTER_LATEST.txt').read_bytes())
    if assess(meta,prior)=='REFUSED_SOURCE_REGRESSION':raise ValueError('CANONICAL_SOURCE_REGRESSION')
    snapshot=hashlib.sha256(meta_raw+digest.encode()).hexdigest();dest=cache/snapshot;dest.mkdir(parents=True,exist_ok=True)
    for name,raw in [('GATE_BTC_QMASTER_LATEST.txt',meta_raw),('GATE_BTC_QMASTER_LATEST.csv',csv_raw)]:
        p=dest/name
        if p.exists():
            if p.read_bytes()!=raw:raise ValueError('CACHE_BYTES_CHANGED')
        else:p.write_bytes(raw)
    proof=dict(source_ref=ref,snapshot=snapshot,csv_sha256=digest,data_as_of=meta['data_as_of'],checked_at_utc=datetime.now(timezone.utc).isoformat(),worktree_changed=False)
    tmp=current.with_suffix('.partial');tmp.write_text(json.dumps(proof,indent=2),encoding='utf-8');os.replace(tmp,current)
    return dest/'GATE_BTC_QMASTER_LATEST.txt',proof
