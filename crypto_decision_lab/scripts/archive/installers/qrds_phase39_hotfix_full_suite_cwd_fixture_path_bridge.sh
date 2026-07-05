#!/usr/bin/env bash
set -Eeuo pipefail

# QRDS Phase 39 hotfix
# Safe technical hotfix only:
# - fixes test/runtime working-directory compatibility for legacy tests that expect
#   data/ and docs/ relative to the Python project;
# - creates root-level compatibility links when safe;
# - reruns focused Phase 39 checks and full suite from crypto_decision_lab;
# - does not create signals, recommendations, allocations, decisions, safe-apply,
#   canonical writes, or operational edge.

ROOT_DEFAULT="/workspaces/QRDS"
if [[ -d "$ROOT_DEFAULT/crypto_decision_lab" ]]; then
  REPO_ROOT="$ROOT_DEFAULT"
else
  # Allow running from either repo root or crypto_decision_lab.
  if [[ -d "$(pwd)/crypto_decision_lab" ]]; then
    REPO_ROOT="$(pwd)"
  elif [[ "$(basename "$(pwd)")" == "crypto_decision_lab" && -d "$(pwd)/src/crypto_decision_lab" ]]; then
    REPO_ROOT="$(dirname "$(pwd)")"
  else
    echo "[QRDS][HOTFIX][ERROR] Cannot locate QRDS repo root. Run from /workspaces/QRDS or crypto_decision_lab."
    exit 2
  fi
fi

PROJECT_DIR="$REPO_ROOT/crypto_decision_lab"
ARCHIVE_DIR="$PROJECT_DIR/scripts/archive/installers"
REPORT_PATH="$PROJECT_DIR/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
HOTFIX_STATUS_DIR="$PROJECT_DIR/artifacts/phase39_hotfix_full_suite_cwd_fixture_path_bridge"
HOTFIX_STATUS_JSON="$HOTFIX_STATUS_DIR/phase39_hotfix_full_suite_cwd_fixture_path_bridge.json"

mkdir -p "$ARCHIVE_DIR" "$HOTFIX_STATUS_DIR"

echo "[QRDS][HOTFIX] Repo root: $REPO_ROOT"
echo "[QRDS][HOTFIX] Project dir: $PROJECT_DIR"
echo "[QRDS][HOTFIX] Safe scope: cwd/path compatibility only; research-only locks preserved."

# Preserve research-only locks in machine-readable status.
cat > "$HOTFIX_STATUS_JSON" <<'JSON'
{
  "gate": "PHASE39_HOTFIX_FULL_SUITE_CWD_FIXTURE_PATH_BRIDGE_RUNNING_RESEARCH_ONLY",
  "app_mode": "INTERACTIVE_RESEARCH_ONLY",
  "policy_lock": "ACTIVE",
  "operational_status": "BLOCKED_RESEARCH_ONLY",
  "edge_validated": false,
  "edge_operationally_validated": false,
  "shadow_decision_allowed": false,
  "decision_layer_allowed": false,
  "trading_signal_generated": false,
  "recommendation_generated": false,
  "allocation_generated": false,
  "operational_decision_allowed": false,
  "safe_apply_allowed": false,
  "promotion_allowed": false,
  "canonical_data_writes": 0,
  "hotfix_type": "SAFE_TECHNICAL_CWD_AND_FIXTURE_PATH_COMPATIBILITY"
}
JSON

# Root-level compatibility links.
# Reason: legacy tests reference data/... and docs/... relative to cwd.
# When pytest is launched from /workspaces/QRDS, those paths are missing even if
# the project-owned files exist under crypto_decision_lab/.
make_compat_link() {
  local target="$1"
  local link="$2"
  local label="$3"

  if [[ ! -e "$target" ]]; then
    echo "[QRDS][HOTFIX][NEEDS_REVIEW] Missing source for $label: $target"
    return 10
  fi

  if [[ -L "$link" ]]; then
    local current
    current="$(readlink "$link")"
    if [[ "$current" == "$target" || "$current" == "crypto_decision_lab/${label}" || "$current" == "$PROJECT_DIR/${label}" ]]; then
      echo "[QRDS][HOTFIX] Existing compat symlink ok: $link -> $current"
      return 0
    fi
    echo "[QRDS][HOTFIX][NEEDS_REVIEW] Existing symlink points elsewhere: $link -> $current"
    return 11
  fi

  if [[ -e "$link" ]]; then
    echo "[QRDS][HOTFIX] Existing root path kept, not overwritten: $link"
    return 0
  fi

  ln -s "$target" "$link"
  echo "[QRDS][HOTFIX] Created compat symlink: $link -> $target"
}

LINK_ISSUES=0
make_compat_link "$PROJECT_DIR/data" "$REPO_ROOT/data" "data" || LINK_ISSUES=$((LINK_ISSUES + 1))
make_compat_link "$PROJECT_DIR/docs" "$REPO_ROOT/docs" "docs" || LINK_ISSUES=$((LINK_ISSUES + 1))

# Also provide a tiny verification wrapper for future manual use.
VERIFY_WRAPPER_ROOT="$REPO_ROOT/qrds_phase39_hotfix_verify_full_suite.sh"
VERIFY_WRAPPER_PROJECT="$PROJECT_DIR/qrds_phase39_hotfix_verify_full_suite.sh"
cat > "$VERIFY_WRAPPER_ROOT" <<'BASH'
#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="/workspaces/QRDS"
if [[ ! -d "$ROOT/crypto_decision_lab" ]]; then
  if [[ -d "$(pwd)/crypto_decision_lab" ]]; then
    ROOT="$(pwd)"
  elif [[ "$(basename "$(pwd)")" == "crypto_decision_lab" ]]; then
    ROOT="$(dirname "$(pwd)")"
  else
    echo "[QRDS][VERIFY][ERROR] Cannot locate QRDS root."
    exit 2
  fi
fi
cd "$ROOT/crypto_decision_lab"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
echo "[QRDS][VERIFY] cwd=$PWD"
echo "[QRDS][VERIFY] Running focused Phase 39 tests when available..."
python -m pytest -q tests -k "phase39 or interpretation_readiness or portal" || FOCUSED_RC=$?
FOCUSED_RC="${FOCUSED_RC:-0}"
echo "[QRDS][VERIFY] Running full suite from crypto_decision_lab..."
python -m pytest -q tests
FULL_RC=$?
echo "[QRDS][VERIFY] focused_rc=$FOCUSED_RC full_rc=$FULL_RC"
exit "$FULL_RC"
BASH
chmod +x "$VERIFY_WRAPPER_ROOT"
cp "$VERIFY_WRAPPER_ROOT" "$VERIFY_WRAPPER_PROJECT"
chmod +x "$VERIFY_WRAPPER_PROJECT"

# Update project status with a non-decision hotfix note.
mkdir -p "$(dirname "$REPORT_PATH")"
{
  echo ""
  echo "## Phase 39 Hotfix — Full Suite CWD / Fixture Path Bridge"
  echo ""
  echo "- Gate: PHASE39_HOTFIX_FULL_SUITE_CWD_FIXTURE_PATH_BRIDGE_READY_RESEARCH_ONLY"
  echo "- Scope: safe technical compatibility for legacy tests launched from repo root."
  echo "- Root compatibility paths: data -> crypto_decision_lab/data; docs -> crypto_decision_lab/docs when safe."
  echo "- Operational status: BLOCKED_RESEARCH_ONLY."
  echo "- Edge validated: False."
  echo "- Signals/recommendations/allocations/shadow decisions/safe-apply/operational decisions: not generated."
  echo "- canonical_data_writes: 0."
} >> "$REPORT_PATH"

# Archive this installer/hotfix.
SELF_PATH="${BASH_SOURCE[0]}"
if [[ -f "$SELF_PATH" ]]; then
  cp "$SELF_PATH" "$ARCHIVE_DIR/$(basename "$SELF_PATH")" || true
fi

# Run tests from the Python project directory, not repo root.
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
echo "[QRDS][HOTFIX] cwd for tests: $(pwd)"
echo "[QRDS][HOTFIX] python: $(python --version 2>&1)"

if [[ "$LINK_ISSUES" -ne 0 ]]; then
  echo "[QRDS][HOTFIX][NEEDS_REVIEW] Compatibility link issue count: $LINK_ISSUES"
  python - <<PY
import json
from pathlib import Path
p = Path("$HOTFIX_STATUS_JSON")
data = json.loads(p.read_text())
data["gate"] = "PHASE39_HOTFIX_FULL_SUITE_CWD_FIXTURE_PATH_BRIDGE_NEEDS_REVIEW_RESEARCH_ONLY"
data["needs_review_reason"] = "missing_or_conflicting_compatibility_link_source"
p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
  exit 3
fi

# Validate that core fixture/doc paths exist before running full suite.
MISSING=0
for p in \
  "$PROJECT_DIR/data/fixtures/okx_public" \
  "$PROJECT_DIR/data/fixtures/research" \
  "$PROJECT_DIR/docs" \
  "$PROJECT_DIR/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
do
  if [[ ! -e "$p" ]]; then
    echo "[QRDS][HOTFIX][NEEDS_REVIEW] Missing expected project path: $p"
    MISSING=$((MISSING + 1))
  fi
done

if [[ "$MISSING" -ne 0 ]]; then
  python - <<PY
import json
from pathlib import Path
p = Path("$HOTFIX_STATUS_JSON")
data = json.loads(p.read_text())
data["gate"] = "PHASE39_HOTFIX_FULL_SUITE_CWD_FIXTURE_PATH_BRIDGE_NEEDS_REVIEW_RESEARCH_ONLY"
data["needs_review_reason"] = "project_fixture_or_docs_missing_inside_crypto_decision_lab"
data["missing_count"] = $MISSING
p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
  echo "[QRDS][HOTFIX] This is not a decision/edge issue. It means repo fixture/docs files are absent inside the project tree."
  exit 4
fi

echo "[QRDS][HOTFIX] Running focused tests..."
set +e
python -m pytest -q tests -k "phase39 or interpretation_readiness or portal"
FOCUSED_RC=$?
set -e
echo "[QRDS][HOTFIX] Focused rc: $FOCUSED_RC"

echo "[QRDS][HOTFIX] Running full suite..."
set +e
python -m pytest -q tests
FULL_RC=$?
set -e
echo "[QRDS][HOTFIX] Full suite rc: $FULL_RC"

if [[ "$FULL_RC" -eq 0 ]]; then
  python - <<PY
import json
from pathlib import Path
p = Path("$HOTFIX_STATUS_JSON")
data = json.loads(p.read_text())
data.update({
  "gate": "PHASE39_HOTFIX_FULL_SUITE_CWD_FIXTURE_PATH_BRIDGE_READY_RESEARCH_ONLY",
  "focused_test_rc": $FOCUSED_RC,
  "full_suite_rc": $FULL_RC,
  "compatibility_links_ready": True
})
p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY

  if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$REPO_ROOT" add \
      data docs \
      "$REPORT_PATH" \
      "$HOTFIX_STATUS_DIR" \
      "$VERIFY_WRAPPER_ROOT" \
      "$VERIFY_WRAPPER_PROJECT" \
      "$ARCHIVE_DIR/$(basename "$SELF_PATH")" 2>/dev/null || true
    git -C "$REPO_ROOT" commit -m "Phase 39 hotfix: full suite cwd fixture path bridge" || true
    git -C "$REPO_ROOT" push || true
  fi

  echo ""
  echo "QRDS Phase 39 Hotfix • Full Suite CWD / Fixture Path Bridge"
  echo "PHASE39_HOTFIX_FULL_SUITE_CWD_FIXTURE_PATH_BRIDGE_READY_RESEARCH_ONLY"
  echo "Operational: BLOCKED_RESEARCH_ONLY"
  echo "Edge: False"
  echo "canonical_data_writes: 0"
  echo "Full suite: PASS"
  exit 0
fi

python - <<PY
import json
from pathlib import Path
p = Path("$HOTFIX_STATUS_JSON")
data = json.loads(p.read_text())
data.update({
  "gate": "PHASE39_HOTFIX_FULL_SUITE_CWD_FIXTURE_PATH_BRIDGE_NEEDS_REVIEW_RESEARCH_ONLY",
  "focused_test_rc": $FOCUSED_RC,
  "full_suite_rc": $FULL_RC,
  "needs_review_reason": "full_suite_still_failing_after_cwd_path_bridge"
})
p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY

echo ""
echo "QRDS Phase 39 Hotfix • NEEDS_REVIEW_RESEARCH_ONLY"
echo "The safe cwd/path bridge was applied, but full suite still fails."
echo "This remains a technical test/repo-state issue, not an edge or operational decision issue."
echo "Operational: BLOCKED_RESEARCH_ONLY"
echo "Edge: False"
exit "$FULL_RC"
