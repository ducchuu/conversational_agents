%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Dialogue logic		                                			%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
:- dynamic
	% An agenda/1 is a list of pattern names that the agent should use in that order to complete
	% its interaction agenda with a user.
	agenda/1,
	% event
	answer/1,
	% Keep track of current pattern for communicating changes to webserver
	currentPattern/1,
	% predicate to record that some event happened
	eventHappened/0,
	% Flag predicate is used to handle repeated button pressing.
	flag/1,
	% Flag to keep track of whether we are listening or not
	listening/0,
	% The initial agenda set at the start of a conversation is stored using the initialAgenda/1
	% predicate, i.e. this predicate stores a copy of the agenda at the start of a session.
	initialAgenda/1,
	% The session/1 history is a list of sequences. Initially this is the empty list. There are
	% a number of constraints on the session history:
	% - only the sequence at the head of the list can be incomplete (but need not be);
	% - the first element of a sequence is a pattern id;
	% - the other elements of a sequence are either
	%   (a) intent triples of the form [actor, intent, parameters] with actor either
	% 	'user' or 'agent', or
	%   (b) subsequences of the form [pattern id, ...] with pattern id a label (constant) and
	%       ... a list of intent triples and subsequences;
	% - a (sub)sequence is (in)complete if its sublist of intent triples (does not) matches the
	%   intent triples of its associated pattern (references by the pattern id).
	session/1,
	steps/2,
	% bot is talking
	talking/0,
	% it's the user's turn to say something
	userTurn/0.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Memory: a memory is a list of entity key, value pairs  %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% The memory/1 predicate is a store for recording user parameter input (entity key-value pairs).
:- dynamic memory/1.

% Retrieves a value for an entity parameter (or key) (and make sure values are all lower case).
memoryKeyValue(EntityKey, EntityValue) :-
	% use of selectchk instead of member to make sure we pick the first value that matches
	memory(Params), member(EntityKey = EntityValue, Params).

memoryFirstKeyValue(EntityKey, EntityValue) :-
	% use of selectchk instead of member to make sure we pick the first value that matches
	memory(Params), selectchk(EntityKey = EntityValue, Params, _).

% getValues predicate: collect all values for one and the same parameter name
getValues(ParamName, Values) :-
	memory(Params), getValues(ParamName, Params, Values).

getValues(_, [], []).
getValues(ParamName, [ ParamName = Value | Params ], [ Value | Values]) :-
	getValues(ParamName, Params, Values).
getValues(ParamName, [ OtherParam = _ | Params ], Values) :-
	ParamName \= OtherParam, getValues(ParamName, Params, Values).

% Returns an entity list with items of the form entityName=entityValue pairs.
% First 'unravels' entity values that are lists; this operation is entity specific so see
% dialogflow.pl for definition.
% Second remove all entities that are empty or contain empty values
cleanParams(Params, CleanedParams) :-
	% first unravel
	unravel(Params, UnRavelled),
	% then remove the empty entities
	removeEmpty(UnRavelled, CleanedParams).

% Removes empty key-value pairs from the given list, i.e., all keys that are empty are
% removed.
removeEmpty([], []).
% remove empty values
removeEmpty([ _ = '' | Pairs ], PairsOut) :-
	removeEmpty(Pairs, PairsOut), !.
removeEmpty([ _ = [] | Pairs ], PairsOut) :-
	removeEmpty(Pairs, PairsOut), !.
% keep non-empty values (all empty values are removed by previous clauses)
removeEmpty([ Key = Value | Pairs ], [ Key = Value | PairsOut ]) :-
	removeEmpty(Pairs, PairsOut).

% updateMemory/3 is a helper predicate for memory updates.
% updateMemory(+NewParams, -OldMemory, -NewMemory)
%
% Assumes that NewParams have been cleaned and unravelled (see cleanParams/2).
%
% @NewParams: list of entity key-value pairs of the form [key1 = value1, key2 = value2 , ...]
% @OldMemory: old memory = list of entity key-value pairs
% @NewMemory: updated memory with new parameters
updateMemory(NewParams, OldMemory, NewMemory) :-
	memory(OldMemory),
	updateWithNewParameters(NewParams, OldMemory, NewMemory).

% updateWithNewParameters predicate
% empty list of parameters does not change memory
updateWithNewParameters([], Memory, Memory).
% parameter is not yet present in memory, or should NOT be overwritten, or is already in
% the memory, then add it, that is, when the parameter is not special.
updateWithNewParameters([ Key = Value | OtherParams], OldMemory, [ Key = Value | NewMemory]) :-
	not(member(Key=Value, OldMemory)),
	( not(member(Key=_, OldMemory)) ; doNotOverwriteThisKey(Key)),
	% recursively update with remaining parameters, if any
	updateWithNewParameters(OtherParams, OldMemory , NewMemory).
% overwrite existing parameters with new values (if they should be overwritten)
updateWithNewParameters([ Key = Value | OtherParams], OldMemory, [ Key = Value | NewMemory]) :-
	member(Key=_, OldMemory),
	overwriteParam(Key, Value),
	select(Key=_, OldMemory, OldParamRemoved),
	% recursively update with remaining parameters, if any
	updateWithNewParameters(OtherParams, OldParamRemoved, NewMemory).

% A Parameter can be overwritten if it is not one of the special filter types
overwriteParam(Key, _) :- not(doNotOverwriteThisKey(Key)).
doNotOverwriteThisKey(Key) :-
	member(Key, ['ingredient', 'ingredienttype', 'tag', 'excludeingredienttype',
		'excludeingredient', 'dietaryrestriction']), !.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Behavioral parameters                                  %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
:- dynamic
	% the name of the dialog agent.
	agentName/1,
	% indicates whether the agent should perform a last topic check at the end of a session.
	lastTopicCheck/0.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Administrative predicates                              %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
:- dynamic
	% used to identify slots (entity parameters) that have not been filled yet.
	missingSlots/1,
	% stepCounter/1 is used to implement the repeat(SubPattern) agenda instruction. This counter
	% counts steps performed when executing this instruction and is initialized to -1 to
	% indicate that the stepCounter has not been used yet.
	stepCounter/1,
	% totalSteps/1 is used to set the target total number of steps to perform when the repeat
	% agenda instruction is executed.
	totalSteps/1,
	% Predicates for monitoring end of (audio) events (used for related percept handling).
	event/1, waitingForEvent/1.

% Retrieve the current top level pattern id
currentTopLevel(PatternId) :- session([[PatternId | _] | _]), !.
% First sequence in session must be empty, assume conversation has been terminated.
currentTopLevel(terminated).

% Retrieve the currently active sequence
currentlyActiveSequence(Sequence) :-
	currentlyActiveSequences([ Sequence | _ ]).

% only a pattern id, no intents yet added
currentlyActivePattern(Seq, Seq) :-
	last(Seq, Sub), not(is_list(Sub)), !.
% intent triple
currentlyActivePattern(Seq, Seq) :-
	last(Seq, Sub), intentTriple(Sub), !.
% subsequence
currentlyActivePattern(Seq, Pattern) :-
	% not an intent triple, must be a subsequence (based on a pattern)
	last(Seq, Sub), currentlyActivePattern(Sub, Pattern).


% Retrieve parent of currently active pattern (topLevel if pattern is at topLevel)
parent(PatternId, ParentId) :-
	currentlyActiveSequenceStack([ [ PatternId | _ ], [ ParentId | _ ] | _]) ;
	currentlyActiveSequenceStack([ [ ParentId | _ ] ]).

% Get the sequence without the currently active pattern (to ignore b12 and b13) Broken
parentSequence(PatternId, [ParentId | ParentSequence]) :-
	currentlyActiveSequenceStack([ [ PatternId | _ ], [ParentId | ParentSequence] | _]) ;
	currentlyActiveSequenceStack([ [ ParentId | ParentSequence ] ]).

% Active pattern sequence stack
currentlyActiveSequenceStack(ActiveSequenceStack) :-
	session([ S | _ ]),
	currentlyActiveSequenceStack(S, [], ActiveSequenceStack).

% -CurrentList (must be instantiated)
currentlyActiveSequenceStack([], CurrentList, CurrentList).
currentlyActiveSequenceStack(IntentTriple, CurrentList, SequenceList) :-
	intentTriple(IntentTriple),
	currentlyActiveSequenceStack([], CurrentList, SequenceList), !.
currentlyActiveSequenceStack([ PatternId | Sequence ], CurrentList, SequenceList) :-
	not(is_list(PatternId)), % must be a pattern id
	getIntentTriples(Sequence, IntentTriples),
	currentlyActiveSequenceStack(Sequence, [ [ PatternId | IntentTriples ] | CurrentList], SequenceList).
currentlyActiveSequenceStack([ IntentTriple | Sequence ], CurrentList, SequenceList) :-
	intentTriple(IntentTriple), last([ IntentTriple | Sequence ], SubSequence),
	currentlyActiveSequenceStack(SubSequence, CurrentList, SequenceList).

% Returns only the non-completed sequences
currentlyActiveSequences(ActiveSequences) :-
	currentlyActiveSequenceStack(Sequences),
	currentlyActiveSequences(Sequences, ActiveSequences).

%
currentlyActiveSequences([], []).
currentlyActiveSequences([Seq | Rest], ActiveSequences) :-
	completedPattern(Seq), % completed pattern
	currentlyActiveSequences(Rest, ActiveSequences).
currentlyActiveSequences([Seq | Rest], [Seq | ActiveSequences]) :-
	not(completedPattern(Seq)), % not completed pattern
	currentlyActiveSequences(Rest, ActiveSequences).

% The getParamsPatternInitiatingIntent predicate retrieves the parameters associated with
% the intent that initiated the pattern (i.e., the first intent of the pattern).
getParamsPatternInitiatingIntent(Actor, Intent, Params) :-
	% either the pattern initiating intent is still available (before the pattern has
	% been instantiated),
	intent(Intent, Params, _, _, _) ;
	% or: we look for the first sequence in the currently active stack that we can find
	% that starts with the [Actor, Intent] pair; we cannot use the
	% currentlyActiveSequences/1 or currentlyActiveSequence/1 predicates because these
	% use this getParamsPatternInitiatingIntent/3 predicate (implicitly through calling
	% pattern/1), which would create an infinite cycle.
	getParamsFromFirstMatchingSequence(Actor, Intent, Params).


% Instantiate -Actor and -Intent
getParamsFromFirstMatchingSequence(Actor, Intent, Params) :-
	currentlyActiveSequenceStack(SeqStack),
	getParamsFromFirstMatchingSequence(SeqStack, Actor, Intent, Params).

getParamsFromFirstMatchingSequence([], _, _, _) :- fail.
getParamsFromFirstMatchingSequence([ [ _, [ Actor, Intent, Params ] | _ ] | _ ],
	Actor, Intent, Params) :- !. % we stop searching after match with first sequence
getParamsFromFirstMatchingSequence([ _ | Sequences ], Actor, Intent, Params) :-
	getParamsFromFirstMatchingSequence(Sequences, Actor, Intent, Params).

% If there is a waiting for event then bot should wait for user response
waiting :- waitingForEvent(_).
% Waiting for a button other than the talk (mic) button; add any buttons that
% you use here; we now only use the 'start' button on the initial page.
waitingForButtonOtherThanMic :- waitingForEvent('start').

/**
 * missingSlots(+Params, -Missing)
 *
 * Identifies any empty slots in parameters (of intent triple) that cannot be retrieved from memory
 * either.
 *
 * @param Params: list of the form [param1 = .., param2 = .., ...].
 * @param Missing: list of missing parameters (slots) of the form [paramM, paramN, ...].
**/
missingSlots(Params, Missing) :-
	findall(Key, member(Key = '', Params), EmptyKeys),
	memory(Memory), findall(Key, member(Key=_, Memory), Keys),
	subtract(EmptyKeys, Keys, Missing).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Sequence handling			                   %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% A list that is part of a session is a sequence if it starts with a pattern id
% (i.e. constant that is not 'agent' or 'user')
sequence([H | _]) :- not(is_list(H)), not(H = agent), not(H = user).

/**
 * add(+Sequence, +Item, UpdatedSequence).
 *
 * Adds a given item to a given sequence. Adds the item to the the currently active and
 * incomplete (sub)sequence.
 *
 * @param Sequence A sequence, i.e. a list starting with a pattern id (head) followed by intent
 *			triples and subsequences (not the complete session history!).
 * @param Item To be added. Should be either an intent triple of the form
 *		[Actor, Intent, Parameters], or a sequence consisting of a pattern name of
 *		the form [PatternId].
 * @param UpdatedSequence The given sequence updated by adding the item.
**/
% Definition by induction on the structure of a sequence.
% Case of completed subsequence as last element of sequence.
add([SubSequence], Item, NewSequence) :-
	completedPattern(SubSequence), append([SubSequence], [Item], NewSequence).
% Case of incomplete subsequence as last element of sequence.
% Add intent triple to this subsequence because by assumption it should match associated
% pattern.
add([SubSequence], Item, [NewSubSequence]) :-
	sequence(SubSequence), not(completedPattern(SubSequence)),
	add(SubSequence, Item, NewSubSequence).
% Case of single pattern id.
add([PatternId], Item, NewSequence) :-
	not(is_list(PatternId)),
	append([PatternId], [Item], NewSequence).
% Case of single intent triple.
add([IntentTriple], Item, NewSequence) :-
	intentTriple(IntentTriple), append([IntentTriple], [Item], NewSequence).
% Case where there are at least two elements in the sequence (where first element can also
% be a pattern id but does not need to be).
add([El1, El2 | Sequence], Item, [El1 | NewSequence]) :-
	add([El2 | Sequence], Item, NewSequence).

% Check if sequence is complete by matching it against associated pattern.
completedPattern([PatternId | Sequence]) :-
	getActorIntentPairs(Sequence, ActorIntentPairs),
	pattern([ PatternId | PatternSequence ]),
	append(ActorIntentPairs, [], PatternSequence).

% Find pattern where first intent matches given intent.
% Pattern b13 for handling out of context dialog moves where first user intent matches any intent
% must be excluded
matchingPattern(Actor, Intent, PatternId) :-
	pattern([ PatternId, [Actor, Intent] | _ ]),
	not(PatternId = b13),
	not(PatternId = b14).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Compute expected intent		                   %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

/**
 * expectedIntent(-Actor, -Intent).
 *
 * Infer the actor and intent that are expected next from the (variant of the) pattern associated
 * with the currently active (sub)sequence and the intent triples part of that sequence;
 * uses the fact that only the sequence at the head of a session can be incomplete (but need not be).
 *
 * @param Actor Either 'agent' or 'user', whoever is expected to contribute to the interaction next.
 * @param Intent The intent (label) that is expected next.
**/
expectedIntent(Actor, Intent) :-
	currentlyActiveSequence([ PatternId | Sequence ]),
	getActorIntentPairs(Sequence, ActorIntentPairs),
	pattern([ PatternId | PatternSequence ]),
	append(ActorIntentPairs, [ [Actor, Intent] | _ ], PatternSequence).

% expectedIntent(Actor, Intent) :- session([ Sequence | _ ]), expectedIntent(Sequence, Actor, Intent).

/**
 * expectedIntent(+Sequence, -Actor, -Intent).
 *
 * Helper predicate to implement expectedIntent(-Actor, -Intent).
 *
 * @param Sequence The currently active sequence (at the head of the session history).
 * @param Actor Either 'agent' or 'user', whoever is expected to contribute to the interaction next.
 * @param Intent The intent (label) that is expected next.
**/
% First, compute the expected actor-intent pair for the case where the last sequence
% element is a subsequence (starting with a pattern id constant); if such a pair is found,
% stop searching (cut).
expectedIntent(Sequence, Actor, Intent) :-
	last(Sequence, [ PatternId | SubSequence ]),
	not(is_list(PatternId)), not(PatternId=user), not(PatternId=agent),
	expectedIntent([PatternId | SubSequence], Actor, Intent).
% Second, compute the expected actor-intent pair by matching the list of actor-intent pairs (ignoring
% any entity key-value pairs) in the given sequence with its associated pattern.
expectedIntent([ PatternId | Sequence ], Actor, Intent) :-
	getActorIntentPairs(Sequence, ActorIntentPairs),
	pattern([ PatternId | PatternSequence ]),
	append(ActorIntentPairs, [ [Actor, Intent] | _ ], PatternSequence).

% Retrieves the intent triples from a given sequence; in other words, removes all
% expansions (subsequences).
getIntentTriples([], []).
getIntentTriples([ IntentTriple | Sequence ], [ IntentTriple | IntentTriples ]) :-
	intentTriple(IntentTriple), getIntentTriples(Sequence, IntentTriples).
getIntentTriples([ Head | Sequence ], ActorIntentPairs) :-
	not(intentTriple(Head)), % must be pattern id or expansion
	getIntentTriples(Sequence, ActorIntentPairs).

% Extract (actor, intent) pairs from a given sequence;
% remove parameters from intent triples and remove subsequences.
getActorIntentPairs([], []).
getActorIntentPairs([ [Actor, Intent, _ ] | Sequence ], [ [Actor, Intent] | ActorIntentPairs ]) :-
	intentTriple([Actor, Intent, _]), getActorIntentPairs(Sequence, ActorIntentPairs).
getActorIntentPairs([ Head | Sequence ], ActorIntentPairs) :-
	not(intentTriple(Head)), getActorIntentPairs(Sequence, ActorIntentPairs).

% Check if a sequence element is an intent triple (list of three items starting with 'agent' or 'user')
intentTriple([user, _, _]).
intentTriple([agent, _, _]).


% When is a button disabled?
% Mic button is disabled on the initial screen when we are waiting for the Start button.
disabled('mic') :- waitingForEvent('start').
% Mic button is disabled when we are already listening and when we're still waiting for
% results from intention detection.
disabled('mic') :- listening.
% All buttons are disabled when the bot is talking (keeps things simple and is polite).
disabled(_) :- talking.
% Any button is disabled if it is flagged.
disabled(Button) :- flag(Button).


/**
 * lastAddedIntentTriple(-IntentTriple)
 *
 * Retrieves the intent that has been added last to the currently active (sub)sequence in the
 * session history.
 *
 * @param IntentTriple The intent triple that was added last to the session history.
**/
lastAddedIntentTriple(IntentTriple) :-
	session([ Sequence | _ ]), lastAddedIntentTriple(Sequence, IntentTriple).

/**
 * lastAddedIntentTriple(+Sequence, -IntentTriple)
 *
 * Retrieves the intent that has been added last to the sequence.
 *
 * @param Sequence A list representing part of a sequence (a list starting with a pattern id).
 * @param IntentTriple The intent triple that was added last to the session history.
**/
% Definition by induction on the structure of a sequence.
% Case single pattern id: in this case, there has not been any intent added, so fail.
lastAddedIntentTriple([PatternId], _) :- not(is_list(PatternId)), fail.
% Case single intent triple:
lastAddedIntentTriple([IntentTriple], IntentTriple) :-
	intentTriple(IntentTriple).
% Case subsequence:
lastAddedIntentTriple([SubSequence], IntentTriple) :- is_list(SubSequence),
	lastAddedIntentTriple(SubSequence, IntentTriple).
% Case where there are at least two elements in the sequence (where first element can also be
% a pattern id):
lastAddedIntentTriple([_, El2 | Sequence], IntentTriple) :-
	lastAddedIntentTriple([El2 | Sequence], IntentTriple).


/**
 * removeEmptyParams(+Params, -NonEmptyParams)
 *
 * Removes key-value pairs from Params where value is empty (= '').
 *
 * @param Params: list of entity key-value pairs of the form [key1 = value1, key2 = value2 , ...],
 * 			possibly with key = '' (empty parameters).
 * @param NonEmptyParams: list of only those entity key-value pairs with non-empty value (not '').
**/
removeEmptyParams([], []).
removeEmptyParams([Key = Value | OldParams], [Key = Value | CleanedParams]) :-
	not(Value = ''), not(Value = []),
	removeEmptyParams(OldParams, CleanedParams).
removeEmptyParams([_ = '' | OldParams], CleanedParams) :-
	removeEmptyParams(OldParams, CleanedParams).
removeEmptyParams([_ = [] | OldParams], CleanedParams) :-
	removeEmptyParams(OldParams, CleanedParams).

/**
 * remove(+Params, +OldParams, -NewParams)
 *
 * Removes all ParamName-Value pairs from Params from the list of such pairs in OldParams
 * and returns the updated list in NewParams. Each of the these is a list of the form
 * [paramName1 = value1, paramName2 = value2 , ...], where ParamName is an intent parameter
 * name.
 *
 * @param Params: list of ParamName-Value pairs.
 * @param OldParams: list of ParamName-Value pairs.
 * @param NewParams: list of ParamName-Value pairs from OldParams where all such pairs from
 * 	Params have been removed.
**/
remove(_, [], []).
remove(Params, [ ParamName = Value | OldParams ], [ ParamName = Value | NewParams]) :-
	not(member(ParamName = Value, Params)), remove(Params, OldParams, NewParams).
remove(Params, [ ParamName = Value | OldParams], NewParams) :-
	member(ParamName = Value, Params), remove(Params, OldParams, NewParams).

/**
 * removeParam(+ParamName, +OldParams, -NewParams)
 *
 * Removes all ParamName-Value pairs from Params from the list of such pairs in OldParams
 * and returns the updated list in NewParams. Each of the these is a list of the form
 * [paramName1 = value1, paramName2 = value2 , ...], where ParamName is an intent parameter
 * name.
 *
 * @param ParamName: a value of a parameter.
 * @param OldParams: list of ParamName-Value pairs.
 * @param NewParams: list of ParamName-Value pairs from OldParams where all such pairs from
 * 	Params have been removed.
**/
removeParam(_, [], []).
    removeParam(Param, [ ParamName = _ | OldParams], NewParams) :-
    	same_param(Param, ParamName), removeParam(ParamName, OldParams, NewParams).
    removeParam(Param, [ ParamName = Value | OldParams ], [ ParamName = Value | NewParams]) :-
    	not(same_param(Param, ParamName)),
    	removeParam(Param, OldParams, NewParams).
    	
    removeParams([], OldMemory, OldMemory).
    removeParams(_=Value, OldMemory, NewMemory) :- 
        removeParam(Value, OldMemory, NewMemory).
    removeParams([_=Value|RestValues], OldMemory, NewerMemory) :-
        removeParam(Value, OldMemory, NewMemory),
        removeParams(RestValues, NewMemory, NewerMemory).
    
    /**
     * removeValue(+Value, +OldParams, -NewParams)
     *
     * Removes all ParamName-Value pairs from Params from the list of such pairs in OldParams
     * and returns the updated list in NewParams. Each of the these is a list of the form
     * [paramName1 = value1, paramName2 = value2 , ...], where ParamName is an intent parameter
     * name.
     *
     * @param Value: a value of a parameter.
     * @param OldParams: list of ParamName-Value pairs.
     * @param NewParams: list of ParamName-Value pairs from OldParams where all such pairs from
     * 	Params have been removed.
    **/
    
    removeValue(_, [], []).
    removeValue(DifferentValue, [ ParamName = Value | OldParams ], [ ParamName = Value | NewParams]) :-
    	not(DifferentValue = Value), removeValue(DifferentValue, OldParams, NewParams).
    removeValue(Value, [ _ = Value | OldParams], NewParams) :-
    	removeValue(Value, OldParams, NewParams).
    	
    removeValues([], OldMemory, OldMemory).
    removeValues(_=Value, OldMemory, NewMemory) :- 
        removeValue(Value, OldMemory, NewMemory).
    removeValues([_=Value|RestValues], OldMemory, NewerMemory) :-
        removeValue(Value, OldMemory, NewMemory),
        removeValues(RestValues, NewMemory, NewerMemory).

/**
 * retrieveIntentsfromPatterns(+Actor:atom, -Intents:list)
 *
 * Retrieves all intents for an actor (agent or user) from available patterns. Excludes 
 * non-atom intents (i.e. variables).
 *
 * @Actor	Instantiate with either 'user' or 'agent'
 * @Intents	List of intent labels.
**/
% 
retrieveIntentsfromPatterns(Actor, Intents) :-
	setof(Intent,
		(pattern(Pattern), member([Actor, Intent], Pattern), atom(Intent)),
		Intents).