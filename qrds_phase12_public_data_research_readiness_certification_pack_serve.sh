#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase12_public_data_research_readiness_certification_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
echo "[QRDS 12S-12Z] Building Phase 12 Public Data Research Readiness Certification Pack..."
bash "$ROOT/qrds_phase12_public_data_research_readiness_certification_pack.sh" "$OUT"
PORT="$(python - <<'PY'
import socket
for port in range(8151, 8200):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port); break
else: raise SystemExit("NO_FREE_PORT")
PY
)"
echo
echo "[QRDS 12S-12Z] Phase 12 Public Data Research Readiness Certification Pack ready."
echo "[QRDS 12S-12Z] Serve directory: $OUT"
echo "[QRDS 12S-12Z] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
