#!/usr/bin/env python3
from pathlib import Path
ALLOWED=('XAWINWDO_REGIME_001','MT5_TERMINAL')
def main():
 files=['XAWINWDO_MT5_PRIMARY_EXPERIMENT.v1.json','MT5_XAWINWDO_SOURCE_ROLE.v1.json','XAWINWDO_MT5_PROMOTION_GATE.v1.json','xawinwdo_mt5_acceptance.v1.json']
 text='\n'.join(Path(__file__).with_name(x).read_text() for x in files)
 assert 'XAWINWDO_REGIME_001' in text and 'automatic_general_factory_promotion": false' in text
 print('XAWINWDO_MT5_SCOPE_OK')
if __name__=='__main__': main()
