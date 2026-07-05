#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${QRDS_ROOT:-$(pwd)}"
if [[ "$(basename "$ROOT")" == "crypto_decision_lab" ]]; then ROOT="$(cd "$ROOT/.." && pwd)"; else ROOT="$(cd "$ROOT" && pwd)"; fi
PROJECT="$ROOT/crypto_decision_lab"
GENERATOR="$PROJECT/scripts/phase38_modern_research_portal_layout_ux_polish.py"
OUT="$ROOT/artifacts/phase38_modern_research_portal_layout_ux_polish"
PORT=""
BIND="0.0.0.0"
HOST="127.0.0.1"
PHASE37_DIR=""
NO_BUILD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir|--out) OUT="$2"; shift 2 ;;
    --portal-dir|--phase37-dir) PHASE37_DIR="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --bind) BIND="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --no-build|--skip-build) NO_BUILD=1; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ "$OUT" != /* ]]; then OUT="$ROOT/$OUT"; fi
mkdir -p "$OUT"

if [[ "$NO_BUILD" -eq 0 ]]; then
  if [[ ! -f "$GENERATOR" ]]; then
    echo "ERROR: generator not found: $GENERATOR" >&2
    exit 2
  fi
  GEN_ARGS=(--root "$ROOT" --output-dir "$OUT")
  if [[ -n "$PHASE37_DIR" ]]; then GEN_ARGS+=(--phase37-dir "$PHASE37_DIR"); fi
  python3 "$GENERATOR" "${GEN_ARGS[@]}"
fi

if [[ ! -f "$OUT/index.html" ]]; then
  cat > "$OUT/index.html" <<'HTML'
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>QRDS Phase 38</title></head><body><h1>QRDS Phase 38</h1><p>index.html fallback criado pelo serve wrapper. Execute sem --no-build para regenerar o portal.</p></body></html>
HTML
fi

if [[ -z "$PORT" ]]; then
  PORT="$(python3 - <<'PY'
import socket
for port in range(8700, 8801):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            print(port)
            raise SystemExit(0)
        except OSError:
            pass
raise SystemExit("No free port found in 8700-8800")
PY
)"
fi

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
out = Path("$OUT")
plan = {
  "phase": 38,
  "title": "QRDS Phase 38 Modern Research Portal Layout / UX Polish",
  "output_dir": str(out),
  "bind": "$BIND",
  "host": "$HOST",
  "port": int("$PORT"),
  "local_url": "http://$HOST:$PORT/index.html",
  "codespaces_instruction": "Abra a aba Ports do Codespaces, localize a porta $PORT, defina como Public/Private conforme sua preferência e clique em Open in Browser.",
  "app_mode": "INTERACTIVE_RESEARCH_ONLY",
  "policy_lock": "ACTIVE",
  "operational_status": "BLOCKED_RESEARCH_ONLY",
  "edge_validated": False,
  "shadow_decision_allowed": False,
  "decision_layer_allowed": False,
  "trading_signal_generated": False,
  "recommendation_generated": False,
  "allocation_generated": False,
  "canonical_data_writes": 0,
  "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
}
(out / "dashboard_serve_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

echo ""
echo "QRDS Phase 38 portal pronto para servir."
echo "URL local: http://$HOST:$PORT/index.html"
echo "Codespaces: abra a aba Ports, localize a porta $PORT e clique em Open in Browser."
echo "Serve plan: $OUT/dashboard_serve_plan.json"
echo ""
cd "$OUT"
python3 -m http.server "$PORT" --bind "$BIND"
