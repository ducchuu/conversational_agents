import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dialog_mngr.agent_python.dialog_manager import DialogManager
from sic_framework.services.nlu.fast_bert_nlu import FastBERTNLU, extract_slots_from_text
from sic_framework.services.webserver.webserver_pca import NLUOutput, normalize_intent_name


def test_fast_bert_nlu_initialization():
    """Verify FastBERTNLU initializes and loads its ONNX/PyTorch backend."""
    engine = FastBERTNLU()
    assert engine.intent_label_encoder is not None
    assert "cookingQuestion" in engine.intent_label_encoder.classes_
    assert "helpRequest" in engine.intent_label_encoder.classes_
    assert "outOfScope" in engine.intent_label_encoder.classes_


def test_nlu_output_normalization():
    """Verify NLUOutput normalizes legacy snake_case intents to canonical camelCase."""
    out1 = NLUOutput.model_validate({"intent": "cooking_question", "confidence": 0.95, "slots": {}})
    out2 = NLUOutput.model_validate({"intent": "help_request", "confidence": 0.95, "slots": {}})
    out3 = NLUOutput.model_validate({"intent": "out_of_scope", "confidence": 0.95, "slots": {}})
    assert out1.intent == "cookingQuestion"
    assert out2.intent == "helpRequest"
    assert out3.intent == "outOfScope"
    assert normalize_intent_name("request_recipe") == "recipeRequest"


def test_subword_slot_extraction_alignment():
    """Verify extract_slots_from_text aligns WordPiece ## continuation tokens accurately."""
    subwords = ["i", "want", "casser", "##oles", "with", "broccoli"]
    tags = ["O", "O", "B-recipe", "I-recipe", "O", "B-ingredient"]
    slots = extract_slots_from_text(tags, "I want casseroles with broccoli", subword_tokens=subwords)
    assert slots.get("recipe") == "casseroles"
    assert slots.get("ingredient") == "broccoli"


def test_dialog_manager_farewell_and_overview_fallbacks():
    """Verify DialogManager never returns empty action list that would lock the client microphone."""
    dm = DialogManager()
    dm.state.state = "recipe_overview"
    actions = dm._process_intent_sync("farewell", {})
    assert dm.state.state == "closing"
    assert any(a.get("type") == "generate_speech" for a in actions)

