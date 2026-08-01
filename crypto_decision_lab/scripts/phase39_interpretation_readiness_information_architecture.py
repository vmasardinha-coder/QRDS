#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

READY_GATE = "PHASE39_INTERPRETATION_READINESS_INFORMATION_ARCHITECTURE_READY_RESEARCH_ONLY"
NEEDS_REVIEW_GATE = "PHASE39_INTERPRETATION_READINESS_INFORMATION_ARCHITECTURE_NEEDS_REVIEW_RESEARCH_ONLY"
PHASE38_GATE = "PHASE38_MODERN_RESEARCH_PORTAL_LAYOUT_UX_POLISH_READY_RESEARCH_ONLY"
PHASE37_GATE = "PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX_READY_RESEARCH_ONLY"
PHASE36_GATE = "PHASE36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_READY_RESEARCH_ONLY"

SAFETY_LOCK: Dict[str, Any] = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

PAGE_ORDER = [
    ("index.html", "Overview"),
    ("reading_guide.html", "Reading Guide"),
    ("metric_map.html", "Metric Map"),
    ("glossary.html", "Glossary"),
    ("evidence_boundaries.html", "Evidence Boundaries"),
    ("candidate_history.html", "Candidate History"),
    ("decision_safety.html", "Decision Safety"),
    ("exports_reports.html", "Exports / Reports"),
]

PHASE38_EXPECTED_PAGES = [
    "index.html",
    "data_trust.html",
    "market_snapshot.html",
    "regime_map.html",
    "volatility_risk.html",
    "recent_history.html",
    "sparklines.html",
    "edge_ledger.html",
    "freshness_audit.html",
    "safety_lock.html",
    "exports_reports.html",
]

INTERPRETATION_DIMENSIONS = [
    {
        "dimension": "Data Trust",
        "question": "Os dados de origem estão presentes, comparáveis e com confiança suficiente para pesquisa?",
        "read_as": "estado de confiabilidade da base de pesquisa",
        "not_read_as": "permissão para operar, comprar, vender ou alocar",
        "primary_pages": "data_trust.html, freshness_audit.html",
        "decision_use": "forbidden",
    },
    {
        "dimension": "Freshness / Audit",
        "question": "Os artefatos recentes, checksums e páginas estão rastreáveis?",
        "read_as": "controle de revisão e integridade do portal",
        "not_read_as": "garantia de edge operacional",
        "primary_pages": "freshness_audit.html, exports_reports.html",
        "decision_use": "forbidden",
    },
    {
        "dimension": "Market Snapshot",
        "question": "Qual era a última observação disponível no dataset de pesquisa?",
        "read_as": "fotografia do dado de pesquisa",
        "not_read_as": "preço-alvo, gatilho de entrada ou sinal",
        "primary_pages": "market_snapshot.html",
        "decision_use": "forbidden",
    },
    {
        "dimension": "Regime Map",
        "question": "Como o dataset classifica estados de regime para diagnóstico?",
        "read_as": "rótulo diagnóstico não-operacional",
        "not_read_as": "ordem, recomendação ou regime negociável",
        "primary_pages": "regime_map.html, regime_history.html",
        "decision_use": "forbidden",
    },
    {
        "dimension": "Volatility Risk",
        "question": "O caminho volatility-first continua promissor apenas como pesquisa?",
        "read_as": "evidência metodológica fraca/moderada para investigar",
        "not_read_as": "edge validado ou sizing",
        "primary_pages": "volatility_risk.html, sparklines.html",
        "decision_use": "forbidden",
    },
    {
        "dimension": "Edge Evidence Ledger",
        "question": "Quais hipóteses passaram, falharam ou ficaram pendentes?",
        "read_as": "ledger de evidência e refutação",
        "not_read_as": "lista de sinais ou candidatos operacionais",
        "primary_pages": "edge_ledger.html, candidate_history.html",
        "decision_use": "forbidden",
    },
    {
        "dimension": "Safety Lock",
        "question": "A camada decisória está bloqueada?",
        "read_as": "prova de travamento research-only",
        "not_read_as": "compliance para operação real",
        "primary_pages": "safety_lock.html, decision_safety.html",
        "decision_use": "forbidden",
    },
]

GLOSSARY = [
    ("research-only", "Modo de pesquisa interativa; não produz recomendação, sinal, alocação, ordem ou decisão operacional."),
    ("edge candidate", "Hipótese estatística candidata que ainda precisa sobreviver a testes de robustez; não é edge operacional."),
    ("stable candidate", "Candidato que sobreviveria a critérios de estabilidade; nas Phases 27–29 a contagem foi zero."),
    ("anti-overfit", "Conjunto de testes para reduzir a chance de uma hipótese funcionar apenas no histórico observado."),
    ("regime label", "Rótulo diagnóstico para organização de pesquisa; não é sinal de compra ou venda."),
    ("volatility-first", "Trilha que prioriza previsão/diagnóstico de volatilidade, pois retorno direcional foi fraco."),
    ("shadow decision", "Simulação de decisão operacional paralela; permanece bloqueada neste projeto."),
    ("safe-apply", "Qualquer aplicação semi-operacional; permanece bloqueada."),
    ("canonical data", "Camada oficial de dados para uso operacional; Phase 39 mantém canonical_data_writes = 0."),
]

CANDIDATE_HISTORY = [
    {
        "phase": "26",
        "event": "Regime-segmented volatility edge audit",
        "candidate_count": 4,
        "stable_count": 0,
        "status": "research candidates only",
        "interpretation": "Apareceram quatro hipóteses candidatas, mas sem elegibilidade operacional.",
    },
    {
        "phase": "27",
        "event": "Stability + anti-overfit",
        "candidate_count": 4,
        "stable_count": 0,
        "status": "failed stability",
        "interpretation": "Nenhum candidato sobreviveu ao split early/late.",
    },
    {
        "phase": "28",
        "event": "Regime taxonomy compression failure analysis",
        "candidate_count": 4,
        "stable_count": 0,
        "status": "failure analysis",
        "interpretation": "Os quatro casos ficaram classificados como falhas de robustez.",
    },
    {
        "phase": "29",
        "event": "Compressed regime retest",
        "candidate_count": 4,
        "stable_count": 0,
        "status": "closed for now",
        "interpretation": "Reteste comprimido confirmou zero candidatos estáveis; caminho fechado por enquanto.",
    },
]


def repo_root_from_file() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2]


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def write_json(path: Path, obj: Any) -> None:
    atomic_write(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_contains(path: Path, needle: str) -> bool:
    try:
        if path.stat().st_size > 5_000_000:
            return False
        return needle in path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False


def find_gate(root: Path, gate: str) -> List[str]:
    matches: List[str] = []
    search_roots = [root / "crypto_decision_lab" / "artifacts", root / "crypto_decision_lab" / "docs" / "reports"]
    for sr in search_roots:
        if not sr.exists():
            continue
        for path in sr.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".json", ".md", ".html", ".txt", ".csv"}:
                if file_contains(path, gate):
                    matches.append(str(path.relative_to(root)))
    return sorted(set(matches))[:50]


def find_phase38_portal(root: Path) -> Tuple[Path | None, int]:
    art = root / "crypto_decision_lab" / "artifacts"
    if not art.exists():
        return None, 0
    candidates = sorted(art.glob("phase38*"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    for cand in candidates:
        if not cand.is_dir():
            continue
        dirs = [cand, cand / "portal", cand / "modern_portal", cand / "site"]
        for d in dirs:
            if d.exists():
                count = sum(1 for name in PHASE38_EXPECTED_PAGES if (d / name).exists())
                if count >= 6:
                    return d, count
    best: Tuple[Path | None, int] = (None, 0)
    for d in art.rglob("*"):
        if d.is_dir():
            count = sum(1 for name in PHASE38_EXPECTED_PAGES if (d / name).exists())
            if count > best[1]:
                best = (d, count)
    return best


def badge(text: str, kind: str = "neutral") -> str:
    return f'<span class="badge badge-{html.escape(kind)}">{html.escape(text)}</span>'


def html_shell(title: str, body: str, nav: List[Tuple[str, str]], active: str) -> str:
    nav_items = "\n".join(
        f'<a class="nav-link {"active" if filename == active else ""}" href="{html.escape(filename, quote=True)}">{html.escape(label)}</a>'
        for filename, label in nav
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)} • QRDS Phase 39</title>
  <link rel="stylesheet" href="assets/phase39.css" />
  <script defer src="assets/phase39.js"></script>
</head>
<body data-page="{html.escape(active)}">
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-kicker">QRDS Gate BTC</div>
      <div class="brand-title">Interpretation Readiness</div>
      <div class="brand-subtitle">Phase 39 • research-only</div>
      <nav class="nav-list">{nav_items}</nav>
      <div class="lock-panel">
        <div class="lock-title">Safety Lock</div>
        <div>{badge('BLOCKED_RESEARCH_ONLY', 'danger')}</div>
        <div>{badge('edge_validated: False', 'safe')}</div>
        <div>{badge('decision_layer_allowed: False', 'safe')}</div>
      </div>
    </aside>
    <main class="content">
      <header class="topbar">
        <div>
          <div class="eyebrow">PHASE39_INTERPRETATION_READINESS_INFORMATION_ARCHITECTURE</div>
          <h1>{html.escape(title)}</h1>
        </div>
        <div class="topbar-badges">
          {badge('INTERACTIVE_RESEARCH_ONLY', 'safe')}
          {badge('NO SIGNAL', 'warn')}
          {badge('NO RECOMMENDATION', 'warn')}
        </div>
      </header>
      {body}
      <footer class="footer-note">Camada de leitura e arquitetura de informação. Não interpreta como decisão operacional, não gera recomendação e não promove candidatos.</footer>
    </main>
  </div>
</body>
</html>
"""


def table(headers: List[str], rows: Iterable[Iterable[Any]]) -> str:
    th = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    trs = []
    for row in rows:
        tds = "".join(f"<td>{html.escape(str(v))}</td>" for v in row)
        trs.append(f"<tr>{tds}</tr>")
    return f"<div class='table-wrap'><table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table></div>"


def render_pages(portal: Path, status: Dict[str, Any], phase38_portal_rel: str | None) -> None:
    nav = PAGE_ORDER
    assets = portal / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    css = """
:root{--bg:#0d1117;--panel:#121a24;--panel2:#172232;--muted:#8ea0b8;--text:#eef5ff;--line:#26364a;--accent:#8bd3ff;--safe:#37d399;--warn:#ffd166;--danger:#ff6b6b;--chip:#223149;--shadow:0 24px 80px rgba(0,0,0,.35)}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top left,#1b2a3f 0,#0d1117 38%,#080b10 100%);color:var(--text);font:15px/1.55 Inter,Segoe UI,Roboto,Arial,sans-serif}.app-shell{display:grid;grid-template-columns:310px minmax(0,1fr);min-height:100vh}.sidebar{position:sticky;top:0;height:100vh;padding:28px 22px;background:rgba(10,15,22,.86);border-right:1px solid var(--line);backdrop-filter:blur(18px);overflow:auto}.brand-kicker{font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:var(--accent)}.brand-title{font-size:25px;font-weight:800;margin-top:8px}.brand-subtitle{color:var(--muted);margin:4px 0 22px}.nav-list{display:grid;gap:8px}.nav-link{display:block;padding:11px 13px;border:1px solid transparent;border-radius:14px;color:var(--muted);text-decoration:none;background:transparent}.nav-link:hover,.nav-link.active{color:var(--text);border-color:var(--line);background:linear-gradient(135deg,rgba(139,211,255,.14),rgba(55,211,153,.07))}.lock-panel{margin-top:24px;padding:16px;border:1px solid var(--line);border-radius:18px;background:rgba(18,26,36,.78)}.lock-title{font-weight:800;margin-bottom:10px}.content{padding:34px;max-width:1320px}.topbar{display:flex;gap:20px;justify-content:space-between;align-items:flex-start;margin-bottom:24px}.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}h1{font-size:36px;line-height:1.05;margin:8px 0 0}h2{font-size:22px;margin:0 0 12px}.topbar-badges{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}.badge{display:inline-block;margin:3px 4px 3px 0;padding:6px 9px;border-radius:999px;font-size:12px;font-weight:800;letter-spacing:.02em;border:1px solid var(--line);background:var(--chip);color:var(--text)}.badge-safe{border-color:rgba(55,211,153,.5);color:var(--safe);background:rgba(55,211,153,.09)}.badge-warn{border-color:rgba(255,209,102,.55);color:var(--warn);background:rgba(255,209,102,.08)}.badge-danger{border-color:rgba(255,107,107,.62);color:var(--danger);background:rgba(255,107,107,.08)}.badge-neutral{color:var(--accent)}.grid{display:grid;gap:16px}.grid-2{grid-template-columns:repeat(2,minmax(0,1fr))}.grid-3{grid-template-columns:repeat(3,minmax(0,1fr))}.card{background:linear-gradient(180deg,rgba(23,34,50,.92),rgba(18,26,36,.92));border:1px solid var(--line);border-radius:24px;padding:21px;box-shadow:var(--shadow)}.card p{color:#cdd9e7}.metric{font-size:34px;font-weight:900;line-height:1}.metric-label{color:var(--muted);font-size:13px;margin-top:6px}.callout{border-left:4px solid var(--accent);padding:14px 16px;background:rgba(139,211,255,.08);border-radius:14px;margin:14px 0}.callout.warn{border-left-color:var(--warn);background:rgba(255,209,102,.08)}.callout.danger{border-left-color:var(--danger);background:rgba(255,107,107,.08)}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:18px}table{width:100%;border-collapse:collapse;background:rgba(13,17,23,.35)}th,td{padding:12px 14px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--accent);font-size:12px;text-transform:uppercase;letter-spacing:.08em;background:rgba(139,211,255,.06)}tr:last-child td{border-bottom:0}.path-card{display:flex;gap:14px;align-items:flex-start}.step-num{flex:0 0 34px;height:34px;border-radius:12px;display:grid;place-items:center;background:rgba(139,211,255,.14);color:var(--accent);font-weight:900}.footer-note{color:var(--muted);margin-top:28px;border-top:1px solid var(--line);padding-top:18px}@media(max-width:880px){.app-shell{grid-template-columns:1fr}.sidebar{position:relative;height:auto}.content{padding:22px}.topbar{display:block}.grid-2,.grid-3{grid-template-columns:1fr}}
"""
    js = """
document.addEventListener('DOMContentLoaded',()=>{const rows=[...document.querySelectorAll('tbody tr')];rows.forEach(r=>r.addEventListener('click',()=>r.classList.toggle('selected')));});
"""
    atomic_write(assets / "phase39.css", css.strip() + "\n")
    atomic_write(assets / "phase39.js", js.strip() + "\n")

    status_cards = f"""
<section class="grid grid-3">
  <article class="card"><div class="metric">{html.escape(str(status['interpretation_page_count']))}</div><div class="metric-label">páginas de readiness</div></article>
  <article class="card"><div class="metric">{html.escape(str(status['phase38_modern_pages_detected']))}</div><div class="metric-label">páginas modernas da Phase 38 detectadas</div></article>
  <article class="card"><div class="metric">0</div><div class="metric-label">candidatos estáveis/operacionais</div></article>
</section>
"""
    overview_body = f"""
{status_cards}
<section class="grid grid-2" style="margin-top:16px">
  <article class="card">
    <h2>O que esta fase entrega</h2>
    <p>Uma camada de arquitetura de informação para ajudar a ler o portal sem transformar métricas em decisão. Ela organiza glossário, mapa de métricas, limites de evidência e histórico dos candidatos reprovados.</p>
    <div class="callout">O objetivo é deixar a leitura mais clara: <strong>entender melhor</strong>, não operar.</div>
  </article>
  <article class="card">
    <h2>Base detectada</h2>
    <p>Phase 38 ready: {badge(str(status['phase38_ready']), 'safe' if status['phase38_ready'] else 'warn')}</p>
    <p>Phase 37 ready: {badge(str(status['phase37_ready']), 'safe' if status['phase37_ready'] else 'warn')}</p>
    <p>Phase 36 ready: {badge(str(status['phase36_ready']), 'safe' if status['phase36_ready'] else 'warn')}</p>
    <p>Portal base: <code>{html.escape(phase38_portal_rel or 'not_detected')}</code></p>
  </article>
</section>
<section class="card" style="margin-top:16px">
  <h2>Fluxo recomendado de leitura</h2>
  <div class="grid grid-3">
    <div class="path-card"><div class="step-num">1</div><div><strong>Confiança</strong><br><span>Ver Data Trust e Freshness antes de qualquer métrica.</span></div></div>
    <div class="path-card"><div class="step-num">2</div><div><strong>Diagnóstico</strong><br><span>Ler regime e volatilidade como contexto de pesquisa.</span></div></div>
    <div class="path-card"><div class="step-num">3</div><div><strong>Evidência</strong><br><span>Ver ledger e histórico de falhas antes de considerar novas hipóteses.</span></div></div>
  </div>
</section>
"""
    atomic_write(portal / "index.html", html_shell("Overview", overview_body, nav, "index.html"))

    reading_body = """
<section class="card">
  <h2>Como ler sem transformar em decisão</h2>
  <div class="callout warn">Toda leitura desta fase é descritiva e metodológica. Nenhum bloco equivale a entrada, saída, sizing, alocação ou recomendação.</div>
</section>
<section class="grid grid-2" style="margin-top:16px">
  <article class="card"><h2>Leitura correta</h2><p>Use os painéis para responder: a fonte é confiável? O artefato está fresco? A hipótese foi refutada? Qual métrica merece pesquisa posterior?</p></article>
  <article class="card"><h2>Leitura proibida</h2><p>Não use regime, volatilidade, sparkline, latest observation ou candidatos históricos como sinal de trade.</p></article>
</section>
<section class="card" style="margin-top:16px">
  <h2>Sequência</h2>
  <ol>
    <li>Safety Lock.</li>
    <li>Data Trust / Freshness.</li>
    <li>Market Snapshot como fotografia.</li>
    <li>Regime Map como rótulo diagnóstico.</li>
    <li>Volatility Risk como pesquisa, não edge.</li>
    <li>Edge Ledger e Candidate History para entender falhas.</li>
  </ol>
</section>
"""
    atomic_write(portal / "reading_guide.html", html_shell("Reading Guide", reading_body, nav, "reading_guide.html"))

    metric_rows = [[d["dimension"], d["question"], d["read_as"], d["not_read_as"], d["primary_pages"]] for d in INTERPRETATION_DIMENSIONS]
    metric_body = f"""
<section class="card"><h2>Mapa de métricas e perguntas</h2><p>Este mapa conecta seções do portal a perguntas de pesquisa e aos limites explícitos de interpretação.</p></section>
<section class="card" style="margin-top:16px">{table(['Dimensão','Pergunta','Ler como','Não ler como','Páginas'], metric_rows)}</section>
"""
    atomic_write(portal / "metric_map.html", html_shell("Metric Map", metric_body, nav, "metric_map.html"))

    glossary_body = f"""
<section class="card"><h2>Glossário research-only</h2><p>Termos usados no portal para evitar confundir diagnóstico com decisão.</p></section>
<section class="card" style="margin-top:16px">{table(['Termo','Definição'], GLOSSARY)}</section>
"""
    atomic_write(portal / "glossary.html", html_shell("Glossary", glossary_body, nav, "glossary.html"))

    boundaries = [
        ["Regime", "diagnóstico", "sinal de compra/venda"],
        ["Volatilidade", "risco e caminho de pesquisa", "sizing operacional"],
        ["Latest observation", "último dado do dataset", "gatilho"],
        ["Sparkline", "visualização histórica", "momentum acionável"],
        ["Edge ledger", "evidência/refutação", "lista de trades"],
        ["Candidate history", "histórico de hipótese reprovada", "candidato ativo"],
    ]
    boundary_body = f"""
<section class="card"><h2>Fronteiras de evidência</h2><p>A fase torna explícito onde a leitura para. Tudo abaixo permanece não-operacional.</p></section>
<section class="card" style="margin-top:16px">{table(['Objeto','Permitido ler como','Proibido ler como'], boundaries)}</section>
<div class="callout danger">Qualquer tentativa de converter esses objetos em recomendação deve ser classificada como fora do escopo da Phase 39.</div>
"""
    atomic_write(portal / "evidence_boundaries.html", html_shell("Evidence Boundaries", boundary_body, nav, "evidence_boundaries.html"))

    cand_rows = [[c["phase"], c["event"], c["candidate_count"], c["stable_count"], c["status"], c["interpretation"]] for c in CANDIDATE_HISTORY]
    candidate_body = f"""
<section class="grid grid-3">
  <article class="card"><div class="metric">4</div><div class="metric-label">candidatos de pesquisa encontrados na Phase 26</div></article>
  <article class="card"><div class="metric">0</div><div class="metric-label">candidatos estáveis após anti-overfit</div></article>
  <article class="card"><div class="metric">0</div><div class="metric-label">candidatos operacionais</div></article>
</section>
<section class="card" style="margin-top:16px"><h2>Histórico não-operacional</h2>{table(['Fase','Evento','Candidatos','Estáveis','Status','Interpretação'], cand_rows)}</section>
<div class="callout warn">Os quatro candidatos permanecem como histórico de falha/refutação. Eles não são base ativa para decisão.</div>
"""
    atomic_write(portal / "candidate_history.html", html_shell("Candidate History", candidate_body, nav, "candidate_history.html"))

    safety_rows = [[k, v] for k, v in SAFETY_LOCK.items()]
    safety_body = f"""
<section class="card"><h2>Decision Safety</h2><p>Contrato de segurança da Phase 39. Esta página existe para impedir que leitura guiada vire decisão.</p></section>
<section class="card" style="margin-top:16px">{table(['Flag','Valor'], safety_rows)}</section>
"""
    atomic_write(portal / "decision_safety.html", html_shell("Decision Safety", safety_body, nav, "decision_safety.html"))

    export_body = f"""
<section class="card"><h2>Arquivos gerados</h2><p>Manifestos, índices, checksums e exportações da camada de leitura.</p></section>
<section class="card" style="margin-top:16px">
  <ul>
    <li><code>interpretation_readiness_manifest.csv</code></li>
    <li><code>interpretation_metric_map.csv</code></li>
    <li><code>interpretation_glossary.csv</code></li>
    <li><code>interpretation_boundaries.json</code></li>
    <li><code>candidate_history_non_operational.json</code></li>
    <li><code>phase39_interpretation_readiness_information_architecture.json</code></li>
    <li><code>phase39_interpretation_readiness_information_architecture_index.json</code></li>
    <li><code>QRDS_PHASE39_INTERPRETATION_READINESS_INFORMATION_ARCHITECTURE_RESEARCH_ONLY.zip</code></li>
  </ul>
</section>
"""
    atomic_write(portal / "exports_reports.html", html_shell("Exports / Reports", export_body, nav, "exports_reports.html"))


def update_project_status(root: Path, status: Dict[str, Any]) -> None:
    report = root / "crypto_decision_lab" / "docs" / "reports" / "PROJECT_STATUS_QRDS_GATE_BTC.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    existing = report.read_text(encoding="utf-8", errors="ignore") if report.exists() else "# PROJECT STATUS — QRDS Gate BTC\n\n"
    marker = "<!-- PHASE39_INTERPRETATION_READINESS_INFORMATION_ARCHITECTURE -->"
    block = f"""
{marker}

## Phase 39 — Interpretation Readiness + Information Architecture

- Gate: `{status['gate']}`
- Generated at: `{status['generated_at']}`
- Phase 38 ready: `{status['phase38_ready']}`
- Interpretation pages: `{status['interpretation_page_count']}`
- Metric dimensions: `{status['metric_dimension_count']}`
- Candidate history: 4 research candidates from Phase 26, 0 stable after Phases 27–29.
- Operational status: `{status['operational_status']}`
- Edge validated: `{status['edge_validated']}`
- Shadow decision allowed: `{status['shadow_decision_allowed']}`
- Decision layer allowed: `{status['decision_layer_allowed']}`
- Trading signal generated: `{status['trading_signal_generated']}`
- Recommendation generated: `{status['recommendation_generated']}`
- Allocation generated: `{status['allocation_generated']}`
- Canonical data writes: `{status['canonical_data_writes']}`

Phase 39 adds a non-operational reading architecture over the modern research portal. It improves comprehension, glossary, metric mapping, evidence boundaries, and candidate-failure history. It does not create a signal, recommendation, allocation, shadow decision, safe-apply, canonical promotion, or operational decision.
""".strip() + "\n"
    if marker in existing:
        before = existing.split(marker)[0].rstrip()
        atomic_write(report, before + "\n\n" + block + "\n")
    else:
        atomic_write(report, existing.rstrip() + "\n\n" + block + "\n")


def generate(out_dir: Path | None = None) -> Dict[str, Any]:
    root = repo_root_from_file()
    project = root / "crypto_decision_lab"
    artifacts = project / "artifacts" / "phase39_interpretation_readiness_information_architecture"
    if out_dir is not None:
        artifacts = out_dir.resolve()
    portal = artifacts / "portal"
    portal.mkdir(parents=True, exist_ok=True)

    phase38_matches = find_gate(root, PHASE38_GATE)
    phase37_matches = find_gate(root, PHASE37_GATE)
    phase36_matches = find_gate(root, PHASE36_GATE)
    phase38_portal, phase38_pages = find_phase38_portal(root)
    phase38_portal_rel = str(phase38_portal.relative_to(root)) if phase38_portal and phase38_portal.exists() else None

    phase38_ready = bool(phase38_matches) and phase38_pages >= 11
    status = dict(SAFETY_LOCK)
    status.update(
        {
            "phase": 39,
            "slug": "interpretation_readiness_information_architecture",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "phase38_ready": phase38_ready,
            "phase37_ready": bool(phase37_matches),
            "phase36_ready": bool(phase36_matches),
            "phase38_modern_pages_detected": phase38_pages,
            "phase38_gate_files": phase38_matches,
            "phase37_gate_files": phase37_matches,
            "phase36_gate_files": phase36_matches,
            "phase38_portal": phase38_portal_rel,
            "interpretation_page_count": len(PAGE_ORDER),
            "metric_dimension_count": len(INTERPRETATION_DIMENSIONS),
            "glossary_term_count": len(GLOSSARY),
            "candidate_research_count_phase26": 4,
            "candidate_stable_count_after_phase27_29": 0,
            "operational_candidate_count": 0,
            "recommendation_count": 0,
            "signal_count": 0,
            "allocation_count": 0,
            "mean_interpretation_readiness_score": 1.0 if phase38_ready else 0.0,
        }
    )
    status["gate"] = READY_GATE if phase38_ready else NEEDS_REVIEW_GATE
    status["interpretation_readiness_ready"] = bool(phase38_ready)
    status["needs_review_reasons"] = [] if phase38_ready else [
        "Phase 38 modern portal gate/pages not fully detected. This is a technical input-detection or missing-artifact review, not an operational failure."
    ]

    copied_pages = 0
    if phase38_portal and phase38_portal.exists():
        inherited = artifacts / "inherited_phase38_modern_portal_reference"
        if inherited.exists():
            shutil.rmtree(inherited)
        shutil.copytree(phase38_portal, inherited, ignore=shutil.ignore_patterns("*.bak", "__pycache__"))
        copied_pages = sum(1 for p in inherited.glob("*.html") if p.is_file())
    status["inherited_phase38_pages_copied"] = copied_pages

    render_pages(portal, status, phase38_portal_rel)

    manifest_rows: List[Dict[str, Any]] = []
    for filename, label in PAGE_ORDER:
        manifest_rows.append({
            "page": filename,
            "label": label,
            "path": f"portal/{filename}",
            "research_only": True,
            "decision_use": "forbidden",
            "generated": (portal / filename).exists(),
        })
    write_csv(artifacts / "interpretation_readiness_manifest.csv", manifest_rows, ["page", "label", "path", "research_only", "decision_use", "generated"])
    write_csv(artifacts / "interpretation_metric_map.csv", INTERPRETATION_DIMENSIONS, ["dimension", "question", "read_as", "not_read_as", "primary_pages", "decision_use"])
    write_csv(artifacts / "interpretation_glossary.csv", [{"term": t, "definition": d} for t, d in GLOSSARY], ["term", "definition"])
    write_json(artifacts / "interpretation_boundaries.json", {
        "gate": status["gate"],
        "safety_lock": SAFETY_LOCK,
        "boundaries": INTERPRETATION_DIMENSIONS,
        "forbidden_conversions": [
            "regime_to_signal",
            "volatility_to_position_size",
            "latest_observation_to_entry_trigger",
            "sparkline_to_momentum_trade",
            "candidate_history_to_operational_candidate",
            "ledger_to_recommendation",
        ],
    })
    write_json(artifacts / "reading_pathways.json", {
        "gate": status["gate"],
        "pathways": [
            {"step": 1, "name": "Safety first", "pages": ["decision_safety.html"], "decision_use": "forbidden"},
            {"step": 2, "name": "Trust and freshness", "pages": ["metric_map.html", "evidence_boundaries.html"], "decision_use": "forbidden"},
            {"step": 3, "name": "Evidence ledger context", "pages": ["candidate_history.html"], "decision_use": "forbidden"},
        ],
    })
    write_json(artifacts / "candidate_history_non_operational.json", {
        "gate": status["gate"],
        "summary": "Four Phase 26 research candidates failed stability/anti-overfit and remain non-operational history.",
        "operational_candidate_count": 0,
        "items": CANDIDATE_HISTORY,
    })

    write_json(artifacts / "phase39_interpretation_readiness_information_architecture.json", status)
    index = {"gate": status["gate"], "root": str(artifacts.relative_to(root)), "portal_index": "portal/index.html", "pages": manifest_rows, "safety_lock": SAFETY_LOCK}
    write_json(artifacts / "phase39_interpretation_readiness_information_architecture_index.json", index)

    report_md = f"""
# QRDS Phase 39 — Interpretation Readiness + Information Architecture

Gate: `{status['gate']}`

This phase creates a non-operational reading architecture for the QRDS Gate BTC Research Portal.
It improves comprehension through a reading guide, metric map, glossary, evidence boundaries,
candidate-history page, and decision-safety page.

## Safety

- operational_status: `{status['operational_status']}`
- edge_validated: `{status['edge_validated']}`
- shadow_decision_allowed: `{status['shadow_decision_allowed']}`
- decision_layer_allowed: `{status['decision_layer_allowed']}`
- trading_signal_generated: `{status['trading_signal_generated']}`
- recommendation_generated: `{status['recommendation_generated']}`
- allocation_generated: `{status['allocation_generated']}`
- canonical_data_writes: `{status['canonical_data_writes']}`

## Candidate interpretation

The four candidates from Phase 26 remain historical research candidates only.
Phases 27–29 left zero stable candidates and zero operational candidates.
""".strip() + "\n"
    atomic_write(artifacts / "phase39_interpretation_readiness_information_architecture.md", report_md)

    checksums: List[Dict[str, Any]] = []
    for path in sorted(artifacts.rglob("*")):
        if path.is_file() and path.name != "phase39_checksums.json" and not path.name.endswith(".zip"):
            checksums.append({"path": str(path.relative_to(artifacts)), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    write_json(artifacts / "phase39_checksums.json", {"gate": status["gate"], "files": checksums})

    zip_path = artifacts / "QRDS_PHASE39_INTERPRETATION_READINESS_INFORMATION_ARCHITECTURE_RESEARCH_ONLY.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(artifacts.rglob("*")):
            if path.is_file() and path != zip_path:
                zf.write(path, path.relative_to(artifacts))
    status["checksum_file_count"] = len(checksums)
    status["zip_path"] = str(zip_path.relative_to(root))
    write_json(artifacts / "phase39_interpretation_readiness_information_architecture.json", status)
    update_project_status(root, status)

    print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))
    return status


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate QRDS Phase 39 interpretation readiness information architecture.")
    parser.add_argument("--output-dir", "--out", "--portal-dir", dest="output_dir", default=None)
    args = parser.parse_args(argv)
    out_dir = Path(args.output_dir) if args.output_dir else None
    status = generate(out_dir)
    return 0 if status["gate"] == READY_GATE else 3


if __name__ == "__main__":
    raise SystemExit(main())
