"""
dataset.py

Core data preparation, ontology encoding, tokenization, and PyTorch model/dataset definitions
for the BERT Natural Language Understanding (NLU) intent classification and BIO slot-filling pipeline.
"""

import json
import sys
from pathlib import Path

# Ensure package root is in sys.path when executed directly or imported without pip -e
_SIC_ROOT = Path(__file__).resolve().parents[4]
if str(_SIC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SIC_ROOT))

try:
    from sklearn.preprocessing import LabelEncoder
except ImportError:
    class LabelEncoder:
        """Lightweight, standalone LabelEncoder fallback when scikit-learn is not installed."""

        def __init__(self):
            self.classes_ = []

        def fit(self, y):
            self.classes_ = sorted(list(set(y)))
            return self

        def inverse_transform(self, indices):
            return [self.classes_[int(i)] for i in indices]

        def transform(self, labels):
            lookup = {label: i for i, label in enumerate(self.classes_)}
            return [lookup[label] for label in labels]

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset
except ImportError:
    torch = None
    nn = None
    Dataset = object

try:
    from transformers import BertModel
except Exception:
    BertModel = None

from sic_framework.services.nlu.utils.tokenization import UnifiedWordPieceTokenizer

# Same WordPiece tokenizer (local vocab.txt) as FastBERTNLU serving -> zero train/serve skew.
tokenizer = UnifiedWordPieceTokenizer()

intent_label_encoder = LabelEncoder()
slot_label_encoder = LabelEncoder()


class BERTNLUModel(nn.Module if nn is not None else object):
    """
    Joint BERT model for intent classification ([CLS] pooled representation)
    and token-level BIO slot tagging (sequence output).
    """

    def __init__(self, num_intents: int, num_slots: int):
        super().__init__()
        self.bert = BertModel.from_pretrained("bert-base-uncased")
        hidden_size = self.bert.config.hidden_size
        self.intent_classifier = nn.Linear(hidden_size, num_intents)
        self.slot_classifier = nn.Linear(hidden_size, num_slots)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids, attention_mask)
        intent_logits = self.intent_classifier(outputs.pooler_output)
        slot_logits = self.slot_classifier(outputs.last_hidden_state)
        return intent_logits, slot_logits


def load_ontology(ontology_path: str) -> dict:
    """Loads the ontology JSON file containing intents and slot definitions."""
    with open(ontology_path, "r", encoding="utf-8") as file:
        return json.load(file)


def fit_encoders(ontology_path: str) -> None:
    """Fits intent and BIO-format slot label encoders from the ontology."""
    ontology = load_ontology(ontology_path)
    intents = ontology["intents"]
    slots = ontology["slots"]

    intent_label_encoder.fit(intents)
    all_slot_tags = (
        ["O"]
        + [f"B-{slot}" for slot in slots.keys()]
        + [f"I-{slot}" for slot in slots.keys()]
    )
    slot_label_encoder.fit(all_slot_tags)


def process_example(example: dict):
    """
    Tokenizes an example utterance and generates aligned BIO slot labels.

    Slot values may be a single string or a list of strings; every value is matched
    independently and all non-overlapping subword spans are labelled B-<slot>/I-<slot>.
    """
    tokens = tokenizer.tokenize(example["text"])
    slots = ["O"] * len(tokens)
    known_tags = set(slot_label_encoder.classes_)

    for slot_type, slot_value in example.get("slots", {}).items():
        if slot_value is None:
            continue
        b_tag, i_tag = f"B-{slot_type}", f"I-{slot_type}"
        if b_tag not in known_tags or i_tag not in known_tags:
            continue

        values = slot_value if isinstance(slot_value, (list, tuple)) else [slot_value]
        for value in values:
            value_str = str(value).strip()
            if not value_str:
                continue
            value_tokens = tokenizer.tokenize(value_str)
            span = len(value_tokens)
            if span == 0:
                continue
            for i in range(len(tokens) - span + 1):
                if tokens[i : i + span] == value_tokens and all(s == "O" for s in slots[i : i + span]):
                    slots[i] = b_tag
                    for j in range(1, span):
                        slots[i + j] = i_tag

    intent = intent_label_encoder.transform([example["intent"]])[0]
    slot_labels = slot_label_encoder.transform(slots)
    return tokens, intent, slot_labels


def load_data(file_path: str) -> list:
    """Loads annotated NLU examples from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


IGNORE_INDEX = -100


def preprocess_data(data: list, max_length: int = 64) -> list:
    """
    Tokenizes text, encodes intents and BIO slots aligned with [CLS] at index 0,
    and masks [CLS], [SEP], and [PAD] positions with IGNORE_INDEX (-100) so padding
    never dilutes token-level slot gradients.
    """
    processed_data = []

    for example in data:
        _, intent, slot_labels = process_example(example)
        ids, mask, _tokens = tokenizer.encode_for_model(example["text"], max_length)
        input_ids = torch.tensor(ids, dtype=torch.long)
        attention_mask = torch.tensor(mask, dtype=torch.long)

        valid_slots = list(slot_labels[: max_length - 2])
        padded_slot_labels = (
            [IGNORE_INDEX]
            + valid_slots
            + [IGNORE_INDEX] * (max_length - 1 - len(valid_slots))
        )

        processed_data.append(
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "intent_label": torch.tensor(intent),
                "slot_labels": torch.tensor(padded_slot_labels, dtype=torch.long),
            }
        )
    return processed_data


class NLURecipeDataset(Dataset):
    """PyTorch Dataset for joint intent classification and BIO slot filling."""

    def __init__(self, data: list, ontology: dict, max_length: int = 64):
        self.data = data
        self.intent_classes = ontology["intents"]
        self.slot_classes = (
            ["O"]
            + [f"B-{slot}" for slot in ontology["slots"].keys()]
            + [f"I-{slot}" for slot in ontology["slots"].keys()]
        )
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> dict:
        example = self.data[idx]
        return {
            "input_ids": example["input_ids"],
            "attention_mask": example["attention_mask"],
            "intent_label": example["intent_label"],
            "slot_labels": example["slot_labels"],
        }
