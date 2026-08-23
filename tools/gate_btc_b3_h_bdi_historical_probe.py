#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

BDI_CLASSIFICATION = "c65bf614-f8ca-4da0-88e9-f7c7e4faacb0"
BDI_TABLE = "TradesDone"
DATES = ["2025-01-03", "2026-03-30"]
OUT = Path("artifacts/b3_h_nextgen/bdi_historical_probe")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bdi_url(iso_date: str) -> str:
    y, m, d = iso_date.split("-")
    return (
        f"https://arquivos.b3.com.br/bdi/tabelas/{d}-{m}-{y}"
        f"?classification={BDI_CLASSIFICATION}&lang=pt-BR&table={BDI_TABLE}"
    )


async def probe_day(iso_date: str) -> dict:
    day = OUT / iso_date
    day.mkdir(parents=True, exist_ok=True)
    rec = {
        "date": iso_date,
        "url": bdi_url(iso_date),
        "classification": BDI_CLASSIFICATION,
        "table": BDI_TABLE,
        "candidate_responses": [],
        "captured_payloads": [],
        "research_only": True,
        "orders": 0,
        "real_capital": 0,
        "h1_economics_read": False,
    }
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=UA, locale="pt-BR")
        page = await context.new_page()

        async def on_response(resp):
            u = resp.url
            ct = (resp.headers.get("content-type") or "").lower()
            lu = u.lower()
            interesting = any(k in lu for k in ["tradesdone", "classification", "download", "export", "/api/", "/bdi/"])
            if not interesting and not any(k in ct for k in ["json", "csv", "zip", "octet-stream"]):
                return
            item = {"status": resp.status, "url": u, "content_type": ct}
            rec["candidate_responses"].append(item)
            if any(k in ct for k in ["json", "csv", "zip", "octet-stream"]):
                try:
                    body = await resp.body()
                    if body and len(body) <= 5_000_000:
                        ext = ".json" if "json" in ct else (".csv" if "csv" in ct else ".bin")
                        p = day / f"payload_{len(rec['captured_payloads']):03d}{ext}"
                        p.write_bytes(body)
                        rec["captured_payloads"].append({
                            "url": u,
                            "path": p.name,
                            "bytes": len(body),
                            "sha256": sha256(body),
                            "content_type": ct,
                        })
                except Exception as exc:
                    item["body_error"] = repr(exc)

        page.on("response", on_response)
        try:
            await page.goto(rec["url"], wait_until="domcontentloaded", timeout=90_000)
            try:
                await page.wait_for_load_state("networkidle", timeout=45_000)
            except PlaywrightTimeoutError:
                rec["networkidle_timeout"] = True
            await page.wait_for_timeout(4000)
            rec["title"] = await page.title()
            rec["final_url"] = page.url
            rec["body_text_prefix"] = (await page.locator("body").inner_text())[:12000]
        except Exception as exc:
            rec["error"] = repr(exc)
        finally:
            await context.close()
            await browser.close()
    rec["api_candidates"] = sorted({
        r["url"] for r in rec["candidate_responses"]
        if any(k in r["url"].lower() for k in ["tradesdone", "/api/", "download", "export"])
    })
    (day / "BDI_HISTORICAL_PROBE.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return rec


async def run() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for d in DATES:
        rows.append(await probe_day(d))
    summary = {
        "schema": "gate_btc.b3.h_nextgen.bdi_historical_probe.v1",
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders": 0,
        "real_capital": 0,
        "h1_economics_read": False,
        "dates_all_pre_h1_cutoff": True,
        "classification": BDI_CLASSIFICATION,
        "table": BDI_TABLE,
        "rows": rows,
    }
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
