"""Offline replay of the frozen HASH proof packet; no admission or network calls."""
import argparse,hashlib,json,sys,tempfile,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from tools import gate_btc_hash_settlement_history as h
p=argparse.ArgumentParser();p.add_argument("--raw",type=Path,default=Path(__file__).with_name("RAW_NATIVE.zip"))
p.add_argument("--cutoff",default="2026-10-15");p.add_argument("--delta",type=Path);args=p.parse_args()
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory)
 from contextlib import ExitStack
 with ExitStack() as stack:
  z=stack.enter_context(zipfile.ZipFile(args.raw))
  manifest=json.loads(z.read("RAW_MANIFEST.json"));expected={x["file"] for x in manifest}
  if set(z.namelist())!=expected|{"RAW_MANIFEST.json"}:raise ValueError("ARCHIVE_MANIFEST_SET_MISMATCH")
  delta=None;changed=set()
  if args.delta:
   delta=stack.enter_context(zipfile.ZipFile(args.delta));info=json.loads(delta.read("DELTA.json"))
   if hashlib.sha256(args.raw.read_bytes()).hexdigest()!=info["base_archive_sha256"]:raise ValueError("WRONG_DELTA_BASE")
   changed=set(info["added_or_replaced_entries"])
   if set(delta.namelist())!=changed|{"DELTA.json","RAW_MANIFEST.json"}:raise ValueError("UNDECLARED_DELTA_ENTRIES")
   manifest=json.loads(delta.read("RAW_MANIFEST.json"))
  for x in manifest:
   path=Path(x["file"])
   if path.is_absolute() or ".." in path.parts or path.parts[0] not in ("HASH","HASH_FIGURE"):raise ValueError("INVALID_PACKET_PATH")
   raw=(delta if x["file"] in changed else z).read(x["file"])
   if hashlib.sha256(raw).hexdigest()!=x["sha256"]:raise ValueError("CORRUPT_RAW_PACKET")
   target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 items=[];total=None
 for f in sorted((root/"HASH").glob("page_*.json")):
  payload=json.loads(f.read_bytes())
  if payload.get("error") or payload.get("jsonrpc")!="2.0":raise ValueError("INVALID_SEARCH_RESPONSE")
  v=payload["result"];count=int(v["total_count"])
  if total is None:total=count
  if count!=total:raise ValueError("UNSTABLE_SEARCH_COUNT")
  items+=v["txs"]
 if len(items)!=total:raise ValueError("INCOMPLETE_SEARCH")
 keys=[(int(x["height"]),int(x["index"])) for x in items]
 if keys!=sorted(set(keys)):raise ValueError("NON_UNIQUE_OR_UNORDERED_TRANSACTIONS")
 blocks={}
 for f in sorted((root/"HASH").glob("blocks_*.json")):
  for entry in json.loads(f.read_bytes()):
   b=entry["result"];height=int(b["block"]["header"]["height"])
   if height in blocks and blocks[height]!=b:raise ValueError("CONFLICTING_CANONICAL_BLOCK")
   blocks[height]=b
 events=[e for x in items for e in h.verify_tx(x,blocks[int(x["height"])])]
 rows,checked=h.reconcile_tape(root/"HASH_FIGURE",args.cutoff,events)
 digest=hashlib.sha256((json.dumps(rows,indent=2)+"\n").encode()).hexdigest()
 print(json.dumps({"status":"PASS_OFFLINE_NATIVE_TAPE_REPLAY_NOT_ADMISSION","rows_sha256":digest,
    "verified_transactions":len(items),"canonical_blocks":len(blocks),**checked,"orders":0},indent=2))
