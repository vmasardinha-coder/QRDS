from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import (
    LOCKS,
    ROOT,
    base_payload,
    read_json,
    sha256_file,
    utc_now_iso,
    validate_locks,
    write_json,
    write_text,
)

BASELINE_PHASE300_HEAD = "76322c9f84dfb29bac508296bf7800fdc607076e"
MIN_TEST_FILES = 529
MIN_TESTS = 1436


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _test_manifest() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((ROOT / "tests").rglob("test_*.py")):
        if not path.is_file():
            continue
        records.append(
            {
                "path": _rel(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def _assign_shards(records: list[dict[str, Any]], count: int = 3) -> list[list[dict[str, Any]]]:
    shards: list[list[dict[str, Any]]] = [[] for _ in range(count)]
    totals = [0] * count
    for record in sorted(records, key=lambda item: (-int(item["size_bytes"]), item["path"])):
        index = min(range(count), key=lambda item: (totals[item], item))
        shards[index].append(record)
        totals[index] += int(record["size_bytes"])
    for shard in shards:
        shard.sort(key=lambda item: item["path"])
    return shards


def _parse_junit(path: Path) -> dict[str, int]:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    for suite in suites:
        for key in totals:
            totals[key] += int(float(suite.attrib.get(key, "0") or "0"))
    return totals


def _git_status_paths() -> dict[str, str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    parts = [part for part in result.stdout.split(b"\0") if part]
    output: dict[str, str] = {}
    index = 0
    while index < len(parts):
        raw = parts[index].decode("utf-8", errors="surrogateescape")
        status = raw[:2]
        path = raw[3:].replace("\\", "/")
        if path.startswith("crypto_decision_lab/"):
            path = path[len("crypto_decision_lab/") :]
        if status and status[0] in {"R", "C"} and index + 1 < len(parts):
            index += 1
            path = parts[index].decode("utf-8", errors="surrogateescape").replace("\\", "/")
            if path.startswith("crypto_decision_lab/"):
                path = path[len("crypto_decision_lab/") :]
        output[path] = status
        index += 1
    return output


def _cleanup_test_side_effects(
    before: dict[str, str],
    protected_roots: tuple[str, ...] = (),
) -> dict[str, Any]:
    after = _git_status_paths()
    new_paths = sorted(set(after) - set(before))
    restored: list[str] = []
    removed: list[str] = []
    refused: list[str] = []
    generated_roots = (
        "artifacts/",
        "docs/reports/",
    )
    for relative in new_paths:
        if any(relative == root.rstrip("/") or relative.startswith(root.rstrip("/") + "/") for root in protected_roots):
            continue
        status = after[relative]
        candidate = (ROOT / relative).resolve()
        try:
            candidate.relative_to(ROOT.resolve())
        except ValueError:
            refused.append(relative)
            continue
        if status == "??":
            if not relative.startswith(generated_roots):
                refused.append(relative)
                continue
            if candidate.is_file() or candidate.is_symlink():
                candidate.unlink()
                removed.append(relative)
            elif candidate.is_dir():
                shutil.rmtree(candidate)
                removed.append(relative)
            continue
        result = subprocess.run(
            ["git", "checkout", "--", relative],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            restored.append(relative)
        else:
            refused.append(relative)
    if refused:
        raise RuntimeError(
            "Global-suite generated unexpected repository paths that were not automatically changed: "
            + ", ".join(refused)
        )
    return {
        "restored_tracked_paths": restored,
        "removed_generated_untracked_paths": removed,
        "refused_paths": refused,
    }


def _safe_name(relative: str) -> str:
    digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:12]
    stem = Path(relative).stem[:80]
    return f"{stem}_{digest}"


def run_resumable_full_suite(
    output_dir: Path,
    *,
    per_file_timeout_seconds: int = 1800,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    junit_dir = output_dir / "junit"
    log_dir = output_dir / "logs"
    junit_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    progress_path = output_dir / "phase305_full_suite_progress.json"

    manifest_before = _test_manifest()
    if len(manifest_before) < MIN_TEST_FILES:
        raise RuntimeError(
            f"Test inventory regression: expected at least {MIN_TEST_FILES}, found {len(manifest_before)}."
        )
    manifest_fingerprint = hashlib.sha256(
        json.dumps(manifest_before, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    shards = _assign_shards(manifest_before, 3)
    shard_by_path = {
        record["path"]: index
        for index, shard in enumerate(shards, start=1)
        for record in shard
    }

    existing: dict[str, Any] = {}
    if progress_path.is_file():
        try:
            loaded = read_json(progress_path)
            if loaded.get("manifest_fingerprint") == manifest_fingerprint:
                existing = dict(loaded.get("results", {}))
        except Exception:
            existing = {}

    baseline_status = _git_status_paths()
    protected_relative = _rel(output_dir).rstrip("/") + "/"
    results: dict[str, Any] = {}
    reused_count = 0
    executed_count = 0
    started = time.monotonic()

    for position, record in enumerate(manifest_before, start=1):
        relative = record["path"]
        cached = existing.get(relative)
        if (
            isinstance(cached, dict)
            and cached.get("sha256") == record["sha256"]
            and cached.get("status") == "PASS"
            and int(cached.get("returncode", 1)) == 0
            and not bool(cached.get("timed_out", False))
            and Path(str(cached.get("junit_path", ""))).is_file()
        ):
            try:
                cached_totals = _parse_junit(Path(cached["junit_path"]))
            except Exception:
                cached_totals = None
            if cached_totals and cached_totals["failures"] == 0 and cached_totals["errors"] == 0:
                item = dict(cached)
                item["reused"] = True
                item["junit"] = cached_totals
                results[relative] = item
                reused_count += 1
                print(f"[{position}/{len(manifest_before)}] REUSE PASS {relative}", flush=True)
                continue

        name = _safe_name(relative)
        junit_path = junit_dir / f"{name}.xml"
        log_path = log_dir / f"{name}.log"
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            f"--junitxml={junit_path}",
            str(ROOT / relative),
        ]
        print(f"[{position}/{len(manifest_before)}] RUN shard {shard_by_path[relative]} {relative}", flush=True)
        file_started = time.monotonic()
        timed_out = False
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=per_file_timeout_seconds,
                check=False,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = 124
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")

        duration = time.monotonic() - file_started
        log_path.write_text(
            f"COMMAND: {' '.join(command)}\nRETURN_CODE: {returncode}\nTIMED_OUT: {timed_out}\n"
            f"DURATION_SECONDS: {duration:.3f}\n\nSTDOUT\n{stdout}\n\nSTDERR\n{stderr}\n",
            encoding="utf-8",
        )
        junit_totals = (
            _parse_junit(junit_path)
            if junit_path.is_file()
            else {"tests": 0, "failures": 0, "errors": 1, "skipped": 0}
        )
        passed = (
            returncode == 0
            and not timed_out
            and junit_totals["failures"] == 0
            and junit_totals["errors"] == 0
        )
        item = {
            "path": relative,
            "sha256": record["sha256"],
            "shard": shard_by_path[relative],
            "status": "PASS" if passed else "FAIL",
            "returncode": returncode,
            "timed_out": timed_out,
            "duration_seconds": duration,
            "junit_path": str(junit_path),
            "log_path": str(log_path),
            "junit": junit_totals,
            "reused": False,
        }
        results[relative] = item
        executed_count += 1
        write_json(
            progress_path,
            {
                "phase": 305,
                "manifest_fingerprint": manifest_fingerprint,
                "updated_at_utc": utc_now_iso(),
                "test_file_count": len(manifest_before),
                "results": results,
            },
        )
        if not passed:
            cleanup = _cleanup_test_side_effects(baseline_status, (protected_relative,))
            raise RuntimeError(
                f"Global-suite failure in {relative}. Classification: TEST_OR_FIXTURE_FAILURE, not strategy failure. "
                f"Return code={returncode}, timed_out={timed_out}, junit={junit_totals}, log={log_path}, cleanup={cleanup}"
            )

    cleanup = _cleanup_test_side_effects(baseline_status, (protected_relative,))
    manifest_after = _test_manifest()
    manifest_stable = manifest_before == manifest_after
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for item in results.values():
        for key in totals:
            totals[key] += int(item["junit"][key])
    all_passed = (
        len(results) == len(manifest_before)
        and all(item["status"] == "PASS" for item in results.values())
        and totals["failures"] == 0
        and totals["errors"] == 0
        and totals["tests"] >= MIN_TESTS
        and manifest_stable
    )
    return {
        "mode": "RESUMABLE_FILEWISE_THREE_SHARD_MANIFEST",
        "started_at_utc": utc_now_iso(),
        "duration_seconds": time.monotonic() - started,
        "per_file_timeout_seconds": per_file_timeout_seconds,
        "test_file_count": len(manifest_before),
        "minimum_test_file_count": MIN_TEST_FILES,
        "minimum_tests": MIN_TESTS,
        "manifest_fingerprint": manifest_fingerprint,
        "manifest_before": manifest_before,
        "manifest_after": manifest_after,
        "manifest_stable": manifest_stable,
        "shard_count": 3,
        "shards": [
            {
                "shard": index,
                "file_count": len(shard),
                "total_bytes": sum(int(record["size_bytes"]) for record in shard),
                "files": [record["path"] for record in shard],
            }
            for index, shard in enumerate(shards, start=1)
        ],
        "reused_file_count": reused_count,
        "executed_file_count": executed_count,
        "all_files_completed": len(results) == len(manifest_before),
        "totals": totals,
        "cleanup": cleanup,
        "passed": all_passed,
    }


def _validate_phase_payload(payload: dict[str, Any], phase: int) -> None:
    assert payload["phase"] == phase
    validate_locks(payload["locks"])
    assert payload["valid_for_decision"] is False
    assert payload["historical_result_authorizes_execution"] is False


def _write_tracking(payload: dict[str, Any], tracking_dir: Path) -> None:
    full = payload["global_full_suite"]
    phase304 = payload["phase_chain"]["304"]
    mean_brl = float(phase304.get("outer_metrics_10bps", {}).get("mean_per_10000_brl", 0.0))
    lower_brl = float(phase304.get("outer_metrics_10bps", {}).get("lower_95_per_10000_brl", 0.0))
    approved = bool(phase304.get("strategy_approved", False))
    selection = bool(phase304.get("selection_stable", False))
    corrected = int(phase304.get("multiple_testing", {}).get("rejected_count", 0))
    practical = (
        "Nenhuma estrategia foi aprovada. Para R$10.000 teoricos, o resultado medio externo foi "
        f"R$ {mean_brl:,.2f} e o limite inferior de 95% foi R$ {lower_brl:,.2f}. "
        "Esses numeros descrevem pesquisa historica e nao autorizam uso de dinheiro."
    )
    master = f"""# QRDS Master Progress by Tens — Phase 305

**Baseline confirmada:** Phase 300, commit `{BASELINE_PHASE300_HEAD}`  
**Checkpoint:** `PHASE301_305_EVIDENCE_REGISTRY_V2_CHECKPOINT_PASS_RESEARCH_ONLY`  
**Framework readiness:** `100/100`  
**Evidence readiness operacional:** `0/100`  
**Operational readiness:** `0/100`

## O que as Phases 301–305 fizeram

- 301: ampliou o histórico público sem autenticação e registrou a linhagem.
- 302: criou features controladas somente com informação disponível no passado.
- 303: congelou 24 hipóteses e um orçamento máximo de 24 experimentos.
- 304: executou nested walk-forward, custos, regimes e correção de múltiplos testes.
- 305: executou a suíte global obrigatória e consolidou o checkpoint.

## Leitura prática

{practical}

## Travas

`BLOCKED_RESEARCH_ONLY` · `NO_ACTION_RESEARCH_ONLY` · posição `0` · capital `R$ 0`.
"""
    mermaid = """# QRDS Architecture Mermaid — Phase 305

```mermaid
flowchart LR
    A[DADOS PUBLICOS HISTORICOS] --> B[INTEGRIDADE E LINHAGEM]
    B --> C[FEATURE REGISTRY V2]
    C --> D[24 HIPOTESES CONGELADAS]
    D --> E[NESTED WALK-FORWARD]
    E --> F[CUSTOS REGIMES MULTIPLOS TESTES]
    F --> G{ESTRATEGIA APROVADA?}
    G -- NAO --> H[NO_ACTION_RESEARCH_ONLY]
    G -- SIM, HISTORICO APENAS --> H
    H --> I[VOCE ESTA AQUI]
    I --> J[AGUARDAR CANDIDATA ELEGIVEL E CONGELADA]
    J --> K[EVIDENCIA FORWARD SOMENTE FUTURA]
    K --> L[FORWARD SHADOW]
    L --> M[PAPER]
    M --> N[REAL]
```

**VOCE ESTA AQUI:** pesquisa histórica ampliada, ainda antes de uma candidata elegível congelada.
"""
    table = f"""# QRDS Progress Table by Tens — Phase 305

| Faixa | Entrega dominante | Estado |
|---|---|---|
| 0–245 | Fundação, integridade, replay e robustez | Concluído como pesquisa |
| 246–285 | Dados públicos, hipóteses, custos e calibração | Concluído; sem edge aprovado |
| 286–295 | Calibração e prontidão de shadow | Reprovado/bloqueado |
| 296–300 | Freeze, relógio forward, paper inativo e handoff | Concluído |
| **301–305** | **Histórico maior, features v2, 24 hipóteses, nested WF e suíte global** | **Checkpoint técnico PASS; estratégia aprovada = {approved}** |
| 306–315 | Diagnóstico de estabilidade e desenho de evidência forward | Planejado, research-only |

Suíte global: `{full['test_file_count']}` arquivos, `{full['totals']['tests']}` testes, `0` falhas, `0` erros, manifesto estável `{full['manifest_stable']}`.
"""
    milestone = f"""# QRDS Integrated Test Milestone 301–305

- Global full-suite passed: `{full['passed']}`
- Test files: `{full['test_file_count']}`
- Tests: `{full['totals']['tests']}`
- Failures: `{full['totals']['failures']}`
- Errors: `{full['totals']['errors']}`
- Manifest stable: `{full['manifest_stable']}`
- Reused file results on resume: `{full['reused_file_count']}`
- Executed file results: `{full['executed_file_count']}`
- Hypotheses tested: `24/24`
- Multiple-testing corrected rejections: `{corrected}`
- Selection stable: `{selection}`
- Strategy approved: `{approved}`
- Operational: `BLOCKED_RESEARCH_ONLY`
- Action: `NO_ACTION_RESEARCH_ONLY`
- Capital used: `R$ 0`

A falha estatística de uma hipótese não é falha de software. Este checkpoint só é PASS porque a infraestrutura e os testes passaram; ele não transforma pesquisa histórica em estratégia operacional.
"""
    roadmap = """# QRDS Roadmap 306–315 — Research Only

## Objetivo

Entender por que a seleção continua ou não estável, sem aumentar o orçamento de hipóteses e sem promover automaticamente qualquer resultado.

## Direção recomendada

- 306–308: auditoria de estabilidade temporal, concentração por regime e dependência entre hipóteses.
- 309–310: auditoria de custos extremos, liquidez e sensibilidade de timestamp.
- 311–313: protocolo de candidato elegível, sem congelar caso os gates falhem.
- 314: portal visual de decisão científica: aprovado/reprovado e o que não foi provado.
- 315: checkpoint integrado, tracking e decisão sobre continuar pesquisa ou encerrar a família.

## Proibição permanente

Nenhuma fase desta janela pode iniciar forward shadow, paper trading, ordem ou uso de capital automaticamente. Histórico positivo não conta como relógio forward.
"""
    snapshot = {
        "project": "QRDS/QOS/GATE BTC",
        "baseline_phase": 305,
        "baseline_phase300_head": BASELINE_PHASE300_HEAD,
        "readiness": {"framework": 100, "evidence": 0, "operational": 0},
        "global_full_suite": {
            "passed": full["passed"],
            "test_files": full["test_file_count"],
            "tests": full["totals"]["tests"],
            "failures": full["totals"]["failures"],
            "errors": full["totals"]["errors"],
            "manifest_stable": full["manifest_stable"],
        },
        "research_result": {
            "selected_hypothesis_id": phase304.get("modal_hypothesis_id"),
            "mean_result_per_10000_brl": mean_brl,
            "lower_95_per_10000_brl": lower_brl,
            "selection_stable": selection,
            "multiple_testing_rejected_count": corrected,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
        },
        "historical_evidence": {
            "expanded": True,
            "forward_evidence_credit": 0,
            "historical_backfill_to_forward_clock": False,
        },
        "safety": dict(LOCKS),
        "next_tracking_checkpoint": 315,
        "next_mandatory_global_full_suite": 325,
        "roadmap_window": "306-315",
    }
    write_text(tracking_dir / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE305.md", master)
    write_text(tracking_dir / "QRDS_ARCHITECTURE_MERMAID_PHASE305.md", mermaid)
    write_text(tracking_dir / "QRDS_PROGRESS_TABLE_BY_TENS_PHASE305.md", table)
    write_text(tracking_dir / "QRDS_INTEGRATED_TEST_MILESTONE_301_305.md", milestone)
    write_text(tracking_dir / "QRDS_ROADMAP_306_315_RESEARCH_ONLY.md", roadmap)
    write_json(tracking_dir / "qrds_progress_snapshot_phase305.json", snapshot)


def build_checkpoint(
    *,
    phase301_path: Path,
    phase302_path: Path,
    phase303_path: Path,
    phase304_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    tracking_dir: Path,
    full_suite_output_dir: Path,
    per_file_timeout_seconds: int = 1800,
) -> dict[str, Any]:
    phase301 = read_json(phase301_path)
    phase302 = read_json(phase302_path)
    phase303 = read_json(phase303_path)
    phase304 = read_json(phase304_path)
    for phase, item in ((301, phase301), (302, phase302), (303, phase303), (304, phase304)):
        _validate_phase_payload(item, phase)

    assert phase301["complete"] is True
    assert phase301["forward_evidence_credit"] == 0
    assert phase301["historical_backfill_to_forward_clock"] is False
    assert phase302["future_leakage_allowed"] is False
    assert phase302["features_use_closed_or_settled_data_only"] is True
    assert phase303["registry_closed"] is True
    assert phase303["experiment_budget"] == 24
    assert len(phase303["hypotheses"]) == 24
    assert phase304["strategy_approved"] is False
    assert phase304["forward_shadow_eligible"] is False

    full_suite = run_resumable_full_suite(
        full_suite_output_dir,
        per_file_timeout_seconds=per_file_timeout_seconds,
    )
    if not full_suite["passed"]:
        raise RuntimeError(f"Mandatory global full-suite did not pass: {full_suite}")

    payload = base_payload(305, "EVIDENCE_REGISTRY_V2_CHECKPOINT_PASS_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE305_EVIDENCE_REGISTRY_V2_FULL_INTEGRATION_READY_RESEARCH_ONLY",
            "batch_gate": "PHASE301_305_EVIDENCE_REGISTRY_V2_CHECKPOINT_PASS_RESEARCH_ONLY",
            "baseline_phase300_head": BASELINE_PHASE300_HEAD,
            "phase_chain": {
                "301": {
                    "gate": phase301["gate"],
                    "complete": phase301["complete"],
                    "max_candle_rows": phase301["max_candle_rows"],
                    "successful_candle_providers": phase301["successful_candle_providers"],
                    "forward_evidence_credit": 0,
                },
                "302": {
                    "gate": phase302["gate"],
                    "feature_count": phase302["feature_count"],
                    "future_leakage_allowed": phase302["future_leakage_allowed"],
                },
                "303": {
                    "gate": phase303["gate"],
                    "hypothesis_count": len(phase303["hypotheses"]),
                    "maximum_experiments": phase303["experiment_budget"],
                    "registry_closed": phase303["registry_closed"],
                },
                "304": {
                    "gate": phase304["gate"],
                    "selected_hypothesis_id": phase304.get("modal_hypothesis_id"),
                    "mean_result_per_10000_brl": phase304.get("outer_metrics_10bps", {}).get("mean_per_10000_brl", 0.0),
                    "lower_95_per_10000_brl": phase304.get("outer_metrics_10bps", {}).get("lower_95_per_10000_brl", 0.0),
                    "selection_stable": phase304.get("selection_stable", False),
                    "multiple_testing_rejected_count": phase304.get("multiple_testing", {}).get("rejected_count", 0),
                    "strategy_approved": False,
                    "forward_shadow_eligible": False,
                },
            },
            "global_full_suite": full_suite,
            "window_integration_passed": True,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
            "historical_backfill_to_forward_clock": False,
            "forward_evidence_credit": 0,
            "next_tracking_checkpoint": 315,
            "next_mandatory_global_full_suite": 325,
        }
    )
    write_json(artifact_path, payload)
    _write_tracking(payload, tracking_dir)
    write_text(
        documentation_path,
        f"""# Phase 305 — Evidence Registry V2 Full Integration Checkpoint

Gate: `{payload['gate']}`  
Batch gate: `{payload['batch_gate']}`

- Global full-suite: `PASS`
- Test files: `{full_suite['test_file_count']}`
- Tests: `{full_suite['totals']['tests']}`
- Failures: `{full_suite['totals']['failures']}`
- Errors: `{full_suite['totals']['errors']}`
- Manifest stable: `{full_suite['manifest_stable']}`
- Strategy approved: `False`
- Forward shadow eligible: `False`
- Historical forward evidence credit: `0`
- Operational: `BLOCKED_RESEARCH_ONLY`
- Action: `NO_ACTION_RESEARCH_ONLY`
- Capital used: `R$ 0`

This checkpoint proves that the expanded research pipeline and the complete software test inventory are internally consistent. It does not prove a tradable edge and does not authorize execution.
""",
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument("--phase301-artifact", type=Path, default=artifacts / "phase301_official_public_history_extension_research_only/phase301_official_public_history_extension.json")
    parser.add_argument("--phase302-artifact", type=Path, default=artifacts / "phase302_controlled_feature_registry_v2_research_only/phase302_controlled_feature_registry_v2.json")
    parser.add_argument("--phase303-artifact", type=Path, default=artifacts / "phase303_finite_hypothesis_registry_v2_research_only/phase303_finite_hypothesis_registry_v2.json")
    parser.add_argument("--phase304-artifact", type=Path, default=artifacts / "phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json")
    parser.add_argument("--artifact", type=Path, default=artifacts / "phase305_evidence_registry_v2_full_integration_checkpoint_research_only/phase305_evidence_registry_v2_full_integration_checkpoint.json")
    parser.add_argument("--documentation", type=Path, default=ROOT / "docs/reports/integration/phase305_evidence_registry_v2_full_integration_checkpoint_summary.md")
    parser.add_argument("--tracking-dir", type=Path, default=ROOT / "docs/reports/project_tracking")
    parser.add_argument("--full-suite-output-dir", type=Path, default=artifacts / "phase305_evidence_registry_v2_full_integration_checkpoint_research_only/full_suite")
    parser.add_argument("--per-file-timeout-seconds", type=int, default=1800)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_checkpoint(
        phase301_path=args.phase301_artifact,
        phase302_path=args.phase302_artifact,
        phase303_path=args.phase303_artifact,
        phase304_path=args.phase304_artifact,
        artifact_path=args.artifact,
        documentation_path=args.documentation,
        tracking_dir=args.tracking_dir,
        full_suite_output_dir=args.full_suite_output_dir,
        per_file_timeout_seconds=args.per_file_timeout_seconds,
    )
    full = payload["global_full_suite"]
    print(payload["gate"])
    print(payload["batch_gate"])
    print("Global full-suite: PASS")
    print("Test files:", full["test_file_count"])
    print("Tests:", full["totals"]["tests"])
    print("Failures:", full["totals"]["failures"])
    print("Errors:", full["totals"]["errors"])
    print("Manifest stable:", full["manifest_stable"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Forward shadow eligible:", payload["forward_shadow_eligible"])
    print("Operational:", payload["locks"]["operational_status"])
    print("Action:", payload["locks"]["action_status"])
    print("Capital used:", payload["locks"]["capital_used"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
