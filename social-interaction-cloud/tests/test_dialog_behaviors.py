"""Behavioural regression tests for the DialogManager / DialogState / PrologInterface gap fixes."""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dialog_mngr.agent_python.dialog_manager import DialogManager  # noqa: E402


@pytest.fixture(scope="module")
def dm_module():
    return DialogManager()


@pytest.fixture
def dm(dm_module):
    dm_module.state.reset()
    dm_module._utterance = ""
    yield dm_module
    dm_module.state.reset()


def _cuisine_with_small_list(dm):
    """Find a cuisine whose filtered list is shown in the UI (2..20 recipes)."""
    for cuisine in ("greek", "thai", "mexican", "japanese", "indian", "french", "korean", "spanish", "chinese"):
        ids = dm.prolog.query_recipes({"cuisine": cuisine})
        if 2 <= len(ids) <= 20:
            return cuisine, ids
    pytest.skip("no cuisine with 2..20 recipes in the knowledge base")


def test_clear_all_filters_keeps_session_in_overview(dm):
    dm.state.state = "recipe_overview"
    dm.state.memory = {"cuisine": "italian", "ingredient": ["garlic"]}
    dm._process_intent_sync("deleteParameter", {}, utterance="clear all filters")
    assert dm.state.memory == {}
    assert dm.state.state in ("recipe_overview", "recipe_overview2")  # not reset to welcome/start


def test_clear_all_filters_with_all_marker(dm):
    dm.state.state = "recipe_overview"
    dm.state.memory = {"cuisine": "italian"}
    dm._process_intent_sync("deleteParameter", {"filterType": "all"}, utterance="reset my filters")
    assert dm.state.memory == {}


def test_delete_parameter_with_filter_type_only_removes_that_category(dm):
    dm.state.state = "recipe_overview"
    dm.state.memory = {"cuisine": "italian", "duration": "30"}
    dm._process_intent_sync("deleteParameter", {"filterType": "cuisine"}, utterance="remove the cuisine filter")
    assert "cuisine" not in dm.state.memory
    assert dm.state.memory.get("duration") == "30"


def test_undo_last_filter_pops_only_most_recent(dm):
    dm.state.state = "recipe_overview"
    dm._process_intent_sync("addFilter", {"cuisine": "italian"}, utterance="italian")
    dm._process_intent_sync("addFilter", {"duration": "30"}, utterance="under 30 minutes")
    dm._process_intent_sync("deleteParameter", {}, utterance="undo the last filter")
    assert "duration" not in dm.state.memory
    assert dm.state.memory.get("cuisine") == "italian"


def test_ordinal_recipe_request_selects_that_candidate(dm):
    cuisine, ids = _cuisine_with_small_list(dm)
    dm.state.state = "recipe_overview2"
    dm.state.memory = {"cuisine": cuisine}
    dm._process_intent_sync("recipeRequest", {}, utterance="I want the second recipe")
    assert dm.state.state == "recipe_confirmation"
    assert dm.state.last_sent_recipe == ids[1]

    dm.state.state = "recipe_overview2"
    dm._process_intent_sync("recipeRequest", {}, utterance="open the last one")
    assert dm.state.last_sent_recipe == ids[-1]


def test_quickest_pick_returns_minimum_cooking_time(dm):
    ids = dm.prolog.query_recipes({})
    assert dm.prolog.recipe_times, "time/2 facts should be cached"
    quickest = dm.prolog.get_quickest_recipe(ids)
    assert dm.prolog.recipe_times[quickest] == min(dm.prolog.recipe_times[i] for i in ids if i in dm.prolog.recipe_times)

    dm.state.state = "welcome"
    dm._process_intent_sync("requestRecommendation", {}, utterance="pick the quickest one")
    assert dm.state.state == "recipe_confirmation"
    assert dm.state.last_sent_recipe == quickest


def test_find_another_recipe_excludes_current_recipe(dm):
    dm.state.state = "recipe_confirmation"
    current = dm.prolog.query_recipes({})[0]
    dm.state.last_sent_recipe = current
    dm._process_intent_sync("requestRecommendation", {}, utterance="find another recipe")
    assert current in dm.state.memory["exclude_recipe"]
    assert dm.state.last_sent_recipe != current
    assert dm.state.state == "recipe_confirmation"

