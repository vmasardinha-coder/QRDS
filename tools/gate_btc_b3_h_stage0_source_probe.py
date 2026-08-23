#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import requests

DATES = ["2025-01-03", "2025-12-12", "2026-03-30", "2026-08-07"]
BASES = [
    ("DRP_CURRENT_TICKER_API", "https://drp.b3.com.br/rapinegocios/tickercsv/{date}"),
    ("ARQUIVOS_LEGACY_ROUTE", "https://arquivos.b3.com.br/rapinegocios/tickercsv/{date}"),
]
OUT = Path("artifacts/b3_h_nextgen/B3_H_STAGE0_SOURCE_PROBE.json")


def probe(url: str) -> dict:
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 GATE-BTC-B3-H-Stage0/1.0", "Accept": "*/*"})
    try:
        with s.get(url, timeout=60, stream=True, allow_redirects=True) as r:
            prefix = b""
            if r.status_code == 200:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        prefix = chunk[:32]
                        break
            return {
                "url": url,
                "final_url": r.url,
                "status": r.status_code,
                "content_type": r.headers.get("content-type"),
                "content_length": r.headers.get("content-length"),
                "content_disposition": r.headers.get("content-disposition"),
                "prefix_hex": prefix.hex(),
                "zip_prefix": prefix[:2] == b"PK",
            }
    except Exception as exc:
        return {"url": url, "error": repr(exc), "status": None, "zip_prefix": False}


def main() -> int:
    rows = []
    for d in DATES:
        for source, template in BASES:
            row = probe(template.format(date=d))
            row.update({"date": d, "source": source})
            rows.append(row)
    payload = {
        "schema": "gate_btc.b3.h_nextgen.stage0_source_probe.v1",
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders": 0,
        "real_capital": 0,
        "h1_economics_read": False,
        "dates_all_pre_h1_cutoff": True,
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
