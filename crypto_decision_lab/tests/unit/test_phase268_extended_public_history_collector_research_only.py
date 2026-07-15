from crypto_decision_lab.scripts.phase266_275_regime_replication_common import SOURCES,p268
def rows(n):return [[1700000000000+i*3600000,"100","200","50",str(100+i*.01),"10"] for i in range(n)]
def fetch(u):
 if "binance" in u:return rows(720)
 if "bybit" in u:return {"retCode":0,"result":{"list":list(reversed(rows(720)))}}
 if "okx" in u:return {"code":"0","data":list(reversed(rows(300)))}
 raise RuntimeError("down")
def test_phase268_collector():p=p268(fetcher=fetch,clock=1703000000000,sources=SOURCES,retries=1);assert p["passed"] and p["long_source_count"]==2
