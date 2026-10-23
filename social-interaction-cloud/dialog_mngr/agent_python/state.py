MULTI_VALUE_FILTER_KEYS = frozenset({
    'ingredient', 'ingredients',
    'ingredienttype', 'ingredient_type',
    'tag', 'tags',
    'excludeingredient', 'exclude_ingredient', 'excludeingredients',
    'excludeingredienttype', 'exclude_ingredient_type',
    'dietaryrestriction', 'dietary_restriction',
    'excludedietaryrestriction', 'exclude_dietary_restriction',
})

class DialogState:
    # Memory keys that are bookkeeping, not user-visible search filters.
    NON_FILTER_KEYS = frozenset({'exclude_recipe'})

    def __init__(self):
        self.memory = {}
        self.state = 'start'
        self.last_sent_recipe = None
        self.recipe_counter = 0
        self.pending_speech = None
        # Ordered recipe IDs matching the current filters (same order as shown in the UI list)
        self.current_candidates = []
        # Chronological (memory_key, added_value) records so "undo the last filter" is possible
        self.filter_history = []

    def reset(self):
        self.memory = {}
        self.state = 'start'
        self.last_sent_recipe = None
        self.recipe_counter = 0
        self.pending_speech = None
        self.current_candidates = []
        self.filter_history = []

    def clear_filters(self):
        """Clear every user filter but keep session state and the rejected-recipe list."""
        self.memory = {k: v for k, v in self.memory.items() if k in self.NON_FILTER_KEYS}
        self.filter_history = []

    def pop_last_filter(self):
        """Remove only the most recently added filter. Returns the (key, value) removed, or None."""
        while self.filter_history:
            key, value = self.filter_history.pop()
            if key not in self.memory:
                continue
            current = self.memory[key]
            if isinstance(current, list):
                for item in (value if isinstance(value, list) else [value]):
                    if item in current:
                        current.remove(item)
                if not current:
                    del self.memory[key]
            else:
                del self.memory[key]
            return key, value
        # No history (e.g. filters restored elsewhere): fall back to the newest user filter key
        user_keys = [k for k in self.memory if k not in self.NON_FILTER_KEYS]
        if user_keys:
            key = user_keys[-1]
            return key, self.memory.pop(key)
        return None

    def reject_recipe(self, recipe_id):
        """Accumulate rejected recipe IDs across turns (unique, insertion-ordered)."""
        if not recipe_id:
            return
        excluded = self.memory.get('exclude_recipe', [])
        if not isinstance(excluded, list):
            excluded = [excluded]
        recipe_id = str(recipe_id)
        if recipe_id not in excluded:
            excluded.append(recipe_id)
        self.memory['exclude_recipe'] = excluded

    def add_filters(self, filters):
        if not filters:
            return
        for k, v in filters.items():
            if not v:
                continue
            k_norm = k.replace('_', '').lower()
            if k_norm in {'userquery', 'query', 'rawtranscript'}:
                continue
            if k_norm in MULTI_VALUE_FILTER_KEYS:
                # Find if key already present in memory under any case
                target_key = k
                for mk in self.memory.keys():
                    if mk.replace('_', '').lower() == k_norm:
                        target_key = mk
                        break
                
                existing = self.memory.get(target_key)
                if existing is not None:
                    if not isinstance(existing, list):
                        existing = [existing]
                    new_items = v if isinstance(v, list) else [v]
                    for item in new_items:
                        if item not in existing:
                            existing.append(item)
                    self.memory[target_key] = existing
                    self.filter_history.append((target_key, v))
                else:
                    self.memory[target_key] = v
                    self.filter_history.append((target_key, v))
            else:
                # Single-value filter (cuisine, duration, servings, mealType): replace existing
                keys_to_remove = [mk for mk in self.memory.keys() if mk.replace('_', '').lower() == k_norm]
                for mk in keys_to_remove:
                    del self.memory[mk]
                self.memory[k] = v
                self.filter_history.append((k, v))

    def delete_filters(self, filters):
        if not filters:
            return
        for k, v in filters.items():
            k_norm = k.replace('_', '').lower()
            v_norm = str(v).lower().strip()
            
            keys_to_delete = []
            for mk, mv in list(self.memory.items()):
                mk_norm = mk.replace('_', '').lower()
                matches_key = (mk_norm == k_norm) or (k_norm in ['filtertype', 'filter'] and mk_norm == v_norm)
                
                if isinstance(mv, list):
                    # Remove matching values from the list
                    remaining = [item for item in mv if str(item).lower().strip() != v_norm]
                    if matches_key and v_norm in ['', 'none', 'all', str(mv).lower().strip()]:
                        remaining = []
                    if not remaining:
                        keys_to_delete.append(mk)
                    else:
                        self.memory[mk] = remaining
                else:
                    if str(mv).lower().strip() == v_norm or matches_key:
                        keys_to_delete.append(mk)

            for mk in keys_to_delete:
                if mk in self.memory:
                    del self.memory[mk]


