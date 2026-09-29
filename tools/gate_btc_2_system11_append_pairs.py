#!/usr/bin/env python3
import argparse,json
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument("--source",type=Path,required=True);p.add_argument("--ledger",type=Path,required=True);a=p.parse_args()
 old=[json.loads(x) for x in a.ledger.read_text().splitlines() if x.strip()] if a.ledger.exists() else []
 seen={x["pair_second_utc"] for x in old}; new=[json.loads(x) for x in a.source.read_text().splitlines() if x.strip()]
 add=[x for x in new if x["pair_second_utc"] not in seen]
 if old and add and min(x["pair_second_utc"] for x in add)<=max(x["pair_second_utc"] for x in old): raise SystemExit("NON_PROSPECTIVE_OR_OUT_OF_ORDER_APPEND")
 with a.ledger.open("a") as f:
  for x in add:f.write(json.dumps(x,sort_keys=True)+"\n")
 print(json.dumps({"existing_pairs":len(old),"new_pairs":len(add),"total_pairs":len(old)+len(add)}))
if __name__=="__main__":main()
