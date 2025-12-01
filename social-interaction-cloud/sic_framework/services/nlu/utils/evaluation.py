"""
evaluation.py

This module provides evaluation and inference functionality for a trained Natural Language Understanding (NLU) intent_slot_classification_model designed for intent classification and slot filling tasks.

### Features:
1. **Model Evaluation**:
   - `evaluate`: Assesses intent_slot_classification_model performance on a test dataset, calculating accuracy and generating classification reports for both intents and slots.

2. **Inference**:
   - `predict`: Performs single-sentence inference, outputting the predicted intent and slots in a BIO (Begin-Inside-Outside) format.

### Dependencies:
- `tokenizer`: BERT tokenizer for processing input text.
- `intent_label_encoder`: Encoder to map intent predictions to human-readable labels.
- `slot_label_encoder`: Encoder to map slot predictions to human-readable BIO tags.

### Usage:
- Use `evaluate()` to assess intent_slot_classification_model performance on test run_data, including intent accuracy and detailed classification reports.
- Use `predict()` to infer the intent and slot tags for new user inputs.

### Note:
Ensure the intent_slot_classification_model and label encoders are properly trained and loaded before using these functions.
"""

import torch
from sklearn.metrics import accuracy_score, classification_report
from dataset import intent_label_encoder, slot_label_encoder, tokenizer


def merge_slot_types(labels, label_encoder):
    """
    Merges BIO tags into unified slot types.

    Args:
        labels (list of int): Encoded BIO labels (e.g., [0, 1, 2]).
        label_encoder (LabelEncoder): The label encoder used to encode BIO tags.

    Returns:
        list of str: Unified slot type labels (e.g., ["ingredient", "O"]).
    """
    merged_labels = []
    for label in labels:
        tag = label_encoder.inverse_transform([label])[0]
        if tag == "O":
            merged_labels.append("O")
        else:
            merged_labels.append(tag.split("-")[-1])  # Extract slot type (e.g., "ingredient")
    return merged_labels


def generate_slot_classification_report(true_labels, pred_labels, label_encoder):
    """
    Generates a slot-level classification report.

    Args:
        true_labels (list of list of int): True BIO labels for all sequences.
        pred_labels (list of list of int): Predicted BIO labels for all sequences.
        label_encoder (LabelEncoder): Label encoder used for BIO tags.

    Returns:
        str: Slot-level classification report.
    """
    # Flatten lists and merge slot types
    flat_true_labels = [label for seq in true_labels for label in seq]
    flat_pred_labels = [label for seq in pred_labels for label in seq]

    unified_true_labels = merge_slot_types(flat_true_labels, label_encoder)
    unified_pred_labels = merge_slot_types(flat_pred_labels, label_encoder)

    # Get unique slot types (excluding "O")
    unique_slot_types = sorted(set(unified_true_labels + unified_pred_labels) - {"O"})

    # Generate classification report
    return classification_report(unified_true_labels, unified_pred_labels, labels=unique_slot_types, zero_division=0)


def evaluate(model, test_data, intent_classes, slot_classes, slot_label_encoder, device="cpu"):
    """
    Evaluates the model on a test dataset, generating BIO and merged slot classification reports.

    Args:
        model (nn.Module): Trained NLU model.
        test_data (Dataset): Preprocessed test dataset.
        intent_classes (list): List of intent classes.
        slot_classes (list): List of BIO slot classes.
        slot_label_encoder (LabelEncoder): Label encoder for slots.
        device (str): Device to use for evaluation ("cpu" or "cuda").

    Returns:
        dict: Evaluation metrics.
    """
    model.to(device)
    model.eval()

    all_intent_preds, all_intent_labels = [], []
    all_slot_preds, all_slot_labels = [], []

    for example in test_data:
        with torch.no_grad():
            input_ids = example['input_ids'].unsqueeze(0).to(device)
            attention_mask = example['attention_mask'].unsqueeze(0).to(device)

            intent_logits, slot_logits = model(input_ids, attention_mask)
            intent_pred = torch.argmax(intent_logits, dim=1).item()
            intent_label = example['intent_label'].item()
            all_intent_preds.append(intent_pred)
            all_intent_labels.append(intent_label)

            slot_preds = torch.argmax(slot_logits, dim=2).squeeze().tolist()
            slot_labels = example['slot_labels'].tolist()
            valid_slot_labels = slot_labels[:len(slot_preds)]
            all_slot_preds.append(slot_preds)
            all_slot_labels.append(valid_slot_labels)

    # BIO Slot Classification Report
    flat_all_slot_labels = [label for seq in all_slot_labels for label in seq]
    flat_all_slot_preds = [label for seq in all_slot_preds for label in seq]

    bio_slot_class_report = classification_report(
        flat_all_slot_labels,
        flat_all_slot_preds,
        target_names=slot_classes,
        zero_division=0
    )

    # Merged Slot Type Classification Report
    merged_slot_class_report = generate_slot_classification_report(all_slot_labels, all_slot_preds, slot_label_encoder)

    # Intent Classification Report
    intent_class_report = classification_report(
        all_intent_labels,
        all_intent_preds,
        target_names=intent_classes
    )

    # Compute Metrics
    metrics = {
        "intent_accuracy": accuracy_score(all_intent_labels, all_intent_preds),
        "slot_f1": classification_report(flat_all_slot_labels, flat_all_slot_preds, output_dict=True)['weighted avg']['f1-score'],
        "slot_accuracy": accuracy_score(flat_all_slot_labels, flat_all_slot_preds),
    }

    # Print Reports
    print(f"Intent Classification Report:\n{intent_class_report}")
    print(f"BIO Slot Classification Report:\n{bio_slot_class_report}")
    print(f"Merged Slot Type Classification Report:\n{merged_slot_class_report}")

    return metrics
