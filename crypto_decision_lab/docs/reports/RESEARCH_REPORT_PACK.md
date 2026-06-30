# QRDS Research Report Pack v1

Sprint 7G generates a human-readable research report from full research CLI
artifacts.

## Generate full research artifacts

From repository root:

```bash
bash qrds_full_research.sh \
  --output-dir artifacts/full_research \
  --run-id full-research-run \
  --report-id edge-report
```

## Generate report pack

```bash
bash qrds_report_pack.sh \
  --full-research-dir artifacts/full_research \
  --output-dir artifacts/report_pack
```

## Outputs

```text
research_report.md
research_report_pack.json
artifact_map.json
research_report_pack_index.json
```

## Safety

The report pack is research-only.

It is not:

```text
a recommendation
a trading signal
an order
an allocation
an execution instruction
```
