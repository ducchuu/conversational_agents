"""
test_golden_dialogues.py - LLMOps & NLU Automated Evaluation Benchmark

Contains a golden benchmark of 50 multi-turn test dialogues spanning all dialogue states:
- Positive filter additions (cuisine, ingredient, duration, mealType, servings)
- Negative exclusion filters (excludeIngredient, excludeCuisine, excludeDietaryRestriction)
- Off-script cooking and substitution queries
- Out-of-scope non-culinary questions
- Greetings, acknowledgments, confirmations, and farewells

Run via:
    pytest tests/evals/
"""

import pytest
import sys
from pathlib import Path

# Add project root to sys.path
TEST_DIR = Path(__file__).resolve().parent
ROOT_DIR = TEST_DIR.parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# 50 Golden Dialogues Benchmark
GOLDEN_DIALOGUE_CASES = [
    # 1-5: Greetings & Conversational Openers
    ("hello", "greeting"),
    ("hi there cooking assistant", "greeting"),
    ("hey how are you", "greeting"),
    ("good morning", "greeting"),
    ("hey broski", "greeting"),

    # 6-15: Standard Filter Additions
    ("I want something with chicken", "addFilter"),
    ("show me italian recipes", "addFilter"),
    ("under 30 minutes please", "addFilter"),
    ("I'm looking for a quick vegan dinner", "addFilter"),
    ("something with tomato and basil", "addFilter"),
    ("can I see mexican food", "addFilter"),
    ("make something for 4 servings", "addFilter"),
    ("I want a healthy breakfast", "addFilter"),
    ("any pasta dishes", "addFilter"),
    ("show me dessert recipes", "addFilter"),

    # 16-25: Complex Negative Exclusions
    ("no onions please", "addFilter"),
    ("without garlic", "addFilter"),
    ("not spicy", "addFilter"),
    ("no dairy products", "addFilter"),
    ("exclude mushrooms", "addFilter"),
    ("anything except pork", "addFilter"),
    ("no peanuts", "addFilter"),
    ("not italian", "addFilter"),
    ("something without butter", "addFilter"),
    ("no gluten", "addFilter"),

    # 26-30: Filter Management & Clearing
    ("remove the chicken filter", "deleteFilterValue"),
    ("clear all filters", "clearFilters"),
    ("start over with filters", "clearFilters"),
    ("delete the italian cuisine", "deleteFilterValue"),
    ("reset my filters", "clearFilters"),

    # 31-35: Explicit Recipe Requests
    ("what can I cook", "requestRecommendation"),
    ("recommend a recipe for me", "requestRecommendation"),
    ("give me a recipe", "requestRecommendation"),
    ("pick a dish for me", "requestRecommendation"),
    ("what do you recommend", "requestRecommendation"),

    # 36-40: Confirmations & Disconfirmations
    ("yes that sounds delicious", "confirmation"),
    ("sure let's cook that", "confirmation"),
    ("no show me something else", "disconfirmation"),
    ("nah I don't want that", "disconfirmation"),
    ("nope next one", "disconfirmation"),

    # 41-45: Off-script Cooking & Substitution Questions
    ("can I substitute butter with olive oil?", "cookingQuestion"),
    ("how long should I boil eggs?", "cookingQuestion"),
    ("what can I use instead of heavy cream?", "cookingQuestion"),
    ("how do I know when chicken is cooked?", "cookingQuestion"),
    ("what is a bain-marie?", "cookingQuestion"),

    # 46-48: Help & Out of Scope
    ("what can I say here?", "helpRequest"),
    ("how does this work?", "helpRequest"),
    ("who is the president of france?", "outOfScope"),

    # 49-50: Farewells & Restarts
    ("goodbye thank you", "farewell"),
    ("restart the conversation", "restart"),

    # 51-60: Website Interaction Guide — recipe_overview.html
    ("With garlic and pasta. Something vegeterian.", "addFilter"),
    ("Under 45 minutes", "addFilter"),
    ("Italian cuisine", "addFilter"),
    ("Without onions", "addFilter"),
    ("No dairy please", "addFilter"),
    ("Show me the mapo tofu", "recipeRequest"),
    ("Pick one for me", "requestRecommendation"),
    ("Recommend the best dish", "requestRecommendation"),
    ("What can I substitute for butter?", "cookingQuestion"),
    ("Can I make this vegetarian?", "cookingQuestion"),

    # 61-71: Website Interaction Guide — recipe_overview2.html
    ("I want the first recipe", "recipeRequest"),
    ("Select mapo tofu", "recipeRequest"),
    ("Pick the quickest one", "requestRecommendation"),
    ("Some dishes that you cook under 20 minutes", "addFilter"),
    ("I want something vegetarian", "addFilter"),
    ("Without dairy", "addFilter"),
    ("How spicy is this recipe?", "cookingQuestion"),
    ("What ingredients are in it?", "cookingQuestion"),
    ("Is it beginner-friendly?", "cookingQuestion"),
    ("Start over from scratch", "restart"),
    ("Help", "helpRequest"),

    # 72-82: Website Interaction Guide — recipe_confirmation.html
    ("Yes, let's cook this!", "confirmation"),
    ("Looks delicious, confirm recipe", "confirmation"),
    ("Sounds great, I'll make it", "confirmation"),
    ("No, show me another recipe", "disconfirmation"),
    ("I don't like this one", "disconfirmation"),
    ("Go back to the recipe list", "disconfirmation"),
    ("What can I use instead of ginger?", "cookingQuestion"),
    ("Can I bake this instead of frying?", "cookingQuestion"),
    ("How long do leftovers last?", "cookingQuestion"),
    ("What side dish pairs with this?", "cookingQuestion"),
    ("Goodbye", "farewell"),

    # 83-87: Website Interaction Guide — closing.html
    ("Start over from the beginning", "restart"),
    ("Find another recipe", "requestRecommendation"),
    ("I want to search again", "restart"),
    ("Goodbye CookingBroski!", "farewell"),
    ("Thank you, bye!", "farewell"),
]



# Mirror the confidence threshold used by the production turn pipeline (webserver_pca.py).
BERT_CONFIDENCE_THRESHOLD = 0.65

# Only genuinely interchangeable labels may substitute for each other. Conflicting intents
# must never mask a regression.
STRICT_EQUIVALENCES = {
    ("recipeRequest", "requestRecommendation"),
    ("requestRecommendation", "recipeRequest"),
    ("helpRequest", "checkCapability"),
    ("checkCapability", "helpRequest"),
}

# Semantic dual-intent utterances: asking for "another recipe" can act as rejecting the active
# dish (disconfirmation) or requesting a new suggestion (requestRecommendation). Both intents
# execute valid recipe-switch transitions in DialogManager.
DUAL_INTENT_UTTERANCES = {
    "Find another recipe": {"requestRecommendation", "disconfirmation"},
}


@pytest.fixture(scope="module")
def nlu_engine():
    """Loads the production FastBERTNLU engine; returns None when no checkpoint is available."""
    try:
        from sic_framework.services.nlu.fast_bert_nlu import FastBERTNLU

        engine = FastBERTNLU()
        if engine.is_loaded():
            return engine
    except Exception:
        pass
    return None


def predict_like_production(nlu_engine, utterance):
    """
    Same decision path as webserver_pca.handle_audio_stream: local BERT first, and the production
    `infer_fallback_intent` rules when BERT is unavailable, below threshold, or non-committal.
    """
    from sic_framework.services.webserver.llm_nlu_service import infer_fallback_intent, normalize_intent_name

    pred_intent = None
    if nlu_engine is not None:
        bert_intent, conf, _slots, _ = nlu_engine.predict(utterance)
        if conf >= BERT_CONFIDENCE_THRESHOLD and bert_intent not in (None, "unknown", "fallback"):
            pred_intent = bert_intent

    if pred_intent is None:
        pred_intent, _slots = infer_fallback_intent(utterance)

    return normalize_intent_name(pred_intent)


@pytest.mark.parametrize("utterance,expected_intent", GOLDEN_DIALOGUE_CASES)
def test_golden_dialogue_utterance(nlu_engine, utterance, expected_intent):
    """Each golden utterance must resolve to its expected canonical intent via the production pipeline."""
    from sic_framework.services.webserver.llm_nlu_service import normalize_intent_name

    predicted = predict_like_production(nlu_engine, utterance)
    expected = normalize_intent_name(expected_intent)

    allowed = DUAL_INTENT_UTTERANCES.get(utterance, {expected})
    assert predicted in allowed or predicted == expected or (expected, predicted) in STRICT_EQUIVALENCES, (
        f"Utterance '{utterance}' predicted '{predicted}', expected '{expected}'"
    )
