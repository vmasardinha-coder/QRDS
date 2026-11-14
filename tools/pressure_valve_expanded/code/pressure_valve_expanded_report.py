"""Daily JSON/CSV and self-contained HTML/SVG views; no trading or source mutation."""
import csv,html,json,math,statistics,zipfile
from collections import defaultdict,Counter
from pathlib import Path
from pressure_valve_expanded import load,save,STRICT,DIAG,at

def dd(values):
    cum=0.;peak=0.;worst=0.
    for v in values:cum+=v;peak=max(peak,cum);worst=min(worst,cum-peak)
    return worst
def corr(xs,ys):
    if len(xs)<2 or len(ys)!=len(xs):return None
    mx=statistics.mean(xs);my=statistics.mean(ys);vx=sum((x-mx)**2 for x in xs);vy=sum((y-my)**2 for y in ys)
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(vx*vy) if vx>0 and vy>0 else None
def csvfile(path,rows,fields):
    with Path(path).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',delimiter=';');w.writeheader();w.writerows(rows)
def basket_sim(records,basket,h,scenario,bar_files):
    ids=basket['families'];eligible=[r for r in records if r['policy']==basket['policy']];days=[];curve=[];offset=0.;peak=0.;worst=0.;gross_exposure=0;net_exposure=0;notional_peak=0.;concentration=defaultdict(float);invalid=[];closed_total=0;cost_total=0.;gross_total=0.;pnl_by_day=[]
    delayed=scenario=='DELAYED_REF';fee=.0003 if scenario=='STRESS' else .0002
    for rec in sorted(eligible,key=lambda r:r['session']):
        obs={o['family_id']:o for o in rec['families']};trades=[];daily={fid:0. for fid in ids};valid=True;day_gross=0.;day_cost=0.
        for fid in ids:
            row=obs.get(fid)
            if row is None or row['state'] not in ['NO_SIGNAL','TRIGGER']:
                valid=False;invalid.append({'session':rec['session'],'family':fid,'reason':row['state'] if row else 'MISSING_FAMILY'});continue
            if row['state']=='NO_SIGNAL':continue
            o=next((x for x in row['outcomes'] if x['horizon_minutes']==h and x['state']=='MODEL_CLOSED'),None)
            if o is None or o['value_per_point_brl'] is None:valid=False;continue
            prefix='delayed_' if delayed else '';e=o[prefix+'entry_timestamp'];x=o[prefix+'exit_timestamp'];ep=o[prefix+'entry_price'];xp=o[prefix+'exit_price'];point=o['value_per_point_brl'];side=o['side'];cost=ep*point*fee;gross=side*(xp-ep)*point
            trades.append({'family':fid,'entry':e,'exit':x,'ep':ep,'xp':xp,'point':point,'side':side,'cost':cost});daily[fid]=gross-cost
            day_cost+=cost;day_gross+=gross
        if not valid:continue
        raw=bar_files.get(rec['session']);prices={r['timestamp']:r['open'] for r in raw['rows']} if raw else {}
        if trades and not prices:invalid.append({'session':rec['session'],'reason':'MISSING_MTM_BARS'});continue
        closed_total+=len(trades);cost_total+=day_cost;gross_total+=day_gross
        pnl_by_day.append({'session':rec['session'],'pnl_brl':sum(daily.values()),'by_family':daily});days.append(rec['session'])
        for ts,price in sorted(prices.items()):
            pnl=0.;active=[]
            for t in trades:
                if ts<t['entry']:continue
                px=t['xp'] if ts>=t['exit'] else float(price)
                pnl+=t['side']*(px-t['ep'])*t['point']-t['cost']
                if t['entry']<=ts<t['exit']:active.append(t);concentration[t['family']]+=1
            equity=offset+pnl;peak=max(peak,equity);worst=min(worst,equity-peak);curve.append({'timestamp':ts,'equity_brl':equity,'gross_contracts':len(active),'net_contracts':sum(t['side'] for t in active)})
            gross_exposure=max(gross_exposure,len(active));net_exposure=max(net_exposure,abs(sum(t['side'] for t in active)));notional_peak=max(notional_peak,sum(t['ep']*t['point'] for t in active))
        offset+=sum(daily.values())
    n=len(pnl_by_day);pair=[]
    for i,a in enumerate(ids):
        for b in ids[i+1:]:pair.append({'family_a':a,'family_b':b,'sessions':n,'correlation':corr([d['by_family'][a] for d in pnl_by_day],[d['by_family'][b] for d in pnl_by_day])})
    total=sum(concentration.values());hhi=sum((v/total)**2 for v in concentration.values()) if total else None
    return {'basket':basket['name'],'policy':basket['policy'],'families':ids,'selection_rule':basket['selection_rule'],'horizon':h,'scenario':scenario,'sessions':n,'closed_positions':closed_total,'gross_brl':gross_total if n else None,'cost_brl':cost_total if n else None,'net_brl':offset if n else None,'drawdown_closed_brl':dd([x['pnl_brl'] for x in pnl_by_day]) if n else None,'drawdown_mtm_brl':worst if n else None,'max_gross_contracts':gross_exposure if n else None,'max_abs_net_contracts':net_exposure if n else None,'max_gross_notional_brl':notional_peak if n else None,'concentration_contract_time_hhi':hhi,'family_contract_time_shares':{k:v/total for k,v in concentration.items()} if total else {},'correlations':pair,'curve':curve,'daily':pnl_by_day,'invalid_sessions':invalid,'state':'MEASURED' if n and not invalid else ('INCOMPLETE_DATA' if invalid else 'WAIT_POST_ACTIVATION_SESSION'),'reserve_for_losses_brl':None,'margin_required_brl':None}
def svg(points):
    if not points:return '<svg viewBox="0 0 900 230"><text x="25" y="110" fill="#526171" font-size="20">Aguardando observações após a ativação. Sem curva econômica ainda.</text></svg>'
    vals=[p['equity_brl'] for p in points];lo=min(0,min(vals));hi=max(0,max(vals));span=max(1,hi-lo)
    xy=' '.join(f'{25+850*i/max(1,len(vals)-1):.2f},{200-175*(v-lo)/span:.2f}' for i,v in enumerate(vals))
    return f'<svg viewBox="0 0 900 230"><polyline points="{xy}" fill="none" stroke="#246ab5" stroke-width="2"/><text x="25" y="225">R$ {vals[-1]:.2f}; curva líquida, uma saída por cenário</text></svg>'
def build(root):
    root=Path(root);cfg=load(root/'CONFIG.json');seed=load(root/'initialization/SEED.json');out=root/'reports';out.mkdir(exist_ok=True)
    records=[]
    for policy in [STRICT,DIAG]:
        for p in sorted((root/'ledger'/policy).glob('*.json')):
            r=load(p)
            assert r['session']>=cfg['activation_date'] and r['kind']=='POST_ACTIVATION_OBSERVATION','MIXED_HISTORY_OR_VALIDATION'
            records.append(r)
    daily=[];families=[];lookup=defaultdict(list)
    for rec in records:
        for row in rec['families']:
            lookup[(rec['policy'],row['family_id'])].append((rec,row))
            for h in [30,60,120]:
                o=next((x for x in row['outcomes'] if x['horizon_minutes']==h),{})
                daily.append({'session':rec['session'],'policy':rec['policy'],'family_id':row['family_id'],'horizon':h,'signal_state':row['state'],'outcome_state':o.get('state'),'reason':row.get('reason'),'z':row.get('z'),'history_available':row['history_available'],'missing':row['missing'],**o})
    for f,initial in zip(cfg['families'],seed['status']):
        c=f['contract'];rows=lookup[(f['policy'],c['family_id'])]
        for h in [30,60,120]:
            outs=[next((x for x in r['outcomes'] if x['horizon_minutes']==h and x['state']=='MODEL_CLOSED'),None) for _,r in rows];valid=[x for x in outs if x]
            measured=bool(valid) or any(r['state']=='NO_SIGNAL' for _,r in rows)
            sums={k:sum(o[k] for o in valid) if measured else None for k in ['gross_bps','net_ref_2bps','net_stress_3bps','delayed_net_ref_2bps']}
            families.append({'family_id':c['family_id'],'policy':f['policy'],'feature':c['feature'],'direction':c['direction'],'window':c['decision_window_minutes'],'lookback':c['standardization_lookback_sessions'],'threshold':c['abs_z_threshold'],'initialized':initial['ready'],'seed_observations':initial['available'],'seed_missing':initial['missing'],'sessions_captured':len(rows),'sessions_evaluated':sum(r['state'] in ['NO_SIGNAL','TRIGGER','TRIGGER_OUTCOME_INCOMPLETE'] for _,r in rows),'no_signal':sum(r['state']=='NO_SIGNAL' for _,r in rows),'triggers':sum(r['state'].startswith('TRIGGER') for _,r in rows),'closed':len(valid),'horizon':h,**sums,'drawdown_closed_bps':dd([o['net_ref_2bps'] for o in valid]) if rows else None,'last_session':rows[-1][0]['session'] if rows else None,'last_state':rows[-1][1]['state'] if rows else ('INITIALIZED_WAIT_ACTIVATION' if initial['ready'] else 'WARMUP_PENDING'),'cost_ref_bps':2,'cost_stress_bps':3,'delay_bars':1})
    bar_files={}
    for p in sorted((root/'captures').glob('*.json')):
        r=load(p);bar_files[r['session']]=r
    baskets=[basket_sim(records,b,h,s,bar_files) for b in cfg['baskets'] for h in [30,60,120] for s in ['REF','STRESS','DELAYED_REF']]
    summary={'activation_date':cfg['activation_date'],'seed_cutoff':seed['cutoff'],'installed':580,'unique_initialized':sum(x['ready'] for x in seed['status']),'blocked_initialization':sum(not x['ready'] for x in seed['status']),'post_activation_records':len(records),'families':families,'baskets':baskets,'margin':load(root/'MARGIN.json') if (root/'MARGIN.json').exists() else load(root/'validation/MARGIN.json') if (root/'validation/MARGIN.json').exists() else None,'selection_rule':'Contracts and technical eligibility frozen before reading P&L; basket membership fixed before activation; horizons are alternatives.','legacy_series_untouched':True,'canonical_credit':0,'orders_sent':0}
    current=[]
    for f,initial in zip(cfg['families'],seed['status']):
        rows=lookup[(f['policy'],f['contract']['family_id'])];last=rows[-1][1] if rows else None
        current.append({'family_id':f['contract']['family_id'],'policy':f['policy'],'state':last['state'] if last else initial['state'],'available':last['history_available'] if last else initial['available'],'missing':last['missing'] if last else initial['missing'],'ready':(last['missing']==0 and last['mad'] is not None and last['mad']>0) if last else initial['ready'],'reason':last.get('reason') if last else initial['reason']})
    summary['current_readiness']=current;summary['current_initialized']=sum(x['ready'] for x in current);summary['current_blocked']=sum(not x['ready'] for x in current)
    save(out/'SUMMARY.json',summary);save(out/'DAILY_HISTORY.json',daily);save(out/'INITIALIZATION_STATUS.json',seed['status']);save(out/'CURRENT_READINESS.json',current)
    timetable=[]
    for f in cfg['families']:
        c=f['contract'];w=c['decision_window_minutes']
        for h in c['holding_horizons_minutes']:
            timetable.append({'family_id':c['family_id'],'policy':f['policy'],'feature':c['feature'],'direction':c['direction'],'lookback':c['standardization_lookback_sessions'],'threshold':c['abs_z_threshold'],'horizon':h,'window_start':'09:00','window_end':at('2026-10-22',w).strftime('%H:%M'),'entry':at('2026-10-22',w).strftime('%H:%M'),'exit':at('2026-10-22',w+h).strftime('%H:%M'),'delayed_entry':at('2026-10-22',w+5).strftime('%H:%M'),'delayed_exit':at('2026-10-22',w+h+5).strftime('%H:%M'),'last_bar_closed_at':at('2026-10-22',w+h+10).strftime('%H:%M'),'timezone':cfg['timezone']})
    csvfile(out/'TIMETABLE.csv',timetable,list(timetable[0]));save(out/'TIMETABLE.json',timetable)
    csvfile(out/'FAMILIES.csv',families,list(families[0]));csvfile(out/'INITIALIZATION.csv',seed['status'],list(seed['status'][0]))
    fields=['session','policy','family_id','horizon','signal_state','outcome_state','reason','z','history_available','missing','entry_timestamp','exit_timestamp','entry_price','exit_price','gross_bps','net_ref_2bps','net_stress_3bps','delayed_net_ref_2bps','gross_brl','cost_ref_brl','cost_stress_brl']
    csvfile(out/'DAILY_HISTORY.csv',daily,fields)
    bflat=[{k:v for k,v in b.items() if not isinstance(v,(list,dict))} for b in baskets];csvfile(out/'BASKETS.csv',bflat,list(bflat[0]))
    data=json.dumps({'families':families,'daily':daily,'baskets':baskets},ensure_ascii=False).replace('</','<\\/')
    table=''.join(f'<tr><td>{html.escape(b["basket"])}</td><td>{b["horizon"]}</td><td>{b["scenario"]}</td><td>{b["sessions"]}</td><td>{b["net_brl"] if b["net_brl"] is not None else "Indisponível"}</td><td>{b["state"]}</td></tr>' for b in baskets)
    page='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Pressure Valve ampliado</title><style>body{font:16px Arial;margin:32px;color:#17365d}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:7px;border-bottom:1px solid #ddd;text-align:left}select{font-size:16px;padding:8px}svg{width:100%;max-height:270px}section{margin:22px 0}p{color:#526171}</style>'''
    page+=f'<h1>Pressure Valve ampliado</h1><p>Ativação: {cfg["activation_date"]}. Inicialização histórica separada; 26 QA de sessão + 490 diagnósticas; 64 bloqueadas. Nenhuma ordem real.</p><p>Referência: 2 bps por operação completa; estresse: 3 bps; atraso: uma barra M5, com 2 bps. Cestas e horizontes alternativos não se somam.</p>'
    page+='<section><label>Família e horizonte <select id="family"></select></label><p id="familyinfo"></p><div id="familychart"></div></section><section><label>Cesta e cenário <select id="basket"></select></label><div id="basketinfo"></div><div id="basketchart"></div></section>'
    page+='<table><thead><tr><th>Cesta</th><th>Horizonte</th><th>Cenário</th><th>Sessões</th><th>Líquido R$</th><th>Estado</th></tr></thead><tbody>'+table+'</tbody></table><p>Margem efetiva da corretora e reserva para perdas: indisponíveis enquanto não verificadas. Retorno de patrimônio não calculado.</p>'
    page+='<script>const D='+data+''';function chart(vals){if(!vals.length)return '<p>Aguardando observações após a ativação. Sem curva econômica ainda.</p>';let lo=Math.min(0,...vals),hi=Math.max(0,...vals),sp=Math.max(1,hi-lo);return '<svg viewBox="0 0 900 230"><polyline fill="none" stroke="#246ab5" stroke-width="2" points="'+vals.map((v,i)=>(25+850*i/Math.max(1,vals.length-1))+','+(200-175*(v-lo)/sp)).join(' ')+'"/></svg>'}D.families.forEach((f,i)=>family.add(new Option(f.family_id+' / '+f.policy+' / '+f.horizon+' min',i)));function ff(){let f=D.families[+family.value];familyinfo.textContent='Estado: '+f.last_state+'; sessões: '+f.sessions_captured+'; gatilhos: '+f.triggers+'; fechadas: '+f.closed+'; líquido: '+(f.net_ref_2bps??'indisponível')+' bps';let a=0,v=D.daily.filter(x=>x.family_id===f.family_id&&x.policy===f.policy&&x.horizon===f.horizon&&x.outcome_state==='MODEL_CLOSED').map(x=>a+=x.net_ref_2bps);familychart.innerHTML=chart(v)}family.onchange=ff;ff();D.baskets.forEach((b,i)=>basket.add(new Option(b.basket+' / '+b.horizon+' min / '+b.scenario,i)));function bb(){let b=D.baskets[+basket.value];basketinfo.textContent='Estado: '+b.state+'; líquido R$: '+(b.net_brl??'indisponível')+'; DD MTM R$: '+(b.drawdown_mtm_brl??'indisponível')+'; contratos simultâneos: '+(b.max_gross_contracts??'indisponível');basketchart.innerHTML=chart(b.curve.map(x=>x.equity_brl))}basket.onchange=bb;bb();</script></html>'''
    (out/'DASHBOARD.html').write_text(page,encoding='utf-8')
    try:
        import pressure_valve_intracycle
        pressure_valve_intracycle.build(root,cfg,records,bar_files)
        link='<p><a href="INTRACYCLE.html">Abrir curvas durante o ciclo: alvo, stop, trailing e lotes</a></p>'
        dashboard=out/'DASHBOARD.html'
        dashboard.write_text(dashboard.read_text(encoding='utf-8').replace('<section>',link+'<section>',1),encoding='utf-8')
    except Exception as exc:
        save(out/'INTRACYCLE_STATUS.json',{'state':'RESEARCH_REPORT_ERROR','error':str(exc),'orders':0})
        dashboard=out/'DASHBOARD.html'
        dashboard.write_text(dashboard.read_text(encoding='utf-8').replace('<section>','<p>Pesquisa intraciclo indisponível: consultar INTRACYCLE_STATUS.json.</p><section>',1),encoding='utf-8')
    downloads=Path.home()/'Downloads' 
    if downloads.exists():
        label=max(r['session'] for r in records) if records else 'INICIALIZACAO_20261021'
        export=downloads/f'QRDS_PRESSURE_VALVE_EXPANDED_{label}.zip'
        with zipfile.ZipFile(export,'w',zipfile.ZIP_DEFLATED) as z:
            for file in out.glob('*'):
                if file.is_file():z.write(file,'reports/'+file.name)
            for rel in ['STATUS.json','MARGIN.json','initialization/SEED.json','INSTALL_RECEIPT.json']:
                if (root/rel).exists():z.write(root/rel,rel)
    print(json.dumps({'report':str(out),'families':580,'initialized':summary['unique_initialized'],'post_activation_records':len(records),'orders':0}))
    return summary
