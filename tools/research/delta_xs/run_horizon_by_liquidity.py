import os, sys, math, statistics as st
sys.path.insert(0, "/home/user/QRDS/tools/research/delta_xs")
os.environ.setdefault("DELTA_XS_DATA", "data_bv")
import xs_core as X
import run_horizon as R

panel = X.load()
dates, bases, close, score, ret1 = X.build(panel)
idx = {d: i for i, d in enumerate(dates)}
vol = X.usd_volume(panel, dates, bases)
pr = X.pit_rank(dates, bases, vol)

def fm(h, off, topn, rank, winsor):
    out = []
    sample = [d for k, d in enumerate(dates) if k % h == off % h]
    for d in sample:
        rows = []
        for b in bases:
            s = score[d].get(b)
            if s is None: continue
            if topn is not None and pr[d].get(b, 10**9) >= topn: continue
            r = R.forward_return(close, dates, idx, b, d, h)
            if r is None: continue
            rows.append((s, r))
        if len(rows) < 20: continue
        xs = [p[0] for p in rows]; ys = [p[1] for p in rows]
        if winsor is not None: ys = [max(-winsor, min(winsor, y)) for y in ys]
        if rank: xs, ys = X._ranks(xs), X._ranks(ys)
        my = st.fmean(ys); ys = [y - my for y in ys]
        mx = st.fmean(xs); den = sum((x-mx)**2 for x in xs)
        if den == 0: continue
        out.append(sum((x-mx)*y for x, y in zip(xs, ys))/den)
    return out

print("painel %d simbolos, %d datas" % (len(bases), len(dates)))
for topn, lab in [(None, "universo inteiro (898)"), (100, "TOP100 liquidez PIT"), (30, "TOP30 liquidez PIT")]:
    print()
    print("===", lab)
    print("  h | n(off0) | t postos (todos os offsets)        | t niveis winsor")
    for h in (1, 3, 5, 7, 14, 21):
        tr, nr = [], []
        for off in range(h):
            sl = fm(h, off, topn, True, None)
            if len(sl) >= 3:
                m, t = X.tstat(sl); tr.append(t); nr.append(len(sl))
        tl = []
        for off in range(h):
            sl = fm(h, off, topn, False, 0.50*math.sqrt(h))
            if len(sl) >= 3:
                m, t = X.tstat(sl); tl.append(t)
        if not tr:
            print("  %2d |    -    | amostra insuficiente" % h); continue
        rng = "min %+.2f max %+.2f" % (min(tr), max(tr))
        print("  %2d | %6d  | %+5.2f  (%s) | %+5.2f (min %+.2f max %+.2f)"
              % (h, nr[0], tr[0], rng, tl[0] if tl else float('nan'),
                 min(tl) if tl else float('nan'), max(tl) if tl else float('nan')))
