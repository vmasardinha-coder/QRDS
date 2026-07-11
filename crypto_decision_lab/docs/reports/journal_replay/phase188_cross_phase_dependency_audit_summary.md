# Phase 188 â€” Cross-Phase Dependency Audit 0â€“185

## Gate

```text
PHASE188_CROSS_PHASE_DEPENDENCY_AUDIT_RESEARCH_ONLY_READY_RESEARCH_ONLY
```

## Result

```text
Phase status: READY_RESEARCH_ONLY_WITH_FINDINGS
Dependency status: CROSS_PHASE_DEPENDENCY_READY_RESEARCH_ONLY_WITH_FINDINGS
Executable dependency edges: 188
Forward executable imports: 0
Dependency cycles: 0
Errors: 0
Warnings: 18
Full suite: SKIPPED_LOCAL_ECONOMICAL
Operational: BLOCKED_RESEARCH_ONLY
Promotion allowed: False
Decision layer allowed: False
Shadow decision allowed: False
canonical_data_writes: 0
```

## Method

This phase reads existing scripts, tests, documents, and JSON artifacts.
It does not execute or rebuild prior phases.

Executable dependencies are derived from Python AST import statements.
String references are inventoried separately and do not become hard graph edges.

Hard failures:

- Python AST parse failure;
- forward executable phase import;
- executable phase dependency cycle.

Warnings:

- imported phase without an indexed script;
- checkpoint directly importing prior phase modules.

Missing legacy tests, documents, or local artifacts are informational only.

## Inventory

```json
{
  "phase_script_files": 149,
  "phase_test_files": 253,
  "phase_document_files": 171,
  "artifact_phases_present": 102,
  "script_phases_present": 146,
  "test_phases_present": 174,
  "document_phases_present": 155
}
```

## Graph summary

```json
{
  "node_count": 87,
  "edge_count": 188,
  "backward_edge_count": 188,
  "forward_edge_count": 0,
  "cycle_count": 0,
  "cycles": [],
  "edges": {
    "73": [
      72
    ],
    "74": [
      72,
      73
    ],
    "75": [
      72,
      73,
      74
    ],
    "76": [
      72,
      73,
      74,
      75
    ],
    "79": [
      72,
      76
    ],
    "80": [
      79
    ],
    "81": [
      80
    ],
    "83": [
      72,
      73,
      74,
      75,
      76,
      79
    ],
    "84": [
      79,
      83
    ],
    "85": [
      84
    ],
    "86": [
      79,
      83,
      84
    ],
    "88": [
      87
    ],
    "89": [
      87,
      88
    ],
    "98": [
      96,
      97
    ],
    "99": [
      96,
      97,
      98
    ],
    "100": [
      96,
      97,
      98,
      99
    ],
    "102": [
      101
    ],
    "103": [
      101,
      102
    ],
    "104": [
      101,
      102,
      103
    ],
    "105": [
      101,
      102,
      103,
      104
    ],
    "107": [
      106
    ],
    "108": [
      106,
      107
    ],
    "109": [
      106,
      107,
      108
    ],
    "110": [
      106,
      107,
      108,
      109
    ],
    "111": [
      106,
      107,
      108,
      109,
      110
    ],
    "112": [
      111
    ],
    "113": [
      111,
      112
    ],
    "114": [
      111,
      112,
      113
    ],
    "115": [
      111,
      112,
      113,
      114
    ],
    "116": [
      115
    ],
    "117": [
      114,
      116
    ],
    "118": [
      117
    ],
    "119": [
      118
    ],
    "120": [
      116,
      117,
      118,
      119
    ],
    "121": [
      116,
      117,
      119
    ],
    "122": [
      121
    ],
    "123": [
      121,
      122
    ],
    "124": [
      123
    ],
    "125": [
      121,
      122,
      123,
      124
    ],
    "127": [
      126
    ],
    "128": [
      127
    ],
    "129": [
      126,
      127,
      128
    ],
    "130": [
      126,
      127,
      128,
      129
    ],
    "131": [
      130
    ],
    "132": [
      131
    ],
    "133": [
      132
    ],
    "134": [
      131,
      132,
      133
    ],
    "135": [
      131,
      132,
      133,
      134
    ],
    "136": [
      135
    ],
    "137": [
      136
    ],
    "138": [
      137
    ],
    "139": [
      136,
      137,
      138
    ],
    "140": [
      136,
      137,
      138,
      139
    ],
    "141": [
      140
    ],
    "142": [
      141
    ],
    "143": [
      142
    ],
    "144": [
      141,
      142,
      143
    ],
    "145": [
      141,
      142,
      143,
      144
    ],
    "146": [
      145
    ],
    "147": [
      146
    ],
    "148": [
      147
    ],
    "149": [
      146,
      147,
      148
    ],
    "150": [
      146,
      147,
      148,
      149
    ],
    "151": [
      150
    ],
    "152": [
      151
    ],
    "153": [
      152
    ],
    "154": [
      151,
      152,
      153
    ],
    "155": [
      151,
      152,
      153,
      154
    ],
    "156": [
      155
    ],
    "157": [
      156
    ],
    "158": [
      157
    ],
    "159": [
      156,
      157,
      158
    ],
    "160": [
      156,
      157,
      158,
      159
    ],
    "161": [
      160
    ],
    "162": [
      161
    ],
    "163": [
      162
    ],
    "164": [
      161,
      162,
      163
    ],
    "165": [
      161,
      162,
      163,
      164
    ],
    "166": [
      165
    ],
    "167": [
      166
    ],
    "168": [
      167
    ],
    "169": [
      166,
      167,
      168
    ],
    "170": [
      166,
      167,
      168,
      169
    ],
    "171": [
      170
    ],
    "172": [
      171
    ],
    "173": [
      172
    ],
    "174": [
      171,
      172,
      173
    ]
  }
}
```

## Error and warning preview

```json
[
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase100_replay_evidence_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 100 directly imports prior phases [96, 97, 98, 99]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase105_replay_evidence_query_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 105 directly imports prior phases [101, 102, 103, 104]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase110_replay_evidence_query_export_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 110 directly imports prior phases [106, 107, 108, 109]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase115_replay_evidence_export_review_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 115 directly imports prior phases [111, 112, 113, 114]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase120_local_review_portal_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 120 directly imports prior phases [116, 117, 118, 119]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase125_review_portal_ux_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 125 directly imports prior phases [121, 122, 123, 124]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase130_data_trust_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 130 directly imports prior phases [126, 127, 128, 129]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase135_evidence_quality_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 135 directly imports prior phases [131, 132, 133, 134]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase140_edge_candidate_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 140 directly imports prior phases [136, 137, 138, 139]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase145_replay_validity_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 145 directly imports prior phases [141, 142, 143, 144]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase150_risk_ruin_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 150 directly imports prior phases [146, 147, 148, 149]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase155_shadow_decision_readiness_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 155 directly imports prior phases [151, 152, 153, 154]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase160_shadow_simulation_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 160 directly imports prior phases [156, 157, 158, 159]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase165_shadow_evidence_replay_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 165 directly imports prior phases [161, 162, 163, 164]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase170_shadow_score_batch_checkpoint_research_only.py",
    "message": "Checkpoint phase 170 directly imports prior phases [166, 167, 168, 169]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase75_journal_replay_quality_flags_research_only.py",
    "message": "Checkpoint phase 75 directly imports prior phases [72, 73, 74]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase80_journal_replay_batch_quarantine_research_only.py",
    "message": "Checkpoint phase 80 directly imports prior phases [79]; verify that it reads artifacts rather than rebuilding chains."
  },
  {
    "severity": "WARNING",
    "code": "CHECKPOINT_DIRECT_PHASE_IMPORT",
    "path": "src/crypto_decision_lab/scripts/phase85_journal_replay_batch_portal_qa_smoke_research_only.py",
    "message": "Checkpoint phase 85 directly imports prior phases [84]; verify that it reads artifacts rather than rebuilding chains."
  }
]
```

## Restrictions

```text
approval_effect: NONE_RESEARCH_ONLY
descriptive_only: True
valid_for_decision: False
full_suite_status: SKIPPED_LOCAL_ECONOMICAL
```

No trading signal, recommendation, allocation, order payload, safe-apply,
operational decision, or canonical data write was generated.
