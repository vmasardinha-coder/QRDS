#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_RETUNE": True,
    "NO_BACKFILL": True,
    "NO_COUNTER_RESET": True,
    "FAIL_CLOSED": True,
    "H1_ECONOMICS_READ": False,
}

DATES = ["2020-01-02", "2021-01-04", "2022-01-03", "2023-01-02"]


def yymmdd(iso: str) -> str:
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%y%m%d")


def fetch(url: str) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 QRDS research-only source QA"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return int(r.status), dict(r.headers.items()), r.read()
    except urllib.error.HTTPError as e:
        return int(e.code), dict(e.headers.items()), e.read()


def inspect_zip(raw: bytes) -> dict:
    out = {"zip_valid": False, "members": [], "contains_bvbg086": False, "contains_win": False, "contains_wdo": False}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = z.namelist()
            out["zip_valid"] = True
            out["members"] = names
            out["contains_bvbg086"] = any("BVBG.086" in n.upper() for n in names)
            for n in names:
                if n.endswith("/"):
                    continue
                b = z.read(n)
                if b"WIN" in b:
                    out["contains_win"] = True
                if b"WDO" in b:
                    out["contains_wdo"] = True
                if out["contains_win"] and out["contains_wdo"]:
                    break
    except zipfile.BadZipFile:
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rows = []
    for iso in DATES:
        url = f"https://www.b3.com.br/pesquisapregao/download?filelist=PR{yymmdd(iso)}.zip"
        status, headers, raw = fetch(url)
        z = inspect_zip(raw)
        rows.append({
            "date": iso,
            "url": url,
            "http_status": status,
            "content_type": headers.get("Content-Type") or headers.get("content-type"),
            "content_disposition": headers.get("Content-Disposition") or headers.get("content-disposition"),
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            **z,
        })
    qualified = [r for r in rows if r["http_status"] == 200 and r["zip_valid"] and r["contains_bvbg086"] and r["contains_win"] and r["contains_wdo"]]
    result = {
        "schema": "qrds.factory.b3_win_wdo_official_source_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "frontier": "WIN_UNIVARIATE_WDO_UNIVARIATE",
        "stage": "DATA_SOURCE_QUALIFICATION_PROBE",
        "official_surface": "B3 Pesquisa por pregao / BVBG.086.01 PriceReport",
        "candidate_contract": "https://www.b3.com.br/pesquisapregao/download?filelist=PR{YYMMDD}.zip",
        "sentinels": rows,
        "sentinel_pass_count": len(qualified),
        "source_admission_pass": len(qualified) == len(rows),
        "economics_read_allowed": False,
        "family_creation_allowed": False,
        "prospective_credit": 0,
        "scientific_credit": 0,
        "safety": SAFETY,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"sentinel_pass_count": len(qualified), "total": len(rows), "source_admission_pass": result["source_admission_pass"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
