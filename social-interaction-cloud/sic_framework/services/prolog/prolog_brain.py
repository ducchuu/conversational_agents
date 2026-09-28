import asyncio
import logging
from pyswip import Prolog

logger = logging.getLogger(__name__)

class PrologBrain:
    """
    Python interface to Prolog using pyswip. 
    This replaces the MARBEL architecture and directly queries a Prolog Knowledge Base.
    """
    def __init__(self, kb_path: str = None):
        self.prolog = Prolog()
        if kb_path:
            self.load_knowledge_base(kb_path)
            
    def load_knowledge_base(self, path: str):
        logger.info(f"Loading Prolog knowledge base from {path}")
        self.prolog.consult(path)
        
    def assert_fact(self, fact: str):
        """Assert a new fact into the Prolog knowledge base (e.g., transcript('hello'))"""
        logger.debug(f"Asserting fact: {fact}")
        self.prolog.assertz(fact)
        
    def retract_fact(self, fact: str):
        """Remove a fact from the knowledge base"""
        logger.debug(f"Retracting fact: {fact}")
        self.prolog.retract(fact)
        
    def query(self, query_str: str):
        """Run a synchronous query against Prolog"""
        logger.debug(f"Querying: {query_str}")
        return list(self.prolog.query(query_str))

    async def async_query(self, query_str: str):
        """
        Run Prolog queries in a threadpool to prevent blocking the async event loop.
        Useful when integrated with async frameworks like FastAPI or async SocketIO.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.query, query_str)

    async def process_intent(self, intent_name: str, entities: dict):
        """
        Example pipeline: Receives an intent from NLU, asserts it to Prolog, 
        queries for the next action, and returns the action to be executed by the web server.
        """
        # Convert intent and entities to a Prolog readable fact
        # e.g., intent('recipe_search', ['chicken']).
        entities_list = [f"'{k}={v}'" for k, v in entities.items()]
        entities_str = f"[{','.join(entities_list)}]"
        fact = f"intent('{intent_name}', {entities_str})"
        
        self.assert_fact(fact)
        
        # Query for the next action from Prolog
        # Assuming you have a Prolog rule: next_action(Action) :- intent(X, Y), ...
        actions = await self.async_query("next_action(Action)")
        
        # After processing, you might want to retract the fact or keep it in history
        # self.retract_fact(fact)
        
        return actions
