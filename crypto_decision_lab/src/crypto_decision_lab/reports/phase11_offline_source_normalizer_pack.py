from __future__ import annotations
import csv, hashlib, html, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
SAFETY_FLAGS = {
    "app_mode": APP_MODE, "research_allowed": True, "hypothetical_only": True,
    "api_key_required": False, "api_key_present": False,
    "account_connection_required": False, "authenticated_connection_used": False,
    "orders_allowed": False, "orders_generated": False, "real_orders_generated": False,
    "real_capital_used": False, "trading_signal_generated": False,
    "executable_signal_generated": False, "recommendation_generated": False,
    "allocation_generated": False, "portfolio_decision_generated": False,
    "operational_decision_allowed": False,
}
REQ = ["timestamp","open","high","low","close","volume","symbol","interval","source"]
NUM = ["open","high","low","close","volume"]
ALIASES = {
    "timestamp":["timestamp","open_time","time","date","datetime","start_time","t"],
    "open":["open","o"], "high":["high","h"], "low":["low","l"], "close":["close","c"],
    "volume":["volume","vol","v","base_volume","base asset volume"],
    "symbol":["symbol","pair","market","ticker"], "interval":["interval","timeframe","tf"],
    "source":["source","venue","provider"],
}

def _root(r=None):
    if r: return Path(r).resolve()
    here = Path.cwd().resolve()
    for p in [here,*here.parents]:
        if (p/"crypto_decision_lab").exists(): return p
    return here

def _load_json(root: Path, rel: str) -> dict[str, Any]:
    try:
        d=json.loads((root/rel).read_text(encoding="utf-8")); d["_present"]=True; return d
    except Exception:
        return {"_present":False,"gate_answer":"MISSING_RESEARCH_ONLY"}

def _payload(d): return d.get("payload") if isinstance(d.get("payload"),dict) else {}
def _field(d,k,default=None): return d[k] if k in d else _payload(d).get(k,default)
def _sha_text(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def _sha_file(p: Path):
    try: return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception: return "MISSING"
def _git(root: Path):
    try:
        p=subprocess.run(["git","status","--short"],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        return [x for x in p.stdout.splitlines() if x.strip()]
    except Exception: return []
def _flt(x):
    try:
        if x in ("",None): return None
        return float(x)
    except Exception: return None

def _read_rows(p: Path):
    rows=[]
    try:
        if p.suffix.lower()==".jsonl":
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    o=json.loads(line)
                    if isinstance(o,dict): rows.append(o)
        elif p.suffix.lower()==".csv":
            with p.open("r",encoding="utf-8",newline="") as f:
                rows=[dict(r) for r in csv.DictReader(f)]
    except Exception:
        return []
    return rows

def _map(headers):
    low={h.strip().lower():h for h in headers}
    m={}
    for canon, aliases in ALIASES.items():
        for a in aliases:
            if a.lower() in low:
                m[canon]=low[a.lower()]; break
    return m

def _infer_symbol(path: Path, row, m):
    if m.get("symbol") and row.get(m["symbol"]):
        return str(row[m["symbol"]]).upper().replace("/","-").replace("_","-")
    name=path.stem.lower().replace("-","_")
    if "btc_usdt" in name or "btcusdt" in name: return "BTC-USDT"
    if "eth_usdt" in name or "ethusdt" in name: return "ETH-USDT"
    if "sol_usdt" in name or "solusdt" in name: return "SOL-USDT"
    return "UNKNOWN"

def _norm_row(path: Path, row, m):
    def g(k, default=None):
        src=m.get(k); return row.get(src, default) if src else default
    out={
        "timestamp": g("timestamp"),
        "open": _flt(g("open")), "high": _flt(g("high")), "low": _flt(g("low")),
        "close": _flt(g("close")), "volume": _flt(g("volume")),
        "symbol": _infer_symbol(path,row,m),
        "interval": str(g("interval","1h") or "1h"),
        "source": str(g("source",f"OFFLINE_FILE:{path.name}") or f"OFFLINE_FILE:{path.name}"),
    }
    err=[]
    for f in REQ:
        if out.get(f) in ("",None,"UNKNOWN"): err.append(f"missing_or_unknown:{f}")
    for f in NUM:
        if out.get(f) is None: err.append(f"not_number:{f}")
    if not any(e.startswith("not_number") for e in err):
        if out["high"] < out["low"]: err.append("shape:high_lt_low")
        if out["open"] < out["low"] or out["open"] > out["high"]: err.append("shape:open_outside_range")
        if out["close"] < out["low"] or out["close"] > out["high"]: err.append("shape:close_outside_range")
    return (out if not err else None), err

def _files(root: Path):
    inbox=root/"crypto_decision_lab/manual_intake/inbox"
    real=sorted([p for p in inbox.glob("*") if p.is_file() and p.suffix.lower() in {".csv",".jsonl"}]) if inbox.exists() else []
    if real: return real, False
    fb=root/"crypto_decision_lab/artifacts/phase10_offline_sample_intake_promotion_pack/validated_staging"
    return (sorted(fb.glob("*.jsonl")) if fb.exists() else []), True

def _normalize(paths, out: Path, fallback: bool):
    nd=out/"normalized"; nd.mkdir(parents=True, exist_ok=True)
    # Clear stale normalized files from prior modes/runs before writing current outputs.
    # This prevents fallback/sample artifacts from being mixed with public inbox data.
    for old_file in nd.glob("*.jsonl"):
        old_file.unlink()
    summaries=[]; outputs=[]
    for p in paths:
        raw=_read_rows(p); headers=list(raw[0].keys()) if raw else []; m=_map(headers)
        norm=[]; errors=[]
        for i,row in enumerate(raw):
            nr, er = _norm_row(p,row,m)
            if er: errors.extend([f"row{i}:{e}" for e in er[:8]])
            elif nr: norm.append(nr)
        symbol=norm[0]["symbol"] if norm else "UNKNOWN"; interval=norm[0]["interval"] if norm else "1h"
        op=nd/f"{symbol.lower().replace('-','_')}_{interval}_{p.stem}_normalized.jsonl"
        text="".join(json.dumps(r,sort_keys=True,ensure_ascii=False)+"\n" for r in norm)
        op.write_text(text,encoding="utf-8")
        s={"file_name":p.name,"source_kind":"ARTIFACT_FALLBACK_SAMPLE" if fallback else "INBOX_FILE","raw_rows":len(raw),"normalized_rows":len(norm),"error_count":len(errors),"errors":errors[:40],"mapping":m,"ready":len(raw)>0 and len(raw)==len(norm) and not errors,"path":str(p),"normalized_path":str(op),"sha256":_sha_file(p)[:16],"normalized_sha256":_sha_text(text)[:16],"canonical_write_allowed":False}
        summaries.append(s); outputs.append({"path":str(op),"rows":len(norm),"symbol":symbol,"interval":interval,"sha256":_sha_text(text)[:16]})
    return summaries, outputs

def _crit(cid, ok, obs, threshold, status=None):
    return {"criterion_id":cid,"status":status or ("PASS" if ok else "FAIL"),"ready":bool(ok),"observed":obs,"threshold":threshold}

def _write_html(path: Path, p: dict[str,Any]):
    esc=lambda x: html.escape(str(x))
    cards=[("Station",p["station"]),("Inbox files",p["inbox_file_count"]),("Fallback used",p["fallback_samples_used"]),("Files normalized",p["files_normalized"]),("Rows normalized",p["rows_normalized"]),("Ready files",p["ready_files"]),("Canonical writes",p["canonical_data_writes"]),("Promotion allowed",p["promotion_allowed"]),("Mean score",p["mean_normalizer_score"])]
    card="".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k,v in cards)
    rows="".join(f"<tr><td>{esc(s['file_name'])}</td><td>{esc(s['source_kind'])}</td><td>{esc(s['raw_rows'])}</td><td>{esc(s['normalized_rows'])}</td><td>{esc(s['error_count'])}</td><td>{esc(s['ready'])}</td><td>{esc(s['normalized_path'])}</td></tr>" for s in p["file_summaries"]) or "<tr><td>NONE</td><td>NONE</td><td>0</td><td>0</td><td>0</td><td>False</td><td>MISSING</td></tr>"
    crit="".join(f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>" for c in p["criteria"])
    page=f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Offline Source Normalizer</title><style>body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{border:1px solid #d9deea;padding:8px;text-align:left}}th{{background:#eef2ff}}.blocked{{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}}</style></head><body><h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 11 Offline Source Normalizer Pack</h2><div class='card'><p><b>Gate answer:</b> {esc(p['gate_answer'])}</p><p><b>Policy lock:</b> {esc(p['policy_lock'])} • <b>Mode:</b> {esc(p['app_mode'])}</p>{card}<p class='blocked'>Canonical writes remain zero; promotion remains blocked.</p></div><h2>Normalized files</h2><table><thead><tr><th>file</th><th>source_kind</th><th>raw_rows</th><th>normalized_rows</th><th>errors</th><th>ready</th><th>normalized_path</th></tr></thead><tbody>{rows}</tbody></table><h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit}</tbody></table><p>Generated at {esc(p['generated_at'])} • SHA256 {esc(p['report_payload_sha256'])}</p></body></html>"""
    path.write_text(page,encoding="utf-8")

def build_phase11_offline_source_normalizer_pack(output_dir: str|Path, repo_root: str|Path|None=None, **_:Any):
    root=_root(repo_root); out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    (root/"crypto_decision_lab/manual_intake/inbox").mkdir(parents=True,exist_ok=True)
    lock=_load_json(root,"crypto_decision_lab/artifacts/phase11_canonical_promotion_dry_run_lock_pack/phase11_canonical_promotion_dry_run_lock_pack_index.json")
    paths,fallback=_files(root)
    summaries,outputs=_normalize(paths,out,fallback)
    ready=sum(1 for s in summaries if s["ready"]); rows=sum(s["normalized_rows"] for s in summaries)
    canon_writes=0; promo=False; gs=_git(root)
    criteria=[
        _crit("phase11_lock_present",bool(lock.get("_present")),lock.get("gate_answer","MISSING"),"11A-11H lock present","PASS" if lock.get("_present") else "WARN"),
        _crit("inbox_ready",(root/"crypto_decision_lab/manual_intake/inbox").exists(),str(root/"crypto_decision_lab/manual_intake/inbox"),"inbox exists"),
        _crit("files_available_or_fallback",bool(paths),len(paths),">0 files or fallback"),
        _crit("normalization_outputs_created",bool(outputs),len(outputs),">0 normalized outputs"),
        _crit("rows_normalized",rows>0,rows,">0 rows"),
        _crit("ready_files",bool(summaries) and ready==len(summaries),f"{ready}/{len(summaries)}","all files ready"),
        _crit("artifact_only",canon_writes==0,canon_writes,"0 canonical writes"),
        _crit("promotion_blocked",not promo,promo,"false"),
        _crit("research_only_lock",True,"ACTIVE","policy lock active"),
    ]
    cr=sum(1 for c in criteria if c["ready"])
    gate="PHASE11_OFFLINE_SOURCE_NORMALIZER_READY_WITH_INBOX_FILES_RESEARCH_ONLY" if summaries and rows>0 and ready==len(summaries) and not fallback else ("PHASE11_OFFLINE_SOURCE_NORMALIZER_READY_SAMPLE_FALLBACK_RESEARCH_ONLY" if summaries and rows>0 and ready==len(summaries) else "PHASE11_OFFLINE_SOURCE_NORMALIZER_NEEDS_REVIEW_RESEARCH_ONLY")
    payload={"schema":"qrds.phase11_offline_source_normalizer_pack.v1","report_name":"qrds-phase11-offline-source-normalizer-pack","generated_at":datetime.now(timezone.utc).isoformat(),"gate_answer":gate,"policy_lock":"ACTIVE","app_mode":APP_MODE,"station":"PHASE_11_OFFLINE_SOURCE_NORMALIZER","phase11_lock_present":bool(lock.get("_present")),"inbox_ready":(root/"crypto_decision_lab/manual_intake/inbox").exists(),"inbox_file_count":0 if fallback else len(paths),"fallback_samples_used":fallback,"files_normalized":len(summaries),"ready_files":ready,"rows_normalized":rows,"normalization_outputs":outputs,"file_summaries":summaries,"canonical_data_writes":canon_writes,"promotion_allowed":promo,"git_status_line_count":len(gs),"git_status_lines":gs[:80],"criteria":criteria,"criteria_ready_count":cr,"criteria_total_count":len(criteria),"mean_normalizer_score":round(cr/len(criteria),4),"safety_flags":SAFETY_FLAGS,**SAFETY_FLAGS}
    payload["report_payload_sha256"]=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode("utf-8")).hexdigest()
    rp=out/"phase11_offline_source_normalizer_pack.json"; mp=out/"phase11_offline_source_normalizer_pack.md"; hp=out/"index.html"; ip=out/"phase11_offline_source_normalizer_pack_index.json"
    rp.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
    mp.write_text(f"# QRDS/QOS Phase 11 Offline Source Normalizer Pack\n\n**Gate answer:** {gate}\n\nArtifact-only normalizer. Canonical writes: 0. Promotion allowed: false.\n",encoding="utf-8")
    _write_html(hp,payload)
    idx={k:payload[k] for k in ["schema","report_name","generated_at","gate_answer","policy_lock","app_mode","station","phase11_lock_present","inbox_ready","inbox_file_count","fallback_samples_used","files_normalized","ready_files","rows_normalized","canonical_data_writes","promotion_allowed","criteria_ready_count","criteria_total_count","mean_normalizer_score","git_status_line_count",*SAFETY_FLAGS.keys()] if k in payload}
    idx.update({"schema":"qrds.phase11_offline_source_normalizer_pack_index.v1","report_path":str(rp),"markdown_path":str(mp),"html_path":str(hp),"index_path":str(ip),"serve_entrypoint":str(hp),"report_payload_sha256":payload["report_payload_sha256"],"payload":payload})
    ip.write_text(json.dumps(idx,indent=2,sort_keys=True),encoding="utf-8")
    return idx

build_normalizer_pack=build_phase11_offline_source_normalizer_pack
