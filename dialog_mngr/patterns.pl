%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Patterns 								 		%%%
%%%											%%%
%%% Organised according to the taxonomy in the book of:					%%%
%%% 	Moore and Arar, 2019, Conversational UX Design:					%%%
%%%	A Practitioner's Guide to the Natural Conversation Framework			%%%
%%% https://doi.org/10.1145/3304087				 			%%%
%%%											%%%							
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

/**
 * pattern(@List)
 *
 * A pattern is a list with the head (the first element) a pattern ID and a tail a list
 * (or sequence) of actor-intent pairs. The idea is that the sequence of actor-intent pairs
 * represents a(n abstract) pattern of actors which are expected to make the consecutive 
 * dialog moves. We identify dialog moves with intents.
 *
 * A simple example is a greeting pattern:
 * 	A: Hello.
 *	U: Hi!
 * where A is the agent (actor) and U is the user (actor). This pattern has code C1.0 in
 * the taxonomy of Moore and Arar, which we represent here as the pattern ID c10.
 * A: hello. is an informal actor-intent pair that we represent as a pair [agent, greeting]
 * in an abstract pattern.
 *
 * The informal greeting pattern example above thus can be represented by the fact:   
 * 	pattern(c10, [agent, greeting], [user, greeting]).
 * See also https://socialrobotics.atlassian.net/l/cp/HKFF8rW0.
 *
 * @List	A list of the form [PatternID, [Actor1, Intent1], ..., [ActorN, IntentN]].
**/

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Conversational Activity Patterns (Moore Ch5)           %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%% A2 Patterns: Open Request

% Pattern A2.4 - Open Request Agent Detail Request
%
% Example: context: cooking a recipe
%	U: how much water do I need?
%	A: for which task?
%	U: for cooking the pasta.
%
% Agent-initiated detail requests are often called “slots” and this pattern “slot filling”.
% The idea is that the agent follows-up with a detailed request for the purpose of slot
% filling after a user made a partial request.
%
% We do not include the partial request of the user in the pattern. The pattern itself has
% a parameter for representing a kind of slot (parameter) that needs to be filled, and use
% the repeat action to continue filling slots until they are all filled.
%
% Generic pattern for slot filling.

pattern([slotFill(X), [agent, repeat(X)]]).

/**
 * slotFill(-Intent, -PatternID)
 *
 * Indicates that PatternID can be used for filling in missing slots for intent Intent.
 *
 * @param Intent	An intent label (which should match a DialogFlow intent).
 * @param PatternID	Pattern ID (which should match a pattern listed in this file).
**/
% Dummy slotFill fact added because at least one such fact needs to be defined.

slotFill(dummyP, dummyI).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Pattern: a21featureRequest								%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Pattern A2.1: Open Request
% Pattern a21featureRequest: user asks for a feature.
% Variant where user requests a feature while already checking a recipe.
% Example:
% 	U: Can you show me a recipe that uses pasta?
%	A: All the recipes left include pasta. Do you want to add another preference?
% Instruction:
%	Add a pattern with pattern ID a21featureRequest here where the user makes a
%	feature request; make sure the context is changed by inserting the a50recipeSelect 
%	pattern again into the session.

pattern([a21featureRequest,
    [user, addFilter],
    [agent, removeConflicts(Params)],
    [agent, ackFilter],
    [agent, insert(a50recipeSelect)] 
]) :-
    currentTopLevel(a50recipeConfirm),
    getParamsPatternInitiatingIntent(user, addFilter, Params),
    not(recipesFiltered([])).


% Variant where user requests a feature while already checking a recipe.
% Example:
% 	U: Can you show me a recipe that uses pasta?
%	A: There are no recipes left. Please remove a feature.
% Instruction:
%	Add a pattern with pattern ID a21featureRequest here where the user makes a
%	feature request; make sure the context is changed by inserting the a50recipeSelect 
%	pattern again into the session.
pattern([a21featureRequest,
    [user, addFilter],
    [agent, removeConflicts(Params)],
    [agent, noRecipesLeft],
    [agent, featureRemovalRequest],
    [agent, insert(a50recipeSelect)]
]) :-
    currentTopLevel(a50recipeConfirm),
    getParamsPatternInitiatingIntent(user, addFilter, Params),
    recipesFiltered([]).


% Variant where user requests a feature while still in the recipe selection context.
% Example:
% 	U: Can you show me a recipe that uses pasta?
%	A: All the recipes left include pasta. Do you want to add another preference?
% Instruction:
%	Add a pattern with pattern ID a21featureRequest here where the user makes a
%	feature request.
pattern([a21featureRequest,
    [user, addFilter],
    [agent, removeConflicts(Params)],
    [agent, ackFilter]
]) :-
    currentTopLevel(a50recipeSelect),
    getParamsPatternInitiatingIntent(user, addFilter, Params),
    not(recipesFiltered([])).

% Variant where user requests a feature while still in the recipe selection context.
% Example:
% 	U: Can you show me a recipe that uses pasta?
%	A: There are no recipes left.
% Instruction:
%	Add a pattern with pattern ID a21featureRequest here where the user makes a
%	feature request.
pattern([a21featureRequest,
    [user, addFilter],
    [agent, removeConflicts(Params)],
    [agent, noRecipesLeft]
]) :-
    currentTopLevel(a50recipeSelect),
    getParamsPatternInitiatingIntent(user, addFilter, Params),
    recipesFiltered([]).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Pattern: a21noMoreFilters								%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Pattern a21noMoreFilters: user indicates they do not want to add more feature requests.
% Variant for when there are 100 or fewer recipes left.
% Example:
% 	U: I don't want to add anything else.
%	A: OK. Here is a list of recipes that you can choose from.
% Instruction:
%	Add a pattern with pattern ID a21noMoreFilters here.

% Variant 1: User is done, and count is <= 100. GRANT the request (enableShow + pictureGranted).
pattern([a21noMoreFilters,
    [user, noMoreFilters],
    [agent, enableShow], 
    [agent, pictureGranted]
]) :-
    currentTopLevel(a50recipeSelect),
    recipesFiltered(Recipes),
    length(Recipes, N),
    N =< 100.

% Variant for when there are more than 100 recipes left.
% Example:
% 	U: I don't want to add anything else.
% 	A: Sorry, there are still too many recipes left to show them all. 
%		Please add more preferences.
% Instruction:
%	Add a pattern with pattern ID a21noMoreFilters here.

% Variant 2: User is done, but count > 100. DENY the request (pictureNotGranted).
pattern([a21noMoreFilters,
    [user, noMoreFilters],
    [agent, pictureNotGranted]
]) :-
    currentTopLevel(a50recipeSelect),
    recipesFiltered(Recipes),
    length(Recipes, N),
    N > 100.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Pattern: a21removeKeyFromMemory							%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%% Handling deleteParameter intent.
% Variant: user wants to delete a specific feature type while already checking a recipe.

pattern([a21removeKeyFromMemory,
	[user, deleteParameter],
	[agent, removeParam(Params)],
	[agent, insert(a50recipeSelect)]])
:-
	parent(a21removeKeyFromMemory, a50recipeConfirm),
	getParamsPatternInitiatingIntent(user, deleteParameter, Params),
	(currentTopLevel(a50recipeSelect);currentTopLevel(a50recipeConfirm)).
	
% Variant: user wants to delete a specific feature type while still in selection phase.

pattern([a21removeKeyFromMemory,
	[user, deleteParameter],
	[agent, removeParam(Params)],
	[agent, featureInquiry] ])
:-
	getParamsPatternInitiatingIntent(user, deleteParameter, Params),
	(currentTopLevel(a50recipeSelect);currentTopLevel(a50recipeConfirm)).
	

%%% Handling deleteFilterValue intent.
% Variant: user wants to delete a specific feature value while already checking a recipe.

pattern([a21removeKeyFromMemory,
	[user, deleteFilterValue],
	
	% remove all filters with Value as value from memory (note this also removes the
	% ...Del filter)
	[agent, removeValue(Params)],
	[agent, insert(a50recipeSelect)] ])
:-
%	only do this pattern if there is a ...Del entity (request to remove a feature)
	parent(a21removeKeyFromMemory, a50recipeConfirm),
	getParamsPatternInitiatingIntent(user, deleteFilterValue, Params),
	(currentTopLevel(a50recipeSelect);currentTopLevel(a50recipeConfirm)).

% Variant: user wants to delete a specific feature value while still in the selection phase.
pattern([a21removeKeyFromMemory,
	[user, deleteFilterValue],
	[agent, removeValue(Params)],
	[agent, featureInquiry] ])
:-
	getParamsPatternInitiatingIntent(user, deleteFilterValue, Params),
	(currentTopLevel(a50recipeSelect);currentTopLevel(a50recipeConfirm)).

pattern([a21removeKeyFromMemory,
	[user, removeAllFilters],
	[agent, clearMemory],
	[agent, insert(a50recipeSelect)]]) :-
	parent(a21removeKeyFromMemory, a50recipeConfirm),
	(currentTopLevel(a50recipeSelect);currentTopLevel(a50recipeConfirm)).

pattern([a21removeKeyFromMemory,
	[user, removeAllFilters],
	[agent, clearMemory],
	[agent, featureInquiry]]) :-
	(currentTopLevel(a50recipeSelect);currentTopLevel(a50recipeConfirm)).
	
	
%%% A5 Patterns: Inquiry (Agent)
% Pattern A5.0: Closed Inquiry (Agent)
% Pattern a50recipeConfirm: ask user to confirm recipe that is presented to them on a page.
% Example:
%	A: goodbye.
%	U: bye.
% Instruction:
%	Add three variants for the recipe confirmation pattern a50recipeConfirm.
% Two variants where user confirms they like the recipe by either a confirmation or
% appreciation intent. For appreciation, agent first says "You're welcome" (b42 style)
% then inserts the closing sequence.

pattern([a50recipeConfirm, [user, confirmation], [agent, insert(c43)]]) :- currentTopLevel(a50recipeConfirm).

pattern([a50recipeConfirm, 
    [user, appreciation], 
    [agent, appreciationReceipt], 
    [agent, insert(c43)] 
]) :-
    currentTopLevel(a50recipeConfirm).

% Variant where user disconfirms, i.e. expresses they do not like the recipe. The
% conversation should move back to the recipe selection stage (a50recipeSelect).

pattern([a50recipeConfirm, [user, disconfirmation], [agent, insert(a50recipeSelect)]]) :- currentTopLevel(a50recipeConfirm).

% Pattern a50recipeSelect: user asks for a recipe.
% Variant where user requests a (random) recommendation.
% Example:
% 	A: What recipe would you like to cook?
%	U: Please, just recommend me something.
%	A: What about ___*.
% Instruction:
%	Add a pattern with pattern ID a50recipeSelect here where the agent asks the user
%	for input on what recipe to select and the user just asks for a recommendation. 

% Pattern a50recipeSelect: user asks for a recipe.
% Variant where user requests a (random) recommendation.
% Example:
% 	A: What recipe would you like to cook?
%	U: Please, just recommend me something.
%	A: What about ___*.
% Instruction:
%	Add a pattern with pattern ID a50recipeSelect here where the agent asks the user
%	for input on what recipe to select and the user just asks for a recommendation. 

pattern([a50recipeSelect,
    [agent, specifyGoal],
    [user, requestRecommendation],
    [agent, recommend],
    [agent, insert(a50recipeConfirm)]
]).

% Pattern a50recipeSelect: user asks for a recipe.
% Variant where user requests a specific recipe by mentioning the recipe's name.
% Example:
% 	A: What recipe would you like to cook?
%	U: I'd like to make an artichoke and pine nut pasta.
%	A: Artichoke and pine nut pasta is a great choice!
% Instruction:
%	Add a pattern with pattern ID a50recipeSelect here where the agent asks the user
%	for input on what recipe to select and the user asks for a specific recipe by name.

pattern([a50recipeSelect,
    [agent, specifyGoal],
    [user, recipeRequest],
    [agent, recipeChoiceReceipt],
    [agent, insert(a50recipeConfirm)]
]).

% Allow recipeRequest directly without requiring specifyGoal first (this is to handle disconfirmation better, as sometimes there were issues when disconfirming with the recipe, the agent did not update the pattern back to a50recipeSelect)
pattern([a50recipeSelect,
    [user, recipeRequest],
    [agent, recipeChoiceReceipt],
    [agent, insert(a50recipeConfirm)]
]).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Sequence Management Patterns (Moore Ch6)               %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%% B1 Patterns: Repair (Agent)
% Pattern B1.2: Paraphrase Request
% Example:
%	U: Have you read the Hobbit?
%	A: What do you mean?
% Instruction:
% 	Add a pattern with pattern ID b12 here where the user expression is not recognized 
%	and the agent responds with a paraphraseRequest to the a fallback intent received.


pattern([b12, [user, fallback], [agent, paraphraseRequest]]).


% Pattern B1.3: Out of context dialog move
% Example:
%	A: What recipe would you like to cook?
%	U: Hey there.
%	A: I am not sure what that means in this context.
% Instruction:
% 	Add a pattern with pattern ID b13 here where the user expression is recognized as
%	an out of context Intent and the agent responds with a contextMismatch(Intent) to
%	this intent.

pattern([b13, [user, Intent], [agent, contextMismatch(Intent)]]).



% Looks like user has repeated themselves b14.


%%% B4: Sequence Closers
% Pattern B4.2: Sequence Closer Appreciation (helped)
% Example:
%	U: Thanks!
%	A: You're welcome.
% Instruction:
% 	Add a pattern with pattern ID b42 here where the users expresses appreciation first
%	and the agent let's the user know it received this appreciation well.
pattern([b42, 
    [user, appreciation], 
    [agent, appreciationReceipt], 
    [agent, insert(a50recipeSelect)]
]) :-
    currentTopLevel(a50recipeSelect).


pattern([b42, [user, appreciation], [agent, appreciationReceipt]]).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Conversation Management Patterns (Moore Ch7)           			%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%% C1 Patterns: Opening (Agent)
% Pattern C1.0: Opening Greeting (Agent)
% Example:
%	A: Hello.
%	U: Hi!
% Instruction:
% 	Add a pattern with pattern ID c10 here where the agent initiates (i.e.
%	starts) greeting and then the user is expected to greet.


pattern([c10, [agent, greeting], [user, greeting]]) :- agentName('').


% Pattern C1.1: Opening Self-Identification (Agent)


% Pattern C1.1: Opening Self-Identification (Agent)
% Example:
%	A: Hello.
%	A: My name is ...
%	U: Hi!
% Instruction:
% 	Introduce an intent 'selfIdentification' for the second dialog move of the agent 
%	and add a pattern with pattern id c10 where the agent initiates a greeting, then
%	self-identifies, and then expects the user to greet.
%
% NB: We deviate here from Moore and Arar's taxonomy of pattern codes and also label this 
% 	pattern c10 to simplify things from an agenda management perspective.

pattern([c10, [agent, greeting], [agent, selfIdentification], [user, greeting]]) :- not(agentName('')).


%%% C3 Patterns: Capabilities
% Pattern C3.0: General Capability Check
% Example:
%	U: What can you do?
%	A: I can ____.
% Instruction:
% 	Add a pattern with pattern ID c30 here where the user requests more information
%	about how the agent can assist and the agent provides an informative response.

pattern([c30, [user, checkCapability], [agent, describeCapability]]).


%%% C4 Patterns: Closing
% Pattern C4.3: Closing Farewell (Agent)
% Variant 1: User chooses to RESTART (say "Start over" after farewell prompt)
pattern([c43,
    [agent, farewell],
    [user, restart],
    [agent, restart]
]).

% Variant 2: User chooses to END (standard goodbye)
% Example: A: goodbye. U: bye.
pattern([c43,
    [agent, farewell],
    [user, farewell],
    [agent, terminate]
]).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Special Patterns									%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%% Button Patterns
% Pattern Start: Start Button (User)
% Example:
%	U: Clicks a Start button.
%	A: -. (start is equivalent to skip action)
%
% This pattern is only available when 'start' is the top level pattern. The pattern is used
% to start the conversation after an initial button-based interaction.

pattern([start, [user, button], [agent, start]]) :-
	getParamsPatternInitiatingIntent(user, button, [button='start']),
	currentTopLevel(start).
	
% Pattern Terminate: End Interaction Button (User)
% Example:
%	U: Clicks an End interaction button.
%	A: Inserts the terminated pattern (see below).

pattern([terminate, [user, button], [agent, insert(terminated)]]) :-
	getParamsPatternInitiatingIntent(user, button, [button='End Interaction']).
	
%%% Terminate Patterns
% Pattern Terminated: Terminate (Agent)
pattern([terminated, [agent, terminate]]).