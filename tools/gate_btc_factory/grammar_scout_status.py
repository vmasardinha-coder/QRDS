#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
STAGES=('scout','handoff','preregistration_transport','source_cost_qualification','factory_entry')
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); a=ap.parse_args(); d=json.loads(Path(a.input).read_text()); candidates=d.get('candidates',[])
 traversed=[]
 for c in candidates:
  if all(bool(c.get('stages',{}).get(s)) for s in STAGES): traversed.append(c.get('id'))
 print(json.dumps({'schema':'qrds.factory.grammar_scout_traversal_status.v1','candidate_count':len(candidates),'full_traversals':traversed,'success':bool(traversed)},sort_keys=True))
 raise SystemExit(0 if traversed else 2)
if __name__=='__main__': main()
