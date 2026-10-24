import unittest
from types import SimpleNamespace
from tools.gate_btc_a7a5_swap_history import request_with_retry

class TransientTests(unittest.TestCase):
    def session(self,codes):
        class Session:
            def __init__(self):self.calls=[];self.codes=iter(codes)
            def get(self,url,**kwargs):self.calls.append((url,kwargs));return SimpleNamespace(status_code=next(self.codes))
        return Session()
    def test_transient_recovers_same_source(self):
        s=self.session([503,200]);wait=[];trace=[]
        r=request_with_retry(s,'get','https://source/exact',timeout=30,sleep_fn=wait.append,trace=trace)
        self.assertEqual(r.status_code,200);self.assertEqual(len(s.calls),2)
        self.assertEqual(s.calls[0],s.calls[1]);self.assertEqual(wait,[1]);self.assertEqual(len(trace),2)
    def test_exhausts_three_attempts(self):
        s=self.session([503]*3);wait=[]
        self.assertEqual(request_with_retry(s,'get','same',sleep_fn=wait.append).status_code,503)
        self.assertEqual(len(s.calls),3);self.assertEqual(wait,[1,2])
    def test_does_not_retry_rate_limit_or_permanent_errors(self):
        for code in [400,403,404,429]:
            s=self.session([code]);request_with_retry(s,'get','same',sleep_fn=lambda _:self.fail('unexpected wait'))
            self.assertEqual(len(s.calls),1)
