import os, sys, math, statistics as st
sys.path.insert(0, "/home/user/QRDS/tools/research/delta_xs")
import xs_core as X, sim_engine as E

panel = X.load()
dates, bases, close, score, ret1 = X.build(panel)
vol = X.usd_volume(panel, dates, bases)
pr = X.pit_rank(dates, bases, vol)
universe = E.build_universe(dates, bases, pr, E.UNIVERSE_N)
idx = {d: i for i, d in enumerate(dates)}
vol30 = {}
for d in dates:
    i = idx[d]
    vol30[d] = {}
    for b in bases:
        w = [ret1[dates[j]].get(b) for j in range(max(0, i-29), i+1)]
        c = [x for x in w if x is not None]
        vol30[d][b] = X.sstdev(c) if len(c) >= X.MIN_HISTORY else None
raw = E.raw_selections(dates, score, universe, E.FROZEN)

def stats(net):
    if len(net) < 3: return float('nan'), float('nan')
    s = st.fmean(net)/st.stdev(net)*math.sqrt(365) if st.stdev(net) else 0.0
    r = (math.prod(1+x for x in net)-1)*100
    return r, s

print("Metades independentes e corte de concentracao. 2% dos dias = K melhores removidos.")
print("Rotacao fixa em 1 dia (congelada); varia SO o stop.")
for bname, gl, gs in E.BOOKS:
    sched = E.target_schedule(dates, raw, vol30, gl, gs, E.FROZEN, 1)
    print()
    print("=== LIVRO", bname)
    print("%-16s | %16s | %16s | %16s | %10s" % ("stop", "serie inteira", "1a metade", "2a metade", "sem 2% dias"))
    print("%-16s | %7s %8s | %7s %8s | %7s %8s | %10s" % ("", "ret%","sharpe","ret%","sharpe","ret%","sharpe","ret%"))
    print("-"*92)
    for label, mult in [("2.5 congelado",2.5), ("4.0",4.0), ("6.0",6.0), ("sem stop",None)]:
        daily, ex, hd = E.run(dates, bases, panel, score, vol30, sched, E.FROZEN,
                              mult, True, True, 1, 40)
        net = [r["net"] for r in daily]
        h = len(net)//2
        rf, sf = stats(net); r1, s1 = stats(net[:h]); r2, s2 = stats(net[h:])
        K = max(1, int(round(0.02*len(net))))
        order = sorted(range(len(net)), key=lambda i: -net[i])[:K]
        cut = [v for i, v in enumerate(net) if i not in set(order)]
        rc, _ = stats(cut)
        print("%-16s | %+7.1f %+8.2f | %+7.1f %+8.2f | %+7.1f %+8.2f | %+10.1f" % (
            label, rf, sf, r1, s1, r2, s2, rc))
    print("   n=%d dias, 1a metade %s a %s, 2a %s a %s, K=%d dias removidos" % (
        len(net), daily[0]["date"], daily[h-1]["date"], daily[h]["date"], daily[-1]["date"], K))
