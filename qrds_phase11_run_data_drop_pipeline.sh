#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[QRDS DATA DROP] Refreshing normalizer + validation chain..."
bash "$ROOT/qrds_phase11_offline_source_normalizer_pack.sh" || true
bash "$ROOT/qrds_phase10_offline_sample_intake_promotion_pack.sh" || true
bash "$ROOT/qrds_phase10_sample_quality_promotion_gate_pack.sh" || true
bash "$ROOT/qrds_phase10_depth_expansion_readiness_pack.sh" || true
bash "$ROOT/qrds_phase11_canonical_promotion_dry_run_lock_pack.sh" || true
bash "$ROOT/qrds_phase11_data_drop_acceptance_pipeline_pack.sh"
