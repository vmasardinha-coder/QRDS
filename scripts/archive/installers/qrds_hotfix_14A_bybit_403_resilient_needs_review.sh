#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then
  ROOT="/workspaces/QRDS"
fi

PROJECT="$ROOT/crypto_decision_lab"
SRC="$PROJECT/src"
OUT="$PROJECT/artifacts/phase14_bybit_public_data_adapter_pack"
export PYTHONPATH="$SRC:${PYTHONPATH:-}"

cd "$ROOT"

echo "[HOTFIX 14A] Patching Bybit adapter to handle public endpoint 403 without crashing..."

python - <<'PY'
from pathlib import Path

path = Path("crypto_decision_lab/src/crypto_decision_lab/reports/phase14_bybit_public_data_adapter_pack.py")
if not path.exists():
    raise SystemExit(f"Missing file: {path}")

text = path.read_text(encoding="utf-8")

if "import urllib.error" not in text:
    text = text.replace("import urllib.parse\nimport urllib.request\n", "import urllib.error\nimport urllib.parse\nimport urllib.request\n")

old_http = '''def _http_get_json(url: str, timeout: int = 25) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "QRDS-Research-Only/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))
'''

new_http = '''def _http_get_json(url: str, timeout: int = 25) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "QRDS-Research-Only/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {
            "__network_error__": True,
            "error_type": "HTTPError",
            "status_code": exc.code,
            "reason": str(exc.reason),
            "url": url,
            "research_status": "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY",
        }
    except Exception as exc:
        return {
            "__network_error__": True,
            "error_type": exc.__class__.__name__,
            "status_code": None,
            "reason": str(exc),
            "url": url,
            "research_status": "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY",
        }
'''

if old_http in text:
    text = text.replace(old_http, new_http, 1)
elif "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY" not in text:
    raise SystemExit("Could not patch _http_get_json block.")

old_fetch_check = '''        data = _http_get_json(url)
        if not isinstance(data, dict) or data.get("retCode") != 0:
            raise RuntimeError(f"Bybit kline failed for {symbol}: {data}")
        result = data.get("result") if isinstance(data.get("result"), dict) else {}
'''

new_fetch_check = '''        data = _http_get_json(url)
        if isinstance(data, dict) and data.get("__network_error__"):
            return []
        if not isinstance(data, dict) or data.get("retCode") != 0:
            return []
        result = data.get("result") if isinstance(data.get("result"), dict) else {}
'''

if old_fetch_check in text:
    text = text.replace(old_fetch_check, new_fetch_check, 1)
elif 'data.get("__network_error__")' not in text:
    raise SystemExit("Could not patch fetch network-error handling block.")

old_payload_marker = '''        "api_base": API_BASE,
        "symbols": symbols,
'''
new_payload_marker = '''        "api_base": API_BASE,
        "endpoint_access_status": "PUBLIC_ENDPOINT_ACCESS_OK_RESEARCH_ONLY" if validation["total_rows"] > 0 else "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY",
        "endpoint_blocked_or_unavailable": validation["total_rows"] == 0,
        "symbols": symbols,
'''
if old_payload_marker in text and '"endpoint_access_status"' not in text:
    text = text.replace(old_payload_marker, new_payload_marker, 1)

old_index_marker = '''        "source_endpoint_family": payload["source_endpoint_family"],
        "symbols": payload["symbols"],
'''
new_index_marker = '''        "source_endpoint_family": payload["source_endpoint_family"],
        "endpoint_access_status": payload["endpoint_access_status"],
        "endpoint_blocked_or_unavailable": payload["endpoint_blocked_or_unavailable"],
        "symbols": payload["symbols"],
'''
if old_index_marker in text and '"endpoint_access_status": payload["endpoint_access_status"]' not in text:
    text = text.replace(old_index_marker, new_index_marker, 1)

path.write_text(text, encoding="utf-8")
print("[HOTFIX 14A] Bybit adapter patch OK.")
PY

cat > "$PROJECT/tests/regression/test_phase14_bybit_403_generates_needs_review_report.py" <<'PY'
from pathlib import Path

import crypto_decision_lab.reports.phase14_bybit_public_data_adapter_pack as bybit_pack


def test_phase14_bybit_403_generates_needs_review_report(monkeypatch, tmp_path: Path) -> None:
    def fake_http_get_json(url: str, timeout: int = 25):
        return {
            "__network_error__": True,
            "error_type": "HTTPError",
            "status_code": 403,
            "reason": "Forbidden",
            "url": url,
            "research_status": "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY",
        }

    monkeypatch.setattr(bybit_pack, "_http_get_json", fake_http_get_json)

    result = bybit_pack.build_phase14_bybit_public_data_adapter_pack(
        tmp_path / "out",
        tmp_path / "repo",
        symbols=["BTCUSDT"],
        rows_per_symbol=3,
        fetch=True,
    )
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE14_BYBIT_PUBLIC_DATA_ADAPTER_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["bybit_adapter_ready"] is False
    assert payload["bybit_rows_total"] == 0
    assert payload["endpoint_access_status"] == "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY"
    assert payload["endpoint_blocked_or_unavailable"] is True
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert payload["order_endpoint_used"] is False
    assert payload["trading_endpoint_used"] is False
    assert Path(result["html_path"]).exists()
PY

echo "[HOTFIX 14A] Running targeted regression..."
cd "$PROJECT"
pytest -q tests/regression/test_phase14_bybit_403_generates_needs_review_report.py

echo "[HOTFIX 14A] Running impacted tests..."
pytest -q \
  tests/unit/test_phase14_bybit_public_data_adapter_pack.py \
  tests/integration/test_phase14_bybit_public_data_adapter_pack_cli.py

echo "[HOTFIX 14A] Running full suite..."
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs

echo "[HOTFIX 14A] Regenerating Bybit report. If Codespaces IP is blocked, this should now end as NEEDS_REVIEW instead of crashing..."
cd "$ROOT"
bash "$ROOT/qrds_phase14_bybit_public_data_adapter_pack.sh" "$OUT" || true

python - <<'PY'
import json
from pathlib import Path

p = Path("crypto_decision_lab/artifacts/phase14_bybit_public_data_adapter_pack/phase14_bybit_public_data_adapter_pack_index.json")
if not p.exists():
    raise SystemExit("Bybit index was not generated.")

d = json.loads(p.read_text(encoding="utf-8"))
print("[HOTFIX 14A] Bybit report summary:")
for k in [
    "gate_answer",
    "station",
    "bybit_adapter_ready",
    "data_nature",
    "source_label",
    "source_endpoint_family",
    "endpoint_access_status",
    "endpoint_blocked_or_unavailable",
    "symbols",
    "category",
    "interval",
    "rows_per_symbol",
    "bybit_file_count",
    "bybit_rows_total",
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
print("[HOTFIX 14A] File summaries:")
for f in d.get("payload", {}).get("file_summaries", []):
    print(f"{f['raw_symbol']}: rows={f['rows']} first={f['first_timestamp']} last={f['last_timestamp']} ready={f['ready']}")
PY

echo "[HOTFIX 14A] Archiving root installers if present..."
cd "$ROOT"
mkdir -p scripts/archive/installers
for f in \
  "qrds_sprint_14A_to_14H_bybit_public_data_adapter_pack.sh" \
  "qrds_hotfix_14A_bybit_403_resilient_needs_review.sh" \
  "qrds_hotfix_14A_bybit_403_resilient_needs_review (1).sh"
do
  if [ -f "$f" ]; then
    mv "$f" "scripts/archive/installers/$f"
    echo "[HOTFIX 14A] Archived $f"
  fi
done

echo "[HOTFIX 14A] Committing changes..."
git add -A
git commit -m "Handle Bybit public endpoint 403 as research needs review" || true
git push || true

echo "[HOTFIX 14A] Final status:"
git status --short
