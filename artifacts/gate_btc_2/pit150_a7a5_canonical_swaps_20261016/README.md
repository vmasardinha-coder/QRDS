# A7A5 exact Ethereum swap source — qualification on 16 October 2026

The future PIT150 route is effective only for completed cutoffs from **17 October 2026**. Qualification does not amend the current 150-member denominator, historic receipts, source gaps, counters or scientific credit.

## Exact identity and physical history

The Ethereum pool 0x14d7aab5b4bca6a02e52ac22520b033bf35f4091 is already bound to A7A5 by the admitted registry entry from PR552, provenance 7cf2076021f6d759c55a9e962db8d946290909456fab9c2f0986a85cdc462fb6. The new adapter verifies that unchanged entry, Ethereum chain ID, token0/token1 through public RPC, and exact token contracts/metadata/6-decimal precision. Token0 is 0x6fa0be17e4bea2fcfa22ef89bf8ac9aab0ab0fc9; token1 is Ethereum USDT.

The frozen Blockscout capture contains 5,950 events, with 5,937 events in the 200 completed daily window ending 14 October. All 119 raw page hashes, continuation parameters and strict block/log ordering were checked. Every required UTC day contains actual swaps; no empty day is filled.

Daily execution price is the final swap's absolute net USDT flow divided by absolute net A7A5 flow, ordered by block number and global log index. Volume is the sum of absolute net USDT swap flows, using Decimal arithmetic. The USD convention is nominal USDT, without historical FX conversion.

## Independent canonical checks

PublicNode canonical block responses verified 1,537 distinct blocks: every final-close block for the 200 days, plus all observed swap blocks on the eleven days where GeckoTerminal volume differed. Block hashes, UTC timestamps and transaction membership all matched.

The independent public dRPC endpoint then returned 2,163 exact pool/topic logs from those 1,537 blocks. Every log matched Blockscout in block hash, transaction hash, global log index, raw data and topics. There were zero missing, changed or additional matching events in the queried blocks. This is a bounded audit of the stated blocks; it is not a claim to have scanned every Ethereum block or reconstructed missing receipt logs from PublicNode.

The public RPCs have different historical capabilities. PublicNode prunes old receipt/log history while retaining block headers; dRPC supplies individual historical block-hash logs. Batch and some range requests were rejected, so the verification uses bounded individual block-hash requests. Raw responses, including the failed probes, are retained.

## GeckoTerminal differences

Across 181 overlapping daily bars, the earlier diagnostic found 23 material close differences and 11 volume differences. Twenty-two of the close differences matched an earlier swap in the final timestamp rather than the final canonical log; one did not. July 10 shows 1,286.091495 USDT of observed swap flow versus 938.082601 in GeckoTerminal, including an independently confirmed 348.008894-USDT final swap. Alternative gross/net/transaction grouping did not resolve the volume differences.

The adapter does not overwrite GeckoTerminal history or force its totals to agree. It uses a separately identified exact execution-log source with its own raw captures and canonical-close checks. No comparative return or economic result was used to select the route.

## Runtime checks

Each capture verifies exact identity, descending non-repeating pagination, unique event keys, directional positive token flows and 200 contiguous completed UTC days. Every daily final-close block is checked through PublicNode, and its actual final pool swap is checked independently through dRPC. A changed, absent, removed or non-final log blocks admission. Network/provider errors also block rather than synthesizing data.

FROZEN_INPUTS.zip contains the physical inputs used by the replay tests. RAW_CANONICAL_PROOF.zip contains the independent raw HTTP proof responses. Live qualification and the final-code replay of its sealed responses are recorded separately when available. The collector itself grants zero historical/scientific credit; the first real PIT receipt remains a separate operational condition.
