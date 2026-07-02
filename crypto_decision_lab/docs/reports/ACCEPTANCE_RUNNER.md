# QRDS/QOS — Acceptance Runner

Sprint 9F adds a local one-command validation summary for the QRDS/QOS research stack.

The runner records:

- upstream gate presence;
- blocking gate count;
- safety-flag consistency;
- pytest pass/fail status;
- suspicious untracked workspace files;
- policy-lock status.

It cannot unlock operational use. It does not create execution instructions, order instructions, allocation outputs, exchange connections, account access, API-key use, or live-fund workflows.

Official mode remains `INTERACTIVE_RESEARCH_ONLY`.
