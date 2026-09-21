# FinBERT standalone — conclusion

Date: 2026-09-21

## Frozen capability question

Can the pinned public `ProsusAI/finbert` model provide a reproducible, useful 3-class financial-sentiment classification capability on the complete frozen `atrost/financial_phrasebank` test split, without fine-tuning or post-outcome adjustment?

## Official first scientific run

- workflow run: `35663304055`
- head SHA: `4e5cc5824a4924eea0a0412f204fd721aafe4ee6`
- artifact: `gate-btc-finbert-sentiment-standalone`
- artifact id: `10668147368`
- artifact digest: `sha256:59dedb48a665ce130f86f81fb55adfee138d31c52c1380fe0500a54a06365cb5`
- model: `ProsusAI/finbert`
- model revision: `a677990aaa7e6db63d673786a74d575cc071522e`
- dataset: `atrost/financial_phrasebank`
- dataset revision: `fc7fb491db5069dc7494bc0a8c937b3661b8fdce`
- split: `test`
- prediction SHA256: `19282942ac24cbb2955b3e2ca42bdc4331c463c28ed12f810c4aa8cbce804bb0`

No scientific parameter was changed after observing the result.

## QA

All frozen QA gates passed:

- examples: `970`
- negative support: `125`
- neutral support: `565`
- positive support: `280`
- duplicate sentences: `0`
- empty sentences: `0`
- one prediction per row: yes
- model revision recorded: yes
- dataset SHA recorded: yes

## Frozen primary metrics

Primary pass thresholds were:

- accuracy >= `0.80`
- macro-F1 >= `0.75`

Observed:

- accuracy: `0.8649484536082475`
- macro-F1: `0.856082202079237`
- macro precision: `0.8311588505183242`
- macro recall: `0.8931142014327854`
- mean confidence: `0.8747081322153819`

Therefore:

`capability_pass = true`

### Per-class

- negative: precision `0.7547169811`, recall `0.96`, F1 `0.8450704225`, support `125`
- neutral: precision `0.9438877756`, recall `0.8336283186`, F1 `0.8853383459`, support `565`
- positive: precision `0.7948717949`, recall `0.8857142857`, F1 `0.8378378378`, support `280`

### Confusion matrix

Gold negative: 120 negative / 3 neutral / 2 positive.

Gold neutral: 32 negative / 471 neutral / 62 positive.

Gold positive: 7 negative / 25 neutral / 248 positive.

## Standalone disposition

`STANDALONE_CAPABILITY_PASS / HOLD_FOR_TIMESTAMPED_CRYPTO_NEWS_EVIDENCE`

FinBERT demonstrated a tangible financial-text classification capability with substantial margin over both frozen primary thresholds. It is retained as an external sentiment/NLP component candidate.

## Integrated BTSE confrontation

The current QRDS `main` was searched for an admissible historical crypto-news corpus using news/headline/article/publication-time terminology. No corpus was found that establishes all of:

- historical headline/article text;
- publication timestamp;
- immutable source identity or content hash;
- explicit temporal availability semantics;
- enough historical coverage for frozen economic evaluation windows.

Accordingly, an integrated economic comparison against BTSE/QRDS is **not currently admissible**. Financial PhraseBank classification accuracy cannot be relabeled as crypto-news alpha, trading performance, or incremental economic gain.

The integrated lane remains:

`HOLD_FOR_TIMESTAMPED_CRYPTO_NEWS_EVIDENCE`

A future integrated test requires a separately preregistered, timestamped crypto-news evidence source or prospectively accumulated immutable corpus. No retrospective timestamp fabrication or opportunistic corpus substitution is authorized.

## Safety / authority boundary

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL_BRL=0`
- `ORDERS=0`
- `NO_RETUNE=true`
- `NO_BACKFILL=true`
- `FACTORY_RUNTIME_UNTOUCHED=true`
- `INTEGRATED_ECONOMIC_COMPARISON_AUTHORIZED=false`
- `ECONOMIC_CLAIM_AUTHORIZED=false`
- `FACTORY_MIGRATION_AUTHORIZED=false`
