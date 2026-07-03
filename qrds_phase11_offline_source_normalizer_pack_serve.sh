#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase11_offline_source_normalizer_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
echo "[QRDS 11I-11P] Building Phase 11 Offline Source Normalizer Pack..."
bash "$ROOT/qrds_phase11_offline_source_normalizer_pack.sh" "$OUT"
PORT="$(python - <<'PY'
import socket
for port in range(8147, 8200):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port); break
else: raise SystemExit("NO_FREE_PORT")
PY
)"
echo; echo "[QRDS 11I-11P] Phase 11 Offline Source Normalizer Pack ready."
echo "[QRDS 11I-11P] Serve directory: $OUT"; echo "[QRDS 11I-11P] Port: $PORT"
echo; echo "Codespaces:"; echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo; echo "Stop server with Ctrl+C."
cd "$OUT"; python -m http.server "$PORT" --bind 0.0.0.0
