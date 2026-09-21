#!/usr/bin/env python3
"""External BTSE standalone: frozen ProsusAI FinBERT capability benchmark."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from importlib import metadata
from pathlib import Path

MODEL_ID = "ProsusAI/finbert"
MODEL_REVISION = "a677990aaa7e6db63d673786a74d575cc071522e"
DATASET_ID = "atrost/financial_phrasebank"
DATASET_SPLIT = "test"
LABELS = ("negative", "neutral", "positive")
MIN_ACCURACY = 0.80
MIN_MACRO_F1 = 0.75


def normalize_label(value, feature=None) -> str:
    if isinstance(value, str):
        label = value.strip().lower()
    elif feature is not None and hasattr(feature, "int2str"):
        label = str(feature.int2str(int(value))).strip().lower()
    else:
        mapping = {0: "negative", 1: "neutral", 2: "positive"}
        label = mapping[int(value)]
    if label not in LABELS:
        raise ValueError(f"unexpected label: {label}")
    return label


def compute_metrics(gold: list[str], pred: list[str]) -> dict:
    if len(gold) != len(pred) or not gold:
        raise ValueError("gold/pred length mismatch or empty benchmark")
    correct = sum(g == p for g, p in zip(gold, pred))
    per_class = {}
    matrix = {g: {p: 0 for p in LABELS} for g in LABELS}
    for g, p in zip(gold, pred):
        if g not in LABELS or p not in LABELS:
            raise ValueError("unknown class")
        matrix[g][p] += 1
    precisions, recalls, f1s = [], [], []
    for label in LABELS:
        tp = matrix[label][label]
        fp = sum(matrix[g][label] for g in LABELS if g != label)
        fn = sum(matrix[label][p] for p in LABELS if p != label)
        support = sum(matrix[label].values())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)
    return {
        "accuracy": correct / len(gold),
        "macro_precision": sum(precisions) / len(precisions),
        "macro_recall": sum(recalls) / len(recalls),
        "macro_f1": sum(f1s) / len(f1s),
        "per_class": per_class,
        "confusion_matrix": matrix,
    }


def qa_gate(sentences: list[str], gold: list[str], pred: list[str], model_revision: str, dataset_sha: str) -> dict:
    counts = Counter(gold)
    duplicate_count = len(sentences) - len(set(sentences))
    checks = {
        "min_examples": len(sentences) >= 500,
        "all_classes_present": all(counts.get(x, 0) > 0 for x in LABELS),
        "min_25_each_class": all(counts.get(x, 0) >= 25 for x in LABELS),
        "one_prediction_per_row": len(pred) == len(sentences),
        "predictions_known": all(x in LABELS for x in pred),
        "no_empty_sentence": all(bool(x.strip()) for x in sentences),
        "model_revision_recorded": bool(model_revision),
        "dataset_sha_recorded": bool(dataset_sha),
    }
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "gold_class_counts": dict(counts),
        "duplicate_sentence_count": duplicate_count,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    from datasets import load_dataset
    from huggingface_hub import HfApi
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

    dataset_info = HfApi().dataset_info(DATASET_ID)
    dataset_sha = dataset_info.sha
    ds = load_dataset(DATASET_ID, revision=dataset_sha, split=DATASET_SPLIT)
    feature = ds.features.get("label")
    sentences = [str(x).strip() for x in ds["sentence"]]
    gold = [normalize_label(x, feature) for x in ds["label"]]

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    clf = pipeline("text-classification", model=model, tokenizer=tokenizer, device=-1)
    outputs = clf(sentences, batch_size=32, truncation=True, max_length=128)
    pred = [normalize_label(x["label"]) for x in outputs]
    confidences = [float(x["score"]) for x in outputs]

    qa = qa_gate(sentences, gold, pred, MODEL_REVISION, dataset_sha)
    metrics = compute_metrics(gold, pred) if qa["pass"] else None
    capability_pass = bool(
        qa["pass"]
        and metrics
        and metrics["accuracy"] >= MIN_ACCURACY
        and metrics["macro_f1"] >= MIN_MACRO_F1
    )

    rows = []
    for i, (sentence, g, p, conf) in enumerate(zip(sentences, gold, pred, confidences)):
        rows.append({"row": i, "sentence": sentence, "gold": g, "prediction": p, "confidence": conf})
    prediction_bytes = ("\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n").encode()
    prediction_sha = hashlib.sha256(prediction_bytes).hexdigest()
    (out / "PREDICTIONS.jsonl").write_bytes(prediction_bytes)

    if not qa["pass"]:
        disposition = "DATA_OR_MODEL_CAPABILITY_NOT_ESTABLISHED"
    elif capability_pass:
        disposition = "STANDALONE_CAPABILITY_PASS / HOLD_FOR_TIMESTAMPED_CRYPTO_NEWS_EVIDENCE"
    else:
        disposition = "REJECT_AS_SENTIMENT_COMPONENT"

    summary = {
        "schema_version": "GATE_BTC_2_FINBERT_STANDALONE_V1",
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "dataset_id": DATASET_ID,
        "dataset_sha": dataset_sha,
        "dataset_split": DATASET_SPLIT,
        "examples": len(sentences),
        "qa": qa,
        **(metrics or {}),
        "mean_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
        "prediction_sha256": prediction_sha,
        "min_accuracy": MIN_ACCURACY,
        "min_macro_f1": MIN_MACRO_F1,
        "capability_pass": capability_pass,
        "disposition": disposition,
        "integrated_economic_comparison_authorized": False,
        "timestamped_crypto_news_corpus_proven": False,
        "research_only": True,
        "shadow_only": True,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "factory_runtime_untouched": True,
        "economic_claim_authorized": False,
        "factory_migration_authorized": False,
        "packages": {
            name: metadata.version(name)
            for name in ("transformers", "datasets", "huggingface-hub", "torch")
        },
    }
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if qa["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
