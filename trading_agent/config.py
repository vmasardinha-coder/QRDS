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
    # --- ampliacao para ~100 nomes (agosto 2026) ---
    "WFC", "MS", "GS", "BLK", "SCHW", "AXP", "SPGI", "C", "PGR", "ICE",
    "ABT", "DHR", "BMY", "PFE", "GILD", "VRTX", "ISRG", "SYK", "ELV",
    "INTU", "NOW", "IBM", "ACN", "MU", "LRCX", "AMAT", "KLAC", "ADI",
    "PANW", "ANET", "UBER",
    "HON", "UNP", "BA", "LMT", "RTX", "DE", "UPS", "ETN",
    "LOW", "TGT", "SBUX", "MCD", "BKNG", "TJX", "CL", "MDLZ", "MO",
    "CVX", "COP", "EOG", "SLB",
    "NEE", "DUK", "SO",
    "LIN", "SHW",
    "TMUS",
    "AMT", "PLD",
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
    # --- ampliacao para 25 ativos (agosto 2026) ---
    "BCH": "bitcoin-cash",
    "XLM": "stellar",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "ETC": "ethereum-classic",
    "HBAR": "hedera-hashgraph",
    "FIL": "filecoin",
    "ICP": "internet-computer",
    "NEAR": "near",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "INJ": "injective-protocol",
    "AAVE": "aave",
    "ALGO": "algorand",
    # --- ampliacao para 150 ativos (agosto 2026, decisao do mandante) ---
    "SHIB": "shiba-inu",
    "SUI": "sui",
    "SEI": "sei-network",
    "TIA": "celestia",
    "STX": "blockstack",
    "IMX": "immutable-x",
    "RENDER": "render-token",
    "GRT": "the-graph",
    "MKR": "maker",
    "LDO": "lido-dao",
    "QNT": "quant-network",
    "VET": "vechain",
    "SAND": "the-sandbox",
    "MANA": "decentraland",
    "AXS": "axie-infinity",
    "EOS": "eos",
    "XTZ": "tezos",
    "THETA": "theta-token",
    "FLOW": "flow",
    "CHZ": "chiliz",
    "CRV": "curve-dao-token",
    "SNX": "havven",
    "COMP": "compound-governance-token",
    "1INCH": "1inch",
    "BAT": "basic-attention-token",
    "ZEC": "zcash",
    "DASH": "dash",
    "KSM": "kusama",
    "ENJ": "enjincoin",
    "ANKR": "ankr",
    "STORJ": "storj",
    "SKL": "skale",
    "CTSI": "cartesi",
    "LRC": "loopring",
    "OCEAN": "ocean-protocol",
    "BAND": "band-protocol",
    "BAL": "balancer",
    "YFI": "yearn-finance",
    "UMA": "uma",
    "NMR": "numeraire",
    "OXT": "orchid-protocol",
    "MASK": "mask-network",
    "ENS": "ethereum-name-service",
    "APE": "apecoin",
    "GMT": "stepn",
    "JASMY": "jasmycoin",
    "ROSE": "oasis-network",
    "CELO": "celo",
    "KAVA": "kava",
    "MINA": "mina-protocol",
    "AR": "arweave",
    "EGLD": "elrond-erd-2",
    "NEO": "neo",
    "IOTA": "iota",
    "ZIL": "zilliqa",
    "ONE": "harmony",
    "WAVES": "waves",
    "QTUM": "qtum",
    "ICX": "icon",
    "ONT": "ontology",
    "RVN": "ravencoin",
    "DCR": "decred",
    "CAKE": "pancakeswap-token",
    "RUNE": "thorchain",
    "KDA": "kadena",
    "FTM": "fantom",
    "CFX": "conflux-token",
    "ASTR": "astar",
    "GLMR": "moonbeam",
    "MOVR": "moonriver",
    "ACA": "acala",
    "PYTH": "pyth-network",
    "JTO": "jito-governance-token",
    "JUP": "jupiter-exchange-solana",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    "PENDLE": "pendle",
    "ONDO": "ondo-finance",
    "ETHFI": "ether-fi",
    "EIGEN": "eigenlayer",
    "ENA": "ethena",
    "W": "wormhole",
    "STRK": "starknet",
    "BLUR": "blur",
    "DYDX": "dydx-chain",
    "GMX": "gmx",
    "SUSHI": "sushi",
    "ZRX": "0x",
    "KNC": "kyber-network-crystal",
    "API3": "api3",
    "AUDIO": "audius",
    "LPT": "livepeer",
    "REQ": "request-network",
    "RLC": "iexec-rlc",
    "FET": "fetch-ai",
    "OGN": "origin-protocol",
    "ALICE": "my-neighbor-alice",
    "TLM": "alien-worlds",
    "YGG": "yield-guild-games",
    "GHST": "aavegotchi",
    "MAGIC": "magic",
    "HIGH": "highstreet",
    "PERP": "perpetual-protocol",
    "RAD": "radworks",
    "FORTH": "ampleforth-governance-token",
    "AMP": "amp-token",
    "COTI": "coti",
    "CVC": "civic",
    "FIS": "stafi",
    "GTC": "gitcoin",
    "LQTY": "liquity",
    "MTL": "metal",
    "NKN": "nkn",
    "POWR": "power-ledger",
    "QUICK": "quickswap",
    "RARE": "superrare",
    "SPELL": "spell-token",
    "SYN": "synapse-2",
    "TRAC": "origintrail",
    "TRB": "tellor",
    "TRU": "truefi",
    "XYO": "xyo-network",
    "TRX": "tron",
    "TON": "toncoin",
    "POL": "matic-network",
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
    # --- ampliacao para ~50 nomes (agosto 2026) ---
    "SANB11", "CSAN3", "VBBR3", "BRKM5", "GOAU4", "ENGI11", "CPFE3",
    "TAEE11", "EGIE3", "SLCE3", "PSSA3", "CMIN3", "NTCO3", "MGLU3",
]

B3_TOP_N = 8
B3_SLIPPAGE_BPS = 10.0
B3_RISK_OFF_EXPOSURE = 0.5       # exposicao quando IBOV < SMA 200

# --- Carteira B3 estruturadas (financiamento coberto) ---
B3S_INITIAL_CAPITAL_BRL = 50_000.0
B3S_UNDERLYING = "BOVA11"        # ETF Ibovespa
B3S_CALL_OTM = 1.03              # strike da call vendida: 3% acima do spot
B3S_CALL_TENOR_DAYS = 30         # prazo da call vendida
B3S_VOL_WINDOW_DAYS = 30         # janela de volatilidade realizada (fallback)
B3S_GARCH_HORIZON_DAYS = 21      # horizonte da previsao GARCH (~30 dias corridos)
B3S_SLIPPAGE_BPS = 10.0

# Serie SGS do Banco Central para o CDI diario (% ao dia)
BCB_SGS_CDI_SERIES = 12

# --- Carta de Operacao: limites fixos de risco (secao 4) ---
# Estes valores sao tetos duros. O agente NAO os altera por conta propria,
# mesmo que o sinal pareca forte; so mudam por decisao explicita do mandante.

MAX_ACTIVE_POSITION_WEIGHT = 0.15   # teto por posicao ativa (fracao do NAV)
# BTC na carteira crypto e ancora de benchmark, nao posicao ativa: cap proprio
CRYPTO_BTC_ANCHOR_MAX = 0.50

EQUITY_MIN_POSITIONS = 5            # piso de diversificacao; abaixo disto -> caixa
B3_MIN_POSITIONS = 4

# Stop estatistico: proporcional a volatilidade do proprio ativo, nunca fixo
STOP_SIGMA_MULTIPLE = 8.0           # queda maxima = k x desvio-padrao diario
STOP_VOL_WINDOW_DAYS = 60           # janela do desvio-padrao usado no stop
STOP_COOLDOWN_DAYS = 30             # dias de carencia apos stop (evita recompra)

# Filtro de liquidez: sinal sem liquidez real nao e executavel (secao 5)
LIQUIDITY_WINDOW_DAYS = 60
MIN_MEDIAN_TURNOVER_USD = 20_000_000.0   # mediana de preco x volume diario
MIN_MEDIAN_TURNOVER_BRL = 20_000_000.0
# Com um universo de 150 ativos, a cauda inclui moedas genuinamente finas.
# O limiar deriva do tamanho da ordem: uma alt recebe no maximo ~$7.5k (teto de
# 15%), e $7.5k sobre 1M de giro mediano diario e 0,75% do volume de um dia.
# Nota: o volume da Coinbase e da propria bolsa, nao global — por isso este
# numero nao e comparavel ao limiar das acoes, que usa volume consolidado.
MIN_MEDIAN_TURNOVER_CRYPTO_USD = 1_000_000.0

DECISION_LOG_MAX_ENTRIES = 120      # log auditavel por carteira (secao 8)

# Pausa entre pedidos de precos de acoes. Com ~150 chamadas por ciclo (100 EUA
# + 50 B3) as fontes publicas comecam a limitar por taxa; a pausa custa ~40s e
# evita falhas de dado que excluiriam ativos sem motivo real.
FETCH_DELAY_S = 0.25

# --- Regras comuns ---
SMA_REGIME_DAYS = 200
REBALANCE_WEEKDAY = 0            # segunda-feira (0 = Monday)
MIN_TRADE_VALUE_USD = 200.0      # ignora ordens minusculas
DRIFT_REBALANCE_THRESHOLD = 0.30 # desvio relativo de peso que forca rebalanceio
STALE_PRICE_MAX_DAYS = 4         # nao negocia com precos mais velhos que isto
