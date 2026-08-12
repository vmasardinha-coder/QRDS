#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import requests
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

LEGACY = "https://arquivos.b3.com.br/rapinegocios/tickercsv/{date}"
BDI_CLASSIFICATION = "c65bf614-f8ca-4da0-88e9-f7c7e4faacb0"
BDI_TABLE = "TradesDone"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def bdi_url(date: str) -> str:
    d = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
    return f"https://arquivos.b3.com.br/bdi/tabelas/{d}?classification={BDI_CLASSIFICATION}&lang=pt-BR&table={BDI_TABLE}"


def legacy_probe(date: str, out: Path) -> dict:
    url = LEGACY.format(date=date)
    rec = {"source": "legacy_rapinegocios", "url": url, "date": date}
    try:
        r = requests.get(url, timeout=90, headers={"User-Agent": UA, "Accept": "*/*"})
        rec.update(http_status=r.status_code, content_type=r.headers.get("content-type", ""), bytes=len(r.content))
        if r.status_code == 200 and r.content[:2] == b"PK":
            p = out / f"{date}_legacy_NEGOCIOSAVISTA.zip"
            p.write_bytes(r.content)
            rec.update(ok=True, path=p.name, sha256=sha256(r.content))
        else:
            rec["ok"] = False
            (out / f"{date}_legacy_response.bin").write_bytes(r.content[:2_000_000])
    except Exception as e:
        rec.update(ok=False, error=repr(e))
    return rec


async def bdi_probe(date: str, out: Path) -> dict:
    url = bdi_url(date)
    rec = {"source": "bdi_browser", "url": url, "date": date, "classification": BDI_CLASSIFICATION,
           "table": BDI_TABLE, "downloads": [], "candidate_responses": []}
    network = []
    response_bodies = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True, user_agent=UA, locale="pt-BR")
        page = await context.new_page()

        async def on_response(resp):
            u = resp.url
            ct = (resp.headers.get("content-type") or "").lower()
            interesting = any(k in u.lower() for k in ["tradesdone", "csv", "download", "export", "/api/", "/bdi/"])
            if interesting or any(k in ct for k in ["csv", "zip", "json", "octet-stream"]):
                item = {"status": resp.status, "url": u, "content_type": ct}
                network.append(item)
                if any(k in ct for k in ["csv", "zip", "json", "octet-stream"]):
                    try:
                        body = await resp.body()
                        if body and len(body) <= 150_000_000:
                            ext = ".json" if "json" in ct else (".csv" if "csv" in ct else (".zip" if "zip" in ct else ".bin"))
                            p = out / f"{date}_xhr_{len(response_bodies):03d}{ext}"
                            p.write_bytes(body)
                            response_bodies.append({"url": u, "path": p.name, "bytes": len(body),
                                                    "sha256": sha256(body), "content_type": ct})
                    except Exception as e:
                        item["body_error"] = repr(e)

        page.on("response", on_response)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            try:
                await page.wait_for_load_state("networkidle", timeout=45_000)
            except PlaywrightTimeoutError:
                rec["networkidle_timeout"] = True
            await page.wait_for_timeout(5000)
            rec["title"] = await page.title()
            rec["final_url"] = page.url
            rec["body_text_prefix"] = (await page.locator("body").inner_text())[:20_000]
            (out / f"{date}_bdi.html").write_text(await page.content(), encoding="utf-8")
            await page.screenshot(path=str(out / f"{date}_bdi.png"), full_page=True)
            rec["controls"] = (await page.locator("a,button,[role=button]").evaluate_all(
                "els => els.map((e,i)=>({i,tag:e.tagName,text:(e.innerText||e.textContent||'').trim(),href:e.href||'',title:e.title||'',aria:e.getAttribute('aria-label')||''})).filter(x=>x.text||x.href||x.title||x.aria)"
            ))[:1000]

            candidates = []
            for selector in ["a:has-text('CSV')", "button:has-text('CSV')", "a:has-text('Exportar')",
                             "button:has-text('Exportar')", "a:has-text('Download')", "button:has-text('Download')", "a[download]"]:
                loc = page.locator(selector)
                for i in range(min(await loc.count(), 20)):
                    candidates.append(loc.nth(i))
            for i, loc in enumerate(candidates[:30]):
                try:
                    txt = (await loc.inner_text()).strip()
                except Exception:
                    txt = ""
                try:
                    async with page.expect_download(timeout=12_000) as di:
                        await loc.click(timeout=8_000)
                    dl = await di.value
                    target = out / f"{date}_download_{len(rec['downloads']):02d}_{re.sub(r'[^A-Za-z0-9._-]+','_',dl.suggested_filename)}"
                    await dl.save_as(str(target))
                    data = target.read_bytes()
                    rec["downloads"].append({"control_text": txt, "path": target.name, "bytes": len(data), "sha256": sha256(data)})
                    if len(data) > 100:
                        break
                except Exception as e:
                    rec.setdefault("download_attempt_errors", []).append({"control_text": txt, "error": repr(e)})
        except Exception as e:
            rec["error"] = repr(e)
        finally:
            rec["candidate_responses"] = network
            rec["captured_response_bodies"] = response_bodies
            await context.close()
            await browser.close()
    rec["ok"] = bool(rec["downloads"] or response_bodies)
    return rec


async def run(dates: list[str], out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    report = {"schema": "gate_btc.b3.h1.source_probe.v1", "research_only": True, "shadow_only": True,
              "orders": 0, "real_capital": 0, "economics_locked": True, "dates": []}
    any_payload = False
    for date in dates:
        day = out / date
        day.mkdir(exist_ok=True)
        legacy = legacy_probe(date, day)
        bdi = None if legacy.get("ok") else await bdi_probe(date, day)
        any_payload |= bool(legacy.get("ok") or (bdi or {}).get("ok"))
        row = {"date": date, "legacy": legacy, "bdi": bdi}
        report["dates"].append(row)
        dump(day / "SOURCE_PROBE.json", row)
    report["any_payload_captured"] = any_payload
    dump(out / "SOURCE_PROBE_SUMMARY.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if any_payload else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", nargs="+", required=True)
    ap.add_argument("--out-dir", default="artifacts/b3_h1_source_probe")
    a = ap.parse_args()
    return asyncio.run(run(a.dates, Path(a.out_dir)))


if __name__ == "__main__":
    raise SystemExit(main())
