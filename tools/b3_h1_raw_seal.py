#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = "https://arquivos.b3.com.br/rapinegocios/tickercsv/{date}"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    url = URL.format(date=a.date)
    rec = {
        "schema": "gate_btc.b3.h1.raw_source_seal.v1",
        "date": a.date,
        "url": url,
        "research_only": True,
        "shadow_only": True,
        "orders": 0,
        "real_capital": 0,
        "economics_locked": True,
        "contract_interpretation_performed": False,
        "structural_qa_performed": False,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    try:
        r = requests.get(url, timeout=120, headers={"User-Agent": UA, "Accept": "*/*"})
        rec["http_status"] = r.status_code
        rec["content_type"] = r.headers.get("content-type", "")
        rec["bytes"] = len(r.content)
        rec["zip_signature_ok"] = r.content[:2] == b"PK"
        if r.status_code == 200 and rec["zip_signature_ok"]:
            raw = out / f"{a.date}_NEGOCIOSAVISTA_original.zip"
            raw.write_bytes(r.content)
            rec["sha256"] = hashlib.sha256(r.content).hexdigest()
            rec["raw_file"] = raw.name
            rec["status"] = "PASS_RAW_SEALED_NO_INTERPRETATION"
            code = 0
        else:
            err = out / f"{a.date}_response.bin"
            err.write_bytes(r.content[:2_000_000])
            rec["status"] = "FAIL_SOURCE_NOT_ZIP"
            code = 2
    except Exception as e:
        rec["status"] = "FAIL_SOURCE_EXCEPTION"
        rec["error"] = repr(e)
        code = 2

    (out / "RAW_SOURCE_SEAL.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(rec, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
