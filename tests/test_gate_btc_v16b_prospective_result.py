import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools import gate_btc_v16b_prospective_result as result
from tools import gate_btc_v16b_prospective_seal as base


def ms(dt): return int(dt.timestamp() * 1000)

def kline_zip(day: str, close: float) -> bytes:
    d = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    row = [ms(d), 100, 110, 90, close, 1, ms(d + timedelta(days=1)) - 1, 1000, 10, 0.5, 500, 0]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("kline.csv", ",".join(map(str, row)) + "\n")
    return buf.getvalue()

def funding_zip(events) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        lines = ["calc_time,funding_interval_hours,last_funding_rate"]
        lines += [f"{t},8,{r}" for t, r in events]
        z.writestr("funding.csv", "\n".join(lines) + "\n")
    return buf.getvalue()

def write_raw(root: Path, rel: str, blob: bytes):
    p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(blob)
    sha = hashlib.sha256(blob).hexdigest()
    cp = root / (rel + ".CHECKSUM"); cp.write_text(f"{sha}  {Path(rel).name}\n", encoding="utf-8")
    return p, cp, sha

def entry_event():
    longs = [f"L{i}" for i in range(10)]; shorts = [f"S{i}" for i in range(10)]
    return {
        "event_type": "V16B_ENTRY_SEAL", "seal_sha256": "e" * 64,
        "candidate_id": base.CANDIDATE_ID, "signal_date_utc": "2026-08-13", "entry_date_utc": "2026-08-14",
        "status": "OK", "longs_10": longs, "shorts_10": shorts,
        "entry_instruments": {a: a + "USDT" for a in longs + shorts},
        "exposure": 0.8, "trailing_vol": 0.25, "turnover_estimate": 0.8,
    }

def make_price_evidence(tmp_path: Path, entry: dict) -> Path:
    root = tmp_path / "prices"; root.mkdir()
    rows = []
    for asset in entry["longs_10"] + entry["shorts_10"]:
        side = "LONG" if asset in entry["longs_10"] else "SHORT"
        venue = "SPOT" if side == "LONG" else "USDM"
        instrument = entry["entry_instruments"][asset]
        closes = (100.0, 110.0) if side == "LONG" else (100.0, 105.0)
        recs = []
        for day, close in zip(("2026-08-14", "2026-08-21"), closes):
            rel = f"raw/{venue.lower()}/{instrument}/{instrument}-1d-{day}.zip"
            blob = kline_zip(day, close); _, cp, sha = write_raw(root, rel, blob)
            parsed = result.parse_daily_close(blob, day)
            recs.append({"venue": venue, "instrument": instrument, "date_utc": day, "close": close,
                         "open_time_ms": parsed["open_time_ms"], "close_time_ms": parsed["close_time_ms"],
                         "raw_file": rel, "checksum_file": str(cp.relative_to(root)).replace("\\", "/"),
                         "raw_sha256": sha, "expected_checksum_sha256": sha, "source_url": "binance"})
        ph = result.hobj({"entry_raw_sha256": recs[0]["raw_sha256"], "exit_raw_sha256": recs[1]["raw_sha256"], "venue": venue, "instrument": instrument})
        rows.append({"asset": asset, "side": side, "instrument": instrument, "venue": venue,
                     "entry": recs[0], "exit": recs[1], "price_source_hash": ph})
    btc_recs = []
    for day, close in (("2026-08-14", 100.0), ("2026-08-21", 102.0)):
        rel = f"raw/spot/BTCUSDT/BTCUSDT-1d-{day}.zip"
        blob = kline_zip(day, close); _, cp, sha = write_raw(root, rel, blob)
        parsed = result.parse_daily_close(blob, day)
        btc_recs.append({"venue": "SPOT", "instrument": "BTCUSDT", "date_utc": day, "close": close,
                         "open_time_ms": parsed["open_time_ms"], "close_time_ms": parsed["close_time_ms"],
                         "raw_file": rel, "checksum_file": str(cp.relative_to(root)).replace("\\", "/"),
                         "raw_sha256": sha, "expected_checksum_sha256": sha, "source_url": "binance"})
    btc_hash = result.hobj({"entry_raw_sha256": btc_recs[0]["raw_sha256"], "exit_raw_sha256": btc_recs[1]["raw_sha256"], "venue": "SPOT", "instrument": "BTCUSDT"})
    payload = {"status": "PASS", "candidate_id": entry["candidate_id"], "signal_date_utc": entry["signal_date_utc"],
               "entry_date_utc": entry["entry_date_utc"], "exit_date_utc": "2026-08-21", "entry_seal_sha256": entry["seal_sha256"],
               "source": "test", "assets": rows,
               "btc": {"asset": "BTC", "instrument": "BTCUSDT", "venue": "SPOT", "entry": btc_recs[0], "exit": btc_recs[1], "price_source_hash": btc_hash},
               "raw_archives": 42, "RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True, "ORDERS": 0, "REAL_CAPITAL": 0, "ENGINE_FEED": False}
    payload["evidence_sha256"] = result.hobj(payload)
    p = root / "V16B_PRICE_EVIDENCE.json"; p.write_text(json.dumps(payload), encoding="utf-8"); return p

def make_funding_evidence(tmp_path: Path, entry: dict):
    root = tmp_path / "funding"; root.mkdir()
    event_times = [ms(datetime(2026, 8, 15, 8, tzinfo=timezone.utc)), ms(datetime(2026, 8, 16, 0, tzinfo=timezone.utc)), ms(datetime(2026, 8, 16, 8, tzinfo=timezone.utc))]
    rates = [0.0001, 0.0001, 0.0001]
    rows = []; raw_archives = []
    for asset in entry["shorts_10"]:
        symbol = entry["entry_instruments"][asset]
        rel = f"raw/{symbol}/{symbol}-fundingRate-2026-08.zip"
        blob = funding_zip(list(zip(event_times, rates))); _, cp, sha = write_raw(root, rel, blob)
        raw_archives.append({"symbol": symbol, "month": "2026-08", "source_url": "binance", "raw_file": rel,
                             "checksum_file": str(cp.relative_to(root)).replace("\\", "/"), "raw_sha256": sha,
                             "expected_checksum_sha256": sha, "header": ["calc_time", "funding_interval_hours", "last_funding_rate"]})
        rows.append({"entry_friday": "2026-08-14", "exit_friday": "2026-08-21", "asset": asset, "futures_symbol": symbol,
                     "portfolio_exposure": 0.8, "funding_events": 3, "funding_rate_sum": 0.0003,
                     "first_event_ms": event_times[0], "last_event_ms": event_times[-1], "raw_evidence_sha256": sha})
    cp = root / "V16B_FUNDING_AUDIT.csv"
    with cp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summary = {"status": "PASS", "candidate_id": entry["candidate_id"], "signal_date_utc": entry["signal_date_utc"],
               "entry_date_utc": "2026-08-14", "exit_date_utc": "2026-08-21", "entry_seal_sha256": entry["seal_sha256"],
               "source": "binance", "method": "raw test", "positions": 10, "symbols": 10, "symbol_months": 10,
               "zero_event_positions": 0, "missing_month_files": [], "raw_archives": raw_archives}
    sp = root / "V16B_FUNDING_AUDIT_SUMMARY.json"; sp.write_text(json.dumps(summary), encoding="utf-8")
    return cp, sp

def setup_evidence(tmp_path):
    entry = entry_event(); ep = tmp_path / "entry.json"; ep.write_text(json.dumps(entry), encoding="utf-8")
    prices = make_price_evidence(tmp_path, entry); fc, fs = make_funding_evidence(tmp_path, entry)
    return entry, ep, prices, fc, fs

def test_result_builder_recomputes_complete_economics_and_passes_sealer(tmp_path):
    entry, ep, prices, fc, fs = setup_evidence(tmp_path)
    out = result.build(ep, prices, fc, fs)
    assert out["gross_long_pnl"] == pytest.approx(0.04)
    assert out["gross_short_pnl"] == pytest.approx(-0.02)
    assert sum(out["short_funding"].values()) == pytest.approx(0.00012)
    assert out["transaction_cost"] == pytest.approx(0.0012)
    assert out["net_pnl"] == pytest.approx(0.01892)
    assert out["btc_benchmark_return"] == pytest.approx(0.02)
    sealed = base.validate_result_row(out, entry, now=datetime(2026, 8, 22, 1, tzinfo=timezone.utc))
    assert sealed["event_type"] == "V16B_RESULT_SEAL"

def test_result_reparses_raw_price_instead_of_trusting_manifest_close(tmp_path):
    _, ep, prices, fc, fs = setup_evidence(tmp_path)
    p = json.loads(prices.read_text()); p["assets"][0]["exit"]["close"] = 999.0
    p["evidence_sha256"] = result.hobj({k: p[k] for k in p if k != "evidence_sha256"}); prices.write_text(json.dumps(p))
    with pytest.raises(ValueError, match="close differs from preserved raw archive"):
        result.build(ep, prices, fc, fs)

def test_result_recomputes_funding_instead_of_trusting_csv(tmp_path):
    _, ep, prices, fc, fs = setup_evidence(tmp_path)
    rows = list(csv.DictReader(fc.open())); rows[0]["funding_rate_sum"] = "0.99"
    with fc.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with pytest.raises(ValueError, match="funding_rate_sum differs"):
        result.build(ep, prices, fc, fs)

def test_result_blocks_wrong_funding_instrument(tmp_path):
    _, ep, prices, fc, fs = setup_evidence(tmp_path)
    rows = list(csv.DictReader(fc.open())); rows[0]["futures_symbol"] = "WRONGUSDT"
    with fc.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with pytest.raises(ValueError, match="futures symbol mismatch"):
        result.build(ep, prices, fc, fs)

def test_result_requires_all_20_price_records(tmp_path):
    _, ep, prices, fc, fs = setup_evidence(tmp_path)
    p = json.loads(prices.read_text()); p["assets"] = p["assets"][:-1]
    p["evidence_sha256"] = result.hobj({k: p[k] for k in p if k != "evidence_sha256"}); prices.write_text(json.dumps(p))
    with pytest.raises(ValueError, match="exactly 20"):
        result.build(ep, prices, fc, fs)

def test_result_detects_tampered_raw_funding_archive(tmp_path):
    _, ep, prices, fc, fs = setup_evidence(tmp_path)
    s = json.loads(fs.read_text()); raw = fs.parent / s["raw_archives"][0]["raw_file"]
    raw.write_bytes(raw.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="funding raw archive hash mismatch"):
        result.build(ep, prices, fc, fs)
