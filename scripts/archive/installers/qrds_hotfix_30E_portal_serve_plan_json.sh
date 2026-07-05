#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then
  ROOT="/workspaces/QRDS"
fi

PROJECT="$ROOT/crypto_decision_lab"
SRC="$PROJECT/src"
OUT="$PROJECT/artifacts/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack"

export PYTHONPATH="$SRC:${PYTHONPATH:-}"

echo "[QRDS 30E HOTFIX] Installing portal serve wrapper with dashboard_serve_plan.json support..."

cat > "$ROOT/qrds_portal_serve.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -d "$SCRIPT_DIR/crypto_decision_lab" ]; then
  ROOT="$SCRIPT_DIR"
  PROJECT="$ROOT/crypto_decision_lab"
elif [ "$(basename "$SCRIPT_DIR")" = "crypto_decision_lab" ] && [ -d "$SCRIPT_DIR/src" ]; then
  PROJECT="$SCRIPT_DIR"
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  ROOT="$SCRIPT_DIR"
  PROJECT="$ROOT/crypto_decision_lab"
fi

OUTPUT_DIR="$PROJECT/artifacts/dashboard_portal/portal"
PORT=""
BIND_HOST="0.0.0.0"
BUILD_PORTAL="1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir|--out|--portal-dir)
      OUTPUT_DIR="${2:?missing value for $1}"
      shift 2
      ;;
    --port)
      PORT="${2:?missing value for --port}"
      shift 2
      ;;
    --bind|--host)
      BIND_HOST="${2:?missing value for $1}"
      shift 2
      ;;
    --no-build|--skip-build)
      BUILD_PORTAL="0"
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: bash qrds_portal_serve.sh [--output-dir DIR] [--port PORT] [--bind HOST] [--no-build]

Starts a local static HTTP server for the QRDS research portal.
Creates dashboard_serve_plan.json in the served directory.
If DIR does not contain an index.html, a small safe placeholder is created.
EOF
      exit 0
      ;;
    --*)
      echo "[QRDS PORTAL SERVE] Ignoring unsupported compatibility option: $1" >&2
      if [[ $# -ge 2 && "${2:-}" != --* ]]; then
        shift 2
      else
        shift
      fi
      ;;
    *)
      echo "[QRDS PORTAL SERVE] Ignoring positional compatibility argument: $1" >&2
      shift
      ;;
  esac
done

mkdir -p "$OUTPUT_DIR"

if [ "$BUILD_PORTAL" = "1" ]; then
  if [ -x "$ROOT/qrds_portal_build.sh" ]; then
    bash "$ROOT/qrds_portal_build.sh" --output-dir "$OUTPUT_DIR" || true
  elif [ -x "$ROOT/qrds_dashboard_portal_build.sh" ]; then
    bash "$ROOT/qrds_dashboard_portal_build.sh" --output-dir "$OUTPUT_DIR" || true
  elif [ -x "$PROJECT/qrds_portal_build.sh" ]; then
    bash "$PROJECT/qrds_portal_build.sh" --output-dir "$OUTPUT_DIR" || true
  elif [ -x "$PROJECT/qrds_dashboard_portal_build.sh" ]; then
    bash "$PROJECT/qrds_dashboard_portal_build.sh" --output-dir "$OUTPUT_DIR" || true
  fi
fi

if [ ! -f "$OUTPUT_DIR/index.html" ]; then
  cat > "$OUTPUT_DIR/index.html" <<'EOF'
<!doctype html>
<html>
<head><meta charset="utf-8"><title>QRDS Research Portal</title></head>
<body>
<h1>QRDS/QOS Research Portal</h1>
<p>Research-only static portal server is running.</p>
<p>No trading signals, recommendations, allocations, or operational decisions.</p>
</body>
</html>
EOF
fi

if [ -z "$PORT" ]; then
  PORT="$(python - <<'PY'
import socket
for port in range(8150, 8200):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit("NO_FREE_PORT")
PY
)"
fi

python - "$OUTPUT_DIR" "$PORT" "$BIND_HOST" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

out = Path(sys.argv[1])
port = int(sys.argv[2])
bind_host = sys.argv[3]
plan = {
    "schema": "qrds.dashboard_portal_serve_plan.v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "serve_directory": str(out),
    "host": bind_host,
    "bind_host": bind_host,
    "port": port,
    "url": f"http://127.0.0.1:{port}/",
    "codespaces_instruction": f"Ports -> {port} -> Open in Browser / Open Preview",
    "entrypoint": "index.html",
    "index_path": str(out / "index.html"),
    "research_only": True,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}
(out / "dashboard_serve_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
PY

echo "[QRDS PORTAL SERVE] Directory: $OUTPUT_DIR"
echo "[QRDS PORTAL SERVE] Plan: $OUTPUT_DIR/dashboard_serve_plan.json"
echo "[QRDS PORTAL SERVE] Bind: $BIND_HOST"
echo "[QRDS PORTAL SERVE] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."

cd "$OUTPUT_DIR"
exec python -m http.server "$PORT" --bind "$BIND_HOST"
SH

chmod +x "$ROOT/qrds_portal_serve.sh"
cp "$ROOT/qrds_portal_serve.sh" "$PROJECT/qrds_portal_serve.sh"
chmod +x "$PROJECT/qrds_portal_serve.sh"

echo "[QRDS 30E HOTFIX] Adding regression test for dashboard_serve_plan.json..."
cat > "$PROJECT/tests/regression/test_portal_serve_plan_30e_hotfix.py" <<'PY'
import json
from pathlib import Path
import socket
import subprocess
import time
import urllib.request


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_portal_serve_writes_dashboard_serve_plan_json(tmp_path: Path) -> None:
    project = Path(__file__).resolve().parents[2]
    port = _free_port()
    out = tmp_path / "portal"
    proc = subprocess.Popen(
        ["bash", "qrds_portal_serve.sh", "--output-dir", str(out), "--port", str(port), "--host", "127.0.0.1", "--no-build"],
        cwd=project,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.time() + 8
        while time.time() < deadline:
            if proc.poll() is not None:
                stdout, stderr = proc.communicate(timeout=1)
                raise AssertionError(f"server exited early rc={proc.returncode}\nstdout={stdout}\nstderr={stderr}")
            if (out / "dashboard_serve_plan.json").exists():
                break
            time.sleep(0.2)

        assert proc.poll() is None
        assert (out / "index.html").exists()
        plan_path = out / "dashboard_serve_plan.json"
        assert plan_path.exists()
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        assert plan["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
        assert plan["policy_lock"] == "ACTIVE"
        assert plan["port"] == port
        assert plan["safe_apply_allowed"] is False
        assert plan["promotion_allowed"] is False
        assert plan["canonical_data_writes"] == 0

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/dashboard_serve_plan.json", timeout=2) as resp:
            served = json.loads(resp.read().decode("utf-8"))
        assert served["port"] == port
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
PY

echo "[QRDS 30E HOTFIX] Running portal serve targeted tests..."
cd "$PROJECT"
pytest -q \
  tests/integration/test_dashboard_portal_serve_cli.py::test_qrds_portal_serve_wrapper_starts_server \
  tests/regression/test_portal_serve_wrapper_30c_hotfix.py \
  tests/regression/test_portal_serve_wrapper_30d_dual_location.py \
  tests/regression/test_portal_serve_plan_30e_hotfix.py

echo "[QRDS 30E HOTFIX] Running Phase 30 targeted tests..."
pytest -q \
  tests/unit/test_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.py \
  tests/integration/test_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_cli.py \
  tests/regression/test_phase30_missing_inputs_needs_review.py \
  tests/regression/test_phase30_readiness_alias_override_hotfix.py

echo "[QRDS 30E HOTFIX] Running full test suite..."
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs

echo "[QRDS 30E HOTFIX] Regenerating Phase 30 report..."
cd "$ROOT"
bash "$ROOT/qrds_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.sh" "$OUT"

python - <<'PY'
import json
from pathlib import Path

p = Path("crypto_decision_lab/artifacts/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_index.json")
d = json.loads(p.read_text(encoding="utf-8"))

for k in [
    "gate_answer",
    "station",
    "no_edge_checkpoint_ready",
    "phase29_retest_ready",
    "data_nature",
    "stable_compressed_candidate_count",
    "edge_validated",
    "edge_operationally_validated",
    "risk_regime_dashboard_research_ready",
    "shadow_decision_allowed",
    "decision_layer_allowed",
    "next_research_path",
    "operational_status",
    "modeling_status",
    "safe_apply_allowed",
    "promotion_allowed",
    "canonical_data_writes",
    "git_status_line_count",
    "criteria_ready_count",
    "criteria_total_count",
    "mean_checkpoint_score",
    "policy_lock",
    "app_mode",
]:
    print(f"{k}: {d.get(k)}")

print("[QRDS 30E HOTFIX] Component readiness:")
for r in d.get("payload", {}).get("component_readiness", []):
    print(f"{r['component_id']}: present={r['index_present']} ready={r['ready']} ready_key={r['ready_key']} gate={r['gate_answer']}")
PY

echo "[QRDS 30E HOTFIX] Committing changes..."
git add -A
git commit -m "Hotfix portal serve plan JSON and regenerate Phase 30" || true
git push || true

echo "[QRDS 30E HOTFIX] Final status:"
git status --short
