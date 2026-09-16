from pathlib import Path
def test_command_has_no_order_or_engine_actions():
 s=Path('tools/gate_btc_factory/xawinwdo_mt5_runtime_command.txt').read_text(); assert 'win_wdo_mt5_qualify.py' in s and 'win_wdo_mt5_materialize.py' in s; assert 'order_send' not in s.lower() and 'ENGINE_FEED=true' not in s
