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
	["duration", 'durationDel'],
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

/**
 * filters_from_memory(-Filters)
 *
 * Extracts parameters used to filter recipes from memory.
 *
 * @Filters: list of parameter-value pairs from memory that are used to filter recipes.
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


format_display_value(Filter, Value, FormattedValue) :- 
	member(Filter, [ 'cuisine', 'dietaryrestriction', 'mealType', 'tag', 'excludedietaryrestriction', 'excludecuisine' ]),
	to_upper_case(Value, FormattedValue), !.
format_display_value(_, Value, Value).

% Format display for one filter
filter_to_atom(Filter, Value, Atom) :-
	format_display_value(Filter, Value, FormattedValue),
	parameter_display_templates(Templates),
	member([Filter, Template], Templates),
	applyTemplate(Template, FormattedValue, Atom).

% Format display for multiple filters 
filters_to_strings(Strings) :-
	% only show filters used to select recipes
	filters_from_memory(Filters), 
	filters_to_strings(Filters, Strings).

filters_to_strings([], []).
filters_to_strings([ Param = Value | Filters], [ String | Strings]) :- 
	filter_to_atom(Param, Value, String),
	filters_to_strings(Filters, Strings).

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

	
format_text_value(Filter, Ingredients, String) :-
	(Filter == 'excludeingredient' ; Filter == 'excludeingredienttype'), 
	%getValues(Filter, Ingredients),
	convert_to_string(Ingredients, String), !.
format_text_value(Filter, Ingredients, String) :-
	(Filter == 'ingredient' ; Filter == 'ingredienttype'),
	%getValues(Filter, Ingredients), 
	convert_to_string(Ingredients, String), !.
format_text_value('tag', Tags, String) :-
	%getValues('tag', Tags),
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
%%% Helper predicates for:								%%%
%%% 	- identifying similar parameters,						%%%
%%%	- simplifying and unravelling parameter-value pairs.				%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Used to establish which parameter names should be identified when they need to be removed
% See removeParam/3 in dialog.pl. 
same_param(ParamName, ParamName).
same_param(ingredient, ingredienttype).
same_param(ingredienttype, ingredient).
same_param(excludeingredient, excludeingredienttype).
same_param(excludeingredienttype, excludeingredient).
same_param(excludedietaryrestriction, dietaryrestriction).
same_param(excludecuisine, cuisine).
same_param(durationlonger, duration).
same_param(nrOfIngredientsMore, nrOfIngredients).


%
% simplify(+Entity, +Value, -SimplifiedValue)
%
% Predicate for simplifying some entity-value pairs when the value is not a simple value.
%
% Only needs to be defined for entities that return a list of key-value pairs that together
% make up the value of the paramater. For example, @sys.duration returns an amount (number)
% and a unit (min, hr, etc.) as a list.
%
% Note that parameters that are lists because they return multiple values for a parameter,
% e.g., multiple ingredients, as indicated by the IS LIST parameter field name do not need
% to be simplified here. The unravel/2 predicate below takes care of that.
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
simplify(_, Value, Value) :- not(is_list(Value)).
% Fails if ParamName is not duration, durationDel, or Value is not a list.

% Unravel entity list and turn into list of the form entityName=entityValue pairs.
unravel([], []).
% Value can be simplified (see simplify/3).
unravel([ ParamName = Value | Entities], [ ParamName = SimplifiedValue | Unravelled]) :-
	simplify(ParamName, Value, SimplifiedValue),
	unravel(Entities, Unravelled).
% Value is a list and cannot be 'simplified'.
% Entity with empty list as value.
unravel([ ParamName = [] | Entities ], [ ParamName = '' | Unravelled]) :-
	unravel(Entities, Unravelled).
% Entity with single item list as value.
unravel([ ParamName = [ Value ] | Entities ], Unravelled) :-
	unravel([ ParamName = Value | Entities ], Unravelled).
% Entity with multiple items in list as value.
unravel([ ParamName = [ Value1, Value2 | Values ] | Entities ], Unravelled) :-
	unravel([ ParamName = Value1, ParamName = [ Value2 | Values ] | Entities ], Unravelled).