from crypto_decision_lab.scripts.phase246_255_public_shadow_decision_common import SOURCES,p248
def f(url):
 rows=[[1700000000000+i*3600000,"100","120","90",str(100+i/10),"10"] for i in range(120)]
 if "binance" in url:return rows
 if "okx" in url:return {"code":"0","data":list(reversed(rows))}
 raise RuntimeError("down")
def test_phase248_two_sources():
 p=p248(fetcher=f,clock=1700500000000,sources=SOURCES[:3],retries=1);assert p["passed"] and p["successful_source_count"]==2
