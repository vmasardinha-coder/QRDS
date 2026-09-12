#!/usr/bin/env python3
import json
from pathlib import Path

P=Path("tools/gate_btc_factory/MULTI_FRONTIER_ROUTING_CONTRACT.v1.json")

def route(c):
    f={x["id"]:x for x in c["frontiers"]}
    assert f["B3_WIN_STRICT_V2"]["source_gate_green"] is False
    assert f["B3_WIN_STRICT_V2"]["waiting_families"] == 512
    assert f["B3_WIN_STRICT_V2"]["economics_read"] is False
    candidates=[x for x in c["frontiers"] if x.get("capacity_weight_when_available",0)>0 and x["status"] not in ("WAITING_SOURCE_QUALIFICATION",)]
    candidates.sort(key=lambda x:(-x.get("capacity_weight_when_available",0), c["routing_policy"]["priority_order"].index(x["id"])))
    return {
      "schema":"qrds.factory.multi_frontier_routing_runtime.v1",
      "blocked_frontiers":["B3_WIN_STRICT_V2"],
      "active_research_frontiers":[x["id"] for x in candidates],
      "primary_capacity_target":candidates[0]["id"] if candidates else None,
      "b3_win_waiting_families":512,
      "b3_win_source_gate_green":False,
      "economics_read_from_blocked_frontiers":False,
      "scientific_credit_transfer":False,
      "orders":0,
      "real_capital":0
    }

def main():
    c=json.loads(P.read_text(encoding="utf-8"))
    out=route(c)
    Path("tools/gate_btc_factory/MULTI_FRONTIER_ROUTING_RUNTIME.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":
    main()
