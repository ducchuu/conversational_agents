import pytest
import asyncio
from sic_framework.services.prolog.prolog_brain import PrologBrain

@pytest.fixture
def brain():
    """Fixture to initialize a fresh PrologBrain for each test."""
    return PrologBrain()

def test_assert_and_query_sync(brain):
    """Test standard synchronous asserting and querying."""
    # Assert a dummy fact
    brain.assert_fact("user_said('hello')")
    
    # Query it back
    results = brain.query("user_said(X)")
    
    assert len(results) == 1
    # pyswip returns atoms as strings/bytes depending on version, 
    # check that X matches 'hello'
    assert results[0]['X'] == b'hello' or results[0]['X'] == 'hello'

@pytest.mark.asyncio
async def test_async_query(brain):
    """Test the async threadpool query method."""
    brain.assert_fact("intent('search_recipe', ['chicken'])")
    
    # Query asynchronously
    results = await brain.async_query("intent(Action, Entities)")
    
    assert len(results) == 1
    assert results[0]['Action'] == b'search_recipe' or results[0]['Action'] == 'search_recipe'

def test_retract_fact(brain):
    """Test retracting a fact."""
    brain.assert_fact("active_recipe('10')")
    results = brain.query("active_recipe(X)")
    assert len(results) == 1
    
    brain.retract_fact("active_recipe('10')")
    results = brain.query("active_recipe(X)")
    assert len(results) == 0
