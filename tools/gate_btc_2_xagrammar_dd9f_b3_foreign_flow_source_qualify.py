#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import re
import urllib.request
from datetime import date
from pathlib import Path

UA = "QRDS-GATE-BTC-2-Research/1.0"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def decode_html(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1", errors="replace")


def norm_text(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s.lower())
    return s.strip()


def extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    chunks=[]
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            chunks.append("")
    return "\n".join(chunks)


def parse_br_date(token: str) -> str | None:
    m=re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", token.strip())
    if not m:
        return None
    d,mn,y=map(int,m.groups())
    return date(y,mn,d).isoformat()


def analyze_bdi(text: str) -> dict:
    n=norm_text(text)
    cutoff=None
    patterns=[
        r"dados acumulados do inicio do mes ate o dia\s+(\d{2}/\d{2}/\d{4})",
        r"dados acumulados.*?ate o dia\s+(\d{2}/\d{2}/\d{4})",
    ]
    for pat in patterns:
        m=re.search(pat,n,re.I)
        if m:
            cutoff=parse_br_date(m.group(1))
            break

    foreign_row_present="investidor estrangeiro" in n
    # Require the table semantics to be present in the same physical document.
    purchase_header=bool(re.search(r"compras\s*\(r\$\)",n) or "compras (r$) mil" in n)
    sales_header=bool(re.search(r"vendas\s*\(r\$\)",n) or "vendas (r$) mil" in n)

    # Extract the first line-like slice after foreign investor. This is evidence only;
    # values are not used for any strategy/outcome selection.
    foreign_context=None
    idx=n.find("investidor estrangeiro")
    if idx >= 0:
        foreign_context=n[idx:idx+300]

    return {
        "data_through": cutoff,
        "foreign_row_present": foreign_row_present,
        "purchase_header_present": purchase_header,
        "sales_header_present": sales_header,
        "foreign_context": foreign_context,
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--out", required=True)
    args=ap.parse_args()

    p=load(Path(args.prereg))
    if p["status"] != "PREREGISTERED_BEFORE_PHYSICAL_B3_BDI_READ":
        raise RuntimeError("PREREG_STATUS_INVALID")
    s=p["safety"]
    if not (s["RESEARCH_ONLY"] and s["SHADOW_ONLY"] and s["NO_BACKFILL"] and s["NO_RETUNE"]):
        raise RuntimeError("SAFETY_INVALID")
    if s["ENGINE_FEED"] is not False or s["ORDERS"] != 0 or s["REAL_CAPITAL"] != 0 or s["ECONOMICS_READ"] is not False:
        raise RuntimeError("TRADING_OR_ECONOMICS_BOUNDARY")

    src=p["official_source"]
    try:
        notice_html=decode_html(fetch(src["publication_notice"]))
    except Exception as e:
        out={
            "schema":"gate_btc_2.xagrammar_dd9f_b3_source_qualification.v1",
            "family_id":p["family_id"],
            "status":"FAIL_CLOSED_PHYSICAL_SOURCE_UNAVAILABLE",
            "error":f"notice:{type(e).__name__}:{e}",
            "economics_read":False,
            "historical_credit":0,
            "safety":s,
        }
        dump(Path(args.out),out)
        print(json.dumps({"status":out["status"]}))
        return 0

    notice_norm=norm_text(re.sub(r"<[^>]+>"," ",notice_html))
    q1=("dois dias uteis retroativos" in notice_norm and
        "boletim diario" in notice_norm and
        "participacao" in notice_norm and
        "investidor" in notice_norm)

    probes=[]
    all_retrievable=True
    all_lag=True
    all_fields=True
    for item in p["frozen_probe_dates"]:
        pub=item["publication_date"]
        ymd=pub.replace("-","")
        url=src["archive_pattern"].replace("{YYYY-MM-DD}",pub).replace("{YYYYMMDD}",ymd)
        try:
            pdf=fetch(url)
            text=extract_pdf_text(pdf)
            a=analyze_bdi(text)
            retrievable=True
        except Exception as e:
            a={"data_through":None,"foreign_row_present":False,"purchase_header_present":False,"sales_header_present":False,"foreign_context":None,"error":f"{type(e).__name__}:{e}"}
            retrievable=False
        expected=item["expected_data_through"]
        lag_ok=(a.get("data_through")==expected)
        fields_ok=bool(a.get("foreign_row_present") and a.get("purchase_header_present") and a.get("sales_header_present"))
        all_retrievable &= retrievable
        all_lag &= lag_ok
        all_fields &= fields_ok
        probes.append({
            "publication_date":pub,
            "expected_data_through":expected,
            "official_url":url,
            "retrievable":retrievable,
            "observed_data_through":a.get("data_through"),
            "lag_consistent":lag_ok,
            "foreign_row_present":a.get("foreign_row_present"),
            "purchase_header_present":a.get("purchase_header_present"),
            "sales_header_present":a.get("sales_header_present"),
            "foreign_context":a.get("foreign_context"),
            "error":a.get("error"),
        })

    q2=bool(all_retrievable and all_lag)
    q3=bool(all_retrievable and all_fields)
    q4=bool(all_retrievable)
    full=q1 and q2 and q3 and q4
    status="PASS_B3_FOREIGN_FLOW_SOURCE_SEMANTICS" if full else (
        "FAIL_CLOSED_PHYSICAL_SOURCE_UNAVAILABLE" if not q4 else "FAIL_CLOSED_BDI_LAG_OR_FIELDS_NOT_PROVEN"
    )

    out={
        "schema":"gate_btc_2.xagrammar_dd9f_b3_source_qualification.v1",
        "family_id":p["family_id"],
        "canonical_channel_id":p["canonical_channel_id"],
        "status":status,
        "official_source":"B3_BDI",
        "questions":{
            "q1_official_lag_rule":q1,
            "q2_physical_lag_consistency":q2,
            "q3_foreign_fields":q3,
            "q4_archive_retrievability":q4,
        },
        "frozen_probe_results":probes,
        "availability_semantics":{
            "publication_day_is_availability_day":p["pass_policy"]["publication_day_is_availability_day"],
            "strict_signal_availability":p["pass_policy"]["strict_signal_availability"],
            "earliest_future_market_join":p["pass_policy"]["earliest_future_market_join"],
            "intraday_publication_time_claimed":False,
            "same_day_market_reaction_credit":0,
        },
        "full_source_qualification":full,
        "daily_flow_derivation_performed":False,
        "market_outcomes_read":False,
        "b3_price_join_performed":False,
        "economics_read":False,
        "historical_credit":0,
        "promotion_authority":False,
        "next_gate":p["next_gate_if_pass"] if full else "SOURCE_BLOCKER_REMAINS_WITH_PHYSICAL_EVIDENCE",
        "safety":s,
    }
    dump(Path(args.out),out)
    print(json.dumps({"status":status,"questions":out["questions"]},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
