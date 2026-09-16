import subprocess,sys
def test_guard(): assert subprocess.run([sys.executable,'tools/gate_btc_factory/xawinwdo_mt5_scope_guard.py']).returncode==0
