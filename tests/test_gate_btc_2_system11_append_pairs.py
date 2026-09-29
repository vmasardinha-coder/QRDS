import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
 def test_append_dedup(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);s=d/"s";l=d/"l"; rows=[{"pair_second_utc":1},{"pair_second_utc":2}]
   s.write_text("\n".join(json.dumps(x) for x in rows)+"\n");l.write_text(json.dumps(rows[0])+"\n")
   subprocess.check_call([sys.executable,str(ROOT/"tools/gate_btc_2_system11_append_pairs.py"),"--source",str(s),"--ledger",str(l)])
   self.assertEqual(len(l.read_text().splitlines()),2)
if __name__=="__main__":unittest.main()
