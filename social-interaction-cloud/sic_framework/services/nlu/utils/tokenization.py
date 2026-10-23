"""
tokenization.py

Single WordPiece tokenizer shared by training (dataset.py), holdout evaluation
(train_and_export.py) and ONNX serving (fast_bert_nlu.py), so subword splits and BIO
alignments are identical everywhere (no train/serve skew).

Only depends on the lightweight Rust `tokenizers` package (no torch / transformers),
so it is safe to import inside the production container.
"""

from pathlib import Path

from tokenizers import BertWordPieceTokenizer

DEFAULT_VOCAB_PATH = Path(__file__).resolve().parent / "data" / "vocab.txt"
PAD_ID = 0


class UnifiedWordPieceTokenizer:
    """bert-base-uncased compatible WordPiece tokenizer loaded from the bundled vocab.txt."""

    def __init__(self, vocab_path=DEFAULT_VOCAB_PATH, max_length: int = 64):
        self.max_length = max_length
        self.backend = BertWordPieceTokenizer(str(vocab_path), lowercase=True)

    def tokenize(self, text: str) -> list:
        """Subword tokens without special tokens (used for BIO label alignment)."""
        encoded = self.backend.encode(text, add_special_tokens=False)
        return list(encoded.tokens)

    def encode_for_model(self, text: str, max_len: int = None):
        """
        Returns (input_ids, attention_mask, tokens), all right-padded / truncated to `max_len`.
        `tokens` includes [CLS]/[SEP] and [PAD] so it aligns index-for-index with model outputs.
        """
        max_len = max_len or self.max_length
        # Truncate so that [SEP] is never cut off.
        self.backend.enable_truncation(max_length=max_len)
        encoded = self.backend.encode(text, add_special_tokens=True)
        ids = list(encoded.ids)[:max_len]
        mask = list(encoded.attention_mask)[:max_len]
        tokens = list(encoded.tokens)[:max_len]
        pad_len = max_len - len(ids)
        if pad_len > 0:
            ids += [PAD_ID] * pad_len
            mask += [0] * pad_len
            tokens += ["[PAD]"] * pad_len
        return ids, mask, tokens
