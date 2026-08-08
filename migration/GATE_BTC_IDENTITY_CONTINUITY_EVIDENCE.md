# GATE BTC — PIT identity continuity evidence

Research-only evidence ledger for historical CoinMarketCap display-name changes. This file is identity-only: it must never be used to infer prices, factors, returns, rankings, or strategy outcomes.

## Admission rule

A continuity alias may be admitted only when primary project documentation explicitly establishes that the historical and later display names refer to the same project/token lineage, with the same ticker or an explicitly uninterrupted ticker transition. Similar names, ticker coincidence, third-party listings, or price correlation are insufficient.

## THETA — `THETA` / `Theta Network`

**Decision:** admit as one THETA lineage.

Primary evidence:

- Theta Labs, *What is Theta Network*: https://docs.thetatoken.org/docs/what-is-theta-network
  - Identifies the project as Theta Network and states that the Theta Token (`THETA`) is the governance token of the Theta protocol.
- Theta Labs, *Theta Network — 2019 Roadmap*: https://medium.com/theta-network/theta-network-2019-roadmap-a69cdbec6536
  - Describes the Theta Network mainnet and the 1:1 transition of existing Theta tokens to native Theta tokens.

Audit aliases after normalization: `theta`, `thetanetwork`.

## HBAR — `Hedera Hashgraph` / `Hedera`

**Decision:** admit as one HBAR lineage.

Primary evidence:

- Hedera, *Sustainable building blocks with Hedera Hashgraph*: https://hedera.com/blog/sustainable-building-blocks-with-hedera-hashgraph
  - Uses the explicit construction `Hedera Hashgraph ("Hedera")`, establishing the two names as references to the same network.
- Hedera, *Hedera Hashgraph’s HBAR Coin Added to Atomic Wallet*: https://hedera.com/blog/hedera-hashgraphs-hbar-coin-added-to-atomic-wallet/
  - Identifies HBAR as Hedera Hashgraph's native coin.

Audit aliases after normalization: `hedera`, `hederahashgraph`.

## FET — `Fetch.ai` / `Artificial Superintelligence Alliance`

**Decision:** admit the CMC name change as one FET lineage for the period in which CMC continued the market under ticker FET.

Primary evidence:

- Fetch.ai, *Artificial Superintelligence Alliance Update on ASI Token Merger*: https://www.fetch.ai/blog/artificial_superintelligence_alliance_update_ASI_token_merger
  - States that the project name/logos would be updated to Artificial Superintelligence Alliance while FET markets remained open and trading continued under ticker `FET` without interruption.
- Fetch.ai, *Artificial Superintelligence Alliance Unveil Token with Migration dApp Tools Now Live*: https://www.fetch.ai/blog/artificial-superintelligence-alliance-unveil-token-with-migration-d-app-tools-now-live
  - States that FET trading remained uninterrupted while the project rebranded across CoinMarketCap and CoinGecko.

Audit aliases after normalization: `fetchai`, `artificialsuperintelligencealliance`.

This evidence does **not** merge historical AGIX or OCEAN returns into FET. Those are separate pre-merger assets and remain separate lineages.

## INJ — `Injective Protocol` / `Injective`

**Decision:** admit as one INJ lineage.

Primary evidence:

- Injective, *Introducing the New Injective: An Evolution of the Mission, Product Offerings and Brand*: https://injective.com/blog/introducing-the-new-injective-an-evolution-of-the-mission-product-offerings-and-brand
  - Explicitly describes an Injective Protocol rebrand/evolution and states that the `INJ` token continues to power the network.
- Injective, *Injective August 2021 Update: Rebrand, Decentralized Derivatives and More*: https://injective.com/blog/injective-august-2021-update-rebrand-decentralized-derivatives-and-more/
  - Records the protocol rebrand and continued role of the INJ token.

Audit aliases after normalization: `injective`, `injectiveprotocol`.

## SNX — `Synthetix Network Token` / `Synthetix`

**Decision:** admit as one SNX lineage.

Primary/canonical evidence:

- Synthetix documentation, *Synthetix Token (SNX)*: https://docs.synthetix.io/synthetix-protocol/the-synthetix-token-snx
  - Describes SNX as the Synthetix Network token and identifies the same SNX token as the protocol collateral/governance asset.
- Synthetix documentation, *Links*: https://docs.synthetix.io/links
  - The official project documentation links the SNX market under the historical `synthetix-network-token` naming lineage.
- CoinMarketCap historical snapshots record the market under ticker `SNX` as `Synthetix Network Token` historically and `Synthetix` later; this is used only to identify the display-name variants seen by the PIT ingestion, not as independent proof of token continuity.

Audit aliases after normalization: `synthetixnetworktoken`, `synthetix`.

## SXP — `Swipe` / `Solar`

**Decision:** admit the CMC display-name transition as one SXP lineage.

Primary/canonical evidence:

- Solar documentation, *Introduction to Solar (SXP)*: https://docs.solar.org/about/introduction/
  - States that Solar Blockchain was previously known as Swipechain and that SXP migrated 1:1 to the Solar mainnet.
- Solar project history: https://solar.org/history/
  - Records the Swipe-to-Solar transition and the SXP mainnet migration/rebrand.
- CoinMarketCap historical snapshot 2020-08-09 records `Swipe` under ticker `SXP`, while the current CMC market is `Solar` under ticker `SXP`; these records identify the exact display-name variants seen by the PIT ingestion.

Audit aliases after normalization: `swipe`, `solar`.

This admission is identity-only. It does not stitch ERC-20/BEP-20/native-chain bars, manufacture a continuous price series, or authorize a venue/source substitution. A price history must independently satisfy the existing source cascade and data-quality contract.

## Explicitly rejected cross-token / cross-contract migrations

### DYDX — `ethDYDX` / `DYDX`

**Decision:** reject identity alias; keep fail-closed.

Primary evidence:

- dYdX Foundation, *The dYdX Chain is Live!*: https://www.dydx.foundation/blog/dydx-chain-live
- dYdX, token migration/bridge documentation: https://www.dydx.xyz/blog/dydx-token-migration

The documented process bridges/converts the Ethereum `ethDYDX` token into the dYdX Chain `DYDX` token. That is not merely a display-name change of one uninterrupted market identity, so the PIT identity gate must not merge the two lineages.

### KNC — `KNCL` / `KNC`

**Decision:** reject identity alias; keep fail-closed.

Primary evidence:

- Kyber Network, *KNC Token Migration Guide*: https://blog.kyber.network/knc-token-migration-guide-fda08bfe62c2
- KyberDAO migration documentation: https://docs.kyber.org/kyberdao/knc-token/migration

Kyber documents an upgrade from the old token/contract (`KNCL`) to a new `KNC` token contract. This is a token-contract migration, not a display-name-only continuity. No KNCL/KNC return stitching is authorized.

## Safety constraints

- This ledger changes identity continuity only.
- It does not authorize stitching different tokens, contracts, venues, or quote currencies.
- It does not synthesize missing prices or returns.
- It does not alter V2A selection rules, weights, execution convention, or the frozen engine.
- If future evidence reveals a ticker reuse or discontinuity, the corresponding alias must fail closed until explicitly re-audited.
