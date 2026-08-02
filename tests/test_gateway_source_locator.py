from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "gateway_source_locator" / "Find-GateBtcGatewaySource.ps1"
CMD = ROOT / "gateway_source_locator" / "RUN_GATEWAY_SOURCE_LOCATOR.cmd"
WORKFLOW = ROOT / ".github" / "workflows" / "gate-btc-windows-powershell51-smoke.yml"


class GatewaySourceLocatorTests(unittest.TestCase):
    def test_locator_is_read_only_and_emits_auditable_reports(self) -> None:
        text = PS1.read_text(encoding="utf-8")
        required = (
            "qos_v2a1_gateway_scanner_v0_9.zip",
            "qos_master_pipeline_v0_2.zip",
            "coingecko_top500",
            "delta_ls_70_30",
            "Get-FileHash -Algorithm SHA256",
            "NETWORK_ACTIONS=NONE",
            "SEARCHED_FILES_MODIFIED=0",
            "PROJECT_FILES_MODIFIED=0",
            "LOCAL_COLLECTION_READ=False",
            "LOCAL_COLLECTION_MODIFIED=False",
            "RESEARCH_ONLY=True",
            "ORDERS_GENERATED=0",
            "REAL_CAPITAL_USED=0",
            "OPERATIONAL_STATUS=NOT_APPROVED",
            "SEND_THIS_TXT_TO_CHAT",
            "GATE_BTC_GATEWAY_SOURCE_LOCATOR_",
        )
        for token in required:
            self.assertIn(token, text)

        forbidden = (
            "Remove-Item",
            "Move-Item",
            "Copy-Item",
            "Invoke-WebRequest",
            "Invoke-RestMethod",
            "Start-BitsTransfer",
        )
        for token in forbidden:
            self.assertNotIn(token, text)

    def test_launcher_is_relative_and_preserves_exit_code(self) -> None:
        text = CMD.read_text(encoding="utf-8")
        self.assertIn("%~dp0Find-GateBtcGatewaySource.ps1", text)
        self.assertIn("ExecutionPolicy Bypass", text)
        self.assertIn("exit /b %RC%", text)

    def test_windows_powershell_workflow_runs_synthetic_locator_smoke(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        required = (
            "gateway_source_locator/**",
            "tests/test_gateway_source_locator.py",
            "Windows PowerShell 5.1 Gateway locator parser check",
            "Windows PowerShell 5.1 Gateway locator synthetic smoke",
            "gate-btc-gateway-source-locator-${{ github.run_id }}",
        )
        for token in required:
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
