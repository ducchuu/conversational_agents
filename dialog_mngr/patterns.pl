%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Patterns 								 		%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

pattern([slotFill(X), [agent, repeat(X)]]).
slotFill(dummyP, dummyI).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Pattern: a21featureRequest								%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% 1. Context: Confirm (User was looking at a specific recipe) -> Move BACK to Select
pattern([a21featureRequest,
    [user, addFilter],
    [agent, removeConflicts(Params)],
    [agent, ackFilter],
    [agent, insert(a50recipeSelect)] 
]) :-
    currentTopLevel(a50recipeConfirm),
    getParamsPatternInitiatingIntent(user, addFilter, Params),
    not(recipesFiltered([])).

% 2. Context: Confirm | No results
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

% 3. Context: Select (Already in list) -> STAY in Select (No loop)
pattern([a21featureRequest,
    [user, addFilter],
    [agent, removeConflicts(Params)],
    [agent, ackFilter]
]) :-
    currentTopLevel(a50recipeSelect),
    getParamsPatternInitiatingIntent(user, addFilter, Params),
    not(recipesFiltered([])).

% 4. Context: Select | No results
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

% Variant 1: Success (15 or fewer recipes) -> Show list
pattern([a21noMoreFilters,
    [user, noMoreFilters],
    [agent, ackFilterEnd]
]) :-
    currentTopLevel(a50recipeSelect),
    recipesFiltered(Recipes),
    length(Recipes, N),
    N =< 15.

% Variant 2: Failure (More than 15 recipes) -> Refuse to show
pattern([a21noMoreFilters,
    [user, noMoreFilters],
    [agent, tooManyRecipesLeft]
]) :-
    currentTopLevel(a50recipeSelect),
    recipesFiltered(Recipes),
    length(Recipes, N),
    N > 15.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Other Standard Patterns (Remove/Delete)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

pattern([a21removeKeyFromMemory,
	[user, deleteParameter],
	[agent, removeParam(Params)],
	[agent, insert(a50recipeSelect)]])
:-
	parent(a21removeKeyFromMemory, a50recipeConfirm),
	getParamsPatternInitiatingIntent(user, deleteParameter, Params),
	(currentTopLevel(a50recipeSelect);currentTopLevel(a50recipeConfirm)).

pattern([a21removeKeyFromMemory,
	[user, deleteParameter],
	[agent, removeParam(Params)],
	[agent, featureInquiry] ])
:-
	getParamsPatternInitiatingIntent(user, deleteParameter, Params),
	(currentTopLevel(a50recipeSelect);currentTopLevel(a50recipeConfirm)).

pattern([a21removeKeyFromMemory,
	[user, deleteFilterValue],
	[agent, removeValue(Params)],
	[agent, insert(a50recipeSelect)] ])
:-
	parent(a21removeKeyFromMemory, a50recipeConfirm),
	getParamsPatternInitiatingIntent(user, deleteFilterValue, Params),
	(currentTopLevel(a50recipeSelect);currentTopLevel(a50recipeConfirm)).

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

pattern([a50recipeConfirm, [user, confirmation], [agent, terminate] ]).
pattern([a50recipeConfirm, [user, appreciation], [agent, terminate] ]).
pattern([a50recipeConfirm, [user, disconfirmation], [agent, insert(a50recipeSelect)] ]).

pattern([a50recipeSelect,
    [agent, specifyGoal],
    [user, requestRecommendation],
    [agent, recommend],
    [agent, insert(a50recipeConfirm)]
]).

pattern([a50recipeSelect,
    [agent, specifyGoal],
    [user, recipeRequest],
    [agent, recipeChoiceReceipt],
    [agent, insert(a50recipeConfirm)]
]).

pattern([c10, [agent, greeting], [user, greeting]]) :- agentName('').
pattern([c10, [agent, greeting], [agent, selfIdentification], [user, greeting]]) :- not(agentName('')).

pattern([start, [user, button], [agent, start]]) :-
	getParamsPatternInitiatingIntent(user, button, [button='start']),
	currentTopLevel(start).

pattern([terminate, [user, button], [agent, insert(terminated)]]) :-
	getParamsPatternInitiatingIntent(user, button, [button='End Interaction']).
pattern([terminated, [agent, terminate]]).