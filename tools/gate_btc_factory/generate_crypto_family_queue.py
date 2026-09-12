#!/usr/bin/env python3
import json
from pathlib import Path

CONTRACT=Path("tools/gate_btc_factory/CRYPTO_FAMILY_FACTORY_CONTRACT.v1.json")

def build_queue(contract):
    required={"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"FAIL_CLOSED":True}
    for k,v in required.items():
        assert contract["safety"][k] == v
    assert contract["economics_read_allowed"] is False
    fams=contract["families"]
    ids=[f["id"] for f in fams]
    assert len(ids)==len(set(ids))
    assert all(f["state"]=="WAITING_SOURCE" for f in fams)
    return {
      "schema":"qrds.factory.crypto_family_queue.v1",
      "frontier":contract["frontier"],
      "family_count":len(fams),
      "counts":{"WAITING_SOURCE":len(fams)},
      "families":[{"id":f["id"],"channel":f["channel"],"mechanism":f["mechanism"],"state":f["state"]} for f in fams],
      "economics_read":False,
      "scientific_credit":0,
      "promotion_allowed":False,
      "next_action":"FREEZE_QUALIFIED_FORWARD_SOURCE_CONTRACT_BEFORE_READY_FORWARD"
    }

def main():
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    q=build_queue(c)
    out=Path("tools/gate_btc_factory/CRYPTO_FAMILY_QUEUE_RUNTIME.json")
    out.write_text(json.dumps(q,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(q,sort_keys=True))

if __name__=="__main__":
    main()
