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
PRICE_TAGS = [b"TckrSymb", b"FrstPric", b"MinPric", b"MaxPric", b"LastPric"]


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
    out = {
        "zip_valid": False,
        "members": [],
        "leaf_payloads": [],
        "contains_pricereport_schema": False,
        "contains_win": False,
        "contains_wdo": False,
    }

    def walk(blob: bytes, prefix: str, depth: int) -> None:
        if depth > 3:
            return
        try:
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                out["zip_valid"] = True
                for n in z.namelist():
                    if n.endswith("/"):
                        continue
                    b = z.read(n)
                    full = f"{prefix}{n}"
                    out["members"].append(full)
                    try:
                        with zipfile.ZipFile(io.BytesIO(b)):
                            walk(b, full + "::", depth + 1)
                            continue
                    except zipfile.BadZipFile:
                        pass
                    out["leaf_payloads"].append({"path": full, "byte_count": len(b), "sha256": hashlib.sha256(b).hexdigest()})
                    if all(tag in b for tag in PRICE_TAGS):
                        out["contains_pricereport_schema"] = True
                    if b"WIN" in b:
                        out["contains_win"] = True
                    if b"WDO" in b:
                        out["contains_wdo"] = True
        except zipfile.BadZipFile:
            return

    walk(raw, "", 0)
    out["leaf_payload_count"] = len(out["leaf_payloads"])
    out["leaf_payload_sha256"] = sorted(x["sha256"] for x in out["leaf_payloads"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rows = []
    for iso in DATES:
        url = f"https://www.b3.com.br/pesquisapregao/download?filelist=PR{yymmdd(iso)}.zip"
        status1, headers1, raw1 = fetch(url)
        z1 = inspect_zip(raw1)
        status2, _headers2, raw2 = fetch(url)
        z2 = inspect_zip(raw2)
        repeat_match = z1["leaf_payload_sha256"] == z2["leaf_payload_sha256"] and bool(z1["leaf_payload_sha256"])
        rows.append({
            "date": iso,
            "url": url,
            "http_status": status1,
            "repeat_http_status": status2,
            "content_type": headers1.get("Content-Type") or headers1.get("content-type"),
            "content_disposition": headers1.get("Content-Disposition") or headers1.get("content-disposition"),
            "outer_byte_count": len(raw1),
            "outer_sha256": hashlib.sha256(raw1).hexdigest(),
            "repeat_outer_sha256": hashlib.sha256(raw2).hexdigest(),
            "repeat_payload_digest_match": repeat_match,
            **z1,
        })
    qualified = [
        r for r in rows
        if r["http_status"] == 200
        and r["repeat_http_status"] == 200
        and r["zip_valid"]
        and r["leaf_payload_count"] > 0
        and r["contains_pricereport_schema"]
        and r["contains_win"]
        and r["contains_wdo"]
        and r["repeat_payload_digest_match"]
    ]
    sentinel_contract_pass = len(qualified) == len(rows)
    result = {
        "schema": "qrds.factory.b3_win_wdo_official_source_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "frontier": "WIN_UNIVARIATE_WDO_UNIVARIATE",
        "stage": "DATA_SOURCE_QUALIFICATION_PROBE",
        "official_surface": "B3 Pesquisa por pregao / BVBG.086.01 PriceReport",
        "candidate_contract": "https://www.b3.com.br/pesquisapregao/download?filelist=PR{YYMMDD}.zip",
        "sentinels": rows,
        "sentinel_pass_count": len(qualified),
        "sentinel_contract_pass": sentinel_contract_pass,
        "source_admission_pass": False,
        "source_admission_blocker": "FULL_2020_2024_COVERAGE_MISSINGNESS_DEDUPE_IDENTITY_AND_PUBLICATION_TIMING_QA_NOT_YET_FROZEN",
        "next_action": "QUALIFY_COVERAGE_INCREMENTALLY_BY_YEAR_WITHOUT_ECONOMICS",
        "economics_read_allowed": False,
        "family_creation_allowed": False,
        "prospective_credit": 0,
        "scientific_credit": 0,
        "safety": SAFETY,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"sentinel_pass_count": len(qualified), "total": len(rows), "sentinel_contract_pass": sentinel_contract_pass, "source_admission_pass": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
