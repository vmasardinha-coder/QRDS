#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[QRDS PUBLIC DATA] Fetching public market OHLCV into manual inbox..."
bash "$ROOT/qrds_phase12_public_market_data_fetch_pack.sh"
echo "[QRDS PUBLIC DATA] Refreshing acceptance pipeline..."
bash "$ROOT/qrds_phase11_offline_source_normalizer_pack.sh"
bash "$ROOT/qrds_phase10_offline_sample_intake_promotion_pack.sh"
bash "$ROOT/qrds_phase10_sample_quality_promotion_gate_pack.sh"
bash "$ROOT/qrds_phase10_depth_expansion_readiness_pack.sh"
bash "$ROOT/qrds_phase11_canonical_promotion_dry_run_lock_pack.sh"
bash "$ROOT/qrds_phase11_data_drop_acceptance_pipeline_pack.sh"
echo "[QRDS PUBLIC DATA] Refreshing public fetch status from existing files..."
python -m crypto_decision_lab.cli.phase12_public_market_data_fetch_pack --output-dir "$ROOT/crypto_decision_lab/artifacts/phase12_public_market_data_fetch_pack" --repo-root "$ROOT" --symbols "${QRDS_PUBLIC_SYMBOLS:-BTCUSDT,ETHUSDT,SOLUSDT}" --interval "${QRDS_PUBLIC_INTERVAL:-1h}" --rows-per-symbol "${QRDS_PUBLIC_ROWS_PER_SYMBOL:-5000}" --no-fetch
