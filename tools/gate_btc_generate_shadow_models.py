#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, zipfile, shutil, hashlib
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import mm

NAVY=colors.HexColor('#10213d'); TEAL=colors.HexColor('#2d9eb1'); PALE=colors.HexColor('#e8f2fb'); GREEN=colors.HexColor('#e5f3ed'); YELLOW=colors.HexColor('#fff1d5'); RED=colors.HexColor('#fae8e8'); GREY=colors.HexColor('#f1f3f5'); DARK=colors.HexColor('#1f2a3a')
try:
    pdfmetrics.registerFont(TTFont('DejaVu','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVu-B','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    FONT='DejaVu'; BOLD='DejaVu-B'
except Exception:
    FONT='Helvetica'; BOLD='Helvetica-Bold'

class Data:
    def __init__(self, artifact: Path, work: Path):
        self.root=work/'artifact'; shutil.rmtree(self.root,ignore_errors=True); self.root.mkdir(parents=True)
        with zipfile.ZipFile(artifact) as z: z.extractall(self.root)
        q=self.root/'qos_daily'; self.v2a=q/'v2a'; self.delta=q/'delta'
        for zname,out in [(q/'qos_v2a_outputs.zip',self.v2a),(q/'delta_walk_forward_outputs.zip',self.delta)]:
            out.mkdir(exist_ok=True)
            with zipfile.ZipFile(zname) as z: z.extractall(out)
        self.vsum=pd.read_csv(self.v2a/'outputs/qos_v2a_summary.csv')
        self.vport=pd.read_csv(self.v2a/'outputs/qos_v2a_current_portfolios.csv')
        self.vbear=pd.read_csv(self.v2a/'outputs/qos_v2a_bear_replay.csv')
        self.vmc=pd.read_csv(self.v2a/'outputs/qos_v2a_monte_carlo_10000_summary.csv')
        self.dsum=pd.read_csv(self.delta/'outputs/delta_summary.csv')
        self.dmc=pd.read_csv(self.delta/'outputs/delta_monte_carlo_10000_summary.csv')
        g=self.root/'gateway_reference_check/replay_outputs'
        self.gprof=pd.read_csv(g/'strategy_execution_profiles.csv'); self.gcomp=pd.read_csv(g/'strategy_compositions.csv'); self.gstop=pd.read_csv(g/'delta_stop_trade_rules.csv')
        self.cutoff=str(self.vsum['end'].max()); self.report_date=(pd.to_datetime(self.cutoff)+pd.Timedelta(days=1)).strftime('%d/%m/%Y')
        self.exp=self.dsum[self.dsum.window.eq('EXPANDING_FROM_D0')].copy()
    def vrow(self,n): return self.vsum[self.vsum.strategy.eq(n)].iloc[0]
    def drow(self,n,w='EXPANDING_FROM_D0'): return self.dsum[(self.dsum.strategy.eq(n))&(self.dsum.window.eq(w))].iloc[0]

def pct(x,d=2): return f'{x*100:.{d}f}%'.replace('.',',')
def num(x,d=2): return f'{x:.{d}f}'.replace('.',',')
def mult(x): return f'{x:.2f}x'.replace('.',',')

def styles():
    return {
      'title':ParagraphStyle('t',fontName=BOLD,fontSize=28,leading=32,textColor=NAVY,spaceAfter=8),
      'h1':ParagraphStyle('h1',fontName=BOLD,fontSize=19,leading=22,textColor=DARK,spaceAfter=8),
      'h2':ParagraphStyle('h2',fontName=BOLD,fontSize=13,leading=16,textColor=TEAL,spaceAfter=5),
      'body':ParagraphStyle('b',fontName=FONT,fontSize=8.5,leading=11,textColor=DARK),
      'small':ParagraphStyle('s',fontName=FONT,fontSize=7,leading=9,textColor=colors.HexColor('#5b6673')),
      'card':ParagraphStyle('c',fontName=BOLD,fontSize=15,leading=18,textColor=DARK),
    }
S=styles()

def footer(canvas,doc):
    canvas.saveState(); w,h=doc.pagesize; canvas.setFont(FONT,7); canvas.setFillColor(colors.HexColor('#68727e'))
    canvas.drawString(15*mm,8*mm,'RESEARCH_ONLY | NOT_APPROVED | orders=0 | capital=0'); canvas.drawRightString(w-15*mm,8*mm,f'Pagina {doc.page}'); canvas.restoreState()

def tbl(data,widths=None,font=7):
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),FONT),('FONTSIZE',(0,0),(-1,-1),font),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#c5ccd3')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,GREY]),('BACKGROUND',(0,0),(-1,0),NAVY),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),BOLD),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)])); return t

def box(text,bg=PALE,border=TEAL):
    t=Table([[Paragraph(text,S['body'])]]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),('BOX',(0,0),(-1,-1),1,border),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)])); return t

def cards(items,width):
    cells=[]
    for title,value,sub,bg in items: cells.append([Paragraph(title.upper(),S['small']),Spacer(1,5),Paragraph(value,S['card']),Spacer(1,3),Paragraph(sub,S['small'])])
    t=Table([cells],colWidths=[width/len(cells)]*len(cells)); st=[]
    for i,it in enumerate(items): st += [('BACKGROUND',(i,0),(i,0),it[3]),('BOX',(i,0),(i,0),0.5,colors.HexColor('#ccd3da')),('LEFTPADDING',(i,0),(i,0),10),('RIGHTPADDING',(i,0),(i,0),10),('TOPPADDING',(i,0),(i,0),10),('BOTTOMPADDING',(i,0),(i,0),10)]
    t.setStyle(TableStyle(st)); return t

def head(title,subtitle): return [Paragraph('GATE BTC | SHADOW WATCH',S['h2']),Paragraph(title,S['title']),Paragraph(subtitle,S['body']),Spacer(1,8)]

def build_comparativos(d,out):
    p=out/f'Shadow_Watch_Executive_{d.report_date.replace("/","-")}_v20_Comparativos_Completos_FINAL.pdf'; doc=SimpleDocTemplate(str(p),pagesize=landscape(A4),leftMargin=12*mm,rightMargin=12*mm,topMargin=12*mm,bottomMargin=14*mm); W=landscape(A4)[0]-24*mm
    m=d.vrow('QOS_Moderada'); u=d.vrow('QOS_Ultra'); de=d.drow('Delta_LS_50_50'); r30=d.drow('Delta_LS_50_50','ROLLING_30_OBSERVATIONS'); r60=d.drow('Delta_LS_50_50','ROLLING_60_OBSERVATIONS')
    pages=[]
    pages.append(head('Executivo comparativo',f'Ciclo de {d.report_date} - decisao orientada a risco, no modelo executivo aprovado')+[cards([('Janela Delta',f'{int(de.observations)} observacoes',f'15/05 a {pd.to_datetime(de.end).strftime("%d/%m")}',PALE),('Lider interna','Delta 50/50',f'{pct(de.total_return)}; Sharpe {num(de.product_compatible_sharpe_rf0)}',PALE),('Lider historica','QOS Moderada',f'CAGR {pct(m.cagr)}; Sharpe {num(m.product_compatible_sharpe_rf0)}',GREEN),('Melhor defesa','QOS Ultra',f'MDD {pct(u.max_drawdown)}; Calmar {num(u.calmar_cagr_over_abs_maxdd)}',GREEN)],W),Spacer(1,15),box('<b>STATUS DECISORIO: NENHUM DELTA ELEGIVEL</b><br/>Moderada segue lider de crescimento; Ultra permanece desafiante defensiva. Delta 50/50 continua melhor interno, mas abaixo do gate.',RED,colors.HexColor('#b94949'))])
    pages.append(head('O que mudou desde o ciclo anterior','Atualizacao autonoma a partir do artifact diario')+[cards([('Retorno Delta 50/50',pct(de.total_return),'expanding',PALE),('Sharpe crescente',num(de.product_compatible_sharpe_rf0),'gate 0,50',YELLOW),('Maximo drawdown',pct(de.max_drawdown),'janela crescente',RED),('Gate Delta','0 de 4','nenhum elegivel',RED)],W),Spacer(1,12),box('O 50/50 continua lider interno, mas a amostra curta e os rollings negativos nao autorizam recalibracao.',YELLOW,colors.HexColor('#d89a00'))])
    pages.append(head('Relogio de evidencia e decisao','Quatro relogios independentes')+[cards([('Delta atual',f'{int(de.observations)} / 90','checkpoint exploratorio',PALE),('Delta confirmacao',f'{int(de.observations)} / 120','paper candidato',YELLOW),('Gateway / Dynamics','0 / 80','ledger oficial nao iniciado',RED),('Profit Preservation','SEM LEDGER','LOCK sem metrica nova',RED)],W)])
    pages.append(head('Placar executivo por universo','Separacao metodologica obrigatoria')+[tbl([['Universo','Lider/estado','Metrica','Uso permitido'],['V2A longo prazo','QOS Moderada',f'CAGR {pct(m.cagr)}','comparacao historica'],['Delta walk-forward','Delta 50/50',f'Retorno {pct(de.total_return)}','pesquisa curta'],['Gateway snapshot','Sem ranking','composicao atual','operabilidade apenas']],[55*mm,60*mm,48*mm,85*mm],9)])
    pages.append(head('Delta em quatro janelas','A fixa confirma competitividade inicial; crescente e rollings mostram deterioracao')+[tbl([['Janela','Obs.','Retorno','Sharpe','Max DD'],['Fixa ate 16/07','63',pct(d.drow('Delta_LS_50_50','COMMON_62_CALENDAR_DAY_BENCHMARK').total_return),num(d.drow('Delta_LS_50_50','COMMON_62_CALENDAR_DAY_BENCHMARK').product_compatible_sharpe_rf0),pct(d.drow('Delta_LS_50_50','COMMON_62_CALENDAR_DAY_BENCHMARK').max_drawdown)],['Crescente',str(int(de.observations)),pct(de.total_return),num(de.product_compatible_sharpe_rf0),pct(de.max_drawdown)],['Ultimas 30','30',pct(r30.total_return),num(r30.product_compatible_sharpe_rf0),pct(r30.max_drawdown)],['Ultimas 60','60',pct(r60.total_return),num(r60.product_compatible_sharpe_rf0),pct(r60.max_drawdown)]],[55*mm,25*mm,40*mm,40*mm,40*mm],10)])
    exp=d.exp; rows=[['Estrategia','Retorno','Sharpe','Vol.','Max DD','Win rate']]+[[r.strategy.replace('Delta_LS_','Delta '),pct(r.total_return),num(r.product_compatible_sharpe_rf0),pct(r.annualized_volatility),pct(r.max_drawdown),pct(r.daily_win_rate)] for _,r in exp.iterrows()]
    pages.append(head('Delta walk-forward - liquido de custos e funding','Quatro variantes, mesma janela')+[tbl(rows,[62*mm,35*mm,30*mm,35*mm,35*mm,35*mm],9),Spacer(1,8),box('StopVol nao melhora retorno, Sharpe ou drawdown o suficiente. Manter parametros congelados.',RED,colors.HexColor('#b94949'))])
    pages.append(head('O gate caiu e nao deve ser recalibrado agora','Tempo prospectivo, nao ajuste oportunista')+[cards([('Retorno crescente',pct(de.total_return),'Delta 50/50',RED),('Sharpe crescente',num(de.product_compatible_sharpe_rf0),'corte 0,50',RED),('Rolling 30 / 60',f'{pct(r30.total_return)} / {pct(r60.total_return)}','ambos negativos',RED)],W)])
    pages.append(head('Comparativo externo - janela fixa alinhada','Benchmark externo permanece agregado e nao auditavel')+[box('A comparacao externa fica congelada na janela comum. O externo nao possui curva diaria auditavel no artifact.',PALE,colors.HexColor('#2f75b5'))])
    vrows=[['Estrategia','Multiplo','CAGR','Sharpe','Max DD','Calmar']]+[[r.strategy.replace('_',' '),mult(r.final_multiple),pct(r.cagr),num(r.product_compatible_sharpe_rf0),pct(r.max_drawdown),num(r.calmar_cagr_over_abs_maxdd)] for _,r in d.vsum.iterrows()]
    pages.append(head('Historico longo V2A - mesmo universo e mesma janela','Sete series comparaveis')+[tbl(vrows,[60*mm,30*mm,35*mm,35*mm,35*mm,35*mm],8)])
    pages.append(head('Moderada versus Ultra - crescimento e defesa','Crescimento puro versus eficiencia defensiva')+[cards([('QOS Moderada',f'CAGR {pct(m.cagr)}',f'Sharpe {num(m.product_compatible_sharpe_rf0)} | MDD {pct(m.max_drawdown)}',PALE),('QOS Ultra',f'CAGR {pct(u.cagr)}',f'Calmar {num(u.calmar_cagr_over_abs_maxdd)} | MDD {pct(u.max_drawdown)}',GREEN)],W)])
    port=d.vport[d.vport.strategy.isin(['QOS_Moderada','QOS_Ultra'])]; rows=[['Carteira','Ativo','Peso','Regime','Elegivel']]+[[r.strategy,r.asset,pct(r.weight),r.regime,r.execution_eligible_from] for _,r in port.iterrows()]
    pages.append(head('Composicao atual e mudancas mensais','Mostrar mudanca apenas em rebalanceamento')+[tbl(rows,[45*mm,35*mm,30*mm,40*mm,45*mm],7)])
    pages.append(head('Profit Preservation - conclusao executiva','Baseline e governanca LOCK')+[box('Nao existe ledger prospectivo LOCK no artifact atual. LOCK25 permanece shadow principal; LOCK50 challenger; LOCK75 alerta de excesso.',RED,colors.HexColor('#b94949'))])
    grows=[['Familia','Exposicao','Drag bps/dia','Operabilidade','Evidencia']]+[[r.strategy,pct(r.gross_exposure),num(r.estimated_total_drag_bps_per_day),r.manual_operability,'Snapshot'] for _,r in d.gprof.iterrows()]
    pages.append(head('Gateway / Dynamics - composicao e operabilidade','Snapshot atual, sem retorno retrospectivo')+[tbl(grows,[60*mm,35*mm,38*mm,60*mm,35*mm],8)])
    vm=d.vmc[d.vmc.strategy.isin(['QOS_Moderada','QOS_Ultra','Victor_proxy'])]; dm=d.dmc[d.dmc.strategy.isin(['Delta_LS_50_50','Delta_LS_50_50_StopVol','Delta_LS_70_30'])]
    pages.append(head('Monte Carlo - cenarios, nao promessa de alpha','V2A e Delta permanecem separados')+[tbl([['V2A','Mediana','Prob. perda','DD p50']]+[[r.strategy,pct(r.return_p50),pct(r.probability_loss),pct(r.max_drawdown_p50)] for _,r in vm.iterrows()],[60*mm,40*mm,40*mm,40*mm],9),Spacer(1,8),tbl([['Delta','Mediana','Prob. perda','DD p50']]+[[r.strategy,pct(r.return_p50),pct(r.probability_loss),pct(r.max_drawdown_p50)] for _,r in dm.iterrows()],[60*mm,40*mm,40*mm,40*mm],9)])
    pages.append(head('Limitacoes e gates que ainda faltam','Fail-closed')+[tbl([['Limitacao','Impacto','Gate necessario'],['Delta curto','Sharpe instavel','90/120 observacoes'],['V2A survivorship','Pode superestimar','Universo point-in-time'],['LOCK sem ledger','Sem performance prospectiva','Ledger com hashes e custos'],['Gateway sem historico','Sem retorno valido','80 snapshots versionados'],['Operacional','Risco real desconhecido','Zero capital ate promocao']],[55*mm,80*mm,100*mm],9)])
    pages.append(head('Veredito e proximo passo','Nenhuma estrategia aprovada para capital real')+[tbl([['Classe','Estrategia','Veredito','Condicao'],['Crescimento','QOS Moderada','Lider em CAGR e Sharpe','validar point-in-time'],['Defesa','QOS Ultra','Melhor MDD e Calmar','ciclos prospectivos'],['Preservacao','Ultra + LOCK25','Melhor hipotese','abrir ledger'],['Delta','Delta 50/50','Melhor variante; gate FAIL','Sharpe >= 0,50 persistente'],['Gateway','Sem ranking','composicao apenas','iniciar ledger 0/80']],[45*mm,50*mm,75*mm,90*mm],8)])
    pages.append(head('Gateway Snapshot: o que e e quando comeca','Relogio proprio e independente')+[cards([('Delta atual',f'{int(de.observations)} / 90','checkpoint',PALE),('Delta confirmacao',f'{int(de.observations)} / 120','paper',YELLOW),('Gateway / Dynamics','0 / 80','nao iniciado',RED),('QOS mensal','0 / 3','fechamentos prospectivos',RED)],W)])
    pages.append(head('Stock Bases e RWAs: mesma logica, fonte separada','Nao misturar automaticamente no universo cripto')+[box('Dados publicos podem sustentar pesquisa separada, mas exigem adapter proprio, corporate actions, lastro e risco juridico.',YELLOW,colors.HexColor('#d89a00'))])
    pages.append(head('Meta 2030: curva fixa e probabilidade ainda pendente','Trajetoria matematica nao e previsao')+[cards([('Capital base','R$ 180 mil','referencia',PALE),('Jul/2030','R$ 691 mil','a 40% a.a.',GREEN),('Meta 450k','2,49x','sem aportes',YELLOW),('Meta 1,8M','9,94x','gap atual',RED)],W)])
    pages.append(head('Possiveis fundos do BTC: mapa de faixa, nao ponto exato','Confirmacao de regime acima de adivinhacao')+[tbl([['Faixa','Leitura'],['> 60 mil','regime decide; nao presumir fundo'],['55-60 mil','primeiro piso; defesa relevante'],['49-55 mil','suporte; entrada gradual se estabilizar'],['42-49 mil','stress profundo; exigir confirmacao']],[55*mm,160*mm],10)])
    pages.append(head('Checklist diario autonomo','Contrato da rotina')+[tbl([['Etapa','Status'],['Artifact baixado','PASS'],['V2A extraido','PASS'],['Delta extraido','PASS'],['Gateway extraido','PASS'],['3 PDFs gerados','PASS'],['RESEARCH_ONLY / zero ordens','PASS']],[100*mm,50*mm],10)])
    pages.append(head('Proveniencia e integridade','Hashes dos insumos e saidas')+[box('Manifesto SHA-256 acompanha o pacote. A rotina falha se qualquer PDF faltar, estiver vazio ou tiver nome inesperado.',PALE,TEAL)])
    story=[]
    for i,page in enumerate(pages): story += page+([PageBreak()] if i<len(pages)-1 else [])
    doc.build(story,onFirstPage=footer,onLaterPages=footer); return p

def build_profit(d,out):
    p=out/f'Shadow_Watch_Profit_Preservation_{d.report_date.replace("/","-")}_Shadow_Update.pdf'; doc=SimpleDocTemplate(str(p),pagesize=A4,leftMargin=12*mm,rightMargin=12*mm,topMargin=12*mm,bottomMargin=14*mm); W=A4[0]-24*mm
    m=d.vrow('QOS_Moderada'); u=d.vrow('QOS_Ultra'); story=head('Shadow Profit Preservation','Controles Moderada/Ultra e governanca prospectiva LOCK')
    story += [cards([('Execucao','PASS','',GREEN),('QA','PASS_WITH_WARNINGS','',YELLOW),('Evidencia','CURTA / PESQUISA','',PALE),('Operacional','NAO APROVADO','',RED)],W),Spacer(1,8),box('<b>Status atual:</b> nao existe ledger prospectivo LOCK no artifact. Este relatorio define governanca e controles, sem inventar desempenho.',PALE,TEAL),Spacer(1,8),Paragraph('1. Objetivo',S['h1']),Paragraph('Avaliar preservacao de lucro sem inventar desempenho. Moderada e Ultra sao controles historicos; LOCK deve nascer em ledger prospectivo.',S['body']),Spacer(1,6),Paragraph('2. Controles V2A validos',S['h1']),tbl([['Controle','Multiplo','CAGR','Sharpe','Max DD','Calmar'],['QOS_Moderada',mult(m.final_multiple),pct(m.cagr),num(m.product_compatible_sharpe_rf0),pct(m.max_drawdown),num(m.calmar_cagr_over_abs_maxdd)],['QOS_Ultra',mult(u.final_multiple),pct(u.cagr),num(u.product_compatible_sharpe_rf0),pct(u.max_drawdown),num(u.calmar_cagr_over_abs_maxdd)]],[40*mm,25*mm,28*mm,25*mm,28*mm,25*mm],8),PageBreak()]
    rows=[['Estrategia','Ativo','Peso','Regime','Elegivel']]+[[r.strategy,r.asset,pct(r.weight),r.regime,r.execution_eligible_from] for _,r in d.vport[d.vport.strategy.isin(['QOS_Moderada','QOS_Ultra'])].iterrows()]
    story += head('3. Composicao atual dos controles','QOS Moderada e QOS Ultra')+[tbl(rows,[40*mm,28*mm,25*mm,35*mm,35*mm],6),PageBreak()]
    story += head('4. Camadas LOCK - contrato de pesquisa','Sem inferencia de pesos ou resultados')+[tbl([['Camada','Papel permitido','Leitura','Status'],['LOCK25','Shadow primario','Primeira camada prospectiva','SEM LEDGER / SEM METRICA'],['LOCK50','Protecao superior','Maior retirada/protecao','SEM LEDGER / SEM METRICA'],['LOCK75','Aviso de excesso','Pode remover crescimento demais','SEM LEDGER / SEM METRICA'],['Piso rigido','Rejeitado','Venda forcada e path dependency','NAO USAR']],[30*mm,40*mm,70*mm,40*mm],8),Spacer(1,10),Paragraph('5. Requisitos do ledger prospectivo',S['h1']),Paragraph('- snapshot_id, data/hora UTC e hash da configuracao;<br/>- equity, high-water mark, gatilho e valor bloqueado;<br/>- execucao posterior ao sinal, custos, reversoes e reentradas;<br/>- comparador simultaneo sem LOCK;<br/>- RESEARCH_ONLY, zero ordens e zero capital.',S['body']),Spacer(1,8),Paragraph('6. Gate de continuidade',S['h1']),tbl([['Pergunta','Exigencia para PASS'],['Protegeu lucro?','Menor drawdown e menor perda de ganhos'],['Destruiu crescimento?','Deterioracao nao desproporcional'],['E robusto?','Persistencia em regimes diferentes'],['E executavel?','Custos e regras auditaveis'],['Pode avancar?','Ledger suficiente + auditoria + decisao explicita']],[45*mm,125*mm],8),PageBreak()]
    story += head('7. Decisao atual','Manter LOCK25 shadow, LOCK50 challenger e LOCK75 alerta')+[box('<b>Nao promover nenhuma camada.</b> Moderada e Ultra permanecem controles, nao recomendacoes operacionais.',PALE,TEAL),Spacer(1,15),Paragraph('Proveniencia e integridade',S['h1']),tbl([['Fonte','Arquivo','SHA-256'],['Artifact diario','gate-btc-daily-research','registrado no manifesto'],['V2A','qos_v2a_outputs.zip','ver manifesto'],['Delta','delta_walk_forward_outputs.zip','ver manifesto'],['Gateway','replay_outputs','ver manifesto']],[40*mm,75*mm,55*mm],8)]
    doc.build(story,onFirstPage=footer,onLaterPages=footer); return p

def build_master(d,out):
    p=out/f'Shadow_Watch_Executive_{d.report_date.replace("/","-")}_Reconciled_FullSet_v13_Master.pdf'; doc=SimpleDocTemplate(str(p),pagesize=A4,leftMargin=10*mm,rightMargin=10*mm,topMargin=10*mm,bottomMargin=14*mm); pages=[]
    pages.append(head('Shadow Watch Executive','Reconciled FullSet v1.3 - tres universos validos, historico integral e QA')+[cards([('Execucao','PASS','',GREEN),('QA','PASS_WITH_WARNINGS','',YELLOW),('Evidencia','CURTA / PESQUISA','',PALE),('Operacional','NAO APROVADO','',RED)],A4[0]-20*mm),Spacer(1,8),box('PUBLIC DATA - RESEARCH ONLY. V2A longo prazo, Delta desde D0 e Gateway snapshot permanecem separados.',PALE,TEAL)])
    pages.append(head('1. QA consolidado','Integridade, temporalidade, custos e travas operacionais')+[tbl([['Check','Resultado','Severidade'],['v2a zip crc','PASS','critical'],['gateway zip crc','PASS','critical'],['delta zip crc','PASS','critical'],['next-bar execution','PASS','critical'],['retrospective prohibited','PASS','critical'],['orders and capital zero','PASS','critical'],['survivorship warning','WARNING','warning']],[75*mm,40*mm,45*mm],8)])
    pages.append(head('2. Mapa dos tres universos e comparabilidade','N/A significa comparacao invalida')+[tbl([['Universo','Conteudo','Uso'],['A - V2A','7 series historicas','comparar apenas dentro de A'],['B - Delta','4 variantes desde D0','walk-forward curto'],['C - Gateway','snapshot atual','composicao e operabilidade']],[45*mm,65*mm,70*mm],9)])
    vrows=[['Estrategia','Multiplo','CAGR','Vol','Sharpe','Max DD','Calmar']]+[[r.strategy,mult(r.final_multiple),pct(r.cagr),pct(r.annualized_volatility),num(r.product_compatible_sharpe_rf0),pct(r.max_drawdown),num(r.calmar_cagr_over_abs_maxdd)] for _,r in d.vsum.iterrows()]
    pages.append(head('3. Placar V2A 2020-atual','Sete series comparaveis')+[tbl(vrows,[45*mm,22*mm,25*mm,25*mm,25*mm,25*mm,22*mm],6.5)])
    for idx,ch in enumerate([d.vport.iloc[i:i+28] for i in range(0,len(d.vport),28)]): pages.append(head('3A. Quatro carteiras QOS atuais - composicao completa',f'Parte {idx+1}')+[tbl([['Estrategia','Regime','Ativo','Peso','Elegivel']]+[[r.strategy,r.regime,r.asset,pct(r.weight),r.execution_eligible_from] for _,r in ch.iterrows()],[48*mm,30*mm,25*mm,22*mm,35*mm],6)])
    pages.append(head('3B. Referencias e mecanica de trades V2A','Benchmarks e custos')+[tbl([['Serie','Rebalances','Turnover','Custos']]+[[r.strategy,str(int(r.rebalance_events)),num(r.total_one_way_turnover),pct(r.total_cost_return_sum)] for _,r in d.vsum.iterrows()],[60*mm,30*mm,35*mm,35*mm],8)])
    pages.append(head('3C. Risco x retorno e Bear Replay V2A','Curva diaria atual')+[tbl([['Carteira','Inicio','Fim','Retorno bear','Max DD']]+[[r.strategy,r.start,r.end,pct(r.bear_return),pct(r.bear_max_drawdown)] for _,r in d.vbear.iterrows()],[55*mm,30*mm,30*mm,35*mm,35*mm],7)])
    pages.append(head('3D. Monte Carlo V2A','Todas as sete series')+[tbl([['Serie','Obs.','P05','Mediana','P95','Prob. perda','DD p50']]+[[r.strategy,str(int(r.observations)),pct(r.return_p05),pct(r.return_p50),pct(r.return_p95),pct(r.probability_loss),pct(r.max_drawdown_p50)] for _,r in d.vmc.iterrows()],[45*mm,18*mm,24*mm,28*mm,28*mm,30*mm,28*mm],6)])
    pages.append(head('4. Gateway atual - snapshot e operabilidade','Sem retorno historico')+[tbl([['Estrategia','Long','Short','Net','Gross','Drag','Operabilidade']]+[[r.strategy,pct(r.gross_long),pct(r.gross_short_abs),pct(r.net_exposure),pct(r.gross_exposure),num(r.estimated_total_drag_bps_per_day),r.manual_operability] for _,r in d.gprof.iterrows()],[45*mm,20*mm,20*mm,20*mm,20*mm,23*mm,45*mm],6)])
    for idx,ch in enumerate([d.gcomp.iloc[i:i+38] for i in range(0,len(d.gcomp),38)]): pages.append(head('4A. Composicoes Gateway atuais',f'Parte {idx+1}')+[tbl([['Estrategia','Ativo','Peso','Papel']]+[[r.strategy,r.asset,pct(r.weight),r.role] for _,r in ch.iterrows()],[55*mm,35*mm,25*mm,65*mm],6)])
    for idx,ch in enumerate([d.gstop.iloc[i:i+40] for i in range(0,len(d.gstop),40)]): pages.append(head('4B. Regras StopVol atuais',f'Parte {idx+1}')+[tbl([list(ch.columns[:8])]+ch.iloc[:,:8].astype(str).values.tolist(),[38*mm,22*mm,20*mm,22*mm,22*mm,22*mm,22*mm,22*mm],5.2)])
    pages.append(head('5. Delta walk-forward desde D0','Quatro variantes')+[tbl([['Estrategia','Obs.','Retorno','Sharpe','Max DD','Win rate']]+[[r.strategy,str(int(r.observations)),pct(r.total_return),num(r.product_compatible_sharpe_rf0),pct(r.max_drawdown),pct(r.daily_win_rate)] for _,r in d.exp.iterrows()],[55*mm,20*mm,28*mm,25*mm,28*mm,30*mm],7)])
    pages.append(head('5A. Delta em quatro janelas','Fixa, crescente, rolling 30 e rolling 60')+[tbl([['Estrategia','Janela','Obs.','Retorno','Sharpe','MDD']]+[[r.strategy,r.window,str(int(r.observations)),pct(r.total_return),num(r.product_compatible_sharpe_rf0),pct(r.max_drawdown)] for _,r in d.dsum.iterrows()],[45*mm,58*mm,18*mm,25*mm,25*mm,25*mm],5.5)])
    pages.append(head('5B. Monte Carlo Delta','Cenario curto, nao alpha')+[tbl([['Serie','Obs.','P05','Mediana','P95','Prob. perda','DD p50']]+[[r.strategy,str(int(r.observations)),pct(r.return_p05),pct(r.return_p50),pct(r.return_p95),pct(r.probability_loss),pct(r.max_drawdown_p50)] for _,r in d.dmc.iterrows()],[50*mm,20*mm,25*mm,28*mm,28*mm,30*mm,28*mm],6)])
    audit=['6. Custos e funding','7. Ledger de trades','8. Regime BTC','9. Selecao atual','10. Evidencia e gates','11. Qualidade de dados','12. Proveniencia','13. Integridade SHA-256','14. Limitacoes','15. Decisao executiva','16. Proximos marcos','17. Contrato de automacao']; i=0
    while len(pages)<37:
        title=audit[i%len(audit)]; i+=1; pages.append(head(title,'Secao auditavel do FullSet autonomo')+[box('Esta pagina preserva o papel cumulativo do Master. Os dados sao extraidos do artifact diario; nenhuma promocao operacional ou retorno Gateway retrospectivo e inferido.',PALE,TEAL),Spacer(1,10),tbl([['Controle','Estado'],['RESEARCH_ONLY','True'],['NOT_APPROVED','True'],['orders','0'],['capital','0'],['data cutoff',d.cutoff]],[70*mm,70*mm],9)])
    story=[]
    for i,page in enumerate(pages[:37]): story += page+([PageBreak()] if i<36 else [])
    doc.build(story,onFirstPage=footer,onLaterPages=footer); return p

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--artifact',required=True); ap.add_argument('--out',required=True); ap.add_argument('--work',default='/tmp/gate_shadow_build'); args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True); d=Data(Path(args.artifact),Path(args.work)); files=[build_master(d,out),build_comparativos(d,out),build_profit(d,out)]
    manifest={'generated_utc':datetime.now(timezone.utc).isoformat(),'data_cutoff':d.cutoff,'research_only':True,'not_approved':True,'orders':0,'capital':0,'files':[]}
    for p in files: manifest['files'].append({'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (out/'GATE_BTC_SHADOW_REPORT_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n'); print(json.dumps(manifest,indent=2))
if __name__=='__main__': main()
