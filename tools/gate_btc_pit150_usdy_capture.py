"""Capture public Bybit USDY payloads natively; publish immutable daily source evidence."""
from __future__ import annotations
import argparse,hashlib,json,subprocess,tempfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tools.gate_btc_pit150_qualified_history import collect_history,BYBIT_CAPTURE_BRANCH,BYBIT_CAPTURE_REPOSITORY

class GitHubError(RuntimeError):pass

def github(gh,path,method="GET",payload=None):
    args=[gh,"api",path,"--method",method]
    with tempfile.TemporaryDirectory() as tmp:
        if payload is not None:
            p=Path(tmp)/"request.json";p.write_bytes(json.dumps(payload,ensure_ascii=False).encode())
            args += ["--input",str(p)]
        result=subprocess.run(args,check=False,capture_output=True,text=True,encoding="utf-8")
    if result.returncode:
        raise GitHubError(result.stderr.strip())
    return json.loads(result.stdout) if result.stdout.strip() else {}

def publish(gh,cutoff,files):
    api=f"repos/{BYBIT_CAPTURE_REPOSITORY}"
    try:
        current=github(gh,f"{api}/git/ref/heads/{BYBIT_CAPTURE_BRANCH}")
        parent=current["object"]["sha"]
        commit=github(gh,f"{api}/git/commits/{parent}")
        base_tree=commit["tree"]["sha"]
        exists=True
    except GitHubError as exc:
        if "404" not in str(exc):raise
        parent=github(gh,f"{api}/git/ref/heads/main")["object"]["sha"]
        base_tree=None;exists=False
    entries=[{"path":f"captures/{cutoff}/{name}","mode":"100644","type":"blob","content":raw.decode("utf-8")} for name,raw in files.items()]
    body={"tree":entries}
    if base_tree:body["base_tree"]=base_tree
    tree=github(gh,f"{api}/git/trees","POST",body)
    # GitHub supplies the committer and publication timestamp; no client backdating.
    commit=github(gh,f"{api}/git/commits","POST",{"message":f"Public USDY source capture {cutoff}; no orders","tree":tree["sha"],"parents":[parent]})
    if exists:
        github(gh,f"{api}/git/refs/heads/{BYBIT_CAPTURE_BRANCH}","PATCH",{"sha":commit["sha"],"force":False})
    else:
        github(gh,f"{api}/git/refs","POST",{"ref":f"refs/heads/{BYBIT_CAPTURE_BRANCH}","sha":commit["sha"]})
    return commit

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--gh",default="gh")
    parser.add_argument("--cutoff")
    args=parser.parse_args()
    now=datetime.now(timezone.utc)
    cutoff=args.cutoff or (now-timedelta(days=1)).date().isoformat()
    boundary=datetime.strptime(cutoff,"%Y-%m-%d").replace(tzinfo=timezone.utc)+timedelta(days=1)
    if boundary>now:raise ValueError("refuse unfinished source day")
    args.root.mkdir(parents=True,exist_ok=True)
    api=f"repos/{BYBIT_CAPTURE_REPOSITORY}"
    # A seal already published for the day is immutable; do not recollect/reprice it.
    try:
        old=github(args.gh,f"{api}/contents/captures/{cutoff}/seal.json?ref={BYBIT_CAPTURE_BRANCH}")
    except GitHubError as exc:
        if "404" not in str(exc):raise
    else:
        result={"status":"ALREADY_PUBLISHED_NO_RECOLLECTION","cutoff":cutoff,"seal_blob_sha":old["sha"],"orders":0,"capital":0}
        (args.root/"LAST_RUN.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
        print(json.dumps(result));return
    import requests
    raw_root=args.root/"native"/cutoff
    rows,evidence=collect_history(requests.Session(),"USDY","ondo-us-dollar-yield",cutoff,raw_root,now=now)
    if evidence.get("delivery"):
        raise ValueError("native producer must not republish a relayed capture")
    raw_dir=raw_root/"USDY"
    files={name:(raw_dir/name).read_bytes() for name in ["identity.json","candles.json"]}
    seal={"schema":"gate_btc.bybit_public_capture.v1","symbol":"USDY","coin_id":"ondo-us-dollar-yield",
          "pair":"USDYUSDT","cutoff":cutoff,"public_api_host":evidence["public_api_host"],
          "fetched_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
          "sha256":{name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()},
          "closed_rows":len(rows),"first_close":rows[0]["date"],"last_close":rows[-1]["date"],
          "runtime_admission":False,"historical_scientific_credit":0,"orders":0,"real_capital":0}
    files["seal.json"]=(json.dumps(seal,indent=2)+"\n").encode()
    (raw_dir/"seal.json").write_bytes(files["seal.json"])
    commit=publish(args.gh,cutoff,files)
    result={"status":"PUBLIC_SOURCE_CAPTURE_PUBLISHED","cutoff":cutoff,"commit_sha":commit["sha"],
            "published_at_utc":commit["committer"]["date"],"closed_rows":len(rows),
            "raw_sha256":seal["sha256"],"runtime_admission":False,"orders":0,"real_capital":0}
    (args.root/"LAST_RUN.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
    print(json.dumps(result))
if __name__=="__main__":main()
