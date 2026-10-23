#!/usr/bin/env python3
"""
train_and_export.py

Automated training, evaluation, and ONNX export pipeline for the BERT NLU model.
Optimized for training on GPU (e.g. NVIDIA RTX A4000) and deploying to CPU/Cloud Run.
Features real-time progress bars with speed (it/s), elapsed/ETA timers, and loss tracking.

Usage:
    python train_and_export.py
    python train_and_export.py --epochs 5 --batch_size 32 --lr 3e-5
"""

import os
import sys
import time
import argparse
import hashlib
import logging
import subprocess
from pathlib import Path

# Ensure social-interaction-cloud root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
SIC_ROOT = SCRIPT_DIR.parents[3]
if str(SIC_ROOT) not in sys.path:
    sys.path.insert(0, str(SIC_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TrainAndExport")

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import numpy as np

# Progress bar support with zero-dependency fallback
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


class FallbackProgressBar:
    """Lightweight ANSI progress bar providing real-time it/s, ETA, and metrics if tqdm is not installed."""
    def __init__(self, iterable, total=None, desc="", unit="it", ncols=95):
        self.iterable = iterable
        self.total = total or (len(iterable) if hasattr(iterable, "__len__") else None)
        self.desc = desc
        self.unit = unit
        self.ncols = ncols
        self.start_t = time.time()
        self.n = 0
        self.postfix_str = ""

    def __iter__(self):
        self.start_t = time.time()
        self._print()
        for item in self.iterable:
            yield item
            self.n += 1
            self._print()
        sys.stdout.write("\n")
        sys.stdout.flush()

    def set_postfix(self, metrics):
        self.postfix_str = ", ".join(f"{k}={v}" for k, v in metrics.items())
        self._print()

    def _format_time(self, seconds):
        mins, secs = divmod(int(seconds), 60)
        return f"{mins:02d}:{secs:02d}"

    def _print(self):
        elapsed = max(time.time() - self.start_t, 1e-4)
        rate = self.n / elapsed
        rate_str = f"{rate:5.2f} {self.unit}/s" if rate >= 1 else f"{1/rate:5.2f} s/{self.unit}"
        pct = self.n / self.total if self.total else 0
        eta = (self.total - self.n) / rate if (self.total and rate > 0) else 0
        time_str = f"{self._format_time(elapsed)}<{self._format_time(eta)}"

        bar_width = 22
        filled = int(bar_width * pct)
        bar = "█" * filled + "░" * (bar_width - filled)
        line = f"\r{self.desc}: {int(pct*100):3d}%|{bar}| {self.n}/{self.total} [{time_str}, {rate_str}]"
        if self.postfix_str:
            line += f" ({self.postfix_str})"
        sys.stdout.write(line.ljust(self.ncols)[:self.ncols])
        sys.stdout.flush()


def get_progress_bar(iterable, total=None, desc="", unit="it"):
    if HAS_TQDM:
        return tqdm(
            iterable,
            total=total,
            desc=desc,
            unit=unit,
            dynamic_ncols=True,
            leave=True,
        )
    return FallbackProgressBar(iterable, total=total, desc=desc, unit=unit)


from sic_framework.services.nlu.utils.dataset import (
    BERTNLUModel,
    NLURecipeDataset,
    fit_encoders,
    intent_label_encoder,
    load_data,
    load_ontology,
    preprocess_data,
    slot_label_encoder,
)


def train_model_with_progress(model, dataset, num_epochs=5, batch_size=16, learning_rate=2e-5, device="cpu"): #if trained on NVIDIA GPU, can be device="cuda" instead
    """
    Trains BERTNLUModel with live progress tracking, showing it/s, elapsed/ETA, and batch losses.
    """
    model.to(device)
    intent_loss_fn = nn.CrossEntropyLoss()
    slot_loss_fn = nn.CrossEntropyLoss(ignore_index=-100)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    total_batches = len(dataloader)

    logger.info(f"Starting training: {num_epochs} epochs | {total_batches} batches/epoch | batch size {batch_size}")

    for epoch in range(1, num_epochs + 1):
        model.train()
        epoch_loss = 0.0
        epoch_intent_loss = 0.0
        epoch_slot_loss = 0.0
        epoch_start = time.time()

        pbar = get_progress_bar(
            dataloader,
            total=total_batches,
            desc=f"Epoch {epoch}/{num_epochs}",
            unit="batch",
        )

        for batch_idx, batch in enumerate(pbar, 1):
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            intent_labels = batch["intent_label"].long().to(device)
            slot_labels = batch["slot_labels"].long().to(device)

            intent_logits, slot_logits = model(input_ids, attention_mask)
            intent_loss = intent_loss_fn(intent_logits, intent_labels)
            slot_loss = slot_loss_fn(slot_logits.view(-1, slot_logits.shape[-1]), slot_labels.view(-1))
            loss = intent_loss + 2.0 * slot_loss

            loss.backward()
            optimizer.step()

            batch_loss = loss.item()
            epoch_loss += batch_loss
            epoch_intent_loss += intent_loss.item()
            epoch_slot_loss += slot_loss.item()

            pbar.set_postfix({
                "loss": f"{batch_loss:.4f}",
                "intent_l": f"{intent_loss.item():.4f}",
                "slot_l": f"{slot_loss.item():.4f}",
                "avg": f"{epoch_loss / batch_idx:.4f}",
            })

        epoch_time = time.time() - epoch_start
        throughput = total_batches / epoch_time if epoch_time > 0 else 0
        logger.info(
            f"Epoch {epoch}/{num_epochs} Complete | "
            f"Avg Loss: {epoch_loss/total_batches:.4f} "
            f"(Intent: {epoch_intent_loss/total_batches:.4f}, Slot: {epoch_slot_loss/total_batches:.4f}) | "
            f"Duration: {epoch_time:.1f}s ({throughput:.2f} batch/s)"
        )

    return model


def merge_slot_types(labels, label_encoder):
    """Merges BIO integer labels into unified slot types (e.g., 'B-ingredient' -> 'ingredient')."""
    merged_labels = []
    for label in labels:
        tag = label_encoder.inverse_transform([label])[0]
        if tag == "O":
            merged_labels.append("O")
        else:
            merged_labels.append(tag.split("-")[-1])
    return merged_labels


def evaluate_with_progress(
    model, test_data, intent_classes, slot_classes, slot_label_encoder, device="cpu", onnx_session=None
):
    """
    Evaluates PyTorch or ONNX/INT8 model performance with a progress bar and classification reports.
    """
    from sklearn.metrics import accuracy_score, classification_report, f1_score

    if model is not None:
        model.to(device)
        model.eval()

    all_intent_preds, all_intent_labels = [], []
    all_slot_preds, all_slot_labels = [], []

    pbar = get_progress_bar(test_data, desc="Evaluating", unit="sample")
    for example in pbar:
        if onnx_session is not None:
            input_ids = example["input_ids"].unsqueeze(0).cpu().numpy().astype(np.int64)
            attention_mask = example["attention_mask"].unsqueeze(0).cpu().numpy().astype(np.int64)
            intent_logits, slot_logits = onnx_session.run(
                None, {"input_ids": input_ids, "attention_mask": attention_mask}
            )
            intent_pred = int(np.argmax(intent_logits, axis=1)[0])
            slot_preds = np.argmax(slot_logits[0], axis=1).tolist()
        else:
            with torch.no_grad():
                input_ids = example["input_ids"].unsqueeze(0).to(device)
                attention_mask = example["attention_mask"].unsqueeze(0).to(device)

                intent_logits, slot_logits = model(input_ids, attention_mask)
                intent_pred = torch.argmax(intent_logits, dim=1).item()
                slot_preds = torch.argmax(slot_logits, dim=2).squeeze().tolist()

        intent_label = example["intent_label"].item()
        all_intent_preds.append(intent_pred)
        all_intent_labels.append(intent_label)

        slot_labels = example["slot_labels"].tolist()
        for pred_id, true_id in zip(slot_preds, slot_labels):
            if true_id != -100:
                all_slot_preds.append(pred_id)
                all_slot_labels.append(true_id)

    unified_true = merge_slot_types(all_slot_labels, slot_label_encoder)
    unified_pred = merge_slot_types(all_slot_preds, slot_label_encoder)
    unique_slots = sorted(set(unified_true + unified_pred) - {"O"})

    intent_acc = accuracy_score(all_intent_labels, all_intent_preds)
    slot_f1 = f1_score(unified_true, unified_pred, labels=unique_slots, average="weighted", zero_division=0)
    intent_report = classification_report(
        all_intent_labels, all_intent_preds, target_names=intent_classes, zero_division=0
    )
    slot_report = classification_report(unified_true, unified_pred, labels=unique_slots, zero_division=0)

    return {
        "intent_accuracy": intent_acc,
        "slot_f1": slot_f1,
        "intent_classification_report": intent_report,
        "slot_classification_report": slot_report,
    }


def export_to_onnx(model, num_intents, num_slots, max_length, output_path, device="cpu"):
    """
    Exports trained BERTNLUModel to ONNX with dynamic batch and sequence axes.
    """
    logger.info(f"Compiling model to ONNX format at {output_path}...")
    model.eval()
    model.to(device)

    dummy_input_ids = torch.zeros((1, max_length), dtype=torch.long, device=device)
    dummy_mask = torch.ones((1, max_length), dtype=torch.long, device=device)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with torch.no_grad():
        torch.onnx.export(
            model,
            (dummy_input_ids, dummy_mask),
            str(output_path),
            input_names=["input_ids", "attention_mask"],
            output_names=["intent_logits", "slot_logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "seq_len"},
                "attention_mask": {0: "batch_size", 1: "seq_len"},
                "intent_logits": {0: "batch_size"},
                "slot_logits": {0: "batch_size", 1: "seq_len"},
            },
            opset_version=14,
        )
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"ONNX model successfully compiled to {output_path} ({file_size_mb:.1f} MB)")

    # Verification with onnxruntime
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(output_path), providers=["CPUExecutionProvider"])
        sample_ids = np.zeros((1, max_length), dtype=np.int64)
        sample_mask = np.ones((1, max_length), dtype=np.int64)
        outputs = session.run(None, {"input_ids": sample_ids, "attention_mask": sample_mask})
        logger.info(f"ONNX Runtime verification succeeded (outputs: {outputs[0].shape}, {outputs[1].shape})")
    except Exception as e:
        logger.warning(f"ONNX verification check skipped: {e}")


def quantize_onnx_model(onnx_path, int8_output_path):
    """
    MLOps: Dynamic INT8 quantization for BERT model.
    Compresses model footprint from 438 MB down to ~110 MB and speeds up CPU inference.
    """
    logger.info(f"Quantizing ONNX model to INT8: {int8_output_path}...")
    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
        quantize_dynamic(
            model_input=str(onnx_path),
            model_output=str(int8_output_path),
            weight_type=QuantType.QInt8,
        )
        size_mb = int8_output_path.stat().st_size / (1024 * 1024)
        logger.info(f"INT8 model successfully compiled: {int8_output_path} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        logger.warning(f"INT8 quantization skipped/failed: {e}")
        return False


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_git_commit_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            cwd=str(SCRIPT_DIR),
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return os.environ.get("GITHUB_SHA", "unknown")[:7] or "unknown"


def _relative_to_repo(path: Path) -> str:
    """Portable path relative to the social-interaction-cloud root (never an absolute local path)."""
    try:
        return path.resolve().relative_to(SIC_ROOT).as_posix()
    except ValueError:
        return path.name


def build_lineage_record(artifact_path, data_files) -> dict:
    """
    Immutable lineage for a run: git commit, dataset digest and (when present) model artifact digest.
    The dataset digest hashes every split/ontology file in sorted-name order.
    """
    existing = sorted((p for p in data_files if p.exists()), key=lambda p: p.name)
    dataset_hash = hashlib.sha256(
        "".join(compute_sha256(p) for p in existing).encode("utf-8")
    ).hexdigest()
    record = {
        "git_sha": get_git_commit_sha(),
        "dataset_sha256": dataset_hash,
        "dataset_files": [_relative_to_repo(p) for p in existing],
    }
    if artifact_path is not None and Path(artifact_path).exists():
        record["onnx_checkpoint"] = _relative_to_repo(Path(artifact_path))
        record["onnx_sha256"] = compute_sha256(Path(artifact_path))
    return record


def log_experiment_run(run_metadata, log_file=None):
    """
    MLOps: Records training/eval run metadata and hyperparameters to runs history.
    """
    import json
    if log_file is None:
        log_file = SCRIPT_DIR / "utils" / "checkpoints" / "experiments_history.json"
    
    history = []
    if log_file.exists():
        try:
            with open(log_file, "r") as f:
                history = json.load(f)
        except Exception:
            history = []
            
    history.append(run_metadata)
    try:
        with open(log_file, "w") as f:
            json.dump(history, f, indent=2)
        logger.info(f"Experiment logged to {log_file}")
    except Exception as e:
        logger.warning(f"Failed to record experiment run: {e}")


def main():
    parser = argparse.ArgumentParser(description="Train BERT NLU on GPU and export to ONNX / PyTorch checkpoint")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs (default: 5)")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate (default: 2e-5)")
    parser.add_argument("--max_length", type=int, default=64, help="Max sequence length (default: 64)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--eval_only", action="store_true", help="Skip training and run evaluation on the test dataset")
    parser.add_argument("--inference", type=str, default=None, help="Run single-utterance prediction and print intent & slots")
    parser.add_argument("--quantize_only", action="store_true", help="Quantize existing ONNX model to INT8 without retraining")
    parser.add_argument("--min_intent_acc", type=float, default=None, help="CI/CD Quality Gate: Minimum intent accuracy (0.0-1.0)")
    parser.add_argument("--min_slot_f1", type=float, default=None, help="CI/CD Quality Gate: Minimum slot F1 (0.0-1.0)")
    args = parser.parse_args()

    # Reproducibility
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using compute device: {device}")
    if device.type == "cuda":
        logger.info(f"GPU Model: {torch.cuda.get_device_name(0)}")
        logger.info(f"Available VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")

    data_dir = SCRIPT_DIR / "utils" / "data"
    checkpoints_dir = SCRIPT_DIR / "utils" / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    ontology_path = data_dir / "ontology.json"
    train_path = data_dir / "train.json"
    test_path = data_dir / "test.json"
    exclusion_train_path = data_dir / "exclusion_examples.json"
    exclusion_test_path = data_dir / "exclusion_examples_test.json"
    lineage_data_files = [
        ontology_path, train_path, test_path, exclusion_train_path, exclusion_test_path,
        data_dir / "synonyms.json", data_dir / "vocab.txt",
    ]
    # 1. Fit encoders
    logger.info("Fitting intent and slot encoders from ontology...")
    ontology = load_ontology(str(ontology_path))
    fit_encoders(str(ontology_path))

    intent_classes = intent_label_encoder.classes_
    slot_classes = slot_label_encoder.classes_
    num_intents = len(intent_classes)
    num_slots = len(slot_classes)
    logger.info(f"Classes: {num_intents} intents, {num_slots} slot tags")

    pt_output_path = checkpoints_dir / "model_checkpoint.pt"
    onnx_output_path = checkpoints_dir / "bert_nlu.onnx"
    onnx_int8_output_path = checkpoints_dir / "bert_nlu_int8.onnx"

    # Quantize-only utility mode
    if args.quantize_only:
        if not onnx_output_path.exists():
            logger.error(f"Cannot quantize: FP32 ONNX model not found at {onnx_output_path}")
            sys.exit(1)
        success = quantize_onnx_model(onnx_output_path, onnx_int8_output_path)
        if not success:
            sys.exit(1)
        return

    # Single utterance test mode
    if args.inference:
        logger.info(f"Running inference on: '{args.inference}'")
        from sic_framework.services.nlu.fast_bert_nlu import FastBERTNLU
        fast_engine = FastBERTNLU(checkpoints_dir=checkpoints_dir)
        if not fast_engine.is_loaded():
            logger.error("No checkpoint found in checkpoints directory. Please train a model first.")
            return
        intent, conf, slots, _ = fast_engine.predict(args.inference)
        print("\n" + "=" * 50)
        print(f"Utterance:  '{args.inference}'")
        print(f"Backend:    {fast_engine.backend}")
        print(f"Intent:     {intent} (Confidence: {conf:.4f})")
        print(f"Slots:      {slots}")
        print("=" * 50 + "\n")
        return

    # Load test dataset
    logger.info("Loading test dataset...")
    test_data = load_data(str(test_path))
    if exclusion_test_path.exists():
        test_data += load_data(str(exclusion_test_path))
    logger.info(f"Total testing examples: {len(test_data)}")
    processed_test = preprocess_data(test_data, max_length=args.max_length)
    test_dataset = NLURecipeDataset(processed_test, ontology, max_length=args.max_length)

    # Standalone Evaluation Mode (--eval_only)
    if args.eval_only:
        onnx_session = None
        eval_model = None
        eval_backend = None

        if onnx_int8_output_path.exists() or onnx_output_path.exists():
            import onnxruntime as ort
            target_onnx = onnx_int8_output_path if onnx_int8_output_path.exists() else onnx_output_path
            eval_backend = "onnx_int8" if target_onnx == onnx_int8_output_path else "onnx_fp32"
            logger.info(f"Loading ONNX checkpoint [{eval_backend}] from {target_onnx} for evaluation...")
            onnx_session = ort.InferenceSession(str(target_onnx), providers=["CPUExecutionProvider"])
        elif pt_output_path.exists():
            eval_backend = "pytorch"
            logger.info(f"Loading PyTorch weights from {pt_output_path} for evaluation...")
            eval_model = BERTNLUModel(num_intents=num_intents, num_slots=num_slots)
            eval_model.load_state_dict(torch.load(str(pt_output_path), map_location=device, weights_only=True))
        else:
            logger.error(
                f"Cannot evaluate: no checkpoint found in {checkpoints_dir} "
                f"(expected bert_nlu_int8.onnx, bert_nlu.onnx, or model_checkpoint.pt)"
            )
            sys.exit(1)

        logger.info("Evaluating model on test dataset...")
        eval_start = time.time()
        metrics = evaluate_with_progress(
            eval_model,
            test_dataset,
            intent_classes,
            slot_classes,
            slot_label_encoder,
            device=device,
            onnx_session=onnx_session,
        )
        eval_duration = time.time() - eval_start
        throughput = len(test_dataset) / eval_duration if eval_duration > 0 else 0

        print("\n" + "=" * 65)
        print("NLU MODEL EVALUATION REPORT")
        print(f"Backend:               {eval_backend}")
        print(f"Test Examples:         {len(test_dataset)}")
        print(f"Overall Intent Acc:    {metrics['intent_accuracy'] * 100:.2f}%")
        print(f"Weighted Slot F1:      {metrics['slot_f1'] * 100:.2f}%")
        print(f"Inference Throughput:  {throughput:.1f} samples/sec ({1000/throughput:.2f} ms/sample)")
        print("=" * 65)
        print("\nIntent Classification Report:")
        print(metrics["intent_classification_report"])
        print("Slot Classification Report (Aggregated):")
        print(metrics["slot_classification_report"])
        print("=" * 65 + "\n")

        # MLOps: Experiment tracking (with immutable lineage: git sha + dataset/artifact digests)
        log_experiment_run({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": "evaluation",
            "backend": eval_backend,
            "test_samples": len(test_dataset),
            "intent_accuracy": round(metrics["intent_accuracy"], 4),
            "slot_f1": round(metrics["slot_f1"], 4),
            "throughput_samples_sec": round(throughput, 1),
            **build_lineage_record(target_onnx if onnx_session is not None else pt_output_path, lineage_data_files),
        })

        # MLOps: CI/CD Quality Gate Enforcement
        if args.min_intent_acc is not None:
            if metrics["intent_accuracy"] < args.min_intent_acc:
                logger.error(
                    f"QUALITY GATE FAILED: Intent accuracy {metrics['intent_accuracy']*100:.2f}% "
                    f"< required {args.min_intent_acc*100:.2f}%"
                )
                sys.exit(1)
            else:
                logger.info(
                    f"QUALITY GATE PASSED: Intent accuracy {metrics['intent_accuracy']*100:.2f}% "
                    f">= {args.min_intent_acc*100:.2f}%"
                )

        if args.min_slot_f1 is not None:
            if metrics["slot_f1"] < args.min_slot_f1:
                logger.error(
                    f"QUALITY GATE FAILED: Slot F1 {metrics['slot_f1']*100:.2f}% "
                    f"< required {args.min_slot_f1*100:.2f}%"
                )
                sys.exit(1)
            else:
                logger.info(
                    f"QUALITY GATE PASSED: Slot F1 {metrics['slot_f1']*100:.2f}% "
                    f">= {args.min_slot_f1*100:.2f}%"
                )

        return

    model = BERTNLUModel(num_intents=num_intents, num_slots=num_slots)

    # Full Training Pipeline
    logger.info("Loading training dataset...")
    train_data = load_data(str(train_path))
    if exclusion_train_path.exists():
        train_data += load_data(str(exclusion_train_path))
    logger.info(f"Total training examples: {len(train_data)}")

    logger.info("Preprocessing training sequences...")
    processed_train = preprocess_data(train_data, max_length=args.max_length)
    train_dataset = NLURecipeDataset(processed_train, ontology, max_length=args.max_length)

    logger.info(f"Initializing BERTNLUModel and training for {args.epochs} epochs...")
    start_time = time.time()
    model = train_model_with_progress(
        model=model,
        dataset=train_dataset,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        device=device,
    )
    elapsed = time.time() - start_time
    logger.info(f"Total training time: {elapsed:.1f} seconds ({elapsed/60:.2f} mins).")

    # Evaluate after training
    logger.info("Evaluating trained model on test dataset...")
    metrics = evaluate_with_progress(
        model, test_dataset, intent_classes, slot_classes, slot_label_encoder, device=device
    )
    print("\n" + "=" * 65)
    print(f"Test Intent Accuracy: {metrics['intent_accuracy'] * 100:.2f}%")
    print(f"Weighted Slot F1:     {metrics['slot_f1'] * 100:.2f}%\n")
    print("Intent Classification Report:")
    print(metrics["intent_classification_report"])
    print("Slot Classification Report (Aggregated):")
    print(metrics["slot_classification_report"])
    print("=" * 65 + "\n")

    # Save PyTorch weights
    torch.save(model.state_dict(), str(pt_output_path))
    logger.info(f"PyTorch checkpoint saved to: {pt_output_path}")

    # Compile to ONNX (FP32)
    export_to_onnx(model, num_intents, num_slots, args.max_length, onnx_output_path, device="cpu")

    # MLOps: Dynamic INT8 Quantization
    quantize_onnx_model(onnx_output_path, onnx_int8_output_path)

    # MLOps: Record experiment run metadata
    log_experiment_run({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "training",
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "intent_accuracy": round(metrics["intent_accuracy"], 4),
        "slot_f1": round(metrics["slot_f1"], 4),
        "training_time_sec": round(elapsed, 1),
        "model_files": {
            "pytorch": _relative_to_repo(pt_output_path),
            "onnx_fp32": _relative_to_repo(onnx_output_path),
            "onnx_int8": _relative_to_repo(onnx_int8_output_path),
        },
        **build_lineage_record(onnx_int8_output_path, lineage_data_files),
    })

    print("\n" + "=" * 65)
    print("TRAINING, EVALUATION, ONNX & INT8 QUANTIZATION COMPLETE!")
    print(f"1. PyTorch weights:    {pt_output_path}")
    print(f"2. Compiled ONNX:      {onnx_output_path}")
    print(f"3. Quantized INT8 ONNX:{onnx_int8_output_path}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
