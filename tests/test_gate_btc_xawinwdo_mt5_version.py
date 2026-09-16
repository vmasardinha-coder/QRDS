from pathlib import Path
def test_version(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_experiment_version.txt').read_text().strip()=='XAWINWDO_MT5_PRIMARY_EXPERIMENT_V1'
