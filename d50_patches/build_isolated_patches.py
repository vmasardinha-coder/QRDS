from pathlib import Path
import hashlib,json,difflib
base=Path(__file__).resolve().parents[1]; source=base/'d50_sources'; dest=base/'d50_patches'
changes={}
cli=(source/'cli.py').read_bytes();s=cli.decode('utf-8')
s=s.replace('from .snapshot import collect_prospective_snapshot, evaluate_qualification','from .snapshot import collect_prospective_snapshot, evaluate_qualification\nfrom .gate_btc_d50_data_review_reporting import documentary_adjudication, reporting_lines')
s=s.replace('        report_lines.append("STATUS=PASS")','        # Reporting only: preserve frozen qualification/config flags and engine.\n        adjudication = documentary_adjudication(\n            contract_path=root / "gate_btc_inputs/candidate_contract_v32.json",\n            v32_zip_path=root / "gate_btc_inputs/GATE_BTC_D50_7D_V32_RATIFICATION_2026-07-30.zip",\n        )\n        result = {**result, "current_documentary_adjudication": adjudication}\n        report_lines.extend(reporting_lines(adjudication))\n        report_lines.append("STATUS=PASS")',1)
changes['cli.py']=(cli,s.encode('utf-8'))
gov=(source/'gate_btc_governance_master_v1.py').read_bytes();s=gov.decode('utf-8-sig')
s=s.replace('from datetime import datetime, timezone','from datetime import datetime, timezone\nfrom gate_btc_d50_data_review_reporting import documentary_adjudication, reporting_lines',1)
s=s.replace('audit = load_json(state / "D50_POSITION_AUDIT_LATEST.json")','audit = load_json(state / "D50_POSITION_AUDIT_LATEST.json")\n\n# Documentary review only; AUTOPILOT V2 is not the audited V3.2 engine.\nadjudication = documentary_adjudication(prospective_status=d50)',1)
s=s.replace('    "created_at_utc": now,','    "created_at_utc": now,\n    "current_documentary_adjudication": adjudication,',1)
s=s.replace('txt.write_text("\\n".join(lines), encoding="utf-8")','lines += ["", "=== D50 DOCUMENTARY DATA REVIEW ==="] + reporting_lines(adjudication)\ntxt.write_text("\\n".join(lines), encoding="utf-8")',1)
s += '\n# Captured by RUN_DAILY Add-Line for the persistent daily report.\nfor review_line in reporting_lines(adjudication):\n    print(review_line)\n'
changes['gate_btc_governance_master_v1.py']=(gov,s.encode('utf-8-sig'))
run=(source/'RUN_DAILY.ps1').read_bytes();encoding='utf-8-sig' if run.startswith(b'\xef\xbb\xbf') else 'utf-8';s=run.decode(encoding)
needle='& $VenvPython `\n                (Join-Path $InstallRoot "governance\\gate_btc_governance_master_v1.py") `'
# Preserve source newline convention.
# Source has mixed newline endings; preserve existing bytes outside hook.
assert needle in s;s=s.replace(needle,'$GovernanceOutput = & $VenvPython `\n                (Join-Path $InstallRoot "governance\\gate_btc_governance_master_v1.py") `',1)
needle2='                $Downloads\n\n            if ($LASTEXITCODE -eq 0) {'
assert needle2 in s;s=s.replace(needle2,'                $Downloads\n            $GovernanceExitCode = $LASTEXITCODE\n            foreach ($GovernanceLine in $GovernanceOutput) {\n                Add-Line ([string]$GovernanceLine)\n            }\n\n            if ($GovernanceExitCode -eq 0) {',1)
changes['RUN_DAILY.ps1']=(run,s.encode(encoding))
manifest=[]
for name,(before,after) in changes.items():
 (dest/name).write_bytes(after)
 (dest/(name+'.patch')).write_text(''.join(difflib.unified_diff(before.decode('utf-8-sig').replace('\r\n','\n').splitlines(True),after.decode('utf-8-sig').replace('\r\n','\n').splitlines(True),fromfile='before/'+name,tofile='after/'+name)))
 manifest.append({'filename':name,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(after).hexdigest()})
(dest/'PATCH_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
