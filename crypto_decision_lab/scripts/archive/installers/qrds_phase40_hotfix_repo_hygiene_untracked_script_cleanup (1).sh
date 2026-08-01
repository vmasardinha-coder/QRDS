#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
ARCHIVE_DIR="$PROJECT_DIR/scripts/archive/installers"
STATUS_DIR="$PROJECT_DIR/artifacts/phase40_hotfix_repo_hygiene_untracked_script_cleanup"
REPORT="$PROJECT_DIR/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
GATE="PHASE40_HOTFIX_REPO_HYGIENE_UNTRACKED_SCRIPT_CLEANUP_READY_RESEARCH_ONLY"
NEEDS_REVIEW_GATE="PHASE40_HOTFIX_REPO_HYGIENE_UNTRACKED_SCRIPT_CLEANUP_NEEDS_REVIEW_RESEARCH_ONLY"

printf '[QRDS][Phase40 hygiene] Root: %s\n' "$ROOT_DIR"
cd "$ROOT_DIR"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "[QRDS][Phase40 hygiene][ERROR] crypto_decision_lab not found at $PROJECT_DIR"
  exit 2
fi

mkdir -p "$ARCHIVE_DIR" "$STATUS_DIR" "$(dirname "$REPORT")"

# Archive installer/hotfix entrypoints that should not remain loose in repo root.
archive_and_remove_if_untracked() {
  local rel="$1"
  local src="$ROOT_DIR/$rel"
  local dst="$ARCHIVE_DIR/$(basename "$rel")"
  if [[ ! -f "$src" ]]; then
    return 0
  fi
  cp -f "$src" "$dst"
  chmod +x "$dst" || true
  git add "crypto_decision_lab/scripts/archive/installers/$(basename "$rel")"
  if git ls-files --error-unmatch "$rel" >/dev/null 2>&1; then
    printf '[QRDS][Phase40 hygiene] Keeping tracked root file: %s\n' "$rel"
  else
    rm -f "$src"
    printf '[QRDS][Phase40 hygiene] Archived and removed untracked root installer: %s\n' "$rel"
  fi
}

# The current script itself may have been downloaded into root and would otherwise show as ??
SELF_PATH="$(python - <<'PY'
import os, sys
print(os.path.abspath(sys.argv[1]))
PY
"${BASH_SOURCE[0]}")"
SELF_BASE="$(basename "$SELF_PATH")"
if [[ "$SELF_PATH" == "$ROOT_DIR/"* && -f "$SELF_PATH" ]]; then
  cp -f "$SELF_PATH" "$ARCHIVE_DIR/$SELF_BASE"
  chmod +x "$ARCHIVE_DIR/$SELF_BASE" || true
  git add "crypto_decision_lab/scripts/archive/installers/$SELF_BASE"
fi

# Known loose installers/hotfix installers from the Phase 39/40 sequence.
archive_and_remove_if_untracked "qrds_phase40_hotfix_package_bridge.sh"
archive_and_remove_if_untracked "qrds_phase40_hotfix_repo_hygiene_untracked_script_cleanup.sh"
archive_and_remove_if_untracked "qrds_phase39_hotfix_full_suite_cwd_fixture_path_bridge.sh"
archive_and_remove_if_untracked "qrds_sprint_40A_to_40R_portal_visual_qa_accessibility_link_audit_pack.sh"
archive_and_remove_if_untracked "qrds_sprint_39A_to_39R_interpretation_readiness_information_architecture_pack.sh"

# Root serve/verify wrappers are intentionally useful UX entrypoints. Track them if present.
for rel in \
  "qrds_phase39_portal_serve.sh" \
  "qrds_phase40_portal_serve.sh" \
  "qrds_phase40_verify.sh" \
  "qrds_phase40_hotfix_verify_package_bridge.sh" \
  "crypto_decision_lab/qrds_phase39_portal_serve.sh" \
  "crypto_decision_lab/qrds_phase40_portal_serve.sh" \
  "crypto_decision_lab/qrds_phase40_verify.sh" \
  "crypto_decision_lab/qrds_phase40_hotfix_verify_package_bridge.sh"; do
  if [[ -e "$ROOT_DIR/$rel" ]]; then
    git add "$rel"
    printf '[QRDS][Phase40 hygiene] Tracking wrapper if changed: %s\n' "$rel"
  fi
done

# Record status without changing any decision/edge flags.
python - <<'PY'
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

project = Path('/workspaces/QRDS/crypto_decision_lab')
status_dir = project / 'artifacts' / 'phase40_hotfix_repo_hygiene_untracked_script_cleanup'
status_dir.mkdir(parents=True, exist_ok=True)
status = {
    'gate': 'PHASE40_HOTFIX_REPO_HYGIENE_UNTRACKED_SCRIPT_CLEANUP_READY_RESEARCH_ONLY',
    'phase': 40,
    'hotfix': True,
    'purpose': 'Clean and track safe root script wrappers/installers after Phase 40 package bridge.',
    'app_mode': 'INTERACTIVE_RESEARCH_ONLY',
    'policy_lock': 'ACTIVE',
    'operational_status': 'BLOCKED_RESEARCH_ONLY',
    'edge_validated': False,
    'edge_operationally_validated': False,
    'shadow_decision_allowed': False,
    'decision_layer_allowed': False,
    'trading_signal_generated': False,
    'recommendation_generated': False,
    'allocation_generated': False,
    'operational_decision_allowed': False,
    'safe_apply_allowed': False,
    'promotion_allowed': False,
    'canonical_data_writes': 0,
    'created_at_utc': datetime.now(timezone.utc).isoformat(),
}
(status_dir / 'phase40_hotfix_repo_hygiene_status.json').write_text(json.dumps(status, indent=2, sort_keys=True), encoding='utf-8')
(status_dir / 'phase40_hotfix_repo_hygiene_summary.md').write_text(
    '# QRDS Phase 40 Hotfix • Repo Hygiene / Untracked Script Cleanup\n\n'
    'Gate: `PHASE40_HOTFIX_REPO_HYGIENE_UNTRACKED_SCRIPT_CLEANUP_READY_RESEARCH_ONLY`\n\n'
    '- Technical cleanup only.\n'
    '- Tracks serve/verify wrappers when present.\n'
    '- Archives loose installers under `crypto_decision_lab/scripts/archive/installers/`.\n'
    '- Does not create trading signals, recommendations, allocations, shadow decisions, safe-apply, or operational decisions.\n'
    '- `canonical_data_writes: 0`.\n',
    encoding='utf-8',
)
PY

git add "crypto_decision_lab/artifacts/phase40_hotfix_repo_hygiene_untracked_script_cleanup" || true

cat > "qrds_phase40_hotfix_repo_hygiene_verify.sh" <<'VERIFY'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
echo "[QRDS][Phase40 hygiene verify] Running focused Phase 40 tests..."
python -m pytest tests/unit/test_phase40_portal_visual_qa_accessibility_link_audit.py
echo "[QRDS][Phase40 hygiene verify] Running full suite..."
python -m pytest
cd "$ROOT_DIR"
if git status --porcelain | grep -E '^\?\? qrds_phase(39|40).*\.sh$' >/tmp/qrds_phase40_hygiene_untracked.txt; then
  echo "[QRDS][Phase40 hygiene verify][NEEDS_REVIEW] Root QRDS scripts still untracked:"
  cat /tmp/qrds_phase40_hygiene_untracked.txt
  exit 3
fi
echo "PHASE40_HOTFIX_REPO_HYGIENE_UNTRACKED_SCRIPT_CLEANUP_READY_RESEARCH_ONLY"
echo "Operational: BLOCKED_RESEARCH_ONLY"
echo "Edge: False"
echo "canonical_data_writes: 0"
VERIFY
chmod +x "qrds_phase40_hotfix_repo_hygiene_verify.sh"
git add "qrds_phase40_hotfix_repo_hygiene_verify.sh"

# Archive this newly created verifier too for reproducibility, but keep root copy as UX wrapper.
cp -f "qrds_phase40_hotfix_repo_hygiene_verify.sh" "$ARCHIVE_DIR/qrds_phase40_hotfix_repo_hygiene_verify.sh"
chmod +x "$ARCHIVE_DIR/qrds_phase40_hotfix_repo_hygiene_verify.sh" || true
git add "crypto_decision_lab/scripts/archive/installers/qrds_phase40_hotfix_repo_hygiene_verify.sh"

{
  echo ""
  echo "## Phase 40 Hotfix — Repo Hygiene / Untracked Script Cleanup"
  echo ""
  echo "Gate: \`$GATE\`"
  echo ""
  echo "- Scope: technical repository hygiene after Phase 40 package bridge."
  echo "- Loose root installers archived under \`crypto_decision_lab/scripts/archive/installers/\`."
  echo "- Root serve/verify wrappers tracked when present."
  echo "- Operational status remains \`BLOCKED_RESEARCH_ONLY\`."
  echo "- Edge remains \`False\`."
  echo "- canonical_data_writes: \`0\`."
} >> "$REPORT"
git add "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"

cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
printf '[QRDS][Phase40 hygiene] Running focused Phase 40 tests...\n'
python -m pytest tests/unit/test_phase40_portal_visual_qa_accessibility_link_audit.py
printf '[QRDS][Phase40 hygiene] Running full suite...\n'
python -m pytest

cd "$ROOT_DIR"
# Final check specifically for root QRDS scripts from this sequence.
if git status --porcelain | grep -E '^\?\? qrds_phase(39|40).*\.sh$' > "$STATUS_DIR/untracked_root_qrds_scripts_after_cleanup.txt"; then
  echo "[QRDS][Phase40 hygiene][NEEDS_REVIEW] Root QRDS scripts still untracked:"
  cat "$STATUS_DIR/untracked_root_qrds_scripts_after_cleanup.txt"
  git add "crypto_decision_lab/artifacts/phase40_hotfix_repo_hygiene_untracked_script_cleanup/untracked_root_qrds_scripts_after_cleanup.txt"
  echo "$NEEDS_REVIEW_GATE"
  echo "Operational: BLOCKED_RESEARCH_ONLY"
  echo "Edge: False"
  echo "canonical_data_writes: 0"
  exit 3
fi
: > "$STATUS_DIR/untracked_root_qrds_scripts_after_cleanup.txt"
git add "crypto_decision_lab/artifacts/phase40_hotfix_repo_hygiene_untracked_script_cleanup/untracked_root_qrds_scripts_after_cleanup.txt"

if git diff --cached --quiet; then
  echo "[QRDS][Phase40 hygiene] No tracked changes to commit."
else
  git commit -m "Phase 40 hotfix: repo hygiene for root wrappers"
  git push
fi

echo ""
echo "QRDS Phase 40 Hotfix • Repo Hygiene / Untracked Script Cleanup"
echo "$GATE"
echo "Operational: BLOCKED_RESEARCH_ONLY"
echo "Edge: False"
echo "canonical_data_writes: 0"
echo "Focused tests: PASS"
echo "Full suite: PASS"
echo "Root QRDS script hygiene: PASS"
