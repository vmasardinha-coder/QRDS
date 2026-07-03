# QRDS/QOS Installer Archive / Repo Slimdown Safe Apply

Sprint 9W applies only reviewed low-risk installer archive moves.

Scope:

- root `qrds_sprint_8*` and `qrds_sprint_9A` through `qrds_sprint_9V` installers;
- root hotfix installers matching `*hotfix*.sh`;
- destination: `scripts/archive/installers/`;
- live wrappers, report modules, docs, datasets, and medium-review files are not removed by this gate.

The generated report remains `INTERACTIVE_RESEARCH_ONLY` and cannot unlock operational use.
