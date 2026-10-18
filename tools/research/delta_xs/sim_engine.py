#!/usr/bin/env python3
"""Replica do motor congelado sobre historico sem vies de sobrevivencia.

PARA QUE SERVE. Medir, ANTES de congelar qualquer sucessora, se afrouxar o
stop e/ou girar mais devagar muda alguma coisa. A alternativa seria preregistrar
um contrato e descobrir em 60 dias de coleta prospectiva — foi o que custou o
V12 e quase custou a V14.

O QUE E REPLICADO, verbatim de tools/gate_btc_delta_v12_engine.py:
  - escore congelado (xs_core, identico a gate_btc_delta_v12_engine.py:265-332)
  - selecao top_n/bottom_n sobre o escore, com persistencia de 2 dias
  - sinal no fechamento, execucao na ABERTURA do dia seguinte
  - stop = clamp(mult*vol30, floor, cap); alvo = 2R; trailing sobre o melhor preco
  - nivel efetivo = o mais APERTADO entre stop fixo e trailing (stop_levels)
  - saida por gap na abertura antes de rebalancear (STOP_GAP / TAKE_PROFIT_GAP)
  - toque intradiario por high/low, com o stop vencendo quando os dois tocam
  - cooldown de reentrada de 2 dias, armado por stop/alvo e NAO por rebalanceamento
  - kill switch diario (-3%) e semanal (-7%) com seus cooldowns
  - custo por lado aplicado sobre |delta de peso|

O QUE DIFERE, e cada item empurra o resultado numa direcao conhecida:
  1. FUNDING AUSENTE. O arquivo diario da Binance Vision nao traz funding.
     No V11 o funding acumulado em 65 dias ficou entre -0,15% e -0,23%, ou seja
     pequeno, mas o sinal e NEGATIVO: omiti-lo favorece levemente todas as
     celulas por igual, e nao muda a comparacao entre elas.
  2. UNIVERSO PONTO-NO-TEMPO. O V11 tem 20 moedas fixas escolhidas hoje. Usar
     essa lista no historico seria exatamente o vies que o portao da V14 pegou,
     ent[a]o aqui o universo de cada dia sao os N mais liquidos ATE aquele dia.
     Nao e o universo do V11; e o universo que o V11 teria tido sem hindsight.
  3. CUSTO CONSTANTE de 8,00 bps por lado, que e o medido no ledger do V11
     (taxa 5,0 + slippage 3,0). O V13 usa faixas e paga ~11,6 na media.
  4. SEM MEMBERSHIP OBSERVADO. O motor real recusa um dia cujo universo nao
     foi observado; aqui o universo e reconstruido do proprio painel.

ESCOPO. PESQUISA. Nenhum ledger lido ou escrito, nenhum parametro congelado
tocado, nenhuma ancora fixada. NAO aplicavel ao V11 nem ao V13, que ja tem
retorno observado: usar isto neles seria retune contra resultado conhecido.

CONFERENCIA OBRIGATORIA. A celula base (stop 2,5 / trailing on / rotacao 1 /
reentrada no ciclo) tem de reproduzir o CARATER do ledger vivo do V11 — giro
diario na casa de 0,4, maioria das saidas por stop, permanencia mediana de
1 dia. Se nao reproduzir, o simulador esta errado e nenhuma outra celula vale.

Uso:
    DELTA_XS_DATA=data_bv python3 -I sim_engine.py
"""
import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import xs_core as X

# --- premissas congeladas do V11, verbatim de delta_paper_monitor_contract.json
FROZEN = dict(
    top_n=5, bottom_n=5, persistence_days=2,
    stop_vol_multiplier=2.5, stop_floor=0.06, stop_cap=0.35,
    take_profit_r_multiple=2.0,
    trailing_vol_multiplier=1.5, trailing_floor=0.04, trailing_cap=0.25,
    reentry_cooldown_days=2,
    daily_loss_kill_switch=0.03, weekly_loss_kill_switch=0.07,
    daily_kill_cooldown_days=1, weekly_kill_cooldown_days=3,
)
COST_PER_SIDE = 8.00 / 10000.0   # medido no ledger do V11
UNIVERSE_N = 20                  # mesma largura do V11, mas ponto-no-tempo
BOOKS = (("70/30", 0.70, 0.30), ("50/50", 0.50, 0.50))


def stop_parameters(vol_daily, mult, cfg):
    """clamp(mult*vol, floor, cap); alvo 2R; trailing proprio. mult=None => sem stop."""
    if mult is None:
        return None, None, None
    vol = (float(vol_daily) if vol_daily is not None and math.isfinite(vol_daily)
           and vol_daily > 0 else cfg["stop_floor"] / mult)
    stop = min(max(mult * vol, cfg["stop_floor"]), cfg["stop_cap"])
    take = min(0.90, stop * cfg["take_profit_r_multiple"])
    trail = min(max(cfg["trailing_vol_multiplier"] * vol,
                    cfg["trailing_floor"]), cfg["trailing_cap"])
    return stop, take, trail


def stop_levels(p, trailing_on):
    """O mais apertado entre stop fixo e trailing, igual a stop_levels do motor."""
    if p["stop_pct"] is None:
        return None, None
    if p["weight"] > 0:
        fixed = p["entry"] * (1 - p["stop_pct"])
        stop = max(fixed, p["best"] * (1 - p["trail_pct"])) if trailing_on else fixed
        take = p["entry"] * (1 + p["take_pct"])
    else:
        fixed = p["entry"] * (1 + p["stop_pct"])
        stop = min(fixed, p["best"] * (1 + p["trail_pct"])) if trailing_on else fixed
        take = p["entry"] * (1 - p["take_pct"])
    return stop, take


def build_universe(dates, bases, pr, n):
    return {d: {b for b, r in pr[d].items() if r < n} for d in dates}


def raw_selections(dates, score, universe, cfg):
    nl, ns = cfg["top_n"], cfg["bottom_n"]
    out = {}
    for d in dates:
        elig = universe[d]
        valid = [(b, v) for b, v in score[d].items() if v is not None and b in elig]
        if len(valid) < nl + ns:
            out[d] = {}
            continue
        ordered = [b for b, _ in sorted(valid, key=lambda kv: -kv[1])]
        longs = ordered[:nl]
        shorts = [b for b in ordered[-ns:] if b not in longs]
        out[d] = {**{b: 1 for b in longs}, **{b: -1 for b in shorts}}
    return out


def target_schedule(dates, raw, vol30, gross_long, gross_short, cfg, rotate_every):
    """Pesos alvo por dia de execucao. rotate_every>1 CONGELA o alvo entre rotacoes."""
    pers = cfg["persistence_days"]
    sched = {}
    held = None
    for i in range(pers - 1, len(dates) - 1):
        signal_day, exec_day = dates[i], dates[i + 1]
        if rotate_every > 1 and held is not None and (i - (pers - 1)) % rotate_every != 0:
            sched[exec_day] = held
            continue
        persistent = {s: v for s, v in raw.get(signal_day, {}).items()
                      if all(raw.get(dates[i - lag], {}).get(s) == v for lag in range(pers))}
        targets = {}
        for side, gross, count in ((1, gross_long, cfg["top_n"]),
                                   (-1, gross_short, cfg["bottom_n"])):
            w = gross / count
            for s in sorted(x for x, v in persistent.items() if v == side):
                targets[s] = side * w
        sched[exec_day] = targets
        held = targets
    return sched


def run(dates, bases, panel, score, vol30, sched, cfg, mult, trailing_on,
        reenter_within_cycle, rotate_every, start_at=0):
    idx = {d: i for i, d in enumerate(dates)}
    traded = dates[start_at:]
    pos, cooldown = {}, {}
    kill_until = -1
    equity = 1.0
    daily, exits, holds = [], [], []
    entry_day = {}
    retired = set()      # saiu neste ciclo e nao volta (quando reenter_within_cycle=False)

    def bar(day, sym):
        return panel.get(day, {}).get(sym)

    def close_pos(sym, day, di, price, reason, arms_cooldown):
        p = pos.pop(sym)
        w = abs(p["weight"])
        exits.append((day, sym, reason, p["weight"],
                      (price / p["entry"] - 1) * (1 if p["weight"] > 0 else -1)))
        if sym in entry_day:
            holds.append((reason, (di - entry_day.pop(sym))))
        if arms_cooldown:
            cooldown[sym] = di + cfg["reentry_cooldown_days"]
        if not reenter_within_cycle:
            retired.add(sym)
        return w

    for di, day in enumerate(traded):
        prev = dates[idx[day] - 1] if idx[day] > 0 else None
        overnight = intraday = cost = turnover = 0.0
        stopped_at_open = set()
        if rotate_every > 1 and di % rotate_every == 0:
            retired.clear()

        # 1. marcacao do fechamento anterior para a abertura + saida por gap
        for sym in list(pos):
            tb, pb = bar(day, sym), bar(prev, sym) if prev else None
            if not tb or not pb or pb["close"] <= 0:
                continue
            p = pos[sym]
            op = tb["open"]
            overnight += p["weight"] * (op / pb["close"] - 1)
            sl, tl = stop_levels(p, trailing_on)
            if sl is None:
                continue
            reason = None
            if p["weight"] > 0:
                if op <= sl:
                    reason = "STOP_GAP"
                elif op >= tl:
                    reason = "TAKE_PROFIT_GAP"
            else:
                if op >= sl:
                    reason = "STOP_GAP"
                elif op <= tl:
                    reason = "TAKE_PROFIT_GAP"
            if reason:
                w = close_pos(sym, day, di, op, reason, True)
                cost += w * COST_PER_SIDE
                turnover += w
                stopped_at_open.add(sym)

        desired = dict(sched.get(day, {}))
        kill_on = di <= kill_until
        if kill_on:
            desired = {}
        for sym in list(desired):
            if (di <= cooldown.get(sym, -1) or sym in stopped_at_open
                    or sym in retired or not bar(day, sym)):
                desired.pop(sym, None)

        # 2. rebalanceamento na abertura
        for sym in sorted(set(pos) | set(desired)):
            old = float(pos.get(sym, {}).get("weight", 0.0))
            new = float(desired.get(sym, 0.0))
            d = new - old
            if abs(d) > 1e-12:
                turnover += abs(d)
                cost += abs(d) * COST_PER_SIDE
            tb = bar(day, sym)
            op = tb["open"] if tb else None
            if old != 0 and (new == 0 or (old > 0) != (new > 0)):
                close_pos(sym, day, di, op if op else pos[sym]["entry"],
                          "REBALANCE_EXIT", False)
            if new != 0 and (old == 0 or (old > 0) != (new > 0)):
                sd = dates[idx[day] - 1]
                sp, tp, tr = stop_parameters(vol30[sd].get(sym), mult, cfg)
                pos[sym] = {"weight": new, "entry": op, "best": op,
                            "stop_pct": sp, "take_pct": tp, "trail_pct": tr}
                entry_day[sym] = di
            elif new != 0 and sym in pos:
                pos[sym]["weight"] = new

        # 3. toque intradiario; o stop vence quando os dois sao tocados
        for sym in list(pos):
            p = pos[sym]
            tb = bar(day, sym)
            if not tb:
                continue
            op, hi, lo, cl = tb["open"], tb["high"], tb["low"], tb["close"]
            sl, tl = stop_levels(p, trailing_on)
            px = reason = None
            if sl is not None:
                if p["weight"] > 0:
                    if lo <= sl:
                        px, reason = sl, "STOP_INTRADAY"
                    elif hi >= tl:
                        px, reason = tl, "TAKE_PROFIT_INTRADAY"
                else:
                    if hi >= sl:
                        px, reason = sl, "STOP_INTRADAY"
                    elif lo <= tl:
                        px, reason = tl, "TAKE_PROFIT_INTRADAY"
            mark = px if px is not None else cl
            intraday += p["weight"] * (mark / op - 1)
            if px is not None:
                w = close_pos(sym, day, di, px, reason, True)
                cost += w * COST_PER_SIDE
                turnover += w
            else:
                p["best"] = max(p["best"], hi) if p["weight"] > 0 else min(p["best"], lo)

        gross = overnight + intraday
        net = gross - cost
        equity *= max(1e-6, 1 + net)
        daily.append(dict(date=day, gross=gross, cost=cost, net=net, nav=equity,
                          turnover=turnover, n=len(pos)))
        if net <= -cfg["daily_loss_kill_switch"]:
            kill_until = max(kill_until, di + cfg["daily_kill_cooldown_days"])
        rec = [r["net"] for r in daily[-7:]]
        if len(rec) == 7:
            wk = math.prod(1 + r for r in rec) - 1
            if wk <= -cfg["weekly_loss_kill_switch"]:
                kill_until = max(kill_until, di + cfg["weekly_kill_cooldown_days"])
    return daily, exits, holds


def summarize(daily, exits, holds):
    net = [r["net"] for r in daily]
    nav = [r["nav"] for r in daily]
    cg = math.prod(1 + r["gross"] for r in daily) - 1
    cc = sum(r["cost"] for r in daily)
    pk, dd = nav[0], []
    for v in nav:
        pk = max(pk, v)
        dd.append(v / pk - 1)
    sh = (st.fmean(net) / st.stdev(net) * math.sqrt(365)) if len(net) > 2 and st.stdev(net) else 0.0
    from collections import Counter
    c = Counter(e[2] for e in exits)
    tot = sum(c.values()) or 1
    stop_share = 100 * (c["STOP_INTRADAY"] + c["STOP_GAP"]) / tot
    hd = [h[1] for h in holds]
    return dict(
        nav=nav[-1], ret=(nav[-1] - 1) * 100, sharpe=sh, ddmax=min(dd) * 100,
        giro=st.fmean(r["turnover"] for r in daily),
        bruto=cg * 100, custo=cc * 100,
        atrito=(cc / cg * 100 if cg > 0 else float("nan")),
        saidas=tot, stop_share=stop_share,
        hold_med=(st.median(hd) if hd else float("nan")),
        hold_mean=(st.fmean(hd) if hd else float("nan")),
        um_dia=(100 * sum(1 for h in hd if h <= 1) / len(hd) if hd else float("nan")),
    )


def main():
    panel = X.load()
    dates, bases, close, score, ret1 = X.build(panel)
    vol = X.usd_volume(panel, dates, bases)
    pr = X.pit_rank(dates, bases, vol)
    universe = build_universe(dates, bases, pr, UNIVERSE_N)
    # vol30 por dia/nome, igual ao painel do motor
    idx = {d: i for i, d in enumerate(dates)}
    vol30 = {}
    for d in dates:
        i = idx[d]
        row = {}
        for b in bases:
            w = [ret1[dates[j]].get(b) for j in range(max(0, i - 29), i + 1)]
            c = [x for x in w if x is not None]
            row[b] = X.sstdev(c) if len(c) >= X.MIN_HISTORY else None
        vol30[d] = row
    raw = raw_selections(dates, score, universe, FROZEN)
    start = 40  # deixa o vol30 e a persistencia maturarem antes de contabilizar

    print("painel: %d simbolos, %d datas (%s a %s) | fonte data.binance.vision"
          % (len(bases), len(dates), dates[0], dates[-1]))
    print("universo do dia: %d mais liquidos PONTO-NO-TEMPO | custo %.2f bps/lado | funding ausente"
          % (UNIVERSE_N, COST_PER_SIDE * 10000))
    print()

    CELLS = [
        ("BASE  congelado",            2.5,  True,  1, True),
        ("stop 4.0",                   4.0,  True,  1, True),
        ("stop 6.0",                   6.0,  True,  1, True),
        ("sem trailing",               2.5,  False, 1, True),
        ("sem stop algum",             None, True,  1, True),
        ("rotacao 5d",                 2.5,  True,  5, True),
        ("rotacao 7d",                 2.5,  True,  7, True),
        ("rotacao 5d, 1 entrada/ciclo", 2.5, True,  5, False),
        ("rot 5d + stop 6.0 + 1/ciclo", 6.0, True,  5, False),
        ("rot 5d + sem stop + 1/ciclo", None, True, 5, False),
    ]
    for bname, gl, gs in BOOKS:
        print("=" * 108)
        print("LIVRO %s" % bname)
        print("%-30s %8s %7s %8s %7s %8s %8s %7s %6s %6s %6s" % (
            "celula", "cota", "ret%", "sharpe", "ddmax", "giro/d", "atrito", "saidas",
            "stop%", "perm", "<=1d"))
        print("-" * 108)
        for label, mult, trail, rot, reent in CELLS:
            sched = target_schedule(dates, raw, vol30, gl, gs, FROZEN, rot)
            daily, exits, holds = run(dates, bases, panel, score, vol30, sched,
                                      FROZEN, mult, trail, reent, rot, start)
            s = summarize(daily, exits, holds)
            at = ("%7.1f%%" % s["atrito"]) if s["atrito"] == s["atrito"] else "    n/a"
            print("%-30s %8.4f %+7.1f %+8.2f %7.1f %8.3f %s %7d %6.0f %6.1f %6.0f" % (
                label, s["nav"], s["ret"], s["sharpe"], s["ddmax"], s["giro"], at,
                s["saidas"], s["stop_share"], s["hold_med"], s["um_dia"]))
        print()
    print("perm = permanencia mediana em dias; <=1d = %% das posicoes que morrem em 1 dia ou menos.")
    print("Nada aqui fixa ancora, congela contrato ou autoriza mexer em V11/V13.")


if __name__ == "__main__":
    main()
