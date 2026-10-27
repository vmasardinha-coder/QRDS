import unittest
from tools import gate_btc_hash_settlement_history as h


def response(body):
    return [{"jsonrpc":"2.0","id":x["id"],"result":{"block":{"header":{
        "chain_id":h.CHAIN,"height":x["params"]["height"]}}}} for x in body]


class BlockBatchTests(unittest.TestCase):
    def test_out_of_order_responses_bind_by_id(self):
        result=h.fetch_block_batch(lambda name,body:list(reversed(response(body))),"blocks",[10,20])
        self.assertEqual(set(result),{10,20})
        self.assertEqual(result[10]["block"]["header"]["height"],"10")

    def test_capacity_rejection_splits_exact_heights_and_preserves_attempt_names(self):
        attempts=[]
        def fetch(name,body):
            attempts.append((name,body))
            return {"error":{"code":-32005,"message":"batch limit exceeded"}} if len(body)>2 else response(body)
        result=h.fetch_block_batch(fetch,"blocks_0000.json",list(range(10,20)))
        self.assertEqual(set(result),set(range(10,20)))
        self.assertLessEqual(len(attempts),19)
        self.assertEqual(len({name for name,_ in attempts}),len(attempts))

    def test_truncated_batch_is_requeried_not_partially_credited(self):
        calls=[]
        def fetch(name,body):
            calls.append(body)
            return response(body)[:1] if len(body)>1 else response(body)
        self.assertEqual(set(h.fetch_block_batch(fetch,"b",[1,2,3])),{1,2,3})
        self.assertEqual(len(calls),5)

    def test_invalid_singleton_fails_closed(self):
        calls=[]
        def fetch(name,body):calls.append(name);return []
        with self.assertRaisesRegex(ValueError,"INVALID_BLOCK_BATCH"):
            h.fetch_block_batch(fetch,"b",[1,2])
        self.assertLessEqual(len(calls),3)

    def test_unwrapped_singleton_requires_exact_id_and_jsonrpc(self):
        self.assertEqual(set(h.fetch_block_batch(lambda n,b:response(b)[0],"b",[3])),{3})
        with self.assertRaisesRegex(ValueError,"INVALID_BLOCK_BATCH"):
            h.fetch_block_batch(lambda n,b:{"id":99,"result":{}},"b",[3])

    def test_wrong_chain_or_height_never_retried_or_accepted(self):
        for field,value in [("chain_id","wrong"),("height","999")]:
            calls=[]
            def fetch(name,body):
                calls.append(name);rows=response(body);rows[0]["result"]["block"]["header"][field]=value;return rows
            with self.assertRaisesRegex(ValueError,"WRONG_BATCH_BLOCK"):
                h.fetch_block_batch(fetch,"b",[1,2])
            self.assertEqual(len(calls),1)

    def test_authorization_error_is_not_retried(self):
        calls=[]
        def fetch(name,body):calls.append(name);return {"error":{"message":"unauthorized"}}
        with self.assertRaisesRegex(ValueError,"HASH_BLOCK_RPC_ERROR"):
            h.fetch_block_batch(fetch,"b",[1,2])
        self.assertEqual(len(calls),1)

    def test_inner_error_cannot_be_credited(self):
        def fetch(name,body):
            rows=response(body);rows[0]={"jsonrpc":"2.0","id":0,"error":{"message":"missing block"}};return rows
        with self.assertRaisesRegex(ValueError,"INVALID_BLOCK_RESPONSE"):
            h.fetch_block_batch(fetch,"b",[1,2])


if __name__=="__main__":unittest.main()
