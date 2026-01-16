%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Knowledge that is specifically related to the (Google) Dialogflow agent		%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

:- dynamic
	% percept
	intent/5,
	transcript/1.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Parameter specific content								%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% dual_parameter_name_pairs/1 is used to check if something is a filter parameter or to
% find the corresponding dual filter parameter name for deletion (see responses_new.pl).
dual_parameter_name_pairs([
	['cuisine', 'cuisineDel'],
	['dietaryrestriction', 'dietaryRestrictionDel'],
	['duration', 'durationDel'],
	['easykeyword', 'easyKeyWordDel'],
	['excludeingredient', 'excludeIngredientDel'],
	['excludeingredienttype', 'excludeIngredientTypeDel'],
	['ingredient', 'ingredientDel'],
	['ingredienttype', 'ingredientTypeDel'],
	['mealType', 'mealTypeDel'],
	['nrOfIngredients', 'ingredientNumberDel'],
	['nrSteps', 'stepsDel'],
	['servings', 'servingsDel'],
	['shorttimekeyword', 'shorttimekeywordDel'],
	['tag', 'tagDel'],
	['excludedietaryrestriction', 'excludeDietaryRestrictionDel'],
	['excludecuisine', 'exludeCuisineDel'],
	['durationlonger', 'durationlongerDel'],
	['nrOfIngredientsMore', 'moreIngredientNumberDel']
]).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Logic for handling and formatting filter parameters					%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Conflict logic is defined in ingredient_hierarchies.pl (conflicts/3).

/**
 * filters_from_memory(-Filters)
 * Extracts parameters used to filter recipes from memory.
**/
filters_from_memory(Filters) :-
	memory(Params),
	filter_params(Params, Filters).

% filter_params: returns those parameters from a list of parameters that are used to filter
% recipes.
filter_params([], []).
filter_params([ ParamName = Value | Params ], [ ParamName = Value | FilteredParams ]) :-
	is_filter_param(ParamName), filter_params(Params, FilteredParams).
filter_params([ ParamName = _ | Params ], FilteredParams) :-
	not(is_filter_param(ParamName)), filter_params(Params, FilteredParams).

% isFilter predicate: checks if a parameter key is a filter. 
is_filter_param(ParamName) :- 
	dual_parameter_name_pairs(ParamNames),
	member([ ParamName, _ ], ParamNames), !.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Formatting of filter parameters for display on screen (text to display)		%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
parameter_display_templates([
	['cuisine', "~a cuisine"],
	['dietaryrestriction', "~a"],
	["duration", "Less than ~a minutes"],
	['easykeyword', "~a recipes"],
	['excludeingredient', "Without ~a"],
	['excludeingredienttype', "Without ~a"],
	['ingredient', "With ~a"],
	['ingredienttype', "With ~a"],
	['mealType', "~a"],
	['nrOfIngredients', "Less than ~a ingredients"],
	['nrSteps', "Less than ~a steps"],
	['servings', "Serves ~a persons"],
	['shorttimekeyword', "~a recipe (less than 30 minutes)"],
	['tag', "~a"],
	['excludedietaryrestriction', 'Not ~a'],
	['excludecuisine', 'Not of ~a cuisine'],
	['durationlonger', 'More than ~a minutes'],
	['nrOfIngredientsMore', 'More than ~a ingredients']
]).

format_display_value(_, Value, FormattedValue) :-
	is_list(Value),
	convert_to_string(Value, FormattedValue), !.
format_display_value(_, Value, FormattedValue) :-
	not(atomic(Value)),
	convert_to_string(Value, FormattedValue), !.
format_display_value(Filter, Value, FormattedValue) :- 
	member(Filter, [ 'cuisine', 'dietaryrestriction', 'mealType', 'tag', 'excludedietaryrestriction', 'excludecuisine' ]),
	to_upper_case(Value, FormattedValue), !.
format_display_value(_, Value, Value).

% Format display for one filter
filter_to_atom(Filter, Value, Atom) :-
	format_display_value(Filter, Value, FormattedValue),
	parameter_display_templates(Templates),
	(	member([Filter, Template], Templates)
	->	applyTemplate(Template, FormattedValue, Atom)
	;	format(string(Atom), "~w = ~w", [Filter, FormattedValue])
	).

% Format display for multiple filters 
filters_to_strings(Strings) :-
	filters_from_memory(Filters), 
	filters_to_strings(Filters, Strings).

filters_to_strings([], []).
filters_to_strings([ Param = Value | Filters], [ String | Strings]) :- 
	filter_to_atom(Param, Value, String),
	filters_to_strings(Filters, Strings).

% Safe wrapper to avoid crashing update rules if formatting fails.
filters_to_strings_or_empty(Strings) :-
	( filters_to_strings(Strings) -> true ; Strings = [] ).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Formatting of filter parameters for agent to acknowledge filters (text to say)	%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
parameter_text_templates([
	['cuisine', "are of ~a cuisine"],
	['dietaryrestriction', " have a ~a diet"],
	['duration', " are within ~a minutes"],
	['easykeyword', " are ~a dishes to prepare"],
	['excludeingredient', " do not include ~a"],
	['excludeingredienttype', " do not include ~a"],
	['ingredient', " include ~a"],
	['ingredienttype', " include ~a"],
	['mealType', " are ~a recipes"],
	['nrOfIngredients', " have less than ~a ingredients"],
	['nrSteps', " only have ~a or fewer steps"],
	['servings', " serve ~a persons"],
	['shorttimekeyword', " are  ~a"],
	['tag', " are all ~a dishes"],
	['excludedietaryrestriction', 'do not have a ~a diet'],
	['excludecuisine', 'are not of ~a cuisine'],
	['durationlonger', 'take more than ~a minutes'],
	['nrOfIngredientsMore', 'include more than ~a ingredients']
]).

recipe_to_json(ID, JSON) :-
    recipeName(ID, Name),
    picture(ID, Url),
    time(ID, Time),
    servings(ID, Servings),
    recipe_ingredients(ID, Ingredients),
    recipe_instructions(ID, Instructions),
    json_array(Ingredients, IngredientsJson),
    json_array(Instructions, InstructionsJson),
    json_string(ID, IdJson),
    json_string(Name, NameJson),
    json_string(Url, UrlJson),
    json_string(Time, TimeJson),
    json_string(Servings, ServingsJson),
    format(string(JSON), '{"id": ~w, "title": ~w, "image": ~w, "time": ~w, "servings": ~w, "ingredients": ~w, "instructions": ~w}', [IdJson, NameJson, UrlJson, TimeJson, ServingsJson, IngredientsJson, InstructionsJson]).

recipe_summary_json(ID, JSON) :-
    recipeName(ID, Name),
    picture(ID, Url),
    time(ID, Time),
    servings(ID, Servings),
    json_string(ID, IdJson),
    json_string(Name, NameJson),
    json_string(Url, UrlJson),
    json_string(Time, TimeJson),
    json_string(Servings, ServingsJson),
    format(string(JSON), '{"id": ~w, "title": ~w, "image": ~w, "time": ~w, "servings": ~w}', [IdJson, NameJson, UrlJson, TimeJson, ServingsJson]).

recipes_to_json(RecipeIDs, JSON) :-
    maplist(recipe_summary_json, RecipeIDs, Items),
    json_array_from_json_items(Items, JSON).
	
format_text_value(Filter, Ingredients, String) :-
	(Filter == 'excludeingredient' ; Filter == 'excludeingredienttype'), 
	convert_to_string(Ingredients, String), !.
format_text_value(Filter, Ingredients, String) :-
	(Filter == 'ingredient' ; Filter == 'ingredienttype'),
	convert_to_string(Ingredients, String), !.
format_text_value('tag', Tags, String) :-
	convert_to_string(Tags, String).
format_text_value(_, Value, Value).

% Format text for one filter
filter_to_text(Filter, Value, Txt) :-
	format_text_value(Filter, Value, FormattedValue),
	parameter_text_templates(Templates),
	member([Filter, Template], Templates),
	applyTemplate(Template, FormattedValue, Txt).

% Format text for multiple filters
filters_to_text([], '').
filters_to_text([Param = Value], Txt) :- 
	filter_to_text(Param, Value, Txt).
filters_to_text([Param1 = Value1, Param2 = Value2 | Params], Txt) :- 
	filter_to_text(Param1, Value1, Txt1), string_concat(Txt1, " and ", Str1),
	filters_to_text([Param2 = Value2 | Params], Txt2),
	string_concat(Str1, Txt2, Txt).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Helpers for formatting recipe payloads as JSON strings				%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

recipe_ingredients(ID, Ingredients) :-
    findall(Item, ingredientAndQuantity(ID, Item), WithQty),
    (   WithQty = []
    ->  findall(Item, ingredient(ID, Item), Ingredients)
    ;   Ingredients = WithQty
    ).

recipe_instructions(ID, Instructions) :-
    findall(Step-Instruction, step(ID, Step, Instruction), Pairs),
    sort(Pairs, Sorted),
    pair_values(Sorted, Instructions).

pair_values([], []).
pair_values([_-Value | Rest], [Value | Values]) :-
    pair_values(Rest, Values).

json_array(List, Json) :-
    maplist(json_string, List, Items),
    json_array_from_json_items(Items, Json).

json_array_from_json_items([], "[]").
json_array_from_json_items(Items, Json) :-
    Items \= [],
    atomic_list_concat(Items, ",", Inner),
    format(string(Json), "[~w]", [Inner]).

json_string(Value, JsonString) :-
    convert_to_string(Value, String),
    json_escape(String, Escaped),
    format(string(JsonString), "\"~w\"", [Escaped]).

json_escape(String, Escaped) :-
    string_codes(String, Codes),
    escape_json_codes(Codes, EscapedCodes),
    string_codes(Escaped, EscapedCodes).

escape_json_codes([], []).
escape_json_codes([92 | Rest], [92, 92 | Out]) :-
    escape_json_codes(Rest, Out).
escape_json_codes([34 | Rest], [92, 34 | Out]) :-
    escape_json_codes(Rest, Out).
escape_json_codes([10 | Rest], [92, 110 | Out]) :-
    escape_json_codes(Rest, Out).
escape_json_codes([13 | Rest], [92, 114 | Out]) :-
    escape_json_codes(Rest, Out).
escape_json_codes([9 | Rest], [92, 116 | Out]) :-
    escape_json_codes(Rest, Out).
escape_json_codes([C | Rest], [C | Out]) :-
    C \= 92,
    C \= 34,
    C \= 10,
    C \= 13,
    C \= 9,
    escape_json_codes(Rest, Out).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Helper predicates
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
same_param(ParamName, ParamName).
same_param(ingredient, ingredienttype).
same_param(ingredienttype, ingredient).
same_param(excludeingredient, excludeingredienttype).
same_param(excludeingredienttype, excludeingredient).
same_param(excludedietaryrestriction, dietaryrestriction).
same_param(excludecuisine, cuisine).
same_param(durationlonger, duration).
same_param(nrOfIngredientsMore, nrOfIngredients).

% ==============================================================================
% SIMPLIFY (ROBUST VERSION)
% ==============================================================================
simplify('duration', Value, Minutes) :- duration_to_min(Value, Minutes), !.
simplify('durationDel', Value, Minutes) :- duration_to_min(Value, Minutes), !.
simplify('nrOfIngredients', Value, Nr) :- convert_to_int(Value, Nr), !.
simplify('ingredientNumberDel', Value, Nr) :- convert_to_int(Value, Nr), !.
simplify('nrSteps', Value, Nr) :- convert_to_int(Value, Nr), !.
simplify('stepsDel', Value, Nr) :- convert_to_int(Value, Nr), !.
simplify('servings', Value, Nr) :- convert_to_int(Value, Nr), !.
simplify('tag', Value, String) :- convert_to_string(Value, String), !.
simplify('nrOfIngredientsMore', Value, Nr) :- convert_to_int(Value, Nr), !.
simplify('moreIngredientNumberDel', Value, Nr) :- convert_to_int(Value, Nr), !.
simplify('durationlonger', Value, Nr) :- duration_to_min(Value, Nr), !.
simplify('durationlongerDel', Value, Nr) :- duration_to_min(Value, Nr), !.
% CATCH-ALL: Pass everything else (lists, atoms) through unchanged.
simplify(_, Value, Value).

% Unravel entity list
unravel([], []).
unravel([ ParamName = Value | Entities], [ ParamName = SimplifiedValue | Unravelled]) :-
	simplify(ParamName, Value, SimplifiedValue),
	unravel(Entities, Unravelled).
unravel([ ParamName = [] | Entities ], [ ParamName = '' | Unravelled]) :-
	unravel(Entities, Unravelled).
unravel([ ParamName = [ Value ] | Entities ], Unravelled) :-
	unravel([ ParamName = Value | Entities ], Unravelled).
unravel([ ParamName = [ Value1, Value2 | Values ] | Entities ], Unravelled) :-
	unravel([ ParamName = Value1, ParamName = [ Value2 | Values ] | Entities ], Unravelled).