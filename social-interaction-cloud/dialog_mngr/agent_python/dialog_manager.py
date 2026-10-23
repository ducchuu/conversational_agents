import asyncio
import logging
import random
import re
from .state import DialogState
from .prolog_interface import PrologInterface

logger = logging.getLogger(__name__)


GREETING_INTENTS = frozenset({'greeting', 'greet', 'hello', 'hi'})
RECOMMEND_INTENTS = frozenset({'requestrecipe', 'requestrecommendation', 'reciperequest', 'a50recipeselect', 'recommend', 'nomorefilters'})
CONFIRM_INTENTS = frozenset({'confirmation', 'appreciate', 'appreciation', 'yes', 'confirm'})
DISCONFIRM_INTENTS = frozenset({'disconfirmation', 'no', 'reject'})
FILTER_INTENTS = frozenset({'addfilter', 'deletefiltervalue', 'deleteparameter', 'clearfilters', 'removeallfilters'})
RESTART_INTENTS = frozenset({'restart', 'start', 'reset'})
INTERCEPTOR_INTENTS = frozenset({'cookingquestion', 'helprequest', 'outofscope', 'unknown', 'chitchat', 'help', 'checkcapability', 'fallback'})
ADVISORY_TRIGGERS = ("pair with", "goes with", "go well with", "substitute", "instead of", "replace")
ANOTHER_RECIPE_INTENTS = frozenset({'requestrecommendation', 'requestrecipe', 'recommend'})
LAST_FILTER_TRIGGERS = ("last", "previous", "undo", "latest")
ALL_FILTER_TYPE_VALUES = frozenset({'', 'all', 'filters', 'filter', 'everything', 'none'})
QUICKEST_TRIGGERS = ("quickest", "fastest", "shortest")
NON_FILTER_SLOT_KEYS = frozenset({'userquery', 'query', 'rawtranscript'})
ORDINAL_INDEX = {
    'first': 0, '1st': 0,
    'second': 1, '2nd': 1,
    'third': 2, '3rd': 2,
    'fourth': 3, '4th': 3,
    'fifth': 4, '5th': 4,
    'last': -1,
}
ORDINAL_RE = re.compile(r"\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|last)\b", re.I)

HELP_PROMPTS = {
    'welcome': "You can ask me for a recipe by specifying a cuisine, an ingredient, or a cooking time!",
    'recipe_overview': "You can add more filters to narrow down the list, or just ask me to pick a recipe for you.",
    'recipe_overview2': "You can add more filters to narrow down the list, or just ask me to pick a recipe for you.",
    'recipe_confirmation': "You can say yes to cook this recipe, or no to see another option.",
}

class DialogManager:
    """
    State-machine dialog manager using a table-driven handler dispatch pattern.
    Replaces nested if/elif branching with isolated state handlers, reusable
    filter transitions, and a decoupled global interceptor pipeline.
    """
    def __init__(self):
        self.prolog = PrologInterface()
        self.state = DialogState()
        self._utterance = ""
        self._handlers = {
            'start': self._handle_start,
            'welcome': self._handle_welcome,
            'recipe_overview': self._handle_overview,
            'recipe_overview2': self._handle_overview,
            'recipe_confirmation': self._handle_confirmation,
            'closing': self._handle_closing,
        }

    def format_filters_string(self, memory):
        if not memory:
            return "[]"
        label_map = {
            'dietaryrestriction': 'Dietary restriction',
            'excludedietaryrestriction': 'Exclude dietary restriction',
            'excludeingredient': 'Exclude ingredient',
            'excludecuisine': 'Exclude cuisine',
            'excludemealtype': 'Exclude meal type',
            'mealtype': 'Meal type',
            'ingredienttype': 'Ingredient type',
            'excludeingredienttype': 'Exclude ingredient type',
            'nrofingredients': 'Max ingredients',
            'nrofsteps': 'Max steps',
            'cuisine': 'Cuisine',
            'ingredient': 'Ingredient',
            'duration': 'Max duration',
            'servings': 'Servings',
            'tag': 'Tag',
            'excludetag': 'Exclude tag',
        }
        items = []
        for k, v in memory.items():
            if k == 'exclude_recipe':
                continue
            k_clean = k.replace('_', '').lower()
            label = label_map.get(k_clean, k.capitalize())
            if isinstance(v, (list, tuple, set)):
                for sub_v in v:
                    items.append(f"{label}: {sub_v}")
            else:
                items.append(f"{label}: {v}")
        return "[" + ", ".join([f"'{item}'" for item in items]) + "]"

    def _speech_action(self, agent_intent, default_text, extra_state_vars=None):
        """Construct a standardized speech generation action dictionary."""
        state_vars = {
            'recipe_counter': self.state.recipe_counter,
            'last_sent_recipe': self.state.last_sent_recipe
        }
        if extra_state_vars:
            state_vars.update(extra_state_vars)
        return {
            'type': 'generate_speech',
            'agent_intent': agent_intent,
            'default': default_text,
            'state_vars': state_vars
        }

    async def process_intent(self, intent, slots, utterance=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._process_intent_sync, intent, slots, utterance)

    def _process_intent_sync(self, intent, slots, utterance=None):
        if slots:
            try:
                from sic_framework.services.nlu.fast_bert_nlu import normalize_slots
                slots = normalize_slots(slots)
            except Exception:
                pass

        intent_lower = intent.replace('_', '').lower() if intent else "unknown"
        user_text = str(
            (slots or {}).get("userQuery")
            or (slots or {}).get("raw_transcript")
            or ""
        )
        # Raw user utterance (when the caller provides it); lets handlers detect ordinals / superlatives.
        self._utterance = str(utterance or user_text or "")
        if (
            self.state.last_sent_recipe is not None
            and intent_lower == "addfilter"
            and any(trigger in user_text.lower() for trigger in ADVISORY_TRIGGERS)
        ):
            intent = "cookingQuestion"
            intent_lower = "cookingquestion"
            slots = {"userQuery": user_text} if user_text else {}

        logger.info(f"State: {self.state.state}, Intent: {intent}, Slots: {slots}")

        if intent_lower in RESTART_INTENTS:
            return self._handle_restart()

        if intent_lower == 'farewell':
            self.state.state = 'closing'
            return [
                {'type': 'emit', 'event': 'pattern', 'data': 'c43'},
                self._speech_action('farewell', "Goodbye! Enjoy your meal!")
            ]

        if intent_lower in INTERCEPTOR_INTENTS:
            return self._handle_interceptor(intent_lower, slots)

        is_filter_intent = intent_lower in FILTER_INTENTS
        if is_filter_intent:
            self._apply_filter_action(intent_lower, slots)

        # "Find another recipe": never re-recommend the recipe the user is currently looking at.
        if intent_lower in ANOTHER_RECIPE_INTENTS and self.state.last_sent_recipe and self.state.state != 'closing':
            self.state.reject_recipe(self.state.last_sent_recipe)

        recipes = self.prolog.query_recipes(self.state.memory)
        self.state.recipe_counter = len(recipes)
        self.state.current_candidates = list(recipes)
        actions = [
            {'type': 'emit', 'event': 'recipecounter', 'data': self.state.recipe_counter},
            {'type': 'emit', 'event': 'filters', 'data': self.format_filters_string(self.state.memory)}
        ]

        handler = self._handlers.get(self.state.state, self._handle_welcome)
        actions.extend(handler(intent_lower, slots, recipes, is_filter_intent))

        if self.state.state == 'recipe_overview2' and 0 < self.state.recipe_counter <= 20:
            if not any(a.get('event') == 'recipes' for a in actions if a.get('type') == 'emit'):
                actions.append({'type': 'emit', 'event': 'recipes', 'data': self.prolog.get_recipes_json(recipes)})

        return actions

    # global cases

    def _handle_restart(self):
        self.state.reset()
        self.state.state = 'welcome'
        return [
            {'type': 'emit', 'event': 'set_turn', 'data': 'true'},
            {'type': 'emit', 'event': 'pattern', 'data': 'c10'},
            self._speech_action('greeting', "Hi! I'm CookingBroski. I'm here to help you find the perfect recipe. What are you in the mood for?")
        ]

    def _handle_interceptor(self, intent_lower, slots):
        user_text = slots.get('userQuery', slots.get('query', ''))
        extra_vars = {
            'current_state': self.state.state,
            'userQuery': user_text,
            'filters': self.state.memory
        }

        if intent_lower == 'cookingquestion':
            return [self._speech_action(
                'cookingQuestion',
                "You can substitute ingredients or adjust cooking times based on what you have at home. What else would you like to know?",
                extra_vars
            )]

        if intent_lower in {'helprequest', 'help', 'checkcapability'}:
            help_text = HELP_PROMPTS.get(self.state.state, "You can specify a cuisine, an ingredient, or ask me to recommend a recipe.")
            return [self._speech_action('helpRequest', help_text, extra_vars)]

        if intent_lower in {'outofscope', 'chitchat', 'fallback'}:
            return [self._speech_action(
                'outOfScope',
                "I'm a kitchen assistant, so I can't help with that! But I can help you find a great recipe. What are you in the mood to cook?",
                extra_vars
            )]

        return [self._speech_action(
            'clarify',
            "I didn't quite catch that. You can specify a cuisine, an ingredient, or tell me what you feel like eating.",
            extra_vars
        )]

    def _apply_filter_action(self, intent_lower, slots):
        filter_slots = {
            k: v for k, v in (slots or {}).items()
            if k.replace('_', '').lower() not in NON_FILTER_SLOT_KEYS
        }
        text = self._utterance.lower()

        if intent_lower == 'addfilter':
            self.state.add_filters(slots)
        elif intent_lower == 'deletefiltervalue':
            if filter_slots:
                self.state.delete_filters(filter_slots)
            else:
                self.state.pop_last_filter()
        elif intent_lower == 'deleteparameter':
            filter_type = str(filter_slots.get('filterType', '') or '').strip().lower()
            only_all_marker = set(filter_slots) <= {'filterType'} and filter_type in ALL_FILTER_TYPE_VALUES
            if only_all_marker and any(re.search(rf"\b{t}\b", text) for t in LAST_FILTER_TRIGGERS):
                # "undo the last filter" -> remove only the most recent constraint
                self.state.pop_last_filter()
            elif only_all_marker:
                # "clear all filters" / "reset my filters": wipe constraints, stay in the recipe-selection flow
                self.state.clear_filters()
            else:
                self.state.delete_filters(filter_slots)
        elif intent_lower in {'clearfilters', 'removeallfilters'}:
            self.state.clear_filters()

    def _pick_recipe(self, recipes):
        """Choose the quickest candidate when the user asks for it, otherwise a random candidate."""
        if not recipes:
            return None
        if any(t in self._utterance.lower() for t in QUICKEST_TRIGGERS):
            quickest = self.prolog.get_quickest_recipe(recipes)
            if quickest:
                return quickest
        return random.choice(recipes)

    def _resolve_ordinal(self, text, candidates):
        """Map 'first/second/.../last' to the candidate shown at that position (None if out of range)."""
        match = ORDINAL_RE.search(text or "")
        if not match or not candidates:
            return None
        idx = ORDINAL_INDEX[match.group(1).lower()]
        try:
            return candidates[idx]
        except IndexError:
            return None

    def _transition_by_recipe_count(self, recipes):
        """Reusable threshold transition based on candidate recipe count."""
        count = self.state.recipe_counter
        if count > 20:
            self.state.state = 'recipe_overview'
            return [
                {'type': 'emit', 'event': 'pattern', 'data': 'a50recipeSelect'},
                self._speech_action('ackFilter', f"I found {count} matching recipes, which is too many to show right now. Please add more filters like cuisine, ingredients, or cooking time.")
            ]
        if 0 < count <= 20:
            self.state.state = 'recipe_overview2'
            return [
                {'type': 'emit', 'event': 'pattern', 'data': 'a21noMoreFilters'},
                {'type': 'emit', 'event': 'recipes', 'data': self.prolog.get_recipes_json(recipes)},
                self._speech_action('ackFilterEnd', f"I found {count} recipes matching your preferences! Take a look at the options, and tap one or tell me which one you'd like to cook.")
            ]
        self.state.state = 'recipe_overview'
        return [
            {'type': 'emit', 'event': 'pattern', 'data': 'a50recipeSelect'},
            self._speech_action('noRecipesLeft', "I couldn't find any recipes matching all those filters. Try removing a filter.")
        ]
    
    # state specific functions
    def _handle_start(self, intent_lower, slots, recipes, is_filter_intent):
        self.state.state = 'welcome'
        return [
            {'type': 'emit', 'event': 'pattern', 'data': 'c10'},
            self._speech_action('greeting', "Hi! I'm CookingBroski. I'm here to help you find the perfect recipe. What are you in the mood for?")
        ]

    def _handle_welcome(self, intent_lower, slots, recipes, is_filter_intent):
        if intent_lower in GREETING_INTENTS:
            self.state.state = 'recipe_overview'
            return [
                {'type': 'emit', 'event': 'pattern', 'data': 'a50recipeSelect'},
                self._speech_action('specifyGoal', "Great! Tell me what you want to eat. You can filter by cuisine, ingredients, or time!")
            ]

        # If user explicitly asks for a recommendation directly from welcome
        if intent_lower in {'requestrecommendation', 'recommend', 'reciperequest'}:
            target_recipe = self._pick_recipe(recipes) if self.state.recipe_counter > 0 else None
            if target_recipe:
                self.state.state = 'recipe_confirmation'
                self.state.last_sent_recipe = target_recipe
                r_title = self.prolog.get_recipe_name(target_recipe)
                rec_msg = f"How about {r_title}? It looks delicious. Shall we cook this one?" if r_title else "How about this one? It looks delicious. Shall we go with this?"
                return [
                    {'type': 'emit', 'event': 'pattern', 'data': 'a50recipeConfirm'},
                    {'type': 'emit', 'event': 'showRecipe', 'data': self.prolog.get_recipe_json(target_recipe)},
                    self._speech_action('recommend', rec_msg)
                ]

        if intent_lower in RECOMMEND_INTENTS:
            self.state.state = 'recipe_overview'
            return [
                {'type': 'emit', 'event': 'pattern', 'data': 'a50recipeSelect'},
                self._speech_action('specifyGoal', "Sure! What kind of food are you in the mood for? You can filter by cuisine, ingredients, or cooking time.")
            ]
        if is_filter_intent:
            return self._transition_by_recipe_count(recipes)

        return [self._speech_action('specifyGoal', "I'm here to help you find recipes! Tell me what you're in the mood for, or say something like 'Italian food' or 'something with chicken'.")]

    def _handle_overview(self, intent_lower, slots, recipes, is_filter_intent):
        recipe_named = (
            slots.get('recipe_name')
            or slots.get('recipe')
            or slots.get('raw_transcript')
            or slots.get('userQuery', '')
        )
        matched_recipe_id = slots.get('recipe_id')
        if not matched_recipe_id and recipe_named:
            matched_recipe_id = self.prolog.find_recipe_by_title(recipe_named, candidate_ids=recipes)

        # Ordinal selection ("the second recipe", "the last one") is only meaningful once a list is on screen.
        if (
            not matched_recipe_id
            and intent_lower == 'reciperequest'
            and 0 < self.state.recipe_counter <= 20
        ):
            matched_recipe_id = self._resolve_ordinal(self._utterance, self.state.current_candidates)

        if matched_recipe_id or intent_lower in RECOMMEND_INTENTS:
            target_recipe = matched_recipe_id or (self._pick_recipe(recipes) if self.state.recipe_counter > 0 else None)
            if target_recipe:
                self.state.state = 'recipe_confirmation'
                self.state.last_sent_recipe = target_recipe
                r_title = self.prolog.get_recipe_name(target_recipe)
                rec_msg = f"How about {r_title}? It looks delicious. Shall we cook this one?" if r_title else "How about this one? It looks delicious. Shall we go with this?"
                return [
                    {'type': 'emit', 'event': 'pattern', 'data': 'a50recipeConfirm'},
                    {'type': 'emit', 'event': 'showRecipe', 'data': self.prolog.get_recipe_json(target_recipe)},
                    self._speech_action('recommend', rec_msg)
                ]
            return [self._speech_action('noRecipesLeft', "I couldn't find any recipes matching your filters. Try removing some.")]

        if is_filter_intent:
            return self._transition_by_recipe_count(recipes)

        return [self._speech_action(
            'specifyGoal',
            "You can add a filter like cuisine, ingredient, or cooking time, or ask me to recommend a recipe for you."
        )]

    def _handle_confirmation(self, intent_lower, slots, recipes, is_filter_intent):
        if intent_lower in CONFIRM_INTENTS:
            self.state.state = 'closing'
            return [
                {'type': 'emit', 'event': 'pattern', 'data': 'c43'},
                self._speech_action('farewell', "Awesome! Have fun cooking! Let me know if you want to restart.")
            ]
        if intent_lower in ANOTHER_RECIPE_INTENTS:
            # The current recipe was already added to exclude_recipe, so `recipes` never contains it.
            target_recipe = self._pick_recipe(recipes)
            if target_recipe:
                self.state.last_sent_recipe = target_recipe
                r_title = self.prolog.get_recipe_name(target_recipe)
                rec_msg = f"How about {r_title}? It looks delicious. Shall we cook this one?" if r_title else "How about this one? It looks delicious. Shall we go with this?"
                return [
                    {'type': 'emit', 'event': 'pattern', 'data': 'a50recipeConfirm'},
                    {'type': 'emit', 'event': 'showRecipe', 'data': self.prolog.get_recipe_json(target_recipe)},
                    self._speech_action('recommend', rec_msg)
                ]
            self.state.state = 'recipe_overview'
            return [
                {'type': 'emit', 'event': 'pattern', 'data': 'a50recipeSelect'},
                self._speech_action('noRecipesLeft', "I've run out of other matching recipes. Try removing a filter.")
            ]
        if intent_lower in DISCONFIRM_INTENTS or intent_lower == 'nomorefilters':
            self.state.reject_recipe(self.state.last_sent_recipe)
            recipes = self.prolog.query_recipes(self.state.memory)
            self.state.recipe_counter = len(recipes)
            self.state.current_candidates = list(recipes)
            actions = [{'type': 'emit', 'event': 'recipecounter', 'data': self.state.recipe_counter}]

            if 0 < self.state.recipe_counter <= 20:
                self.state.state = 'recipe_overview2'
                actions.append({'type': 'emit', 'event': 'pattern', 'data': 'a21noMoreFilters'})
                actions.append({'type': 'emit', 'event': 'recipes', 'data': self.prolog.get_recipes_json(recipes)})
            else:
                self.state.state = 'recipe_overview'
                actions.append({'type': 'emit', 'event': 'pattern', 'data': 'a50recipeSelect'})

            actions.append(self._speech_action('ackFilterEnd', "No problem. Let's find something else. What else are you looking for?"))
            return actions

        if is_filter_intent:
            return self._transition_by_recipe_count(recipes)

        return [self._speech_action(
            'helpRequest',
            "You can say yes to confirm this recipe, no to choose another dish, or ask any cooking question."
        )]

    def _handle_closing(self, intent_lower, slots, recipes, is_filter_intent):
        if intent_lower == 'farewell':
            return [self._speech_action('farewell', "Goodbye! Enjoy your meal!")]
        if intent_lower in DISCONFIRM_INTENTS or intent_lower in RECOMMEND_INTENTS or is_filter_intent:
            self.state.reset()
            self.state.state = 'recipe_overview'
            return [
                {'type': 'emit', 'event': 'ClearFilters', 'data': ''},
                {'type': 'emit', 'event': 'pattern', 'data': 'a50recipeSelect'},
                self._speech_action('specifyGoal', "Sure, let's find another recipe! Tell me what you're in the mood for.")
            ]
        return [self._speech_action(
            'farewell',
            "Thanks for cooking with me! Say 'start over' if you'd like to search for another recipe."
        )]
