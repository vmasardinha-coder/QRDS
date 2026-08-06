"""Parametros do agente de trading."""

from __future__ import annotations

INITIAL_CAPITAL_USD = 50_000.0

# --- Carteira de acoes (EUA) ---
EQUITY_BENCHMARK = "SPY"

# Universo liquido de large caps dos EUA (simbolos Stooq: <ticker>.us).
EQUITY_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO",
    "JPM", "V", "UNH", "XOM", "LLY", "JNJ", "PG", "MA", "HD", "COST",
    "MRK", "ABBV", "CRM", "NFLX", "AMD", "ORCL", "KO", "PEP", "WMT",
    "BAC", "DIS", "CSCO", "ADBE", "TMO", "INTC", "QCOM", "TXN", "AMGN",
    "CAT", "GE", "PM", "NKE",
]

EQUITY_TOP_N = 10                # posicoes na carteira de acoes
EQUITY_MOM_LONG_DAYS = 252       # janela longa do momentum (12 meses)
EQUITY_MOM_SKIP_DAYS = 21        # exclui o mes mais recente (momentum 12-1)
EQUITY_MIN_HISTORY_DAYS = 260    # historico minimo para elegibilidade
EQUITY_SLIPPAGE_BPS = 5.0        # custo de execucao modelado
EQUITY_RISK_OFF_EXPOSURE = 0.5   # exposicao quando SPY < SMA 200

# --- Carteira de crypto ---
CRYPTO_BENCHMARK = "BTC"

# id Coinbase Exchange -> id CoinGecko (fallback)
CRYPTO_UNIVERSE = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "LTC": "litecoin",
    "DOT": "polkadot",
}

CRYPTO_BTC_CORE_WEIGHT = 0.5     # peso base em BTC dentro da parte investida
CRYPTO_MAX_ALTS = 3              # alts com momentum superior ao BTC
CRYPTO_MOM_SHORT_DAYS = 30
CRYPTO_MOM_LONG_DAYS = 90
CRYPTO_MIN_HISTORY_DAYS = 210
CRYPTO_SLIPPAGE_BPS = 10.0
CRYPTO_RISK_OFF_EXPOSURE = 0.5   # exposicao quando BTC < SMA 200

# --- Carteira de acoes B3 (Brasil) ---
B3_INITIAL_CAPITAL_BRL = 50_000.0
B3_BENCHMARK = "^BVSP"           # Ibovespa
B3_BENCHMARK2 = "CDI"            # indice acumulado do CDI (BCB SGS 12)

# Universo liquido da B3 (sufixo .SA no Yahoo Finance)
B3_UNIVERSE = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3", "ABEV3", "WEGE3", "RENT3",
    "B3SA3", "ITSA4", "SUZB3", "GGBR4", "CSNA3", "EMBR3", "RADL3", "LREN3",
    "RAIL3", "PRIO3", "EQTL3", "VIVT3", "TOTS3", "HAPV3", "RDOR3", "CMIG4",
    "ELET3", "SBSP3", "BPAC11", "CPLE6", "TIMS3", "UGPA3", "JBSS3", "BRFS3",
    "KLBN11", "CYRE3", "MULT3", "ASAI3",
]

B3_TOP_N = 8
B3_SLIPPAGE_BPS = 10.0
B3_RISK_OFF_EXPOSURE = 0.5       # exposicao quando IBOV < SMA 200

# --- Carteira B3 estruturadas (financiamento coberto) ---
B3S_INITIAL_CAPITAL_BRL = 50_000.0
B3S_UNDERLYING = "BOVA11"        # ETF Ibovespa
B3S_CALL_OTM = 1.03              # strike da call vendida: 3% acima do spot
B3S_CALL_TENOR_DAYS = 30         # prazo da call vendida
B3S_VOL_WINDOW_DAYS = 30         # janela de volatilidade realizada
B3S_SLIPPAGE_BPS = 10.0

# Serie SGS do Banco Central para o CDI diario (% ao dia)
BCB_SGS_CDI_SERIES = 12

# --- Regras comuns ---
SMA_REGIME_DAYS = 200
REBALANCE_WEEKDAY = 0            # segunda-feira (0 = Monday)
MIN_TRADE_VALUE_USD = 200.0      # ignora ordens minusculas
DRIFT_REBALANCE_THRESHOLD = 0.30 # desvio relativo de peso que forca rebalanceio
STALE_PRICE_MAX_DAYS = 4         # nao negocia com precos mais velhos que isto
