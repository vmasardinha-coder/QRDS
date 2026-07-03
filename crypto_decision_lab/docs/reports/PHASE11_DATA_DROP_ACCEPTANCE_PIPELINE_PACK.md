# QRDS/QOS Phase 11 Data Drop Acceptance Pipeline Pack

Sprint 11Q–11Z consolidates the data-drop pipeline into one acceptance portal.

It reads the normalizer, sample intake, quality gate, depth readiness, and promotion-lock reports, then reports whether the latest data drop is still fallback-only or inbox-driven.

Primary launcher:

```bash
bash qrds_phase11_data_drop_acceptance_pipeline_pack_serve.sh
```
