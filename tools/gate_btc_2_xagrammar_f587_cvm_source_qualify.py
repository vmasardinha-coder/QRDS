#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path

UA = "QRDS-GATE-BTC-2-Research/1.0"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def decode_text(data: bytes) -> tuple[str, str]:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            pass
    raise UnicodeDecodeError("unknown", b"", 0, 1, "no supported encoding")


def norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def find_field(headers: list[str], predicates) -> str | None:
    for h in headers:
        n = norm(h)
        if any(p(n) for p in predicates):
            return h
    return None


def meta_mentions_field(meta_norm: str, field: str | None) -> bool:
    if not field:
        return False
    return norm(field) in meta_norm


def extract_meta_context(meta_text: str, fields: list[str | None], radius: int = 2) -> dict[str, list[str]]:
    lines = meta_text.splitlines()
    out: dict[str, list[str]] = {}
    for f in fields:
        if not f:
            continue
        nf = norm(f)
        hits=[]
        for i,line in enumerate(lines):
            if nf and nf in norm(line):
                lo=max(0,i-radius); hi=min(len(lines),i+radius+1)
                hits.extend(lines[lo:hi])
        if hits:
            # Bound evidence size while preserving exact source text.
            out[f]=hits[:20]
    return out


def parse_csv_from_zip(zbytes: bytes) -> tuple[str, list[str], list[dict[str,str]], str, str]:
    with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
        names=[n for n in zf.namelist() if n.lower().endswith((".csv", ".txt")) and not n.endswith("/")]
        if not names:
            raise RuntimeError("NO_TABULAR_FILE_IN_ZIP")
        # Deterministic: shortest path/name, then lexical. Never content/outcome selected.
        name=sorted(names,key=lambda x:(len(x),x))[0]
        raw=zf.read(name)
    text,enc=decode_text(raw)
    sample=text[:32768]
    delim=';'
    try:
        delim=csv.Sniffer().sniff(sample,delimiters=';,\t|').delimiter
    except csv.Error:
        pass
    reader=csv.DictReader(io.StringIO(text),delimiter=delim)
    headers=list(reader.fieldnames or [])
    rows=[]
    for i,row in enumerate(reader):
        rows.append({str(k):"" if v is None else str(v) for k,v in row.items()})
        if i>=499:
            break
    return name,headers,rows,enc,delim


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--prereg', required=True)
    ap.add_argument('--out', required=True)
    args=ap.parse_args()
    p=load(Path(args.prereg))
    if p['status'] != 'PREREGISTERED_BEFORE_PHYSICAL_CVM_SOURCE_READ':
        raise RuntimeError('PREREG_STATUS_INVALID')
    s=p['safety']
    if not (s['RESEARCH_ONLY'] and s['SHADOW_ONLY'] and s['NO_BACKFILL'] and s['NO_RETUNE']):
        raise RuntimeError('SAFETY_INVALID')
    if s['ENGINE_FEED'] is not False or s['ORDERS'] != 0 or s['REAL_CAPITAL'] != 0 or s['ECONOMICS_READ'] is not False:
        raise RuntimeError('TRADING_OR_ECONOMICS_BOUNDARY')

    src=p['source']
    try:
        meta_bytes=fetch_bytes(src['metadata_url'])
        data_bytes=fetch_bytes(src['data_url_2026'])
    except Exception as e:
        out={
            'schema':'gate_btc_2.xagrammar_f587_cvm_source_qualification.v1',
            'family_id':p['family_id'],
            'status':'FAIL_CLOSED_PHYSICAL_SOURCE_UNAVAILABLE',
            'error':f'{type(e).__name__}:{e}',
            'economics_read':False,
            'historical_credit':0,
            'safety':s,
        }
        dump(Path(args.out),out)
        print(json.dumps({'status':out['status']}))
        return 0

    meta_text,meta_enc=decode_text(meta_bytes)
    tab_name,headers,rows,data_enc,delimiter=parse_csv_from_zip(data_bytes)
    meta_norm=norm(meta_text)

    delivery_date=find_field(headers,[
        lambda n: ('entreg' in n or 'receb' in n or 'protocol' in n or 'envio' in n) and ('data' in n or n.startswith('dt_')),
    ])
    delivery_time=find_field(headers,[
        lambda n: ('entreg' in n or 'receb' in n or 'protocol' in n or 'envio' in n) and ('hora' in n or 'time' in n),
    ])
    combined_timestamp=find_field(headers,[
        lambda n: ('entreg' in n or 'receb' in n or 'protocol' in n or 'envio' in n or 'public' in n) and ('timestamp' in n or 'datetime' in n),
    ])
    issuer_id=find_field(headers,[
        lambda n: n in {'codigo_cvm','cod_cvm','cd_cvm','cnpj_companhia','cnpj_cia','cnpj'},
        lambda n: 'cnpj' in n and ('companh' in n or 'cia' in n),
    ])
    category=find_field(headers,[
        lambda n: n in {'categoria','tipo','especie','categoria_documento','tipo_documento','especie_documento'},
        lambda n: ('categoria' in n or 'tipo' in n or 'especie' in n) and ('doc' in n or len(n)<24),
    ])

    documented_date=meta_mentions_field(meta_norm,delivery_date)
    documented_time=meta_mentions_field(meta_norm,delivery_time)
    documented_combined=meta_mentions_field(meta_norm,combined_timestamp)
    q1=bool(documented_combined or (documented_date and documented_time))

    def positive_fraction(field: str | None) -> float:
        if not field or not rows:
            return 0.0
        return sum(1 for r in rows if str(r.get(field,'')).strip())/len(rows)

    q2=bool((combined_timestamp and positive_fraction(combined_timestamp)>0.80) or
            (delivery_date and delivery_time and positive_fraction(delivery_date)>0.80 and positive_fraction(delivery_time)>0.80))
    q3=bool(issuer_id and meta_mentions_field(meta_norm,issuer_id) and positive_fraction(issuer_id)>0.80)
    q4=bool(category and meta_mentions_field(meta_norm,category) and positive_fraction(category)>0.80)

    full=q1 and q2 and q3 and q4
    if full:
        status='PASS_CVM_EVENT_SOURCE_SEMANTICS'
    elif q1 and q2:
        status='PARTIAL_TIMESTAMP_PASS_IDENTITY_OR_CATEGORY_PENDING'
    else:
        status='FAIL_CLOSED_TIMESTAMP_NOT_PROVEN'

    candidate_fields=[delivery_date,delivery_time,combined_timestamp,issuer_id,category]
    out={
        'schema':'gate_btc_2.xagrammar_f587_cvm_source_qualification.v1',
        'family_id':p['family_id'],
        'canonical_channel_id':p['canonical_channel_id'],
        'status':status,
        'official_source':src['provider'],
        'dataset':src['dataset'],
        'physical_file':tab_name,
        'metadata_encoding':meta_enc,
        'data_encoding':data_enc,
        'delimiter':delimiter,
        'header_count':len(headers),
        'headers':headers,
        'sample_rows_checked':len(rows),
        'fields':{
            'delivery_date':delivery_date,
            'delivery_time':delivery_time,
            'combined_timestamp':combined_timestamp,
            'issuer_identity':issuer_id,
            'event_category':category,
        },
        'metadata_documents_candidate_fields':{
            'delivery_date':documented_date,
            'delivery_time':documented_time,
            'combined_timestamp':documented_combined,
            'issuer_identity':meta_mentions_field(meta_norm,issuer_id),
            'event_category':meta_mentions_field(meta_norm,category),
        },
        'nonempty_fraction_sample':{f:positive_fraction(f) for f in candidate_fields if f},
        'metadata_context':extract_meta_context(meta_text,candidate_fields),
        'questions':{
            'q1_timestamp_dictionary':q1,
            'q2_timestamp_physical':q2,
            'q3_issuer_identity':q3,
            'q4_event_category':q4,
        },
        'full_source_qualification':full,
        'economics_read':False,
        'market_outcomes_read':False,
        'b3_price_join_performed':False,
        'historical_credit':0,
        'promotion_authority':False,
        'next_gate':p['next_gate_if_full_pass'] if full else 'SOURCE_BLOCKER_REMAINS_WITH_PHYSICAL_EVIDENCE',
        'safety':s,
    }
    dump(Path(args.out),out)
    print(json.dumps({'status':status,'questions':out['questions'],'fields':out['fields']},sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
