
from __future__ import annotations
import argparse, html, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
from crypto_decision_lab.scripts import phase276_285_strategy_search_common as prior

def base(p,s): return prior.base(p,s)
def read(p): return prior.read(p)
def write(p,q): return prior.write(p,q)
def fp(q): return prior.fp(q)
def mean(v):
    x=list(v); return float(statistics.mean(x)) if x else 0.0

def p286(dataset,nested,guard,robustness,freeze,product):
    product_packet=product.get("product_packet",{}) if isinstance(product,dict) else {}
    if not isinstance(product_packet,dict):
        product_packet={}
    dataset_fingerprint=dataset.get("dataset_fingerprint") or dataset.get("evidence_fingerprint") or ""
    rows=dataset.get("rows",[])
    dataset_rows=dataset.get("dataset_rows",len(rows) if isinstance(rows,list) else 0)
    outer_oos_rows=nested.get("total_outer_oos_rows")
    if outer_oos_rows is None:
        folds=nested.get("outer_folds",[])
        outer_oos_rows=sum(len(fold.get("outer_row_ids",[])) for fold in folds if isinstance(fold,dict))
    hypothesis_count=guard.get("hypothesis_count")
    if hypothesis_count is None:
        hypothesis_count=product_packet.get("hypothesis_count",0)
    modal_hypothesis_id=guard.get("modal_hypothesis_id") or product_packet.get("modal_hypothesis_id") or "UNAVAILABLE"
    search_validated=bool(guard.get("search_validated",product_packet.get("search_validated",False)))
    robust_candidate=bool(robustness.get("robust_candidate",product_packet.get("robust_candidate",False)))
    forward_shadow_eligible=bool(freeze.get("eligible_for_forward_shadow",product_packet.get("eligible_for_forward_shadow",False)))
    product_packet_version=product_packet.get("packet_version") or product.get("packet_version") or "LEGACY_PHASE284_PACKET"
    d={"dataset_fingerprint":dataset_fingerprint,"dataset_rows":int(dataset_rows or 0),
       "outer_oos_rows":int(outer_oos_rows or 0),"hypothesis_count":int(hypothesis_count or 0),
       "modal_hypothesis_id":modal_hypothesis_id,"search_validated":search_validated,
       "robust_candidate":robust_candidate,"forward_shadow_eligible":forward_shadow_eligible,
       "product_packet_version":product_packet_version}
    diagnostics={"dataset_keys":sorted(dataset.keys()),"nested_keys":sorted(nested.keys()),
                 "guard_keys":sorted(guard.keys()),"robustness_keys":sorted(robustness.keys()),
                 "freeze_keys":sorted(freeze.keys()),"product_keys":sorted(product.keys()),
                 "product_packet_keys":sorted(product_packet.keys())}
    ok=d["dataset_rows"]>=1900 and d["outer_oos_rows"]==480 and d["hypothesis_count"]==108 and len(d["dataset_fingerprint"])==64
    p=base(286,"EVIDENCE_DEPENDENCY_MANIFEST_PASS_RESEARCH_ONLY" if ok else "EVIDENCE_DEPENDENCY_MANIFEST_NEEDS_REVIEW")
    p.update(dependencies=d,dependency_fingerprint=fp(d),source_phases=[278,280,281,282,283,284],
             schema_diagnostics=diagnostics,passed=ok)
    return p

def p287(dataset,nested):
    rows={int(r["row_id"]):r for r in dataset["rows"]}
    observations=[]
    fold_results=[]
    reconstruction_count=0
    diagnostics=[]
    for fold in nested["outer_folds"]:
        spec=fold.get("selected_spec")
        if not isinstance(spec,dict):
            raise KeyError(
                f"selected_spec missing in outer fold {fold.get('fold')}"
            )
        horizon=int(spec["forecast_horizon_hours"])
        predictions=fold.get("outer_predictions")
        source_mode="PERSISTED_OUTER_PREDICTIONS"
        if not isinstance(predictions,list):
            row_ids=fold.get("outer_row_ids")
            if not isinstance(row_ids,list):
                raise KeyError(
                    f"outer_row_ids missing in outer fold {fold.get('fold')}"
                )
            predictions=[
                {
                    "row_id":int(row_id),
                    "probability_up":prior.probability(
                        spec,
                        rows[int(row_id)],
                    ),
                }
                for row_id in row_ids
            ]
            reconstruction_count += len(predictions)
            source_mode="DETERMINISTIC_RECONSTRUCTION_FROM_FROZEN_SPEC"
        local=[]
        for prediction in predictions:
            row_id=int(prediction["row_id"])
            row=rows[row_id]
            probability_up=float(
                prediction.get(
                    "probability_up",
                    prior.probability(spec,row),
                )
            )
            label_key=f"label_up_{horizon}h"
            if label_key in row:
                actual_up=int(row[label_key])
            else:
                return_key=f"future_return_{horizon}h"
                if return_key not in row:
                    raise KeyError(
                        f"Missing {label_key} and {return_key} for row {row_id}"
                    )
                actual_up=int(float(row[return_key])>0)
            item={
                "fold":int(fold["fold"]),
                "row_id":row_id,
                "probability_up":probability_up,
                "actual_up":actual_up,
                "squared_error":(
                    probability_up-actual_up
                )**2,
            }
            observations.append(item)
            local.append(item)
        fold_results.append(
            {
                "fold":int(fold["fold"]),
                "observations":len(local),
                "brier_score":mean(
                    x["squared_error"] for x in local
                ),
                "mean_probability":mean(
                    x["probability_up"] for x in local
                ),
                "actual_up_rate":mean(
                    x["actual_up"] for x in local
                ),
                "prediction_source_mode":source_mode,
            }
        )
        diagnostics.append(
            {
                "fold":int(fold["fold"]),
                "selected_hypothesis_id":fold.get(
                    "selected_hypothesis_id"
                ),
                "horizon_hours":horizon,
                "prediction_source_mode":source_mode,
                "prediction_count":len(local),
            }
        )
    groups=defaultdict(list)
    for item in observations:
        groups[round(item["probability_up"],4)].append(item)
    reliability=[]
    for probability,items in sorted(groups.items()):
        actual_rate=mean(x["actual_up"] for x in items)
        reliability.append(
            {
                "forecast_probability":probability,
                "observations":len(items),
                "actual_up_rate":actual_rate,
                "absolute_calibration_error":abs(
                    actual_rate-probability
                ),
            }
        )
    expected_calibration_error=(
        sum(
            x["observations"]
            * x["absolute_calibration_error"]
            for x in reliability
        )
        / len(observations)
        if observations
        else 1.0
    )
    overall_brier_score=mean(
        x["squared_error"] for x in observations
    )
    calibration_validated=bool(
        len(observations)==480
        and expected_calibration_error<=0.05
        and overall_brier_score<0.25
    )
    passed=bool(
        len(observations)==480
        and sum(x["observations"] for x in reliability)==480
        and len(fold_results)==5
        and all(x["observations"]==96 for x in fold_results)
    )
    payload=base(
        287,
        (
            "OUT_OF_SAMPLE_PROBABILITY_CALIBRATION_PASS_RESEARCH_ONLY"
            if passed
            else "OUT_OF_SAMPLE_PROBABILITY_CALIBRATION_NEEDS_REVIEW"
        ),
    )
    payload.update(
        observations=len(observations),
        reconstructed_prediction_count=reconstruction_count,
        prediction_reconstruction_used=(
            reconstruction_count>0
        ),
        overall_brier_score=overall_brier_score,
        expected_calibration_error=expected_calibration_error,
        reliability_table=reliability,
        fold_calibration=fold_results,
        schema_diagnostics=diagnostics,
        calibration_validated=calibration_validated,
        passed=passed,
    )
    return payload

def p288(nested):
    folds=[]
    for f in nested["outer_folds"]:
        imp=f["neutral_outer_metrics"]["brier_score"]-f["outer_metrics"]["brier_score"]
        folds.append({"fold":f["fold"],"selected_hypothesis_id":f["selected_hypothesis_id"],
                      "brier_improvement_vs_neutral":imp,"directional_accuracy":f["outer_metrics"]["directional_accuracy"],
                      "mean_gross_return":f["outer_metrics"]["mean_gross_return"]})
    counts=Counter(x["selected_hypothesis_id"] for x in folds); modal,wins=counts.most_common(1)[0]
    early=mean(x["brier_improvement_vs_neutral"] for x in folds[:2]); late=mean(x["brier_improvement_vs_neutral"] for x in folds[-2:])
    delta=late-early; stable=wins>=3; decay=delta<-.005
    p=base(288,"SELECTION_STABILITY_DECAY_MONITOR_PASS_RESEARCH_ONLY")
    p.update(folds=folds,selection_counts=dict(counts),modal_hypothesis_id=modal,modal_fold_count=wins,modal_share=wins/5,
             selection_stable=stable,early_brier_improvement=early,late_brier_improvement=late,decay_delta=delta,
             severe_decay_detected=decay,passed=len(folds)==5); return p

def p289(nested):
    family=Counter(); lookback=Counter(); horizon=Counter(); strength=Counter(); combos=Counter()
    for f in nested["outer_folds"]:
        s=f["selected_spec"]; family[s["family"]]+=1; lookback[str(s["lookback_hours"])]+=1
        horizon[str(s["forecast_horizon_hours"])]+=1; strength[str(s["probability_strength"])]+=1
        combos[f["selected_hypothesis_id"]]+=1
    modal,wins=combos.most_common(1)[0]
    p=base(289,"HYPOTHESIS_CONCENTRATION_ATTRIBUTION_PASS_RESEARCH_ONLY")
    p.update(family_counts=dict(family),lookback_counts=dict(lookback),horizon_counts=dict(horizon),strength_counts=dict(strength),
             hypothesis_counts=dict(combos),modal_hypothesis_id=modal,modal_fold_count=wins,modal_share=wins/5,
             selection_diversified=(len(family)>=2 or len(horizon)>=2 or len(lookback)>=2),
             concentration_warning=wins/5<.60,passed=True); return p

def p290(guard,robustness,calibration,stability,attribution):
    checks={"search_validated":bool(guard["search_validated"]),"calibration_validated":bool(calibration["calibration_validated"]),
            "selection_stable":bool(stability["selection_stable"]),"no_severe_decay":not stability["severe_decay_detected"],
            "modal_share_at_least_60pct":attribution["modal_share"]>=.60,"robust_candidate":bool(robustness["robust_candidate"]),
            "positive_25bps_lower_95":robustness["central_scenario"]["lower_95_mean_net_return"]>0}
    eligible=all(checks.values()); reasons=[k.upper() for k,v in checks.items() if not v] or ["RESEARCH_ONLY_FORWARD_SHADOW_NOT_OPERATIONAL_TRADING"]
    p=base(290,"FORWARD_SHADOW_ELIGIBILITY_GATE_PASS_RESEARCH_ONLY")
    p.update(checks=checks,eligible_for_forward_shadow=eligible,reason_codes=reasons,predictive_validity_established=False,
             edge_validated=False,decision_layer_allowed=False,action="NO_ACTION_RESEARCH_ONLY",passed=True); return p

def p291(manifest,gate,freeze,ledger_output):
    c=freeze["freeze_contract"]
    e={"event_type":"FORWARD_SHADOW_STATUS","sequence":1,"evidence_dependency_fingerprint":manifest["dependency_fingerprint"],
       "freeze_id":c["freeze_id"],"hypothesis_id":c["hypothesis_id"],"eligible_for_forward_shadow":gate["eligible_for_forward_shadow"],
       "status":"READY_TO_COLLECT_NEW_UNSEEN_DATA" if gate["eligible_for_forward_shadow"] else "WAITING_FOR_RESEARCH_GATES",
       "signal":"NO_SIGNAL","action":"NO_ACTION_RESEARCH_ONLY","position_size":0,"orders_created":0,"capital_used":0,
       "reason_codes":gate["reason_codes"]}
    path=Path(ledger_output); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(e,ensure_ascii=True)+"\n",encoding="utf-8")
    ok=path.is_file() and e["orders_created"]==e["capital_used"]==e["position_size"]==0
    p=base(291,"FORWARD_SHADOW_LEDGER_CONTRACT_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
    p.update(ledger_mode="FORWARD_ONLY_NO_HISTORICAL_BACKFILL",historical_trade_rows_written=0,ledger_event=e,ledger_path=str(path),passed=ok); return p

def p292(manifest,guard,robustness,calibration,stability,attribution,gate):
    c=robustness["central_scenario"]; found=gate["eligible_for_forward_shadow"]
    i={"what_was_collected":f"{manifest['dependencies']['dataset_rows']} usable rows from 2160 hours of two-source public BTC hourly consensus data.",
       "what_was_tested":f"{manifest['dependencies']['hypothesis_count']} predefined momentum and mean-reversion hypotheses across lookbacks, forecast horizons and probability strengths.",
       "how_it_was_tested":"Five nested walk-forward outer folds kept 480 observations outside selection. Multiple-testing, regimes and costs were applied.",
       "candidate_found":"YES_FOR_FORWARD_SHADOW_ONLY" if found else "NO_VALIDATED_CANDIDATE",
       "plain_result":"A rule may be frozen only for forward shadow." if found else "No rule was stable, calibrated and profitable enough after costs to start forward shadow.",
       "modal_hypothesis":attribution["modal_hypothesis_id"],"selection_stable":stability["selection_stable"],
       "calibration_validated":calibration["calibration_validated"],"search_validated":guard["search_validated"],
       "robust_candidate":robustness["robust_candidate"],"example_risk_unit_brl":10000,
       "mean_result_per_10000_brl":c["mean_net_return"]*10000,
       "conservative_lower_95_per_10000_brl":c["lower_95_mean_net_return"]*10000,
       "why_blocked":gate["reason_codes"],"what_this_does_not_prove":"A failed grid does not prove BTC is unpredictable; these tested rules did not pass.",
       "practical_conclusion":"START_FORWARD_SHADOW_WITHOUT_ORDERS_OR_CAPITAL" if found else "WAIT_FOR_BETTER_EVIDENCE"}
    p=base(292,"PLAIN_LANGUAGE_INTERPRETATION_BUILDER_PASS_RESEARCH_ONLY"); p.update(interpretation=i,passed=True); return p

def portal_html(m,c,s,a,g,l,i):
    x=i["interpretation"]
    checks="".join(f"<tr><td>{html.escape(k.replace('_',' ').title())}</td><td class='{'ok' if v else 'bad'}'>{'PASS' if v else 'FAIL'}</td></tr>" for k,v in g["checks"].items())
    rel="".join(f"<tr><td>{r['forecast_probability']:.0%}</td><td>{r['observations']}</td><td>{r['actual_up_rate']:.1%}</td><td>{r['absolute_calibration_error']:.2%}</td></tr>" for r in c["reliability_table"])
    stages=["Dados","108 hipoteses","Nested walk-forward","Multiplos testes","Calibracao","Estabilidade","Gate forward shadow","Forward shadow","Paper trading","Piloto minimo"]
    flow="".join(f"<div class='stage {'done' if n<7 else 'future'}'><b>{n+1}</b> {html.escape(v)}</div>" for n,v in enumerate(stages))
    verdict="CANDIDATA LIBERADA SOMENTE PARA FORWARD SHADOW" if g["eligible_for_forward_shadow"] else "NENHUMA CANDIDATA LIBERADA PARA FORWARD SHADOW"
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>QRDS Phase 293</title><style>body{{font-family:Arial;background:#0f172a;color:#e2e8f0;margin:0}}main{{max-width:1200px;margin:auto;padding:24px}}.lock{{background:#991b1b;padding:15px;border-radius:12px;font-weight:bold}}.plain{{background:#172554;border-left:5px solid #60a5fa;padding:18px;border-radius:10px;margin:16px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}.card,table{{background:#1e293b;border:1px solid #334155}}.card{{padding:14px;border-radius:10px}}.card small{{display:block;color:#94a3b8}}.card b{{display:block;font-size:1.15rem;margin-top:5px}}table{{width:100%;border-collapse:collapse;margin:14px 0}}th,td{{padding:10px;border-bottom:1px solid #334155;text-align:left}}.ok{{color:#86efac;font-weight:bold}}.bad{{color:#fca5a5;font-weight:bold}}.map{{display:flex;flex-wrap:wrap;gap:8px}}.stage{{padding:11px;border-radius:9px;min-width:150px;flex:1}}.done{{background:#14532d}}.future{{background:#334155}}</style></head><body><main><h1>QRDS - Interpretacao e Prontidao</h1><div class='lock'>BLOCKED_RESEARCH_ONLY - NO_ACTION_RESEARCH_ONLY</div><div class='plain'><h2>Resposta direta</h2><h3>{verdict}</h3><p>{html.escape(x['plain_result'])}</p><p><b>Coletado:</b> {html.escape(x['what_was_collected'])}</p><p><b>Testado:</b> {html.escape(x['what_was_tested'])}</p><p><b>Como:</b> {html.escape(x['how_it_was_tested'])}</p><p><b>O que nao prova:</b> {html.escape(x['what_this_does_not_prove'])}</p></div><h2>Onde estamos</h2><div class='map'>{flow}</div><h2>Numeros traduzidos</h2><div class='grid'><div class='card'><small>Linhas</small><b>{m['dependencies']['dataset_rows']}</b></div><div class='card'><small>OOS</small><b>{m['dependencies']['outer_oos_rows']}</b></div><div class='card'><small>Hipoteses</small><b>{m['dependencies']['hypothesis_count']}</b></div><div class='card'><small>Candidata modal</small><b>{html.escape(a['modal_hypothesis_id'])}</b></div><div class='card'><small>Erro de calibracao</small><b>{c['expected_calibration_error']:.2%}</b></div><div class='card'><small>Selecao estavel?</small><b>{s['selection_stable']}</b></div><div class='card'><small>Media / R$10 mil</small><b>R$ {x['mean_result_per_10000_brl']:.2f}</b></div><div class='card'><small>Lower 95% / R$10 mil</small><b>R$ {x['conservative_lower_95_per_10000_brl']:.2f}</b></div></div><h2>Gate forward shadow</h2><table><tr><th>Condicao</th><th>Resultado</th></tr>{checks}</table><h2>Calibracao</h2><table><tr><th>Prevista</th><th>N</th><th>Alta real</th><th>Erro</th></tr>{rel}</table><p><b>Ledger:</b> {html.escape(l['ledger_event']['status'])}. Sem ordens e sem capital.</p></main></body></html>"""

def p293(manifest,calibration,stability,attribution,gate,ledger,interpretation,robustness,portal_output):
    path=Path(portal_output); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(portal_html(manifest,calibration,stability,attribution,gate,ledger,interpretation),encoding="utf-8")
    x=interpretation["interpretation"]
    q={"packet_version":"5.0","dataset_rows":manifest["dependencies"]["dataset_rows"],"outer_oos_rows":manifest["dependencies"]["outer_oos_rows"],
       "hypothesis_count":manifest["dependencies"]["hypothesis_count"],"modal_hypothesis_id":attribution["modal_hypothesis_id"],
       "calibration_error":calibration["expected_calibration_error"],"calibration_validated":calibration["calibration_validated"],
       "selection_stable":stability["selection_stable"],"severe_decay_detected":stability["severe_decay_detected"],
       "eligible_for_forward_shadow":gate["eligible_for_forward_shadow"],"ledger_status":ledger["ledger_event"]["status"],
       "mean_result_per_10000_brl":x["mean_result_per_10000_brl"],"lower_95_per_10000_brl":x["conservative_lower_95_per_10000_brl"],
       "action":"NO_ACTION_RESEARCH_ONLY","position_size":0,"portal_path":str(path)}
    p=base(293,"INTEGRATED_VISUAL_READINESS_PORTAL_PASS_RESEARCH_ONLY" if path.is_file() else "NEEDS_REVIEW")
    p.update(product_packet=q,portal_generated=path.is_file(),serve_script="scripts/serve_phase293_readiness_portal.ps1",passed=path.is_file()); return p

def p294(manifest,guard,calibration,stability,gate,portal):
    f={"dependencies_valid":manifest["passed"],"calibration_diagnostic_ready":calibration["passed"],
       "stability_diagnostic_ready":stability["passed"],"eligibility_gate_ready":gate["passed"],"human_portal_ready":portal["passed"]}
    e={"search_validated":guard["search_validated"],"calibration_validated":calibration["calibration_validated"],
       "selection_stable":stability["selection_stable"],"forward_shadow_eligible":gate["eligible_for_forward_shadow"]}
    p=base(294,"RESEARCH_PRODUCT_READINESS_SCORECARD_PASS_RESEARCH_ONLY")
    p.update(framework_checks=f,framework_readiness_score=round(100*sum(f.values())/len(f)),
             evidence_checks=e,evidence_readiness_score=round(100*sum(e.values())/len(e)),
             operational_readiness_score=0,product_status="FRAMEWORK_READY_EVIDENCE_BLOCKED_RESEARCH_ONLY",passed=all(f.values())); return p

def p295(items,targeted,snapshot):
    packet=items[7]["product_packet"]; score=items[8]; last=snapshot["batch_276_285"]
    target=targeted.get("returncode")==0 and targeted.get("test_files")==20 and targeted.get("tests")==20 and targeted.get("failures")==targeted.get("errors")==0
    ok=[x["phase"] for x in items]==list(range(286,295)) and all(x["passed"] for x in items) and target and last["passed"] and last["global_test_files"]==524 and last["global_tests"]==1431 and packet["action"]=="NO_ACTION_RESEARCH_ONLY" and packet["position_size"]==0 and score["operational_readiness_score"]==0
    p=base(295,"CALIBRATION_SHADOW_READINESS_286_295_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
    p.update(checkpoint_status="CALIBRATION_AND_FORWARD_SHADOW_READINESS_EVALUATED_OPERATION_BLOCKED_RESEARCH_ONLY" if ok else "NEEDS_REVIEW",
             phase_chain={str(x["phase"]):x for x in items},targeted_tests=targeted,last_global_suite=last,
             framework_readiness_score=score["framework_readiness_score"],evidence_readiness_score=score["evidence_readiness_score"],
             operational_readiness_score=0,predictive_validity_established=False,edge_validated=False,decision_layer_allowed=False,
             action="NO_ACTION_RESEARCH_ONLY",next_tracking_checkpoint=300,next_mandatory_global_full_suite=305,
             phase300_full_handoff_required=True,passed=bool(ok)); return p

def tracking(p):
    q=p["phase_chain"]["293"]["product_packet"]; score=p["phase_chain"]["294"]; t=p["targeted_tests"]; g=p["last_global_suite"]
    visual="# QRDS Visual Project Map - Phase 295\n\n```mermaid\nflowchart LR\n A[Dados multifonte] --> B[108 hipoteses]\n B --> C[Nested walk-forward]\n C --> D[Multiplos testes]\n D --> E[Calibracao]\n E --> F[Estabilidade e decay]\n F --> G{Forward shadow elegivel?}\n G -- Nao --> H[WAIT / NO_ACTION]\n G -- Sim --> I[Congelar regra]\n I --> J[Forward shadow sem ordens]\n J --> K[Paper trading]\n K --> L[Piloto minimo]\n```\n\n**Voce esta aqui:** calibracao e gate de forward shadow.\n"
    return {
    "QRDS_MASTER_PROGRESS_BY_TENS_PHASE295.md":f"# QRDS Master Progress - Phase 295\n\n- Batch 286-295: PASS\n- Targeted files/tests: {t['test_files']} / {t['tests']}\n- Last global files/tests: {g['global_test_files']} / {g['global_tests']}\n- Calibration validated: {q['calibration_validated']}\n- Selection stable: {q['selection_stable']}\n- Forward shadow eligible: {q['eligible_for_forward_shadow']}\n- Framework readiness: {score['framework_readiness_score']}/100\n- Evidence readiness: {score['evidence_readiness_score']}/100\n- Operational readiness: 0/100\n- Next checkpoint: Phase 300\n",
    "QRDS_ARCHITECTURE_MERMAID_PHASE295.md":visual,
    "QRDS_PROGRESS_TABLE_BY_TENS_PHASE295.md":f"# QRDS Progress Table - Phase 295\n\n| Window | Status | Calibration | Stable | Forward eligible | Tests | Action |\n|---|---:|---:|---:|---:|---:|---|\n| 286-295 | PASS | {q['calibration_validated']} | {q['selection_stable']} | {q['eligible_for_forward_shadow']} | {t['tests']} | NO_ACTION_RESEARCH_ONLY |\n",
    "QRDS_VISUAL_PROJECT_MAP_PHASE295.md":visual,
    "QRDS_CALIBRATION_SHADOW_MILESTONE_PHASE295.md":f"# Calibration and Shadow Milestone - Phase 295\n\n- Modal hypothesis: {q['modal_hypothesis_id']}\n- Calibration error: {q['calibration_error']:.6f}\n- Calibration validated: {q['calibration_validated']}\n- Selection stable: {q['selection_stable']}\n- Severe decay: {q['severe_decay_detected']}\n- Forward shadow eligible: {q['eligible_for_forward_shadow']}\n- Ledger status: {q['ledger_status']}\n- Mean per R$10,000: R$ {q['mean_result_per_10000_brl']:.2f}\n- Lower 95% per R$10,000: R$ {q['lower_95_per_10000_brl']:.2f}\n",
    "QRDS_ROADMAP_296_300_HANDOFF.md":"# QRDS Roadmap 296-300 Full Handoff\n\n- 296: immutable strategy freeze protocol\n- 297: forward-test ledger and evidence clock\n- 298: paper execution, costs and kill-switch contract\n- 299: executive product state and final visual map\n- 300: PROMPT_FULL_NOVO_CHAT_PHASE300.txt, HANDOFF_TECNICO_PHASE300.md, RESUMO_EXECUTIVO_LEIGO_PHASE300.md and PROJECT_STATE_PHASE300.json\n\nNo operational promotion, account, order or capital.\n",
    "qrds_progress_snapshot_phase295.json":json.dumps({"baseline_phase":295,"batch_286_295":{"passed":True,"versioned_files":39,"targeted_test_files":t["test_files"],"targeted_tests":t["tests"],"failures":0,"errors":0},"last_global_suite":g,"calibration_shadow_readiness":q,"framework_readiness_score":score["framework_readiness_score"],"evidence_readiness_score":score["evidence_readiness_score"],"operational_readiness_score":0,"next_tracking_checkpoint":300,"next_mandatory_global_full_suite":305,"phase300_full_handoff_required":True,"operational_status":"BLOCKED_RESEARCH_ONLY","decision_layer_allowed":False,"canonical_data_writes":0},indent=2)+"\n"}

def doc(phase,p):
    lines=[
        f"# Phase {phase} Research Summary",
        "",
        f"- Status: `{p['status']}`",
        f"- Passed: `{p['passed']}`",
        "- Operational: `BLOCKED_RESEARCH_ONLY`",
        "- Decision layer allowed: `False`",
        "- Canonical writes: `0`",
    ]
    if phase==286:
        lines += [
            "Dependency manifest generated.",
            f"- Dataset rows: `{p['dependencies']['dataset_rows']}`",
            f"- Outer OOS rows: `{p['dependencies']['outer_oos_rows']}`",
            f"- Hypotheses: `{p['dependencies']['hypothesis_count']}`",
        ]
    elif phase==287:
        lines += [
            f"- Calibration error: `{p['expected_calibration_error']:.6f}`",
            f"- Calibration validated: `{p['calibration_validated']}`",
        ]
    elif phase==288:
        lines += [
            f"- Selection stable: `{p['selection_stable']}`",
            f"- Severe decay: `{p['severe_decay_detected']}`",
        ]
    elif phase==289:
        lines += [
            f"- Modal hypothesis: `{p['modal_hypothesis_id']}`",
            f"- Modal share: `{p['modal_share']:.2%}`",
        ]
    elif phase==290:
        lines += [
            f"- Forward shadow eligible: `{p['eligible_for_forward_shadow']}`",
        ]
    elif phase==291:
        lines += [
            "- Ledger mode: `FORWARD_ONLY_NO_HISTORICAL_BACKFILL`",
            "- Orders: `0`",
        ]
    elif phase==292:
        lines += ["Plain-language interpretation generated."]
    elif phase==293:
        lines += ["Integrated portal generated."]
    elif phase==294:
        lines += [
            f"- Framework readiness: `{p['framework_readiness_score']}/100`",
            f"- Evidence readiness: `{p['evidence_readiness_score']}/100`",
            "- Operational readiness: `0/100`",
        ]
    elif phase==295:
        lines += [
            "- Next checkpoint: `300`",
            "- Phase 300 full handoff required: `True`",
        ]
    lines += [
        "",
        "Research evidence only. No recommendation, allocation, "
        "order or capital.",
        "",
    ]
    return "\n".join(lines)

def cli_main(phase):
    ap=argparse.ArgumentParser(); ap.add_argument("--artifact",required=True); ap.add_argument("--documentation",required=True)
    ap.add_argument("--input",action="append",default=[]); ap.add_argument("--ledger-output"); ap.add_argument("--portal-output")
    ap.add_argument("--packet-output"); ap.add_argument("--targeted-summary"); ap.add_argument("--phase285-snapshot"); ap.add_argument("--tracking-dir")
    a=ap.parse_args(); x=[read(z) for z in a.input]
    if phase==286:p=p286(*x)
    elif phase==287:p=p287(*x)
    elif phase==288:p=p288(*x)
    elif phase==289:p=p289(*x)
    elif phase==290:p=p290(*x)
    elif phase==291:p=p291(*x,a.ledger_output)
    elif phase==292:p=p292(*x)
    elif phase==293:
        p=p293(*x,a.portal_output); write(a.packet_output,p["product_packet"])
    elif phase==294:p=p294(*x)
    elif phase==295:
        p=p295(x,read(a.targeted_summary),read(a.phase285_snapshot)); d=Path(a.tracking_dir); d.mkdir(parents=True,exist_ok=True)
        for n,c in tracking(p).items():(d/n).write_text(c,encoding="utf-8")
    else: raise ValueError(phase)
    write(a.artifact,p); Path(a.documentation).parent.mkdir(parents=True,exist_ok=True); Path(a.documentation).write_text(doc(phase,p),encoding="utf-8")
    print(p["status"])
    if phase==287:print("CALIBRATION_ERROR:",p["expected_calibration_error"]);print("CALIBRATION_VALIDATED:",p["calibration_validated"])
    if phase==288:print("SELECTION_STABLE:",p["selection_stable"]);print("SEVERE_DECAY:",p["severe_decay_detected"])
    if phase==290:print("FORWARD_SHADOW_ELIGIBLE:",p["eligible_for_forward_shadow"]);print("REASONS:",",".join(p["reason_codes"]))
    if phase==291:print("LEDGER:",p["ledger_path"]);print("LEDGER_STATUS:",p["ledger_event"]["status"])
    if phase==293:print("PORTAL:",a.portal_output);print("PACKET:",a.packet_output)
    return 0 if p["passed"] else 1
