# QRDS/QOS Workspace Housekeeping

This operational-development utility standardizes local cleanup after QRDS/QOS sprints.

It is **not** a trading, allocation, signal, or execution component. It only:

- removes Python cache directories and pytest caches;
- reinforces `.gitignore` entries for generated artifacts;
- keeps sprint installer files such as `qrds_sprint_*.sh` out of Git;
- reports `git status --short` in HTML/Markdown/JSON;
- flags suspicious untracked files for human review.

## Safety scope

The command keeps the project in `INTERACTIVE_RESEARCH_ONLY` mode.

It does not request API keys, does not connect to an authenticated exchange, does not generate orders, does not generate signals, does not generate recommendations, does not generate allocations, and does not use real capital.

## Standard command

```bash
cd /workspaces/QRDS
bash qrds_housekeeping.sh
```

## Serve command

```bash
cd /workspaces/QRDS
bash qrds_housekeeping_serve.sh
```

Then open:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

## Artifact cleanup

By default, generated artifacts are **not removed**, because the user may be reviewing a local portal. To remove artifacts intentionally:

```bash
cd /workspaces/QRDS
bash qrds_housekeeping.sh --clean-artifacts
```

Use this only after you have finished reviewing local outputs.
