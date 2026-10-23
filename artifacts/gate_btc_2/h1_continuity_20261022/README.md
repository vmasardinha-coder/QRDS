# H1 continuity repair — 22 October 2026

The canonical H1 schedule ended on 20 October at 17/20: source gaps on 9,
14 and 15 October did not count. This adds a separate hash-pinned extension
for 23, 26, 27, 28 and 29 October, WINZ26/WDOX26. The original prefix,
eight-date amendment and all ledger evidence stay unchanged. Only unique
future structural passes count; the canonical gate still stops at 20 and
keeps economics locked pending integrity review. Dates 21/22 get no backfill.

The local Inspired clock was calling the legacy checkout runner while its
exit guard called local H1 Opening V2. On 22 October at 08:55 BRT, its H1
binding was corrected to `local_h1_opening_v2/run_h1.py` and a deployment
preflight added. 215 spool files were unchanged; no tasks were reconfigured,
no strategy executed by the installer, and no terminal restart requested.
Only the clock task was restarted at 08:58 BRT before the open; its natural
startup log confirmed `H1_V2_BINDING=PASS` at 08:59 BRT. Unversioned events
from 20/21 remain unmodified and separate.

The repository clock template receives the same binding/guard so another
installation does not restore the legacy H1 pointer. Its calendar, H31
arguments, sync policy and timing remain unchanged.

## Local canonical materialization

After the source commit is merged and the normal guarded sync completes,
install this directory's `materialize_h1_collector.py` over the local helper
after backing up its exact bytes. It reads all five blobs from one exact HEAD,
checks both frozen contracts before writing and does not run a collector.
No scheduled-task action needs changing.

Acceptance of the future H1 collector still requires a natural scheduled
attempt on/after the first declared session. The Inspired runner also needs
its next natural decision/entry/close to verify event provenance; a startup
guard does not substitute for a closed trade.
