import os
import sys
import logging

# On macOS, prevent pyswip from loading broken /Applications/SWI-Prolog.app bundle
if sys.platform == "darwin" and "SWI_HOME_DIR" not in os.environ:
    os.environ["SWI_HOME_DIR"] = "/nonexistent"

from pyswip import Prolog

logger = logging.getLogger(__name__)

PROLOG_FILTER_KEY_MAP = {
    'dietaryrestriction': 'dietaryrestriction',
    'dietary_restriction': 'dietaryrestriction',
    'diet': 'dietaryrestriction',
    'dietary': 'dietaryrestriction',
    'excludedietaryrestriction': 'excludedietaryrestriction',
    'exclude_dietary_restriction': 'excludedietaryrestriction',
    'excludediet': 'excludedietaryrestriction',
    'excludeingredient': 'excludeingredient',
    'exclude_ingredient': 'excludeingredient',
    'excludeingredients': 'excludeingredient',
    'excludecuisine': 'excludecuisine',
    'exclude_cuisine': 'excludecuisine',
    'excludemealtype': 'excludemealtype',
    'exclude_meal_type': 'excludemealtype',
    'excludemeal': 'excludemealtype',
    'mealtype': 'mealType',
    'meal_type': 'mealType',
    'meal': 'mealType',
    'ingredienttype': 'ingredienttype',
    'ingredient_type': 'ingredienttype',
    'excludeingredienttype': 'excludeingredienttype',
    'exclude_ingredient_type': 'excludeingredienttype',
    'cuisine': 'cuisine',
    'cuisines': 'cuisine',
    'ingredient': 'ingredient',
    'ingredients': 'ingredient',
    'duration': 'duration',
    'time': 'duration',
    'cookingtime': 'duration',
    'cooking_time': 'duration',
    'max_duration': 'duration',
    'nrofingredients': 'nrOfIngredients',
    'nr_of_ingredients': 'nrOfIngredients',
    'max_ingredients': 'nrOfIngredients',
    'ingredient_count': 'nrOfIngredients',
    'nrofsteps': 'nrOfSteps',
    'nr_of_steps': 'nrOfSteps',
    'nrsteps': 'nrOfSteps',
    'steps': 'nrOfSteps',
    'max_steps': 'nrOfSteps',
    'servings': 'servings',
    'serving': 'servings',
    'portions': 'servings',
    'portion': 'servings',
    'tag': 'tag',
    'tags': 'tag',
    'excludetag': 'excludetag',
    'exclude_tag': 'excludetag',
    'easykeyword': 'easy',
    'easy_key_word': 'easy',
    'difficulty': 'easy',
    'easy': 'easy',
    'fast': 'fast',
    'quick': 'fast',
    'short_time': 'fast',
    'shorttimekeyword': 'fast',
}

DIETARY_CANONICAL_MAP = {
    'vegatarian': 'vegetarian',
    'vegetarian': 'vegetarian',
    'veggie': 'vegetarian',
    'vegetarians': 'vegetarian',
    'vegan': 'vegan',
    'vegans': 'vegan',
    'plant-based': 'vegan',
    'plant based': 'vegan',
    'gluten-free': 'gluten-free',
    'gluten free': 'gluten-free',
    'gluten': 'gluten-free',
    'dairy-free': 'dairy-free',
    'dairy free': 'dairy-free',
    'diary-free': 'dairy-free',
    'diary free': 'dairy-free',
    'non-dairy': 'dairy-free',
    'non dairy': 'dairy-free',
    'lactose-free': 'lactose-free',
    'lactose free': 'lactose-free',
    'pescatarian': 'pescatarian',
    'pescetarian': 'pescatarian',
    'pescatarians': 'pescatarian',
    'pescetarians': 'pescatarian',
    'spicy': 'spicy',
    'spice': 'spicy',
    'healthy': 'healthy',
}

AGENT_INTENT_ALIAS_MAP = {
    'helpRequest': 'describeCapability',
    'helprequest': 'describeCapability',
    'help': 'describeCapability',
    'checkCapability': 'describeCapability',
    'checkcapability': 'describeCapability',
    'clarify': 'paraphraseRequest',
    'fallback': 'paraphraseRequest',
}

class PrologInterface:
    def __init__(self):
        self.prolog = Prolog()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pl_files = ["utils.pl", "ingredient_hierarchies.pl", "recipe_database.pl", "recipe_selection.pl", "dialog.pl", "dialogflow.pl", "patterns.pl", "responses.pl"]
        for f in pl_files:
            path = os.path.join(base_dir, f)
            if os.path.exists(path):
                self.prolog.consult(path)
                logger.info(f"Loaded {f}")
            else:
                logger.warning(f"Could not find {path}")

        # In-memory cache of recipe names: {recipe_id: recipe_name}
        self.recipe_names = {}
        try:
            for r in self.prolog.query("recipeName(ID, Name)"):
                rid = r['ID'].decode('utf-8') if isinstance(r['ID'], bytes) else str(r['ID'])
                name = r['Name'].decode('utf-8') if isinstance(r['Name'], bytes) else str(r['Name'])
                self.recipe_names[rid] = name
            logger.info(f"Cached {len(self.recipe_names)} recipe names in memory.")
        except Exception as e:
            logger.warning(f"Could not pre-cache recipe names: {e}")

        # In-memory cache of cooking times in minutes: {recipe_id: minutes} from time/2 facts
        self.recipe_times = {}
        try:
            for r in self.prolog.query("time(ID, Minutes)"):
                rid = r['ID'].decode('utf-8') if isinstance(r['ID'], bytes) else str(r['ID'])
                try:
                    minutes = int(float(str(r['Minutes'])))
                except (TypeError, ValueError):
                    continue
                self.recipe_times[rid] = min(minutes, self.recipe_times.get(rid, minutes))
            logger.info(f"Cached cooking times for {len(self.recipe_times)} recipes.")
        except Exception as e:
            logger.warning(f"Could not pre-cache recipe times: {e}")

    def get_quickest_recipe(self, candidate_ids):
        """
        Return the candidate recipe ID with the smallest cooking time (time/2 minutes).
        Candidates without a known time are ignored; returns None if no candidate has one.
        """
        timed = [(self.recipe_times[str(rid)], str(rid)) for rid in candidate_ids if str(rid) in self.recipe_times]
        if not timed:
            return None
        return min(timed, key=lambda pair: pair[0])[1]

    def get_recipe_name(self, recipe_id):
        """Retrieve recipe title string by ID."""
        if not recipe_id:
            return None
        rid_str = str(recipe_id)
        if rid_str in self.recipe_names:
            return self.recipe_names[rid_str]
        try:
            res = list(self.prolog.query(f"recipeName('{rid_str}', Name)"))
            if res:
                return res[0]['Name'].decode('utf-8') if isinstance(res[0]['Name'], bytes) else str(res[0]['Name'])
        except Exception:
            pass
        return None

    def get_recipe_context_summary(self, recipe_ref=None) -> dict:
        """
        Resolves a recipe from state.last_sent_recipe (ID, name, or dict)
        or Prolog's currentRecipe/1 fact, returning a compact dict for LLM NLG.
        """
        recipe_id = None
        recipe_name = None

        # 1. Unpack if last_sent_recipe is a dictionary
        if isinstance(recipe_ref, dict):
            recipe_id = recipe_ref.get("id") or recipe_ref.get("recipe_id") or recipe_ref.get("recipeID")
            recipe_name = recipe_ref.get("name") or recipe_ref.get("recipe_name") or recipe_ref.get("title") or recipe_ref.get("recipeName")
        elif isinstance(recipe_ref, (str, int)):
            ref_str = str(recipe_ref).strip()
            if ref_str.isdigit():
                recipe_id = ref_str
            elif ref_str:
                recipe_name = ref_str

        try:
            # 2. Fallback: check Prolog's active currentRecipe/1 predicate if recipe_ref wasn't set
            if not recipe_id and not recipe_name:
                curr = list(self.prolog.query("currentRecipe(ID)"))
                if curr:
                    recipe_id = str(curr[0]["ID"])

            # 3. If we only have the recipe name, resolve its recipeID from recipeName/2
            if not recipe_id and recipe_name:
                escaped_name = recipe_name.replace("'", "\\'").lower()
                id_res = list(self.prolog.query(f"recipeName(ID, '{escaped_name}')"))
                if id_res:
                    recipe_id = str(id_res[0]["ID"])

            if not recipe_id:
                return {"title": recipe_name} if recipe_name else {}

            # 4. Query recipe_database.pl facts for the resolved recipeID
            name_res = list(self.prolog.query(f"recipeName('{recipe_id}', Name)"))
            cuisine_res = list(self.prolog.query(f"cuisine('{recipe_id}', Cuisine)"))
            meal_res = list(self.prolog.query(f"mealType('{recipe_id}', Meal)"))
            tag_res = list(self.prolog.query(f"tag('{recipe_id}', Tag)"))
            time_res = list(self.prolog.query(f"time('{recipe_id}', Time)"))
            servings_res = list(self.prolog.query(f"servings('{recipe_id}', Servings)"))
            ing_res = list(self.prolog.query(f"ingredientAndQuantity('{recipe_id}', Ing)"))
            step_res = list(self.prolog.query(f"step('{recipe_id}', StepNum, StepText)"))

            steps_sorted = sorted(
                [(int(s["StepNum"]), str(s["StepText"])) for s in step_res],
                key=lambda x: x[0],
            )

            return {
                "recipe_id": recipe_id,
                "title": str(name_res[0]["Name"]) if name_res else (recipe_name or ""),
                "cuisine": str(cuisine_res[0]["Cuisine"]) if cuisine_res else "",
                "meal_type": str(meal_res[0]["Meal"]) if meal_res else "",
                "tags": [str(t["Tag"]) for t in tag_res[:5]],
                "time_minutes": int(time_res[0]["Time"]) if time_res else None,
                "servings": int(servings_res[0]["Servings"]) if servings_res else None,
                "ingredients": [str(r["Ing"]) for r in ing_res[:15]],
                "steps_preview": [text for _, text in steps_sorted[:6]],
            }
        except Exception as e:
            logger.debug(f"Non-fatal Prolog context lookup skipped: {e}")
            return {"title": recipe_name or str(recipe_ref or "")}

    def find_recipe_by_title(self, query, candidate_ids=None):
        """
        Match a user title query against candidate or all recipes.
        Supports exact match, substring match, and token overlap.
        """
        if not query:
            return None
        q = str(query).lower().strip().strip(" .,!?;:'\"-()")

        # Strip conversational prefixes
        prefixes = [
            "i would like the ", "i would like ", "i'd like the ", "i'd like ",
            "i want the ", "i want ", "how about the ", "how about ",
            "let's do the ", "let's do ", "give me the ", "give me ",
            "can i have the ", "can i have ", "recipe for the ", "recipe for ",
            "show me the ", "show me ", "select the ", "select ",
            "choose the ", "choose ", "cook the ", "cook ", "make the ", "make ",
        ]
        for prefix in prefixes:
            if q.startswith(prefix):
                q = q[len(prefix):].strip()
                break

        # Helper to search a list of candidate IDs
        def search_ids(ids_list):
            # 1. Exact match
            for rid in ids_list:
                name = self.get_recipe_name(rid)
                if name and name.lower() == q:
                    return rid

            # 2. Substring containment match
            best_r = None
            best_l = 0
            for rid in ids_list:
                name = self.get_recipe_name(rid)
                if name:
                    nl = name.lower()
                    if nl in q or q in nl:
                        if len(nl) > best_l:
                            best_r = rid
                            best_l = len(nl)
            if best_r:
                return best_r

            # 3. Token overlap match (Jaccard similarity on significant tokens)
            q_tokens = set([w for w in q.replace(',', ' ').split() if len(w) > 2])
            if len(q_tokens) >= 2:
                best_score = 0.0
                best_tok_rid = None
                for rid in ids_list:
                    name = self.get_recipe_name(rid)
                    if name:
                        n_tokens = set([w for w in name.lower().replace(',', ' ').split() if len(w) > 2])
                        if n_tokens:
                            intersection = len(q_tokens.intersection(n_tokens))
                            score = intersection / len(n_tokens)
                            if score > 0.5 and score > best_score:
                                best_score = score
                                best_tok_rid = rid
                if best_tok_rid:
                    return best_tok_rid
            return None

        # Try searching candidates first (if provided)
        if candidate_ids:
            found = search_ids([str(cid) for cid in candidate_ids])
            if found:
                return found

        # Fall back to searching all recipes in the cookbook
        return search_ids(list(self.recipe_names.keys()))

    def query_recipes(self, memory):
        query = "findall(R, recipeID(R), R0)"
        var_idx = 0
        for raw_k, raw_v in memory.items():
            if raw_k == 'exclude_recipe':
                excluded = raw_v if isinstance(raw_v, (list, tuple, set)) else [raw_v]
                excluded_ids = [str(e).replace("\\", "\\\\").replace("'", "\\'") for e in excluded if e]
                if excluded_ids:
                    excluded_list = "[" + ",".join(f"'{e}'" for e in excluded_ids) + "]"
                    query += f", findall(RX, (member(RX, R{var_idx}), \\+ memberchk(RX, {excluded_list})), R{var_idx+1})"
                    var_idx += 1
                continue

            k_norm = raw_k.replace('_', '').lower()
            k = PROLOG_FILTER_KEY_MAP.get(k_norm, raw_k)
            values = raw_v if isinstance(raw_v, (list, tuple, set)) else [raw_v]

            for v in values:
                if k in ['duration', 'servings', 'nrOfIngredients', 'nrOfSteps']:
                    import re
                    match = re.search(r'\d+', str(v))
                    if match:
                        num_val = int(match.group(0))
                        query += f", applyFilter('{k}', {num_val}, R{var_idx}, R{var_idx+1})"
                    else:
                        v_str = str(v).lower().strip()
                        if v_str in ['quick', 'fast', 'short']:
                            query += f", applyFilter('{k}', 30, R{var_idx}, R{var_idx+1})"
                        elif v_str in ['mid', 'medium']:
                            query += f", applyFilter('{k}', 60, R{var_idx}, R{var_idx+1})"
                        else:
                            logger.warning(f"Skipping unparseable numeric filter {k}={v}")
                            continue
                else:
                    v_str = str(v).strip().lower()
                    if k in ['dietaryrestriction', 'excludedietaryrestriction']:
                        v_str = DIETARY_CANONICAL_MAP.get(v_str, v_str)
                    safe_v = v_str.replace("'", "\\'")
                    query += f", applyFilter('{k}', '{safe_v}', R{var_idx}, R{var_idx+1})"
                var_idx += 1
            
        try:
            res = list(self.prolog.query(query))
            if res:
                return [r.decode('utf-8') if isinstance(r, bytes) else str(r) for r in res[0][f'R{var_idx}']]
        except Exception as e:
            logger.error(f"Prolog query failed: {e}")
        return []

    def get_recipe_json(self, recipe_id):
        try:
            res = list(self.prolog.query(f"recipe_to_json('{recipe_id}', JSON)"))
            if res:
                json_val = res[0]['JSON']
                return json_val.decode('utf-8') if isinstance(json_val, bytes) else str(json_val)
        except Exception as e:
            logger.error(f"Prolog get_recipe_json failed: {e}")
        return "{}"

    def get_recipes_json(self, recipe_ids):
        ids_str = "[" + ",".join([f"'{rid}'" for rid in recipe_ids]) + "]"
        try:
            res = list(self.prolog.query(f"recipes_to_json({ids_str}, JSON)"))
            if res:
                json_val = res[0]['JSON']
                return json_val.decode('utf-8') if isinstance(json_val, bytes) else str(json_val)
        except Exception as e:
            logger.error(f"Prolog get_recipes_json failed: {e}")
        return "[]"

    def get_speech_examples(self, agent_intent, state_vars):
        try:
            # Assert state variables in Prolog so that conditional text generation works
            list(self.prolog.query("retractall(recipesFiltered(_))"))
            list(self.prolog.query("retractall(currentRecipe(_))"))
            
            recipes_count = state_vars.get('recipe_counter', 0)
            dummy_list = "[" + ",".join(["1"] * min(recipes_count, 1000)) + "]"
            list(self.prolog.query(f"assertz(recipesFiltered({dummy_list}))"))
            
            if state_vars.get('last_sent_recipe'):
                list(self.prolog.query(f"assertz(currentRecipe('{state_vars['last_sent_recipe']}'))"))
                
            lookup_intents = [agent_intent]
            if agent_intent in AGENT_INTENT_ALIAS_MAP:
                lookup_intents.append(AGENT_INTENT_ALIAS_MAP[agent_intent])

            examples = []
            for intent_name in lookup_intents:
                query = f"text({intent_name}, Txt)"
                try:
                    res = list(self.prolog.query(query))
                    examples.extend([r['Txt'].decode('utf-8') if isinstance(r['Txt'], bytes) else str(r['Txt']) for r in res])
                except Exception:
                    pass

                query_pattern = f"text(_, {intent_name}, Txt)"
                try:
                    res_pattern = list(self.prolog.query(query_pattern))
                    examples.extend([r['Txt'].decode('utf-8') if isinstance(r['Txt'], bytes) else str(r['Txt']) for r in res_pattern])
                except Exception:
                    pass

            return list(set(examples))
        except Exception as e:
            logger.error(f"Prolog text query failed for {agent_intent}: {e}")
            return []
