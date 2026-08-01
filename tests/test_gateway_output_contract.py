import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gateway_validator", ROOT / "tools" / "validate_gateway_output_contract.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class GatewayOutputContractTests(unittest.TestCase):
    def test_fails_closed_when_outputs_are_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            errors = MODULE.validate(Path(temp), ROOT / "migration" / "gateway" / "gateway_output_contract_v010.json")
        self.assertTrue(errors)
        self.assertTrue(all(item.startswith("missing:") for item in errors))

    def test_rejects_operational_promotion(self):
        contract = json.loads((ROOT / "migration" / "gateway" / "gateway_output_contract_v010.json").read_text())
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            for name, fields in contract["required_files"].items():
                path = output / name
                if path.suffix == ".json":
                    payload = {field: [] if field.endswith("checks") else "x" for field in fields}
                    if name == "v2a1_run_manifest.json":
                        payload.update(version=contract["gateway_version"], mode=contract["safety_invariants"]["mode"], operational_status="APPROVED", evidence_status=contract["safety_invariants"]["evidence_status"])
                    path.write_text(json.dumps(payload))
                else:
                    path.write_text(",".join(fields) + "\n", encoding="utf-8")
            errors = MODULE.validate(output, ROOT / "migration" / "gateway" / "gateway_output_contract_v010.json")
        self.assertIn("safety_mismatch:operational_status:'APPROVED'", errors)


if __name__ == "__main__":
    unittest.main()
