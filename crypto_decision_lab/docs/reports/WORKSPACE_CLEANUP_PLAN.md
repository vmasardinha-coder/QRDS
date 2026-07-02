# QRDS/QOS Controlled Workspace Cleanup Plan

Sprint 9Q converts the workspace, portal, and documentation inventory into a controlled cleanup plan.

The report is research-only and plan-only. It must not delete files by itself. Cleanup actions require a later explicit cleanup sprint.

## Acceptance criteria

- Duplicate wrappers are classified.
- Cleanup candidates are categorized by risk.
- Portal and documentation surfaces remain visible.
- Git status is reported.
- No operational permissions are introduced.
- Policy lock remains active.

## Current policy

Generated caches, backup files, old local hotfix installers, and exact duplicate script wrappers may be candidates for later cleanup. Different-content duplicates require manual review.
