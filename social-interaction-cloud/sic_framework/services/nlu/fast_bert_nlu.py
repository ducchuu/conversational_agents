import json
import logging
import os
import re
import time
from importlib.resources import files
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHED_SYNONYMS = None
_CACHED_ONTOLOGY = None


def load_synonyms():
    """Load the ontology synonyms mapping from synonyms.json with in-memory caching."""
    global _CACHED_SYNONYMS
    if _CACHED_SYNONYMS is not None:
        return _CACHED_SYNONYMS
    try:
        synonyms_path = str(files("sic_framework.services.nlu.utils.data").joinpath("synonyms.json"))
        with open(synonyms_path, "r", encoding="utf-8") as f:
            _CACHED_SYNONYMS = json.load(f)
    except Exception:
        fallback = os.path.join(os.path.dirname(__file__), "utils", "data", "synonyms.json")
        with open(fallback, "r", encoding="utf-8") as f:
            _CACHED_SYNONYMS = json.load(f)
    return _CACHED_SYNONYMS


def load_ontology():
    """Load the master ontology database from ontology.json with in-memory caching."""
    global _CACHED_ONTOLOGY
    if _CACHED_ONTOLOGY is not None:
        return _CACHED_ONTOLOGY
    try:
        ontology_path = str(files("sic_framework.services.nlu.utils.data").joinpath("ontology.json"))
        with open(ontology_path, "r", encoding="utf-8") as f:
            _CACHED_ONTOLOGY = json.load(f)
    except Exception:
        fallback = os.path.join(os.path.dirname(__file__), "utils", "data", "ontology.json")
        with open(fallback, "r", encoding="utf-8") as f:
            _CACHED_ONTOLOGY = json.load(f)
    return _CACHED_ONTOLOGY


def get_canonical_value(synonyms_dict, slot_type, slot_value):
    """
    Get the canonical value from synonyms.json and ontology.json based on slot type.
    Handles:
    - Stripping punctuation and whitespace (e.g. 'Japan.' -> 'japanese')
    - Mapping exclusion slots (e.g. 'excludeCuisine' -> 'cuisine')
    - Plural ingredient normalization (e.g. 'onions' -> 'onion')
    - Duration number extraction (e.g. 'under 30 minutes' -> '30')
    """
    if not slot_value:
        return slot_value

    clean_val = str(slot_value).strip().strip(" .,!?;:'\"-()")
    if not clean_val:
        return clean_val

    slot_lower = slot_type.lower()
    if "cuisine" in slot_lower:
        base_type = "cuisine"
    elif "dietary" in slot_lower or "diet" in slot_lower:
        base_type = "dietaryRestriction"
    elif "ingredient" in slot_lower:
        base_type = "ingredient"
    elif "meal" in slot_lower:
        base_type = "mealType"
    elif "duration" in slot_lower or "time" in slot_lower:
        base_type = "duration"
    elif "tag" in slot_lower:
        base_type = "tag"
    elif "filter" in slot_lower:
        base_type = "filterType"
    else:
        base_type = slot_type

    if base_type == "duration":
        match = re.search(r"\d+", clean_val)
        if match:
            return match.group(0)
        return clean_val

    clean_lower = clean_val.lower()

    if synonyms_dict and base_type in synonyms_dict:
        slot_dict = synonyms_dict[base_type]

        for key in slot_dict.keys():
            if clean_lower == key.lower():
                return key

        for key, syn_list in slot_dict.items():
            cleaned_syns = [s.strip(" .,!?;:'\"-()").lower() for s in syn_list]
            if clean_lower in cleaned_syns:
                return key

        for key, syn_list in slot_dict.items():
            for s in syn_list:
                s_clean = s.strip(" .,!?;:'\"-()").lower()
                if s_clean and (s_clean == clean_lower or f" {s_clean} " in f" {clean_lower} "):
                    return key

    try:
        ontology = load_ontology()
        slots_onto = ontology.get("slots", {})
        if base_type in slots_onto:
            known_values = slots_onto[base_type]

            if base_type in ("ingredient", "tag"):
                if clean_lower.endswith("ies") and (clean_lower[:-3] + "y") in known_values:
                    return clean_lower[:-3] + "y"
                elif clean_lower.endswith("es") and clean_lower[:-2] in known_values:
                    return clean_lower[:-2]
                elif clean_lower.endswith("s") and clean_lower[:-1] in known_values:
                    return clean_lower[:-1]

            for kv in known_values:
                if clean_lower == kv.lower():
                    return kv
    except Exception:
        pass

    return clean_lower


def normalize_slots(slots):
    """Normalize all slot values in the dictionary using the ontology and synonyms mapping."""
    synonyms_dict = load_synonyms()
    normalized_slots = {}

    for slot_type, slot_value in slots.items():
        if isinstance(slot_value, list):
            normalized_slots[slot_type] = [
                get_canonical_value(synonyms_dict, slot_type, v) for v in slot_value
            ]
        else:
            normalized_slots[slot_type] = get_canonical_value(synonyms_dict, slot_type, slot_value)

    return normalized_slots


def correct_exclusion_polarity(text: str, slots: dict) -> dict:
    """
    Inference Guard: Remap erroneously extracted positive slots (cuisine, ingredient, tag)
    to their exclusion counterparts (excludeCuisine, excludeIngredient, excludeTag) when the
    utterance context explicitly negates or excludes that entity (e.g. 'exclude ...', 'no ...',
    'without ...', 'don't want any ...', 'skip ...', 'omit ...').
    """
    if not slots:
        return slots

    text_lower = text.lower()
    mapping = {
        "cuisine": "excludeCuisine",
        "ingredient": "excludeIngredient",
        "ingredientType": "excludeIngredient",
        "tag": "excludeTag",
        "mealType": "excludeMealType",
    }

    neg_patterns = [
        r"\b(?:exclude|without|no|omit|skip|avoid|except\s+for|except)\s+(?:any\s+)?(?:the\s+)?(?:all\s+)?",
        r"\b(?:don\'t|dont|do\s+not)\s+want\s+(?:any\s+)?(?:the\s+)?",
    ]

    is_overall_exclusion = bool(
        re.match(r"^(?:please\s+)?(?:exclude|without|no|omit|skip|avoid)\b", text_lower)
    )

    updated = dict(slots)
    for pos_key, neg_key in mapping.items():
        if pos_key in updated:
            vals = updated[pos_key]
            val_list = vals if isinstance(vals, list) else [vals]
            remaining_pos = []

            for v in val_list:
                v_str = str(v).lower()
                is_negated = False
                for p in neg_patterns:
                    pattern = p + r"[^,.]*?\b" + re.escape(v_str) + r"\b"
                    if re.search(pattern, text_lower):
                        is_negated = True
                        break

                if not is_negated and is_overall_exclusion:
                    is_negated = True

                if is_negated:
                    if neg_key in updated:
                        curr = (
                            updated[neg_key]
                            if isinstance(updated[neg_key], list)
                            else [updated[neg_key]]
                        )
                        if v not in curr:
                            curr.append(v)
                        updated[neg_key] = curr
                    else:
                        updated[neg_key] = v
                else:
                    remaining_pos.append(v)

            if remaining_pos:
                updated[pos_key] = (
                    remaining_pos if isinstance(vals, list) else remaining_pos[0]
                )
            else:
                del updated[pos_key]

    return updated


def extract_slots_from_text(slots_array, inference_text, subword_tokens=None):
    """
    Extracts slot values from the predicted BIO slots array and input text.
    When subword_tokens (WordPiece tokens matching slots_array indices) are provided,
    merges '##' subword continuations accurately so multi-subword words never shift alignment.
    Falls back to whitespace word alignment when subword_tokens is None.
    """
    slots_dict = {}
    current_slot_type = None
    current_slot_value = []

    def add_slot(s_type, s_value_list):
        clean_words = [w.strip(" .,!?;:'\"-()") for w in s_value_list]
        clean_words = [w for w in clean_words if w]
        if not clean_words:
            return
        value_str = " ".join(clean_words)
        if s_type in slots_dict:
            if isinstance(slots_dict[s_type], list):
                if value_str not in slots_dict[s_type]:
                    slots_dict[s_type].append(value_str)
            elif slots_dict[s_type] != value_str:
                slots_dict[s_type] = [slots_dict[s_type], value_str]
        else:
            slots_dict[s_type] = value_str

    if subword_tokens is not None:
        for tok, slot_tag in zip(subword_tokens, slots_array):
            if tok in ("[CLS]", "[SEP]", "[PAD]", "[UNK]"):
                if current_slot_type and current_slot_value:
                    add_slot(current_slot_type, current_slot_value)
                    current_slot_type = None
                    current_slot_value = []
                continue

            is_subword = tok.startswith("##")
            piece = tok[2:] if is_subword else tok

            if is_subword and current_slot_type and current_slot_value:
                current_slot_value[-1] += piece
                continue

            clean_w = piece.strip(" .,!?;:'\"-()")
            if not clean_w:
                if current_slot_type and current_slot_value:
                    add_slot(current_slot_type, current_slot_value)
                    current_slot_type = None
                    current_slot_value = []
                continue

            if slot_tag == "O":
                if current_slot_type and current_slot_value:
                    add_slot(current_slot_type, current_slot_value)
                    current_slot_type = None
                    current_slot_value = []
            elif slot_tag.startswith("B-"):
                if current_slot_type and current_slot_value:
                    add_slot(current_slot_type, current_slot_value)
                current_slot_type = slot_tag[2:]
                current_slot_value = [clean_w]
            elif slot_tag.startswith("I-"):
                tag_type = slot_tag[2:]
                if current_slot_type == tag_type:
                    current_slot_value.append(clean_w)
                else:
                    if current_slot_type and current_slot_value:
                        add_slot(current_slot_type, current_slot_value)
                    current_slot_type = tag_type
                    current_slot_value = [clean_w]

        if current_slot_type and current_slot_value:
            add_slot(current_slot_type, current_slot_value)
        return slots_dict

    words = inference_text.split()
    for word, slot_tag in zip(words, slots_array):
        clean_w = word.strip(" .,!?;:'\"-()")
        if not clean_w:
            clean_w = word

        if slot_tag == "O":
            if current_slot_type and current_slot_value:
                add_slot(current_slot_type, current_slot_value)
                current_slot_type = None
                current_slot_value = []
        elif slot_tag.startswith("B-"):
            if current_slot_type and current_slot_value:
                add_slot(current_slot_type, current_slot_value)
            current_slot_type = slot_tag[2:]
            current_slot_value = [clean_w]
        elif slot_tag.startswith("I-") and current_slot_type == slot_tag[2:]:
            current_slot_value.append(clean_w)

    if current_slot_type and current_slot_value:
        add_slot(current_slot_type, current_slot_value)

    return slots_dict


class SimpleLabelEncoder:
    """Lightweight, standalone LabelEncoder without scikit-learn dependency."""

    def __init__(self):
        self.classes_ = []

    def fit(self, y):
        self.classes_ = sorted(list(set(y)))
        return self

    def inverse_transform(self, indices):
        return [self.classes_[i] for i in indices]

    def transform(self, labels):
        lookup = {label: i for i, label in enumerate(self.classes_)}
        return [lookup[label] for label in labels]


class FastBERTNLU:
    """
    High-performance, low-latency NLU inference engine for BERT Intent & Slot tagging.
    Supports two backends:
    1. ONNX Runtime (fastest: ~6-8 ms on CPU with INT8 dynamic quantization)
    2. Pre-warmed PyTorch (fast: ~20-25 ms on CPU with model.eval())

    If no checkpoint exists yet, is_loaded() returns False and allows graceful fallback.
    """

    def __init__(self, checkpoints_dir=None, max_length=64):
        self.max_length = max_length
        self.backend = None
        self.session = None
        self.model = None
        self.tokenizer = None
        self.tokenizer_type = None
        self.intent_label_encoder = None
        self.slot_label_encoder = None
        self.ontology = None

        if checkpoints_dir is None:
            base_dir = Path(__file__).resolve().parent
            checkpoints_dir = base_dir / "utils" / "checkpoints"
            data_dir = base_dir / "utils" / "data"
        else:
            checkpoints_dir = Path(checkpoints_dir)
            data_dir = checkpoints_dir.parent / "data"

        self.checkpoints_dir = checkpoints_dir
        self.data_dir = data_dir
        self.onnx_int8_path = checkpoints_dir / "bert_nlu_int8.onnx"
        self.onnx_path = checkpoints_dir / "bert_nlu.onnx"
        self.pt_path = checkpoints_dir / "model_checkpoint.pt"
        self.ontology_path = data_dir / "ontology.json"

        self._init_encoders()
        self._load_engine()

    def _init_encoders(self):
        try:
            if not self.ontology_path.exists():
                return

            with open(self.ontology_path, "r", encoding="utf-8") as f:
                self.ontology = json.load(f)

            self.intent_label_encoder = SimpleLabelEncoder()
            self.slot_label_encoder = SimpleLabelEncoder()

            intents = self.ontology.get("intents", [])
            slots = self.ontology.get("slots", {})

            self.intent_label_encoder.fit(intents)
            all_slot_tags = (
                ["O"]
                + [f"B-{s}" for s in slots.keys()]
                + [f"I-{s}" for s in slots.keys()]
            )
            self.slot_label_encoder.fit(all_slot_tags)

            vocab_path = self.data_dir / "vocab.txt"
            if vocab_path.exists():
                try:
                    # Same tokenizer class as training/eval (dataset.py) -> no train/serve skew.
                    from sic_framework.services.nlu.utils.tokenization import UnifiedWordPieceTokenizer

                    self.tokenizer = UnifiedWordPieceTokenizer(vocab_path, max_length=self.max_length)
                    self.tokenizer_type = "unified_wordpiece"
                    logger.info(f"Loaded UnifiedWordPieceTokenizer from local {vocab_path}")
                except Exception as e:
                    logger.warning(f"Could not initialize UnifiedWordPieceTokenizer: {e}")

        except Exception as e:
            logger.warning(f"Failed to initialize NLU encoders: {e}")

    def _load_engine(self):
        target_onnx = None
        target_backend = None
        if self.onnx_path.exists():
            target_onnx = self.onnx_path
            target_backend = "onnx"
        elif self.onnx_int8_path.exists():
            target_onnx = self.onnx_int8_path
            target_backend = "onnx_int8"

        if target_onnx:
            try:
                import onnxruntime as ort

                sess_options = ort.SessionOptions()
                sess_options.intra_op_num_threads = 2
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                self.session = ort.InferenceSession(
                    str(target_onnx), sess_options, providers=["CPUExecutionProvider"]
                )
                self.backend = target_backend
                logger.info(f"Loaded FastBERTNLU [{self.backend}] from {target_onnx}")
                return
            except Exception as e:
                logger.warning(
                    f"Found ONNX model at {target_onnx} but failed to initialize onnxruntime: {e}"
                )

        if self.pt_path.exists() and self.intent_label_encoder is not None:
            try:
                import torch
                from sic_framework.services.nlu.utils.dataset import BERTNLUModel

                num_intents = len(self.intent_label_encoder.classes_)
                num_slots = len(self.slot_label_encoder.classes_)
                self.model = BERTNLUModel(num_intents=num_intents, num_slots=num_slots)
                self.model.load_state_dict(
                    torch.load(str(self.pt_path), map_location="cpu", weights_only=True)
                )
                self.model.eval()
                torch.set_grad_enabled(False)
                self.backend = "pytorch"
                logger.info(f"Loaded FastBERTNLU using pre-warmed PyTorch from {self.pt_path}")
                return
            except Exception as e:
                logger.warning(f"Found PyTorch checkpoint but failed to load: {e}")

        logger.info("No BERT NLU checkpoint found yet (onnx_int8, onnx, or pt). FastBERTNLU is in standby.")

    def is_loaded(self):
        return self.backend is not None and self.tokenizer is not None

    def predict(self, text):
        """
        Runs inference on input text.
        Returns: (intent, confidence, slot_dict, slot_confidences)
        """
        if not self.is_loaded():
            return None, 0.0, {}, []

        start_t = time.time()
        import numpy as np

        ids, mask, subword_tokens = self.tokenizer.encode_for_model(text, self.max_length)
        input_ids = np.array([ids], dtype=np.int64)
        attention_mask = np.array([mask], dtype=np.int64)

        if self.backend in ("onnx", "onnx_int8"):
            ort_inputs = {"input_ids": input_ids, "attention_mask": attention_mask}
            intent_logits, slot_logits = self.session.run(None, ort_inputs)

            exp_intent = np.exp(intent_logits - np.max(intent_logits, axis=1, keepdims=True))
            intent_probs = (exp_intent / np.sum(exp_intent, axis=1, keepdims=True))[0]
            intent_pred = int(np.argmax(intent_probs))
            intent = self.intent_label_encoder.inverse_transform([intent_pred])[0]
            intent_confidence = float(intent_probs[intent_pred])

            exp_slot = np.exp(slot_logits - np.max(slot_logits, axis=-1, keepdims=True))
            slot_probs = exp_slot / np.sum(exp_slot, axis=-1, keepdims=True)
            slot_preds = np.argmax(slot_probs[0], axis=1).tolist()
            slot_confidences = [float(slot_probs[0, i, pred]) for i, pred in enumerate(slot_preds)]
            slots = self.slot_label_encoder.inverse_transform(slot_preds)

        else:
            import torch

            with torch.no_grad():
                input_ids = torch.from_numpy(input_ids)
                attention_mask = torch.from_numpy(attention_mask)
                intent_logits, slot_logits = self.model(input_ids, attention_mask)

                intent_probs = torch.softmax(intent_logits, dim=1).squeeze(0)
                intent_pred = torch.argmax(intent_probs).item()
                intent = self.intent_label_encoder.inverse_transform([intent_pred])[0]
                intent_confidence = float(intent_probs[intent_pred].item())

                slot_probs = torch.softmax(slot_logits, dim=2).squeeze(0)
                slot_preds = torch.argmax(slot_probs, dim=1).tolist()
                slot_confidences = [float(slot_probs[i, p].item()) for i, p in enumerate(slot_preds)]
                slots = self.slot_label_encoder.inverse_transform(slot_preds)

        slot_dict = extract_slots_from_text(slots, text, subword_tokens=subword_tokens)
        normalized_slots = normalize_slots(slot_dict)
        normalized_slots = correct_exclusion_polarity(text, normalized_slots)

        # Quantitative slot extraction (servings, nrOfIngredients, nrOfSteps)
        # These constraints exist in the dialogue manager and Prolog engine but
        # are not part of the token classification vocabulary.
        if "servings" not in normalized_slots:
            m = re.search(
                r"\b(?:for\s+)?(\d+)\s+servings?\b|\bservings?\s*(?:of|for)?\s*(\d+)\b|\bfor\s+(\d+)\s+(?:people|persons?|guests?)\b|\bserves?\s+(\d+)\b",
                text,
                re.I,
            )
            if m:
                val = next(g for g in m.groups() if g is not None)
                normalized_slots["servings"] = val

        if "nrOfIngredients" not in normalized_slots:
            m = re.search(
                r"\b(?:under|less than|fewer than|at most|max|maximum)\s+(\d+)\s+ingredients?\b",
                text,
                re.I,
            )
            if m:
                normalized_slots["nrOfIngredients"] = m.group(1)

        if "nrOfSteps" not in normalized_slots:
            m = re.search(
                r"\b(?:under|less than|fewer than|at most|max|maximum)\s+(\d+)\s+steps?\b",
                text,
                re.I,
            )
            if m:
                normalized_slots["nrOfSteps"] = m.group(1)

        if intent in ("addFilter", "checkCapability") and re.match(
            r"^(can\s+i\s+make\s+(this|it)\b|is\s+(it|this)\s+\w+|how\s+(spicy|long)\b|what\s+side\s+dish\b|what\s+ingredients\b)",
            text.strip(),
            re.I,
        ):
            intent = "cookingQuestion"
            normalized_slots = {"userQuery": text.strip()}

        # Domain contract: addFilter strictly requires at least one extracted filter slot.
        # An addFilter prediction without slots is semantically invalid; ungrounded requests
        # to cook/find dishes without criteria represent recipe recommendation requests.
        elif intent == "addFilter" and not normalized_slots:
            intent = "requestRecommendation"
            intent_confidence = max(intent_confidence, 0.75)

        latency_ms = (time.time() - start_t) * 1000
        logger.debug(
            f"BERT NLU [{self.backend}] took {latency_ms:.1f}ms: intent={intent} ({intent_confidence:.2f})"
        )
        return intent, intent_confidence, normalized_slots, slot_confidences
