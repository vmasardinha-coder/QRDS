import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone

import pytest

from tools import gate_btc_v16b1_mature_official as m


def fixture(tmp_path):
    week = tmp_path / m.BASE / "2026-10-08"
    week.mkdir(parents=True)
    features = "symbol,feature_ok\nAAAUSDT,True\n"
    exclusions = "symbol,reason,missing_features\nNEWUSDT,INCOMPLETE_FROZEN_FEATURES,mom90\n"
    (week / "FEATURES.csv").write_text(features)
    (week / "EXCLUSIONS.csv").write_text(exclusions)
    meta = {"signal_date": "2026-10-08", "entry_date": "2026-10-09",
            "exit_date": "2026-10-16", "label_status": "PENDING_FROZEN_EXIT",
            "eligible_feature_rows": 1, "features_sha256": m.sha(features.encode()),
            "exclusions_sha256": m.sha(exclusions.encode()), "scientific_credit": 0}
    (week / "WEEK.json").write_text(json.dumps(meta))
    return week


def archive(day, close):
    from datetime import date, timedelta
    start = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)
    end = start + 86400000 - 1
    row = f"{start},1,1,1,{close},1,{end},1,0,0,0,0\n"
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(f"AAAUSDT-1d-{day}.csv", row)
    return out.getvalue()


def fake_fetch(session, venue, symbol, day):
    assert venue == "SPOT" and symbol == "AAAUSDT"
    raw = archive(day, 100 if day == "2026-10-09" else 112)
    digest = hashlib.sha256(raw).hexdigest()
    return raw, digest, digest + "  archive.zip\n", "https://data.binance.vision/test"


def test_official_labels_only_after_exit_and_only_for_frozen_members(tmp_path, monkeypatch):
    week = fixture(tmp_path)
    monkeypatch.setattr(m, "fetch_verified", fake_fetch)
    with pytest.raises(ValueError, match="has not closed"):
        m.mature(tmp_path, "2026-10-08", datetime(2026, 10, 16, 23, 59, tzinfo=timezone.utc), object())
    out = m.mature(tmp_path, "2026-10-08", datetime(2026, 10, 17, tzinfo=timezone.utc), object())
    assert out["label_rows"] == 1 and out["raw_archives"] == 2
    labels = list(csv.DictReader((week / "LABELS.csv").open()))
    assert labels[0]["symbol"] == "AAAUSDT" and float(labels[0]["fwd_ret"]) == pytest.approx(0.12)
    assert json.loads((week / "MATURED.json").read_text())["scientific_credit"] == 0
    evidence = json.loads((week / "LABEL_EVIDENCE.json").read_text())
    assert len(evidence["records"]) == 2
    assert m.sha((week / "raw/AAAUSDT/AAAUSDT-1d-2026-10-16.zip").read_bytes()) == evidence["records"][1]["raw_sha256"]
    assert not (week / "raw/NEWUSDT").exists()


def test_frozen_feature_tamper_blocks_network(tmp_path, monkeypatch):
    week = fixture(tmp_path)
    (week / "FEATURES.csv").write_text("symbol,feature_ok\nBADUSDT,True\n")
    monkeypatch.setattr(m, "fetch_verified", lambda *args: pytest.fail("network must not be called"))
    with pytest.raises(ValueError, match="hash mismatch"):
        m.mature(tmp_path, "2026-10-08", datetime(2026, 10, 17, tzinfo=timezone.utc), object())
