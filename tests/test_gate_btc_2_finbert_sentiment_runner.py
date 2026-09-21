from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "gate_btc_2_finbert_sentiment_runner.py"
spec = importlib.util.spec_from_file_location("finbert_runner", MODULE_PATH)
fb = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(fb)


class FinBERTSentimentRunnerTests(unittest.TestCase):
    def test_normalize_labels(self):
        self.assertEqual(fb.normalize_label("Positive"), "positive")
        self.assertEqual(fb.normalize_label(" negative "), "negative")
        with self.assertRaises(ValueError):
            fb.normalize_label("bullish")

    def test_metrics_perfect_predictions(self):
        gold = ["negative", "neutral", "positive"] * 4
        result = fb.compute_metrics(gold, list(gold))
        self.assertEqual(result["accuracy"], 1.0)
        self.assertEqual(result["macro_f1"], 1.0)
        for label in fb.LABELS:
            self.assertEqual(result["per_class"][label]["f1"], 1.0)

    def test_metrics_detects_confusion(self):
        gold = ["negative", "neutral", "positive"]
        pred = ["neutral", "neutral", "positive"]
        result = fb.compute_metrics(gold, pred)
        self.assertAlmostEqual(result["accuracy"], 2 / 3)
        self.assertEqual(result["confusion_matrix"]["negative"]["neutral"], 1)

    def test_qa_gate_is_fail_closed(self):
        sentences = [f"sentence {i}" for i in range(600)]
        gold = ["negative"] * 200 + ["neutral"] * 200 + ["positive"] * 200
        pred = list(gold)
        qa = fb.qa_gate(sentences, gold, pred, fb.MODEL_REVISION, "datasetsha")
        self.assertTrue(qa["pass"])
        bad = fb.qa_gate(sentences, gold, pred[:-1], fb.MODEL_REVISION, "datasetsha")
        self.assertFalse(bad["pass"])

    def test_frozen_constants_and_boundaries(self):
        self.assertEqual(fb.MODEL_ID, "ProsusAI/finbert")
        self.assertEqual(fb.MODEL_REVISION, "a677990aaa7e6db63d673786a74d575cc071522e")
        self.assertEqual(fb.DATASET_ID, "atrost/financial_phrasebank")
        self.assertEqual(fb.DATASET_SPLIT, "test")
        self.assertEqual(fb.MIN_ACCURACY, 0.80)
        self.assertEqual(fb.MIN_MACRO_F1, 0.75)
        text = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('"integrated_economic_comparison_authorized": False', text)
        self.assertIn('"timestamped_crypto_news_corpus_proven": False', text)
        self.assertIn('"economic_claim_authorized": False', text)
        self.assertIn('"factory_migration_authorized": False', text)
        self.assertIn('"no_retune": True', text)
        self.assertIn('"no_backfill": True', text)


if __name__ == "__main__":
    unittest.main()
