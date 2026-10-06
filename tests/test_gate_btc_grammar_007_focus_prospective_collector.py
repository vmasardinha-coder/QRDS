import json
from pathlib import Path
def test_focus_prereg_is_future_only_and_zero_credit():
 p=json.loads(Path("artifacts/gate_btc_2/GRAMMAR_007_FOCUS_PROSPECTIVE_PREREG_20261006.json").read_text())
 assert p["family_id"]=="XAGRAMMAR_728DC88D691B"
 assert p["activation_utc"]=="2026-10-06T00:00:00Z"
 assert p["scientific_credit"]==0 and p["prospective_credit"]==0
 assert p["promotion_authority"] is False and p["safety"]["NO_BACKFILL"] is True
