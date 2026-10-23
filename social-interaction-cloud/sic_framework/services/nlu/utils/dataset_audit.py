"""
dataset_audit.py

Automated NLU dataset quality & label-consistency audit tool.
Uses Stratified K-Fold out-of-fold probability estimates (Confident Learning heuristic)
and TF-IDF cosine similarity to detect:
1. Near-duplicate cross-intent label conflicts
2. Suspected mislabeled utterances
3. Spurious n-gram shortcuts
"""

import argparse
import json
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import StratifiedKFold, cross_val_predict

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
warnings.filterwarnings("ignore", category=ConvergenceWarning)

DATA_DIR = Path(__file__).resolve().parent / "data"

# (file name, split) pairs; must mirror the files consumed by train_and_export.py
SPLIT_FILES = (
    ("train.json", "train"),
    ("exclusion_examples.json", "train"),
    ("test.json", "test"),
    ("exclusion_examples_test.json", "test"),
)


def load_samples(file_path: Path, split_name: str) -> list[dict]:
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list) or not raw:
        return []

    text_key = next((k for k in ("text", "utterance", "sentence", "input") if k in raw[0]), "text")
    slot_key = next((k for k in ("slots", "entities", "tags") if k in raw[0]), "slots")

    records = []
    for idx, item in enumerate(raw):
        records.append({
            "split": split_name,
            "index": idx,
            "text": str(item.get(text_key, "")).strip(),
            "intent": str(item.get("intent", "")).strip(),
            "slots": item.get(slot_key, {}),
        })
    return records


def load_all_splits(data_dir: Path = DATA_DIR) -> list[dict]:
    """
    Load every NLU split used by train_and_export.py:
    train = train.json + exclusion_examples.json, test = test.json + exclusion_examples_test.json.
    """
    records: list[dict] = []
    for fname, split in SPLIT_FILES:
        records.extend(load_samples(data_dir / fname, split))
    return records


def compute_top_k_neighbors(X, k: int = 5, chunk_size: int = 1000):
    """
    Chunked top-k cosine neighbours (self excluded) so memory stays O(chunk_size * n)
    instead of materialising the full n x n similarity matrix.
    Returns (indices, similarities), each shaped (n, k) and sorted by descending similarity.
    """
    n = X.shape[0]
    k = min(k, n - 1)
    idx_out = np.zeros((n, k), dtype=np.int64)
    sim_out = np.zeros((n, k), dtype=np.float64)
    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        sims = cosine_similarity(X[start:end], X)
        rows = np.arange(end - start)
        sims[rows, rows + start] = -1.0
        part = np.argpartition(-sims, k - 1, axis=1)[:, :k]
        part_sims = np.take_along_axis(sims, part, axis=1)
        order = np.argsort(-part_sims, axis=1)
        idx_out[start:end] = np.take_along_axis(part, order, axis=1)
        sim_out[start:end] = np.take_along_axis(part_sims, order, axis=1)
    return idx_out, sim_out


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def find_train_test_leakage(records: list[dict]) -> list[dict]:
    """Exact (case/whitespace-normalised) utterance overlap between train and test splits."""
    train_texts = {}
    for r in records:
        if r["split"] == "train":
            train_texts.setdefault(_normalize_text(r["text"]), r)
    leaked = []
    for r in records:
        if r["split"] != "test":
            continue
        match = train_texts.get(_normalize_text(r["text"]))
        if match is not None:
            leaked.append({
                "text": r["text"],
                "test_index": r["index"],
                "train_index": match["index"],
                "test_intent": r["intent"],
                "train_intent": match["intent"],
            })
    return leaked


def find_spurious_ngrams(
    records: list[dict], min_support: int = 4, purity_threshold: float = 0.90
) -> list[dict]:
    texts = [r["text"] for r in records if r["split"] == "train"]
    intents = [r["intent"] for r in records if r["split"] == "train"]

    vec = CountVectorizer(ngram_range=(1, 3), lowercase=True)
    X = vec.fit_transform(texts)
    vocab = vec.get_feature_names_out()

    intent_list = sorted(list(set(intents)))
    intent_to_idx = {c: i for i, c in enumerate(intent_list)}
    y = np.array([intent_to_idx[c] for c in intents])

    ngram_totals = np.asarray(X.sum(axis=0)).ravel()
    shortcuts = []

    for col_idx, total_count in enumerate(ngram_totals):
        if total_count < min_support:
            continue
        col_mask = X[:, col_idx].toarray().ravel() > 0
        class_counts = Counter(y[col_mask])
        top_class_idx, top_count = class_counts.most_common(1)[0]
        purity = top_count / total_count
        if purity >= purity_threshold:
            shortcuts.append({
                "ngram": vocab[col_idx],
                "dominant_intent": intent_list[top_class_idx],
                "occurrences": int(total_count),
                "intent_purity": round(float(purity), 3),
            })

    shortcuts.sort(key=lambda x: (x["intent_purity"], x["occurrences"]), reverse=True)
    return shortcuts[:50]


def audit_dataset(records: list[dict]) -> dict:
    texts = [r["text"] for r in records]
    intents = [r["intent"] for r in records]

    classes, y = np.unique(intents, return_inverse=True)
    class_counts = Counter(y)
    min_class_samples = min(class_counts.values())
    n_splits = min(5, max(2, min_class_samples))

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    X_tfidf = vectorizer.fit_transform(texts)

    clf = LogisticRegression(C=2.0, max_iter=1000, class_weight="balanced")
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    oof_probs = cross_val_predict(clf, X_tfidf, y, cv=skf, method="predict_proba")

    top_k_idx_all, top_k_sim_all = compute_top_k_neighbors(X_tfidf, k=5)

    suspected_errors = []
    near_duplicate_conflicts = []
    seen_pairs = set()

    for i, rec in enumerate(records):
        given_idx = y[i]
        given_prob = float(oof_probs[i, given_idx])
        pred_idx = int(np.argmax(oof_probs[i]))
        pred_prob = float(oof_probs[i, pred_idx])

        top_k_indices = top_k_idx_all[i]
        top_k_sims = top_k_sim_all[i]
        neighbor_intents = [records[n_idx]["intent"] for n_idx in top_k_indices]
        neighbor_disagreement = sum(
            1 for ni in neighbor_intents if ni != rec["intent"]
        ) / len(neighbor_intents)

        for n_idx, sim_score in zip(top_k_indices, top_k_sims):
            sim_score = float(sim_score)
            if sim_score >= 0.85 and records[n_idx]["intent"] != rec["intent"]:
                pair_key = tuple(sorted((i, int(n_idx))))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    near_duplicate_conflicts.append({
                        "similarity": round(sim_score, 3),
                        "sample_a": {
                            "split": rec["split"],
                            "index": rec["index"],
                            "text": rec["text"],
                            "intent": rec["intent"],
                        },
                        "sample_b": {
                            "split": records[n_idx]["split"],
                            "index": records[n_idx]["index"],
                            "text": records[n_idx]["text"],
                            "intent": records[n_idx]["intent"],
                        },
                    })

        if pred_idx != given_idx and (
            pred_prob >= 0.55 or (given_prob < 0.25 and neighbor_disagreement >= 0.6)
        ):
            suspected_errors.append({
                "split": rec["split"],
                "index": rec["index"],
                "text": rec["text"],
                "given_intent": rec["intent"],
                "given_intent_confidence": round(given_prob, 3),
                "suggested_intent": str(classes[pred_idx]),
                "suggested_intent_confidence": round(pred_prob, 3),
                "neighbor_disagreement_ratio": round(neighbor_disagreement, 2),
                "closest_neighbors": [
                    {
                        "text": records[n_idx]["text"],
                        "intent": records[n_idx]["intent"],
                        "similarity": round(float(n_sim), 3),
                    }
                    for n_idx, n_sim in zip(top_k_indices[:3], top_k_sims[:3])
                ],
            })

    suspected_errors.sort(key=lambda x: x["given_intent_confidence"])
    near_duplicate_conflicts.sort(key=lambda x: x["similarity"], reverse=True)

    leaked = find_train_test_leakage(records)

    return {
        "summary": {
            "total_samples_audited": len(records),
            "suspected_label_errors_count": len(suspected_errors),
            "near_duplicate_conflicts_count": len(near_duplicate_conflicts),
            "train_test_leakage_count": len(leaked),
        },
        "suspected_label_errors": suspected_errors,
        "near_duplicate_conflicts": near_duplicate_conflicts,
        "train_test_leakage": leaked,
        "spurious_shortcuts": find_spurious_ngrams(records),
    }


def main():
    parser = argparse.ArgumentParser(description="Audit NLU train/test splits for label noise and conflicts")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to save the full JSON audit report",
    )
    parser.add_argument(
        "--max_conflicts",
        type=int,
        default=None,
        help="CI/CD Quality Gate: Fail if near_duplicate_conflicts_count exceeds this value",
    )
    parser.add_argument(
        "--max_leakage",
        type=int,
        default=None,
        help="CI/CD Quality Gate: Fail if exact train/test utterance overlap exceeds this value",
    )
    args = parser.parse_args()

    all_records = load_all_splits(DATA_DIR)

    if not all_records:
        print(f"No dataset records found in {DATA_DIR}.")
        sys.exit(1)

    report = audit_dataset(all_records)
    print(f"Audit complete: {report['summary']}")

    if args.output:
        output_file = Path(args.output)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        print(f"Detailed report written to {output_file.resolve()}")

    if args.max_conflicts is not None:
        conflicts = report["summary"]["near_duplicate_conflicts_count"]
        if conflicts > args.max_conflicts:
            print(
                f"DATASET GATE FAILED: {conflicts} near-duplicate label conflicts > allowed {args.max_conflicts}"
            )
            sys.exit(1)
        print(f"DATASET GATE PASSED: {conflicts} near-duplicate label conflicts <= {args.max_conflicts}")

    if args.max_leakage is not None:
        leakage = report["summary"]["train_test_leakage_count"]
        if leakage > args.max_leakage:
            print(f"DATASET GATE FAILED: {leakage} train/test leaked utterances > allowed {args.max_leakage}")
            sys.exit(1)
        print(f"DATASET GATE PASSED: {leakage} train/test leaked utterances <= {args.max_leakage}")


if __name__ == "__main__":
    main()

