# Momentum BP / SHFL current-close delivery repair

The normal economics execution 39050051660 failed at cutoff 2026-10-16:
BP and SHFL were absent from CDD/Binance, despite exact native routes already
qualified in PIT150 since cutoff 2026-10-13. No economic row was appended.

This change extends the restricted economic bridge from five to seven pinned
identities: BP/backpack via MEXC BPUSDT and SHFL/shuffle-2 via XT shfl_usdt.
The existing collector revalidates pair, identity, contract, source epoch,
closed UTC candles and exact requested date. Primary source priority is retained.

A physical read-only probe on 2026-10-17 captured cutoff 2026-10-16:
BP 1.0036 USDT (208 closed native days); SHFL 0.5113 USDT (947).
The manifest and raw HTTP archive are preserved here. Prices are source marks,
not synthetic fills, observed transaction costs or retroactive scientific credit.

Validation: 33 focused unit tests passed, including wrong asset/coin/date
rejection, sealed-source retries, held quantities and canonical net boundaries.
Daily economic publication after integration must be verified separately.
No strategy parameters, frozen portfolio history or capital settings changed.
