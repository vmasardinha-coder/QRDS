#!/usr/bin/env bash
set -euo pipefail

PHASE="phase40_hotfix_repo_hygiene_untracked_script_cleanup"
READY_GATE="PHASE40_HOTFIX_REPO_HYGIENE_UNTRACKED_SCRIPT_CLEANUP_READY_RESEARCH_ONLY"
NEEDS_REVIEW_GATE="PHASE40_HOTFIX_REPO_HYGIENE_UNTRACKED_SCRIPT_CLEANUP_NEEDS_REVIEW_RESEARCH_ONLY"
OPERATIONAL_STATUS="BLOCKED_RESEARCH_ONLY"
EDGE_VALIDATED="False"
CANONICAL_DATA_WRITES="0"

log() { printf '[QRDS][Phase40-Hygiene] %s\n' "$*"; }

fail_review() {
  local reason="$1"
  log "NEEDS_REVIEW: ${reason}"
  mkdir -p "${PROJECT_DIR:-crypto_decision_lab}/artifacts/${PHASE}" || true
  cat > "${PROJECT_DIR:-crypto_decision_lab}/artifacts/${PHASE}/hotfix_status.json" <<JSON || true
{
  "gate": "${NEEDS_REVIEW_GATE}",
  "ready": false,
  "reason": "${reason}",
  "operational_status": "${OPERATIONAL_STATUS}",
  "edge_validated": false,
  "canonical_data_writes": 0,
  "app_mode": "INTERACTIVE_RESEARCH_ONLY",
  "policy_lock": "ACTIVE",
  "shadow_decision_allowed": false,
  "decision_layer_allowed": false,
  "trading_signal_generated": false,
  "recommendation_generated": false,
  "allocation_generated": false,
  "safe_apply_allowed": false,
  "promotion_allowed": false
}
JSON
  printf '\nQRDS Phase 40 Hotfix • Repo Hygiene\n%s\nOperational: %s\nEdge: %s\ncanonical_data_writes: %s\nReason: %s\n' \
    "${NEEDS_REVIEW_GATE}" "${OPERATIONAL_STATUS}" "${EDGE_VALIDATED}" "${CANONICAL_DATA_WRITES}" "${reason}"
  exit 2
}

if git rev-parse --show-toplevel >/dev/null 2>&1; then
  REPO_ROOT="$(git rev-parse --show-toplevel)"
elif [[ -d "/workspaces/QRDS/.git" ]]; then
  REPO_ROOT="/workspaces/QRDS"
else
  fail_review "Git repository root not found. Run from /workspaces/QRDS or inside the QRDS repository."
fi

cd "${REPO_ROOT}"

PROJECT_DIR="crypto_decision_lab"
[[ -d "${PROJECT_DIR}" ]] || fail_review "Missing ${PROJECT_DIR} directory."
[[ -d "${PROJECT_DIR}/tests" ]] || fail_review "Missing ${PROJECT_DIR}/tests directory."

ARCHIVE_DIR="${PROJECT_DIR}/scripts/archive/installers"
ARTIFACT_DIR="${PROJECT_DIR}/artifacts/${PHASE}"
STATUS_FILE="${ARTIFACT_DIR}/hotfix_status.json"
REPORT_FILE="${PROJECT_DIR}/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"

mkdir -p "${ARCHIVE_DIR}" "${ARTIFACT_DIR}" "$(dirname "${REPORT_FILE}")"

log "Repository: ${REPO_ROOT}"
log "Archiving installer-style scripts and tracking useful wrappers."

installer_scripts=(
  "qrds_phase40_hotfix_package_bridge.sh"
  "qrds_phase40_hotfix_repo_hygiene_untracked_script_cleanup.sh"
)

for script in "${installer_scripts[@]}"; do
  if [[ -f "${script}" ]]; then
    cp -f "${script}" "${ARCHIVE_DIR}/${script}"
    chmod +x "${ARCHIVE_DIR}/${script}" || true
  fi
done

wrapper_scripts=(
  "qrds_phase39_portal_serve.sh"
  "qrds_phase40_portal_serve.sh"
  "qrds_phase40_verify.sh"
  "qrds_phase40_hotfix_verify_package_bridge.sh"
)

for script in "${wrapper_scripts[@]}"; do
  if [[ -f "${script}" ]]; then
    chmod +x "${script}" || true
    git add "${script}"
  fi
done

for script in "${installer_scripts[@]}"; do
  if [[ -f "${script}" ]]; then
    rm -f "${script}"
  fi
done

git add "${ARCHIVE_DIR}" || true
[[ -L data || -d data ]] && git add data || true
[[ -L docs || -d docs ]] && git add docs || true

cat > "${STATUS_FILE}" <<JSON
{
  "gate": "${READY_GATE}",
  "ready": true,
  "scope": "repo_hygiene_untracked_script_cleanup",
  "app_mode": "INTERACTIVE_RESEARCH_ONLY",
  "policy_lock": "ACTIVE",
  "operational_status": "${OPERATIONAL_STATUS}",
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
  "canonical_data_writes": 0
}
JSON

git add "${STATUS_FILE}"

cat >> "${REPORT_FILE}" <<MD

## Phase 40 Hotfix — Repo Hygiene / Untracked Script Cleanup

Gate: \`${READY_GATE}\`  
Operational: \`${OPERATIONAL_STATUS}\`  
Edge validated: \`False\`  
canonical_data_writes: \`0\`  
Scope: technical cleanup only. Installer-style hotfix scripts are archived under \`${ARCHIVE_DIR}\`; useful serve/verify wrappers are tracked when present. No signal, recommendation, allocation, shadow decision, safe-apply, promotion, canonical write, or operational decision was created.
MD

git add "${REPORT_FILE}"

cd "${PROJECT_DIR}"
export PYTHONPATH="${PWD}/src:${PYTHONPATH:-}"

FOCUSED_TEST="tests/unit/test_phase40_portal_visual_qa_accessibility_link_audit.py"
[[ -f "${FOCUSED_TEST}" ]] || fail_review "Focused Phase 40 test not found: ${PROJECT_DIR}/${FOCUSED_TEST}"

log "Running focused tests..."
python -m pytest "${FOCUSED_TEST}" -q
log "Focused tests: PASS"

log "Running full suite..."
python -m pytest -q
log "Full suite: PASS"

cd "${REPO_ROOT}"

untracked_qrds_scripts="$(git status --short --untracked-files=all | awk '$1 == "??" && $2 ~ /^qrds_phase(39|40).*\.sh$/ {print $2}' || true)"
if [[ -n "${untracked_qrds_scripts}" ]]; then
  printf '%s\n' "${untracked_qrds_scripts}" > "${ARTIFACT_DIR}/remaining_untracked_qrds_scripts.txt"
  git add "${ARTIFACT_DIR}/remaining_untracked_qrds_scripts.txt"
  fail_review "Root still has untracked QRDS phase39/phase40 shell scripts: ${untracked_qrds_scripts}"
fi

git status --short > "${ARTIFACT_DIR}/git_status_after_cleanup.txt"
git add "${ARTIFACT_DIR}/git_status_after_cleanup.txt"

if ! git diff --cached --quiet; then
  git commit -m "Phase 40 hotfix: repo hygiene for untracked QRDS scripts"
  git push
else
  log "No staged changes to commit."
fi

printf '\nQRDS Phase 40 Hotfix • Repo Hygiene / Untracked Script Cleanup\n%s\nOperational: %s\nEdge: %s\ncanonical_data_writes: %s\nFocused tests: PASS\nFull suite: PASS\n' \
  "${READY_GATE}" "${OPERATIONAL_STATUS}" "${EDGE_VALIDATED}" "${CANONICAL_DATA_WRITES}"
