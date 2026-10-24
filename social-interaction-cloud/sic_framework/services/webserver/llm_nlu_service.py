import os
import json
import re
import logging
from anthropic import Anthropic
from sic_framework.services.webserver.telemetry import telemetry

logger = logging.getLogger(__name__)

try:
    from langfuse import observe
except ImportError:
    try:
        from langfuse.decorators import observe
    except ImportError:
        def observe(*args, **kwargs):
            def decorator(f):
                return f
            return decorator

CLAUDE_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5").strip()
anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# Intents that are strictly deterministic and require 0ms template bypass
DETERMINISTIC_INTENTS = {
    "greeting",
    "specifyGoal",
    "ackFilter",
    "ackFilterEnd",
    "noRecipesLeft",
    "farewell",
    "helpRequest",
}

INTENT_CANONICAL_MAP = {
    "addfilter": "addFilter",
    "appreciation": "appreciation",
    "checkcapability": "checkCapability",
    "clearfilters": "deleteParameter",
    "confirmation": "confirmation",
    "cookingquestion": "cookingQuestion",
    "deletefiltervalue": "deleteFilterValue",
    "deleteparameter": "deleteParameter",
    "disconfirmation": "disconfirmation",
    "fallback": "fallback",
    "farewell": "farewell",
    "greeting": "greeting",
    "helprequest": "helpRequest",
    "nomorefilters": "noMoreFilters",
    "outofscope": "outOfScope",
    "reciperequest": "recipeRequest",
    "requestrecipe": "recipeRequest",
    "requestrecommendation": "requestRecommendation",
    "restart": "restart",
    "unknown": "unknown",
}


def normalize_intent_name(intent_str: str) -> str:
    if not intent_str:
        return "unknown"
    key = intent_str.replace("_", "").strip().lower()
    return INTENT_CANONICAL_MAP.get(key, intent_str.strip())


try:
    from pydantic import BaseModel, Field, field_validator

    class NLUOutput(BaseModel):
        intent: str
        confidence: float = 1.0
        slots: dict = Field(default_factory=dict)

        @field_validator("intent", mode="before")
        @classmethod
        def _normalize_intent(cls, v):
            return normalize_intent_name(str(v))
except Exception:
    class NLUOutput:
        def __init__(self, intent="unknown", confidence=1.0, slots=None):
            self.intent = normalize_intent_name(str(intent))
            self.confidence = confidence
            self.slots = slots or {}

        @classmethod
        def model_validate(cls, data):
            return cls(
                intent=normalize_intent_name(str(data.get("intent", "unknown"))),
                confidence=data.get("confidence", 1.0),
                slots=data.get("slots", {}),
            )


FEW_SHOT_SYSTEM_PROMPT = None


def get_few_shot_prompt():
    global FEW_SHOT_SYSTEM_PROMPT
    if FEW_SHOT_SYSTEM_PROMPT is not None:
        return FEW_SHOT_SYSTEM_PROMPT

    prompt = """You are an NLU engine for a recipe recommender bot.
Classify the following transcript into one of the following intents:
- greeting (e.g. "hello", "hi", "hey")
- addFilter (e.g. "I want italian food", "something with chicken", "under 30 minutes", "vegan please")
- deleteFilterValue (e.g. "remove the chicken filter", "no more italian")
- deleteParameter (e.g. "clear all filters", "start over with filters")
- requestRecommendation (e.g. "show me a recipe", "recommend something", "what can I cook")
- recipeRequest (e.g. "I want the chicken parmesan recipe")
- noMoreFilters (e.g. "no more filters", "that's all, show me the recipes")
- confirmation (e.g. "yes", "sure", "sounds good", "I like it")
- disconfirmation (e.g. "no", "nah", "I don't like it", "show me another")
- appreciation (e.g. "thank you", "thanks a lot")
- cookingQuestion (e.g. "can I substitute butter with olive oil?", "how long to boil eggs?", "what is a bain-marie?")
- helpRequest (e.g. "what can I say?", "how does this work?", "help me", "what are my options?")
- checkCapability (e.g. "can you filter by cooking time?", "are you able to recommend vegan dishes?")
- outOfScope (e.g. "who is the president?", "what's the weather like?", "tell me a joke", "sing me a song")
- farewell (e.g. "bye", "goodbye", "thanks bye")
- restart (e.g. "start over", "restart")
- unknown (e.g. unclear, inaudible, or nonsensical)

If the intent is 'addFilter', extract the slots. Valid slot keys are:
- cuisine (e.g. "italian", "mexican", "thai")
- ingredient (e.g. "chicken", "tomato", "rice")
- dietaryRestriction (e.g. "vegan", "vegetarian", "gluten-free")
- duration (max cooking time in minutes, e.g. "30")
- mealType (e.g. "breakfast", "dinner", "dessert")
- tag (e.g. "pasta", "curry", "soup", "quick", "comfort-food")
- servings (e.g. "4")
- excludeIngredient (e.g. "no onions")
- excludeCuisine (e.g. "not italian")
- excludeDietaryRestriction (e.g. "not vegan")
- excludeMealType (e.g. "no breakfast")
- excludeTag (e.g. "no soup", "no pizza", "not spicy")

If the intent is 'cookingQuestion', 'helpRequest', 'outOfScope', or 'unknown', output slots: {"userQuery": "<user input>"}.
If it's 'deleteFilterValue', extract the slots to be deleted.

Here are some examples of how to classify user input:
Input: 'can I use olive oil instead of butter' -> Intent: cookingQuestion, Slots: {"userQuery": "can I use olive oil instead of butter"}
Input: 'what can I say here' -> Intent: helpRequest, Slots: {"userQuery": "what can I say here"}
Input: 'who is the president' -> Intent: outOfScope, Slots: {"userQuery": "who is the president"}
"""
    try:
        import random
        base_dir = os.path.dirname(__file__)
        train_path = os.path.abspath(os.path.join(base_dir, "../nlu/utils/data/train.json"))
        exclusion_path = os.path.abspath(os.path.join(base_dir, "../nlu/utils/data/exclusion_examples.json"))

        examples = []
        if os.path.exists(train_path):
            with open(train_path, "r") as f:
                examples.extend(json.load(f))
        if os.path.exists(exclusion_path):
            with open(exclusion_path, "r") as f:
                examples.extend(json.load(f))

        if examples:
            sample = random.Random(42).sample(examples, min(15, len(examples)))
            for ex in sample:
                prompt += f"Input: '{ex.get('text', '')}' -> Intent: {ex.get('intent', '')}, Slots: {ex.get('slots', {})}\n"
    except Exception as e:
        logger.error(f"Failed to load few-shot examples: {e}")

    prompt += '\nOutput STRICTLY in JSON format: {"intent": "<intent>", "confidence": 1.0, "slots": {<slots>}}'
    FEW_SHOT_SYSTEM_PROMPT = prompt
    return prompt


def _extract_anthropic_text(response) -> str:
    """Safely extracts text content from Anthropic response, handling ThinkingBlock in newer models."""
    if not hasattr(response, "content") or not response.content:
        return ""
    text_parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text" and hasattr(block, "text"):
            text_parts.append(block.text)
        elif hasattr(block, "text") and not hasattr(block, "thinking"):
            text_parts.append(block.text)
    if text_parts:
        return "".join(text_parts).strip()
    first_block = response.content[0]
    return getattr(first_block, "text", "") or getattr(first_block, "content", "")


_CLAUSE_SPLIT_RE = re.compile(
    r"^((?:\S+\s+){2,}?\S+[.?!;:]|(?:\S+\s+){5,}?\S+,)\s+(\S.*)$",
    re.DOTALL,
)

STATIC_NLG_SYSTEM_PROMPT = """You are 'CookingBroski', a friendly, ultra-fast voice-first kitchen chef and recipe recommendation assistant.
Your output is spoken aloud directly to the user via browser text-to-speech (Web Speech API).

STRICT VOICE & FORMATTING RULES:
1. Length: Maximum 2 short, punchy sentences (under 35 words total).
2. TTS Cleanliness: Output ONLY raw spoken sentences. Never use Markdown, asterisks (*), bullet points (-), numbered lists, quotes, XML tags, or JSON.
3. Grounded Context: You will receive a <kitchen_context> JSON block containing:
   - "current_state": The dialogue phase ('welcome', 'recipe_overview', 'recipe_overview2', 'recipe_confirmation', 'closing').
   - "active_filters": Dietary restrictions, cuisines, meal types, tags, time limits, and excluded ingredients or tags the user has applied.
   - "remaining_recipes_count": How many recipes in the database currently match their filters.
   - "active_recipe": The specific dish currently on screen (including title, cuisine, time_minutes, servings, ingredients, and steps_preview).

INTENT-SPECIFIC BEHAVIORS:
- If <agent_intent> is 'cookingQuestion':
  Sentence 1: Answer the user's culinary, pairing, substitution, quantity, or technique question directly and specifically.
  * When "active_recipe" is present and the user refers to "this", "it", "the dish", or asks what pairs well / how to substitute an ingredient / how much to use, explicitly tailor your answer to the "active_recipe" title and its "ingredients" or "steps_preview".
  * Always respect "active_filters" (e.g., if 'vegan', 'vegetarian', 'lactose-free', or an 'excludeIngredient' is active, never suggest a pairing or substitute that violates their dietary filters).
  Sentence 2: Smoothly pivot back to the task based on "current_state":
  * 'welcome': Ask what cuisine, ingredient, or meal they'd like to cook today.
  * 'recipe_overview' or 'recipe_overview2': Ask if they want to add another filter or hear a recipe recommendation.
  * 'recipe_confirmation': Ask if they'd like to cook this recipe or see another option.

- If <agent_intent> is 'outOfScope':
  Sentence 1: Politely decline the non-cooking query in one brief clause by acknowledging their topic and stating you are strictly a kitchen assistant.
  Sentence 2: Pivot back to the recipe task based on "current_state" (ask what they want to cook in 'welcome', whether to add a filter in 'recipe_overview', or whether to cook the active dish in 'recipe_confirmation').

- If <agent_intent> is 'clarify':
  Sentence 1: Politely state that you didn't quite catch that.
  Sentence 2: Prompt them with a quick example of what they can say in "current_state" (such as naming a cuisine like Italian, an ingredient like chicken, or asking for a quick meal).

- For any other <agent_intent>:
  Adapt the provided <reference_templates> into a natural, accurate 1-to-2 sentence spoken response that reflects <kitchen_context>.

CULINARY SUBSTITUTION & PAIRING GUIDELINES (FOR PROMPT CACHE):
- Dairy-free / Vegan swaps: Replace butter with olive oil or vegan butter; replace heavy cream with full-fat coconut milk or cashew cream; replace parmesan with nutritional yeast.
- Gluten-free swaps: Replace wheat flour with a 1-to-1 gluten-free baking blend or cornstarch for thickening; replace soy sauce with tamari or coconut aminos.
- Egg swaps: For baking, use 1 tablespoon ground flaxseed mixed with 3 tablespoons water per egg, or unsweetened applesauce.
- Regional side dish pairings:
  * Italian pasta/risotto: Crisp arugula salad with lemon vinaigrette or roasted garlic broccolini.
  * Korean / East Asian stir-fries and fried chicken: Steamed jasmine rice, pickled radish, or sesame cucumber salad.
  * Mexican tacos/enchiladas: Cilantro-lime rice, black beans, or charred street corn.
  * Indian curries: Basmati rice, warm garlic naan, or cooling cucumber raita.

FEW-SHOT SPOKEN EXAMPLES:
- User in 'recipe_confirmation' (active_recipe: "Sweet and Spicy Gochujang Fried Chicken"): "What side dish pairs well with this?"
  Response: Steamed jasmine rice and a crisp sesame cucumber salad balance the sweet and spicy gochujang glaze wonderfully. Would you like to cook this recipe or see another option?
- User in 'recipe_overview' (active_filters: {"dietaryrestriction": ["vegan"]}): "What can I use instead of heavy cream?"
  Response: Since you're browsing vegan recipes, full-fat coconut milk or blended cashew cream makes a rich one-to-one substitute for heavy cream. Want to add another filter or hear a recipe recommendation?
- User in 'welcome': "Can you help me with my calculus homework?"
  Response: I'm a kitchen assistant, so I can't help with calculus homework, but I'd love to help with dinner. What cuisine or ingredient are you in the mood for today?"""


def _hydrate_recipe_from_prolog(prolog_iface, recipe_ref) -> dict:
    """Queries SWI-Prolog for the active recipe's details in <2ms without failing if methods are absent."""
    if not prolog_iface:
        return {"title": str(recipe_ref)} if recipe_ref else {}

    if hasattr(prolog_iface, "get_recipe_context_summary"):
        try:
            summary = prolog_iface.get_recipe_context_summary(recipe_ref)
            if isinstance(summary, dict) and summary:
                return summary
        except Exception as e:
            logger.debug(f"get_recipe_context_summary fallback triggered: {e}")

    if not hasattr(prolog_iface, "prolog"):
        return {"title": str(recipe_ref)} if recipe_ref else {}

    recipe_id = None
    recipe_name = None

    if isinstance(recipe_ref, dict):
        recipe_id = recipe_ref.get("id") or recipe_ref.get("recipe_id") or recipe_ref.get("recipeID")
        recipe_name = recipe_ref.get("name") or recipe_ref.get("recipe_name") or recipe_ref.get("title")
    elif isinstance(recipe_ref, (str, int)):
        ref_str = str(recipe_ref).strip()
        if ref_str.isdigit():
            recipe_id = ref_str
        elif ref_str:
            recipe_name = ref_str

    try:
        if not recipe_id and not recipe_name:
            curr = list(prolog_iface.prolog.query("currentRecipe(ID)"))
            if curr:
                recipe_id = str(curr[0]["ID"])

        if not recipe_id and recipe_name:
            escaped = recipe_name.replace("'", "\\'").lower()
            id_res = list(prolog_iface.prolog.query(f"recipeName(ID, '{escaped}')"))
            if id_res:
                recipe_id = str(id_res[0]["ID"])

        if not recipe_id:
            return {"title": recipe_name} if recipe_name else {}

        name_res = list(prolog_iface.prolog.query(f"recipeName('{recipe_id}', Name)"))
        cuisine_res = list(prolog_iface.prolog.query(f"cuisine('{recipe_id}', Cuisine)"))
        time_res = list(prolog_iface.prolog.query(f"time('{recipe_id}', Time)"))
        serv_res = list(prolog_iface.prolog.query(f"servings('{recipe_id}', Servings)"))
        ing_res = list(prolog_iface.prolog.query(f"ingredientAndQuantity('{recipe_id}', Ing)"))
        step_res = list(prolog_iface.prolog.query(f"step('{recipe_id}', StepNum, StepText)"))

        steps_sorted = sorted(
            [(int(s["StepNum"]), str(s["StepText"])) for s in step_res],
            key=lambda x: x[0],
        )

        return {
            "recipe_id": recipe_id,
            "title": str(name_res[0]["Name"]) if name_res else (recipe_name or ""),
            "cuisine": str(cuisine_res[0]["Cuisine"]) if cuisine_res else "",
            "time_minutes": int(time_res[0]["Time"]) if time_res else None,
            "servings": int(serv_res[0]["Servings"]) if serv_res else None,
            "ingredients": [str(r["Ing"]) for r in ing_res[:12]],
            "steps_preview": [text for _, text in steps_sorted[:4]],
        }
    except Exception as e:
        logger.debug(f"Non-fatal Prolog context lookup skipped: {e}")
        return {"title": recipe_name or str(recipe_ref or "")}


def build_dynamic_kitchen_context(dialog_manager) -> str:
    """
    Extracts live state from DialogState (state.py) and PrologInterface
    without mutating the cached static system prefix.
    """
    state_obj = getattr(dialog_manager, "state", None)
    if state_obj is None:
        return "{}"

    recipe_details = {}
    prolog_iface = getattr(dialog_manager, "prolog", None)
    if prolog_iface is not None and hasattr(prolog_iface, "get_recipe_context_summary"):
        recipe_details = prolog_iface.get_recipe_context_summary(state_obj.last_sent_recipe)
    elif state_obj.last_sent_recipe:
        recipe_details = {"title": str(state_obj.last_sent_recipe)}

    context_payload = {
        "dialogue_state": state_obj.state,
        "recipe_counter": state_obj.recipe_counter,
        "active_filters_memory": state_obj.memory,
        "last_sent_recipe": recipe_details,
    }
    return json.dumps(context_payload, ensure_ascii=False, sort_keys=True)


def _build_kitchen_context(brain, state_vars: dict) -> dict:
    """Combines DialogState (state.py) and state_vars into a compact dictionary for Claude Haiku."""
    state_obj = getattr(brain, "state", None) if brain else None
    prolog_iface = getattr(brain, "prolog", None) if brain else None

    current_state = state_vars.get("current_state") or (getattr(state_obj, "state", None) if state_obj else "welcome")
    active_filters = getattr(state_obj, "memory", {}) if state_obj else state_vars.get("filters", {})
    recipe_counter = getattr(state_obj, "recipe_counter", None) if state_obj else state_vars.get("recipe_counter")
    last_recipe_ref = (
        state_vars.get("recipe_name")
        or state_vars.get("recipe_id")
        or (getattr(state_obj, "last_sent_recipe", None) if state_obj else None)
    )

    active_recipe = (
        _hydrate_recipe_from_prolog(prolog_iface, last_recipe_ref)
        if (last_recipe_ref or current_state == "recipe_confirmation")
        else {}
    )

    return {
        "current_state": current_state,
        "remaining_recipes_count": recipe_counter,
        "active_filters": active_filters,
        "active_recipe": active_recipe,
    }


@observe()
def generate_agent_speech_llm(agent_intent, default_text, state_vars, prolog_examples, on_chunk=None, brain=None):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return default_text

    user_text = state_vars.get("userQuery", state_vars.get("query", ""))
    kitchen_context = _build_kitchen_context(brain, state_vars)
    templates = prolog_examples if prolog_examples else ([default_text] if default_text else [])

    user_prompt = (
        f"<kitchen_context>\n{json.dumps(kitchen_context, ensure_ascii=False)}\n</kitchen_context>\n"
        f"<agent_intent>{agent_intent}</agent_intent>\n"
        f"<userQuery>{user_text}</userQuery>\n"
        f"<reference_templates>{json.dumps(templates, ensure_ascii=False)}</reference_templates>"
    )

    system_blocks = [
        {
            "type": "text",
            "text": STATIC_NLG_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    if on_chunk is not None and hasattr(anthropic_client.messages, "stream"):
        is_first = True
        full_text_parts = []
        buffer = ""

        def _consume_stream(model_name):
            nonlocal is_first, buffer
            with anthropic_client.messages.stream(
                model=model_name,
                max_tokens=90,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                for text_delta in stream.text_stream:
                    if not text_delta:
                        continue
                    full_text_parts.append(text_delta)
                    buffer += text_delta
                    while True:
                        match = _CLAUSE_SPLIT_RE.match(buffer)
                        if not match:
                            break
                        chunk_text = match.group(1).strip()
                        buffer = match.group(2)
                        if chunk_text:
                            on_chunk(chunk_text, is_first, False)
                            is_first = False

        try:
            try:
                _consume_stream(CLAUDE_MODEL)
            except Exception as api_err:
                if is_first and ("not_found" in str(api_err).lower() or "model" in str(api_err).lower()):
                    full_text_parts.clear()
                    buffer = ""
                    _consume_stream("claude-haiku-4-5-20251001")
                else:
                    raise api_err

            final_chunk = buffer.strip()
            if final_chunk:
                on_chunk(final_chunk, is_first, True)
                is_first = False
            elif not is_first:
                on_chunk("", False, True)

            full_text = "".join(full_text_parts).strip()
            if full_text:
                return full_text
        except Exception as e:
            if not is_first:
                on_chunk("", False, True)
            telemetry.record_llm_error()
            logger.error(f"LLM Speech Stream failed: {e}. Falling back to default Prolog template.")
            return "".join(full_text_parts).strip() or default_text

    try:
        try:
            response = anthropic_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=90,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as api_err:
            if "not_found" in str(api_err).lower() or "model" in str(api_err).lower():
                response = anthropic_client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=90,
                    system=system_blocks,
                    messages=[{"role": "user", "content": user_prompt}],
                )
            else:
                raise api_err
        return _extract_anthropic_text(response)
    except Exception as e:
        telemetry.record_llm_error()
        logger.error(f"LLM Speech Generation failed: {e}. Falling back to default Prolog template.")
        return default_text


def resolve_speech_text(brain, agent_intent, default_text, state_vars, on_chunk=None):
    """
    Tier 1 vs Tier 2 routing:
    - Tier 1: Pull grounded Prolog canned responses (0 ms)
    - Tier 2: Call Claude Haiku for dynamic recommendation / advice with live DialogState
    """
    prolog_examples = brain.prolog.get_speech_examples(agent_intent, state_vars)

    if agent_intent in DETERMINISTIC_INTENTS:
        if prolog_examples and len(prolog_examples) > 0:
            return prolog_examples[0]
        return default_text

    return generate_agent_speech_llm(
        agent_intent,
        default_text,
        state_vars,
        prolog_examples,
        on_chunk=on_chunk,
        brain=brain,
    )


@observe()
def extract_intent_llm(transcript):
    """
    LLMOps-enhanced NLU:
    - Native Anthropic Prompt Caching via cache_control (90% cost cut, 80% lower latency)
    - Pydantic schema validation for strict types
    - Fallback circuit breaker
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY is not set!")
        return None, {}

    system_prompt = get_few_shot_prompt()
    try:
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=150,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f'Classify this utterance: "{transcript}"',
                }
            ],
        )
        raw = _extract_anthropic_text(response)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        parsed = NLUOutput.model_validate(json.loads(raw))
        try:
            from sic_framework.services.nlu.fast_bert_nlu import normalize_slots
            norm_slots = normalize_slots(parsed.slots)
        except Exception:
            norm_slots = parsed.slots
        return parsed.intent, norm_slots
    except Exception as e:
        telemetry.record_llm_error()
        logger.warning(f"LLM Intent extraction failed ({e}). Circuit breaker activated; falling back to local NLU / rules.")
        return None, {}


_RE_CLEAR_ALL_FILTERS = re.compile(
    r"\b(clear|reset|start over|wipe|remove|delete)\b(?:\s+\S+){0,3}?\s+filters\b", re.I
)
_RE_ORDINAL_RECIPE = re.compile(r"\b(first|second|third|fourth|fifth|1st|2nd|3rd|last)\s+(recipe|one|option|dish)\b", re.I)
_RE_SUPERLATIVE_PICK = re.compile(
    r"\b(pick|choose|recommend|suggest|give me|select)\b.*\b(quickest|fastest|best|easiest)\s+(one|recipe|dish|option)\b",
    re.I,
)
_RE_ALTERNATIVE_RECIPE = re.compile(
    r"\b(find|suggest|recommend|show|pick|give)\b.*\b(another|different|something else)\b", re.I
)
_RE_WHAT_CAN_I_COOK = re.compile(
    r"\bwhat (can|should|could) (i|we|you) (cook|make|prepare|recommend|suggest)\b", re.I
)
_RE_BACK_TO_LIST = re.compile(r"\b(go back|return|back)\b.*\b(recipe list|recipes|overview|options|list)\b", re.I)


def infer_fallback_intent(transcript: str) -> tuple[str, dict]:
    """Deterministic keyword fallback when both FastBERTNLU and Claude LLM are unavailable or return unknown."""
    lower_trans = transcript.lower().strip()
    slots = {"userQuery": transcript}

    # Domain-boundary overrides (checked first; they disambiguate phrases the generic rules below mis-route).
    if _RE_CLEAR_ALL_FILTERS.search(lower_trans):
        return "deleteParameter", {}
    if _RE_ORDINAL_RECIPE.search(lower_trans):
        return "recipeRequest", {}
    if (
        _RE_SUPERLATIVE_PICK.search(lower_trans)
        or _RE_ALTERNATIVE_RECIPE.search(lower_trans)
        or _RE_WHAT_CAN_I_COOK.search(lower_trans)
    ):
        return "requestRecommendation", {}
    if _RE_BACK_TO_LIST.search(lower_trans):
        return "disconfirmation", {}

    is_question = any(
        lower_trans.startswith(q)
        for q in [
            "can i ",
            "could i ",
            "how do ",
            "how to ",
            "how long ",
            "how spicy ",
            "is it ",
            "is this ",
            "what is ",
            "what are ",
            "what can ",
            "what ingredients ",
            "what side dish ",
            "why ",
            "substitute ",
            "is it possible ",
        ]
    ) or any(
        kw in lower_trans
        for kw in [
            "instead of",
            "substitute",
            "replace",
            "ingredients in",
            "ingredient in",
            "pairs with",
            "pair with",
            "leftovers last",
            "beginner-friendly",
            "beginner friendly",
        ]
    )

    if is_question:
        return "cookingQuestion", slots
    if any(greet in lower_trans for greet in ["hello", "hi ", "hey"]) or lower_trans in ["hi", "hey"]:
        return "greeting", {}
    if any(h in lower_trans for h in ["help", "what can i say", "what are my options", "how does this work", "what do i do"]):
        return "helpRequest", slots
    if any(c in lower_trans for c in ["who is ", "what is the weather", "tell me a joke", "sing me a song", "how old are you", "how are you"]):
        return "outOfScope", slots
    if any(conf in lower_trans for conf in ["yes", "sure", "sounds good", "okay", "yep", "perfect"]):
        return "confirmation", {}
    if any(dis in lower_trans for dis in ["no", "nah", "nope", "don't like it"]):
        return "disconfirmation", {}
    if any(fare in lower_trans for fare in ["bye", "goodbye", "see you", "thanks bye"]):
        return "farewell", {}
    if any(res in lower_trans for res in ["restart", "start over", "reset", "search again", "from scratch", "from the beginning"]):
        return "restart", {}
    if any(rec in lower_trans for rec in ["recommend", "pick one", "choose for me", "pick a recipe", "suggest", "surprise me", "best dish"]):
        return "requestRecommendation", {}
    if any(verb in lower_trans for verb in ["want", "like", "show", "give me", "find", "make", "cook", "recipe", "food"]):
        return "addFilter", {"ingredient": transcript.strip()}
    return "unknown", slots

