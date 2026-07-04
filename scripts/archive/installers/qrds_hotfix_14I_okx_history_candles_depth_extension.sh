#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then
  ROOT="/workspaces/QRDS"
fi

PROJECT="$ROOT/crypto_decision_lab"
SRC="$PROJECT/src"
OUT="$PROJECT/artifacts/phase14_okx_public_data_adapter_pack"
export PYTHONPATH="$SRC:${PYTHONPATH:-}"

cd "$ROOT"

echo "[HOTFIX 14I] Patching OKX adapter to extend depth with history-candles..."

python - <<'PY'
from pathlib import Path

path = Path("crypto_decision_lab/src/crypto_decision_lab/reports/phase14_okx_public_data_adapter_pack.py")
if not path.exists():
    raise SystemExit(f"Missing OKX adapter file: {path}")

text = path.read_text(encoding="utf-8")

new_func = '''def _normalize_okx_candle_rows(inst_id: str, rows_raw: list[list[Any]], rows: int) -> list[dict[str, Any]]:
    ordered = [rows_raw_item for rows_raw_item in sorted(rows_raw, key=lambda r: int(r[0]))][-rows:]
    normalized: list[dict[str, Any]] = []
    for row in ordered:
        # OKX candle row shape: ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm
        normalized.append(
            {
                "timestamp": _ms_to_iso(int(row[0])),
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
                "volume_currency": row[6] if len(row) > 6 else "",
                "volume_quote": row[7] if len(row) > 7 else "",
                "confirm": row[8] if len(row) > 8 else "",
                "symbol": inst_id,
                "inst_id": inst_id,
                "bar": "1h",
                "source": SOURCE_LABEL,
                "venue": "OKX",
            }
        )
    return normalized


def _fetch_okx_endpoint_pages(inst_id: str, bar: str, rows: int, endpoint_path: str, page_limit: str, after_start: str | None = None, attempts_limit: int = 80) -> dict[int, list[Any]]:
    collected: dict[int, list[Any]] = {}
    after = after_start
    attempts = 0

    while len(collected) < rows and attempts < attempts_limit:
        attempts += 1
        params = {"instId": inst_id, "bar": bar, "limit": page_limit}
        if after:
            params["after"] = after
        url = API_BASE + endpoint_path + "?" + urllib.parse.urlencode(params)
        data = _http_get_json(url)
        if isinstance(data, dict) and data.get("__network_error__"):
            break
        if not isinstance(data, dict) or data.get("code") != "0":
            break
        batch = data.get("data") if isinstance(data.get("data"), list) else []
        if not batch:
            break

        usable = [row for row in batch if isinstance(row, list) and len(row) >= 6]
        if not usable:
            break
        before_count = len(collected)
        for row in usable:
            collected[int(row[0])] = row

        oldest = min(int(row[0]) for row in usable)
        after = str(oldest)

        if len(collected) == before_count or len(usable) < 2:
            break
        time.sleep(0.12)

    return collected


def fetch_okx_candles(inst_id: str, bar: str, rows: int) -> list[dict[str, Any]]:
    # OKX recent candles can be shallower than our 5000-row research target.
    # Start with recent candles, then extend backwards with history-candles.
    recent = _fetch_okx_endpoint_pages(
        inst_id=inst_id,
        bar=bar,
        rows=rows,
        endpoint_path="/api/v5/market/candles",
        page_limit="300",
        after_start=None,
        attempts_limit=12,
    )

    all_rows: dict[int, list[Any]] = dict(recent)
    after_start = str(min(all_rows.keys())) if all_rows else None

    if len(all_rows) < rows:
        history = _fetch_okx_endpoint_pages(
            inst_id=inst_id,
            bar=bar,
            rows=rows - len(all_rows),
            endpoint_path="/api/v5/market/history-candles",
            page_limit="100",
            after_start=after_start,
            attempts_limit=80,
        )
        all_rows.update(history)

    return _normalize_okx_candle_rows(inst_id, list(all_rows.values()), rows)
'''

lines = text.splitlines(keepends=True)
start = None
for i, line in enumerate(lines):
    if line.startswith("def fetch_okx_candles("):
        start = i
        break

if start is None:
    if "_fetch_okx_endpoint_pages" in text:
        print("[HOTFIX 14I] fetch_okx_candles already patched.")
        raise SystemExit(0)
    raise SystemExit("Could not locate fetch_okx_candles.")

end = len(lines)
for j in range(start + 1, len(lines)):
    if lines[j].startswith("def ") or lines[j].startswith("class "):
        end = j
        break

new_text = "".join(lines[:start]) + new_func + "\n\n" + "".join(lines[end:])

new_text = new_text.replace(
    '"source_endpoint_family": "OKX_V5_MARKET_CANDLES",',
    '"source_endpoint_family": "OKX_V5_MARKET_CANDLES_AND_HISTORY_CANDLES",'
)
new_text = new_text.replace(
    "OKX public market candles endpoint family;",
    "OKX public market candles and history-candles endpoint family;"
)

path.write_text(new_text, encoding="utf-8")
print(f"[HOTFIX 14I] Replaced fetch_okx_candles lines {start+1}-{end}.")
PY

cat > "$PROJECT/tests/regression/test_phase14_okx_history_candles_extends_depth.py" <<'PY'
from pathlib import Path

import crypto_decision_lab.reports.phase14_okx_public_data_adapter_pack as okx_pack


def test_phase14_okx_history_candles_extends_depth(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_http_get_json(url: str, timeout: int = 25):
        calls.append(url)
        if "/api/v5/market/candles" in url:
            return {
                "code": "0",
                "data": [
                    ["5000", "104", "105", "103", "104.5", "1000", "10", "100000", "1"],
                    ["4000", "103", "104", "102", "103.5", "1000", "10", "100000", "1"],
                ],
            }
        if "/api/v5/market/history-candles" in url:
            return {
                "code": "0",
                "data": [
                    ["3000", "102", "103", "101", "102.5", "1000", "10", "100000", "1"],
                    ["2000", "101", "102", "100", "101.5", "1000", "10", "100000", "1"],
                    ["1000", "100", "101", "99", "100.5", "1000", "10", "100000", "1"],
                ],
            }
        return {"code": "0", "data": []}

    monkeypatch.setattr(okx_pack, "_http_get_json", fake_http_get_json)

    result = okx_pack.build_phase14_okx_public_data_adapter_pack(
        tmp_path / "out",
        tmp_path / "repo",
        inst_ids=["BTC-USDT-SWAP"],
        rows_per_instrument=5,
        fetch=True,
    )
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE14_OKX_PUBLIC_DATA_ADAPTER_READY_RESEARCH_ONLY"
    assert payload["okx_adapter_ready"] is True
    assert payload["okx_rows_total"] == 5
    assert payload["source_endpoint_family"] == "OKX_V5_MARKET_CANDLES_AND_HISTORY_CANDLES"
    assert any("/api/v5/market/history-candles" in url for url in calls)
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
PY

cat > "$PROJECT/tests/regression/test_phase14_okx_partial_recent_stays_needs_review.py" <<'PY'
from pathlib import Path

import crypto_decision_lab.reports.phase14_okx_public_data_adapter_pack as okx_pack


def test_phase14_okx_partial_recent_stays_needs_review_when_history_empty(monkeypatch, tmp_path: Path) -> None:
    def fake_http_get_json(url: str, timeout: int = 25):
        if "/api/v5/market/candles" in url:
            return {
                "code": "0",
                "data": [
                    ["2000", "101", "102", "100", "101.5", "1000", "10", "100000", "1"],
                    ["1000", "100", "101", "99", "100.5", "1000", "10", "100000", "1"],
                ],
            }
        if "/api/v5/market/history-candles" in url:
            return {"code": "0", "data": []}
        return {"code": "0", "data": []}

    monkeypatch.setattr(okx_pack, "_http_get_json", fake_http_get_json)

    result = okx_pack.build_phase14_okx_public_data_adapter_pack(
        tmp_path / "out",
        tmp_path / "repo",
        inst_ids=["BTC-USDT-SWAP"],
        rows_per_instrument=5,
        fetch=True,
    )
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE14_OKX_PUBLIC_DATA_ADAPTER_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["okx_adapter_ready"] is False
    assert payload["okx_rows_total"] == 2
    assert payload["endpoint_access_status"] == "PUBLIC_ENDPOINT_ACCESS_OK_RESEARCH_ONLY"
    assert payload["endpoint_blocked_or_unavailable"] is False
    assert payload["canonical_data_writes"] == 0
PY

echo "[HOTFIX 14I] Running targeted OKX history regressions..."
cd "$PROJECT"
pytest -q \
  tests/regression/test_phase14_okx_history_candles_extends_depth.py \
  tests/regression/test_phase14_okx_partial_recent_stays_needs_review.py \
  tests/regression/test_phase14_okx_blocked_generates_needs_review_report.py

echo "[HOTFIX 14I] Running impacted OKX tests..."
pytest -q \
  tests/unit/test_phase14_okx_public_data_adapter_pack.py \
  tests/integration/test_phase14_okx_public_data_adapter_pack_cli.py

echo "[HOTFIX 14I] Running full suite..."
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs

echo "[HOTFIX 14I] Regenerating OKX report with history-candles depth extension..."
cd "$ROOT"
bash "$ROOT/qrds_phase14_okx_public_data_adapter_pack.sh" "$OUT" || true

python - <<'PY'
import json
from pathlib import Path

p = Path("crypto_decision_lab/artifacts/phase14_okx_public_data_adapter_pack/phase14_okx_public_data_adapter_pack_index.json")
if not p.exists():
    raise SystemExit("OKX index was not generated.")

d = json.loads(p.read_text(encoding="utf-8"))
print("[HOTFIX 14I] OKX report summary:")
for k in [
    "gate_answer",
    "station",
    "okx_adapter_ready",
    "data_nature",
    "source_label",
    "source_endpoint_family",
    "endpoint_access_status",
    "endpoint_blocked_or_unavailable",
    "inst_ids",
    "bar",
    "rows_per_instrument",
    "okx_file_count",
    "okx_rows_total",
    "separate_inbox_path",
    "operational_status",
    "modeling_status",
    "order_endpoint_used",
    "trading_endpoint_used",
    "safe_apply_allowed",
    "promotion_allowed",
    "canonical_data_writes",
    "git_status_line_count",
    "criteria_ready_count",
    "criteria_total_count",
    "mean_adapter_score",
    "policy_lock",
    "app_mode",
]:
    print(f"{k}: {d.get(k)}")
print("[HOTFIX 14I] File summaries:")
for f in d.get("payload", {}).get("file_summaries", []):
    print(f"{f['inst_id']}: rows={f['rows']} first={f['first_timestamp']} last={f['last_timestamp']} ready={f['ready']} ann_vol_research={f['ann_vol_research']}")
PY

echo "[HOTFIX 14I] Archiving root installers if present..."
cd "$ROOT"
mkdir -p scripts/archive/installers
for f in \
  "qrds_sprint_14I_to_14R_okx_public_data_adapter_pack.sh" \
  "qrds_hotfix_14I_okx_history_candles_depth_extension.sh" \
  "qrds_hotfix_14I_okx_history_candles_depth_extension (1).sh"
do
  if [ -f "$f" ]; then
    mv "$f" "scripts/archive/installers/$f"
    echo "[HOTFIX 14I] Archived $f"
  fi
done

echo "[HOTFIX 14I] Committing changes..."
git add -A
git commit -m "Extend OKX adapter with history candles depth fallback" || true
git push || true

echo "[HOTFIX 14I] Final status:"
git status --short
