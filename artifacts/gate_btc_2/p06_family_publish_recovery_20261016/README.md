# P0.6 family-source publication recovery

Bridge PR48 merged at a09903e08d1bfc3db2f277a41f1cea9c937c5179.

The publisher builds a new tree over the freshly fetched runtime parent, with one isolated Git index. Each verified non-fast-forward race causes a fresh fetch/tree/commit using the same captured bytes. No full runtime checkout is required. Five Git integration tests passed locally and in PR run 38886168549: real competing commit preserved, bounded exhaustion, immutable collision refusal, malformed input refusal, idempotent recovery without moving latest pointers.

Failed run 38835087073 artifact 12019241332 was downloaded without recollection. All four original packet bytes were published under runtime/factory_sources/mt5/recovered/38835087073 and the original SOURCE_PACKET under audits/38835087073.json, in commit e01a16c5948417b0f5a1c1cf7570a4bae7ef3133. A separate read through the GitHub API confirmed every published file byte for byte; RECOVERY_PROOF.json records hashes. The recovery commit changes exactly these five paths. Original capture timestamps and zero-credit semantics remain unchanged, and current latest files were not touched by recovery.

Main-branch workflow 38886372562 completed successfully and published a new capture with the repaired helper in runtime commit e3f541a9dbfab81f4097c2e712f70b675b3579a8, attempt 1. This real delivery and the deterministic race test are separate evidence. Recovery grants no scientific observations and resolves no historical market-data gap.
