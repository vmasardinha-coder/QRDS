import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_rejection_ledger_initializes_without_adjudication_or_credit():
    lines = [x for x in (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_REJECTION_LEDGER_20260915.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 1
    d = json.loads(lines[0])
    assert d["event"] == "LEDGER_INITIALIZED"
    assert d["scientific_credit"] == 0
