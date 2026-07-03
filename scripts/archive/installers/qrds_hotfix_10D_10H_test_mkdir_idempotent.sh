#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then
  ROOT="/workspaces/QRDS"
fi

PROJECT="$ROOT/crypto_decision_lab"
TEST="$PROJECT/tests/unit/test_phase10_offline_intake_validation_pack.py"

if [ ! -f "$TEST" ]; then
  echo "[HOTFIX 10D-10H] Missing test file: $TEST"
  exit 1
fi

python - <<'PY'
from pathlib import Path

path = Path("crypto_decision_lab/tests/unit/test_phase10_offline_intake_validation_pack.py")
text = path.read_text(encoding="utf-8")

old = "    t.parent.mkdir(parents=True)\n"
new = "    t.parent.mkdir(parents=True, exist_ok=True)\n"

if old not in text and new not in text:
    raise SystemExit("Expected mkdir line not found; inspect test manually.")

text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("[HOTFIX 10D-10H] Patched mkdir idempotency in unit test.")
PY

echo
echo "[HOTFIX 10D-10H] Running targeted tests..."
cd "$PROJECT"
pytest -q tests/unit/test_phase10_offline_intake_validation_pack.py tests/integration/test_phase10_offline_intake_validation_pack_cli.py

echo
echo "[HOTFIX 10D-10H] Running full test suite..."
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs

echo
echo "[HOTFIX 10D-10H] Generating report..."
cd "$ROOT"
bash "$ROOT/qrds_phase10_offline_intake_validation_pack.sh" "$PROJECT/artifacts/phase10_offline_intake_validation_pack"

python - <<'PY'
import json
from pathlib import Path

p = Path("crypto_decision_lab/artifacts/phase10_offline_intake_validation_pack/phase10_offline_intake_validation_pack_index.json")
d = json.loads(p.read_text(encoding="utf-8"))
keys = [
    "gate_answer",
    "station",
    "collection_queue_present",
    "adapter_queue_present",
    "template_report_present",
    "templates_checked",
    "valid_templates",
    "staging_manifest_entry_count",
    "canonical_data_writes",
    "git_status_line_count",
    "criteria_ready_count",
    "criteria_total_count",
    "mean_pack_score",
    "policy_lock",
    "app_mode",
]
print("[HOTFIX 10D-10H] Summary:")
for k in keys:
    print(f"{k}: {d.get(k)}")
PY

echo
echo "[HOTFIX 10D-10H] Archiving installers if present..."
mkdir -p "$ROOT/scripts/archive/installers"
for f in \
  "$ROOT/qrds_sprint_10D_to_10H_offline_intake_validation_pack.sh" \
  "$ROOT/qrds_hotfix_10D_10H_test_mkdir_idempotent.sh"
do
  if [ -f "$f" ]; then
    mv "$f" "$ROOT/scripts/archive/installers/"
  fi
done

echo
echo "[HOTFIX 10D-10H] Commit/push..."
cd "$ROOT"
git add -A
git commit -m "Fix 10D-10H offline intake validation test idempotency" || true
git push || true

echo
echo "[HOTFIX 10D-10H] Final status:"
git status --short
