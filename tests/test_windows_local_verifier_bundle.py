from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "windows_local_verifier" / "Invoke-GateBtcLocalVerify.ps1"
CMD = ROOT / "windows_local_verifier" / "RUN_GATE_BTC_LOCAL_VERIFY.cmd"
WORKFLOW = ROOT / ".github" / "workflows" / "gate-btc-migration-parallel.yml"


class WindowsLocalVerifierBundleTests(unittest.TestCase):
    def test_powershell_verifier_is_fail_closed_and_offline(self) -> None:
        text = PS1.read_text(encoding="utf-8")
        required = (
            'GATE_BTC_RESEARCH_ONLY must remain true',
            'EXCHANGE_API_SECRET',
            'EXCHANGE_PRIVATE_KEY',
            'TRADING_API_KEY',
            '--no-index',
            'NETWORK_ACTIONS=NONE',
            'PROJECT_FILES_MODIFIED=0',
            'LOCAL_COLLECTION_READ=False',
            'LOCAL_COLLECTION_MODIFIED=False',
            'ORDERS_GENERATED=0',
            'REAL_CAPITAL_USED=0',
            'OPERATIONAL_STATUS=NOT_APPROVED',
            'SEND_THIS_TXT_TO_CHAT',
            'Compress-Archive',
            'Downloads',
            'exit 1',
        )
        for token in required:
            self.assertIn(token, text)

    def test_native_process_wrapper_uses_exit_code_not_stderr_records(self) -> None:
        text = PS1.read_text(encoding="utf-8")
        required = (
            '[System.Diagnostics.ProcessStartInfo]::new()',
            'RedirectStandardOutput = $true',
            'RedirectStandardError = $true',
            '$Process.StandardOutput.ReadToEnd()',
            '$Process.StandardError.ReadToEnd()',
            '$ExitCode = $Process.ExitCode',
        )
        for token in required:
            self.assertIn(token, text)
        self.assertNotIn('& $FilePath @Arguments 1> $StdoutPath 2> $StderrPath', text)

    def test_launcher_is_relative_and_returns_verifier_exit_code(self) -> None:
        text = CMD.read_text(encoding="utf-8")
        self.assertIn('%~dp0', text)
        self.assertIn('ExecutionPolicy Bypass', text)
        self.assertIn('Invoke-GateBtcLocalVerify.ps1', text)
        self.assertIn('exit /b %RC%', text)

    def test_workflow_builds_and_self_tests_offline_bundle(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        required = (
            'tests/test_windows_local_verifier_bundle.py',
            'Build offline Windows local verifier bundle',
            'Self-test packaged Windows local verifier',
            'gate-btc-windows-local-verifier-${{ github.run_id }}',
            'BUNDLE_MANIFEST.json',
            'pip download',
            '$PSNativeCommandUseErrorActionPreference = $true',
        )
        for token in required:
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
