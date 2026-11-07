#!/usr/bin/env python3
# TESTE DIRETO: a selecao tem conteudo, ou e a maquina de saida que a destroi?
#
# Definicoes fixadas ANTES de olhar numeros:
#  - Para cada (execution_date, symbol, side) de SELECTIONS_HISTORY, calcula o retorno
#    da POSICAO sem stop, sem trailing, sem alvo e sem cooldown.
#  - lag = 1 reproduz a convencao congelada (entra na abertura de D+1). lag = 0 entra no
#    fechamento de D (sinal e execucao no mesmo instante, fisicamente impossivel, serve
#    so para medir quanto do resultado o atraso de um dia consome). lag = 2 e 3 adiam mais.
#  - h = dias de calendario de permanencia; sai na abertura do dia lag+h (ou fechamento, se lag=0).
#  - Retorno da cesta = media equiponderada das posicoes daquele dia, com sinal (long +, short -).
#  - A cesta diaria e a unidade de observacao; as cestas se sobrepoem no tempo, entao os
#    erros padrao sao otimistas e estao marcados como tal.
#  - Custo de ida e volta subtraido uma vez por posicao: V11 0,160%, V13 0,232%.
#  - A GRADE INTEIRA e reportada. Nenhuma celula e escolhida como resultado: varrer prazos
#    e garimpar, e a leitura legitima e a do padrao da grade, nao a do melhor numero dela.
import zipfile, glob, csv, datetime as dt, statistics as st, os
from collections import defaultdict

openp = defaultdict(dict)
closep = defaultdict(dict)

def load(pat):
    for z in glob.glob(pat):
        sym = os.path.basename(z).split("-1d-")[0]
        if not sym.endswith("USDT"):
            continue
        base = sym[:-4]
        try:
            with zipfile.ZipFile(z) as zf:
                for nm in zf.namelist():
                    for line in zf.read(nm).decode(errors="replace").splitlines():
                        p = line.split(",")
                        if not p or not p[0].lstrip("-").isdigit():
                            continue
                        ts = int(p[0]); ts = ts // 1000 if ts > 1e12 else ts
                        d = dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                        try:
                            o = float(p[1]); c = float(p[4])
                        except Exception:
                            continue
                        if o > 0 and c > 0:
                            openp[base][d] = o
                            closep[base][d] = c
        except zipfile.BadZipFile:
            continue

load("panel/*-1d-*.zip")
load("panel_nov/*-1d-*.zip")
print("simbolos carregados: %d" % len(openp))

LAGS = [0, 1, 2, 3]
HOR = [1, 2, 3, 5, 10, 20]

def run(lab, path, cost_pct, strat):
    sel = defaultdict(list)
    for r in csv.DictReader(open(path)):
        if r["strategy"] != strat:
            continue
        sg = 1 if r["side"] == "LONG" else -1
        sel[r["execution_date"]].append((r["symbol"], sg))
    dates = sorted(sel)
    # calendario de datas de preco disponiveis
    alld = sorted({d for s in closep for d in closep[s]})
    pos = {d: i for i, d in enumerate(alld)}
    print("\n" + "=" * 78)
    print("%s — %d dias de selecao, de %s a %s | custo ida/volta %.3f%%" % (lab, len(dates), dates[0], dates[-1], cost_pct))
    print("retorno MEDIO da cesta por dia de selecao, SEM stop/trailing/alvo/cooldown, liquido de custo")
    print("(entre parenteses: o retorno BRUTO, antes do custo)")
    hdr = "  lag |" + "".join("   h=%-2d        " % h for h in HOR)
    print(hdr)
    for lag in LAGS:
        cells = []
        for h in HOR:
            vals = []
            for d in dates:
                if d not in pos:
                    continue
                i = pos[d]
                # entrada
                if lag == 0:
                    ei, ekind = i, "c"
                else:
                    ei, ekind = i + lag, "o"
                xi, xkind = ei + h, ("c" if lag == 0 else "o")
                if xi >= len(alld):
                    continue
                ed, xd = alld[ei], alld[xi]
                rs = []
                for sym, sg in sel[d]:
                    src_e = closep if ekind == "c" else openp
                    src_x = closep if xkind == "c" else openp
                    if sym not in src_e or ed not in src_e[sym]:
                        continue
                    if sym not in src_x or xd not in src_x[sym]:
                        continue
                    pe, px = src_e[sym][ed], src_x[sym][xd]
                    if pe <= 0:
                        continue
                    rs.append(sg * (px / pe - 1) * 100)
                if rs:
                    vals.append(st.mean(rs))
            if len(vals) < 5:
                cells.append("     n/d      ")
                continue
            g = st.mean(vals)
            net = g - cost_pct
            cells.append("%+6.3f (%+6.3f)" % (net, g))
        print("   %d  |" % lag + "".join(cells))
    # erro padrao da linha lag=1, h=1 e h=5, para calibrar o ruido
    for h in (1, 5):
        vals = []
        for d in dates:
            if d not in pos:
                continue
            i = pos[d] + 1
            if i + h >= len(alld):
                continue
            ed, xd = alld[i], alld[i + h]
            rs = []
            for sym, sg in sel[d]:
                if sym in openp and ed in openp[sym] and xd in openp[sym]:
                    rs.append(sg * (openp[sym][xd] / openp[sym][ed] - 1) * 100)
            if rs:
                vals.append(st.mean(rs))
        if len(vals) > 3:
            m = st.mean(vals); se = st.stdev(vals) / len(vals) ** 0.5
            print("   lag=1 h=%-2d: bruto %+0.3f%% | erro padrao %0.3f (otimista: cestas se sobrepoem) | t=%+0.2f | n=%d"
                  % (h, m, se, m / se if se else 0, len(vals)))

run("V11 · 50/50 (20 moedas fixas, 5+5)", "d38/delta_paper_monitor/SELECTIONS_HISTORY.csv", 0.160, "Delta_LS_50_50")
run("V13 · 50/50 (TOP100 rotativo, 10+10)", "d38/delta_v13_engine/SELECTIONS_HISTORY.csv", 0.232, "V13_LS_50_50")
