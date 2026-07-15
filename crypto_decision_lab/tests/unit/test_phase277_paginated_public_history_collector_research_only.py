from crypto_decision_lab.scripts.phase276_285_strategy_search_common import LONG_SOURCES,p277
def rows(start,n):return [[start+i*3600000,"100","200","50",str(100+i*.01),"10"] for i in range(n)]
def fetch(u):
 end=int(u.split("endTime=")[1].split("&")[0]) if "endTime=" in u else int(u.split("end=")[1].split("&")[0]) if "end=" in u else 1708000000000
 start=end-999*3600000;data=rows(start,1000)
 return data if "binance" in u else {"retCode":0,"result":{"list":list(reversed(data))}}
def test_phase277_paginates_two_sources():
 p=p277(fetcher=fetch,clock=1708000000000,sources=LONG_SOURCES);assert p["passed"] and p["successful_source_count"]==2 and p["consensus_hours"]>=2000
