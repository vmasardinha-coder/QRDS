from pathlib import Path
import socket
import subprocess
import time
import urllib.request


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_qrds_portal_serve_wrapper_30c_starts_server(tmp_path: Path) -> None:
    port = _free_port()
    out = tmp_path / "portal"
    proc = subprocess.Popen(
        ["bash", "qrds_portal_serve.sh", "--output-dir", str(out), "--port", str(port), "--bind", "127.0.0.1", "--no-build"],
        cwd=Path(__file__).resolve().parents[2],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.time() + 8
        body = ""
        while time.time() < deadline:
            if proc.poll() is not None:
                stdout, stderr = proc.communicate(timeout=1)
                raise AssertionError(f"server exited early rc={proc.returncode}\nstdout={stdout}\nstderr={stderr}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as resp:
                    body = resp.read().decode("utf-8")
                    break
            except Exception:
                time.sleep(0.2)
        assert proc.poll() is None
        assert "QRDS" in body
        assert (out / "index.html").exists()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
