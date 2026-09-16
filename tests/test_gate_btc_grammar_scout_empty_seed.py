import subprocess,sys
def test_empty_seed_not_success():
 r=subprocess.run([sys.executable,'tools/gate_btc_factory/grammar_scout_status.py','--input','tools/gate_btc_factory/grammar_scout_status.example.json']); assert r.returncode==2
