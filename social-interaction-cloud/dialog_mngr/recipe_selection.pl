%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Basic rules for retrieving information about recipes from the recipe database	%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
:- dynamic recipeCounter/1.
:- discontiguous applyFilter/4.

/**
 * currentRecipe(-RecipeID:atom)
 *
 * Retrieves the chosen recipe from memory (assumes that the last time a recipe is mentioned 
 * also is the user's choice).
 *
 * @RecipeID	An identifier for a recipe in the database of the form '1', '2', etc.
**/
% Project Assignment: Capability 2: Request a Recommendation
%
% Instruction: Add a definition for currentRecipe/1 here.

currentRecipe(RecipeID) :-
    memoryKeyValue('recipe', RecipeName),
    recipeName(RecipeID, RecipeName).
    
    
/**
 * ingredients(+RecipeID:atom, -IngredientList:list)
 *
 * Retrieves all ingredients for a recipe with identifier RecipeID from the recipe database
 * and returns these in a list in the output argument.
 *
 *
 * @RecipeID	An identifier for a recipe in the database.
 * @IngredientList
 *		A list containing all of the ingredients and their quantity.
**/
% Project Assignment: Capability 6: Filter by Number of Ingredients & Recipe Steps
%
% Instruction: Add a definition for ingredients/2 here.

ingredients(RecipeID, IngredientList) :-
    findall(Ing, ingredientAndQuantity(RecipeID, Ing), IngredientList).
 
	

% Project Assignment: Capability 6: Filter by Number of Ingredients & Recipe Steps
%
% Instruction: Add a definition for nrOfIngredients(RecipeID, N) here.
   
nrOfIngredients(RecipeID, N) :-
    ingredients(RecipeID, IngredientList),
    length(IngredientList, N).

/**
 * steps(+RecipeID:atom, -StepList:list)
 *
 * Retrieves the instruction steps for a recipe from the recipe database.
 *
 * @StepList	A list containing all of the instruction steps of the recipe in memory.
**/
% Project Assignment: Capability 6: Filter by Number of Ingredients & Recipe Steps
%
% Instruction: Add a definition for steps/2 here.

steps(RecipeID, StepList) :-
    findall(StepDescription, step(RecipeID, _, StepDescription), StepList).


% Project Assignment: Capability 6: Filter by Number of Ingredients & Recipe Steps
%
% Instruction: Add a definition for nrOfSteps(RecipeID, N) here.

nrOfSteps(RecipeID, N) :-
    steps(RecipeID, StepList),
    length(StepList, N).


/**
 * recipeIDs(-RecipeIDs:list)
 *
 * Retrieves all recipe IDs from the recipe database.
 *
 * @RecipesIDs	A list of recipe identifiers.
**/
% Project Assignment: Capability 2: Request a Recommendation
%
% Instruction: Add a definition for recipeIDs/1 here.
recipeIDs(RecipeIDs) :- setof(RecipeID, recipeID(RecipeID), RecipeIDs).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Rules for retrieving only those recipes from the database that satisfy all requests	%%%
%%%											%%%
%%% The idea is that the recipesFiltered(RecipeIDs) retrieves all recipes that satisfy 	%%%
%%% the requests a user has made. That is, only those recipes are retrieved that have 	%%%
%%% all the features asked for.								%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

/**
 * recipesFiltered(-RecipesIDs:list)
 *
 * Retrieves all identifiers of recipes that meet the requests a user has made (the user's 
 * preferences, constraints, etc. such as cuisine='southern-american'). Retrieves all these 
 * requests from the agent's conversational memory and applies these requests as filters to 
 * the recipes in the database. If there are no filters to apply, identifiers for all 
 * recipes in the database are returned.
 *
 * @RecipeIDs	A list of identifiers of recipes that meet all user requests stored in the
 * 		agent's conversational memory.
**/
% Project Assignment: Capability 2: Request a Recommendation


%
% recipesFilteredNew(-RecipeIDs):
% retrieves all recipes that are filtered with the currently active feature selections 
% this is done by retrieving all recipes and the memory, filtering the memory by feature selection parameters
% and then recursively filter all recipes on the filters.
recipesFiltered(RecipeIDs) :-
	recipeIDs(RecipeIDsAll),
	filters_from_memory(Filters),
	recipesFiltered(RecipeIDsAll, Filters, RecipeIDsFiltered),
	list_to_set(RecipeIDsFiltered, RecipeIDs).


/**
 * recipesFiltered(+RecipeIDs:list, +Filters:list, -RecipeIDsFiltered:list)
 *
 * Given a list of recipe identifiers RecipeIDs, returns the identifiers in that list that
 * meet the constraints in the list of Filters provided in the output argument 
 * RecipeIDsFiltered.
 *
 * @RecipeIDs	A list of recipe identifiers.
 * @Filters	A list of filters or constraints of the form 'Feature=Value'.
 * @RecipeIDsFiltered
 *		A list of identifiers of recipes that match with all the filters.
**/
% Project Assignment: Capability 2: Request a Recommendation
%
% Recursively go through all user provided features to find those recipes that satisfy all
% of these features.  
recipesFiltered(RecipeIDs, [], RecipeIDs).


% Project Assignment: Capability 5: Filter Recipes by Ingredients
recipesFiltered(RecipeIDsIn, [ ParamName = Value | Filters], RemainingRecipeIDs) :-
	applyFilterCheck(ParamName, Value, RecipeIDsIn, RecipeIDsOut),
	recipesFiltered(RecipeIDsOut, Filters, RemainingRecipeIDs).


/**
 * applyFilter(+ParamName, +Value, +RecipeIDs, -FilteredRecipes)
 *
 * Filters the recipes provided as input using the (Key) feature with associated value and
 * returns the recipes that satisfy the feature as output.
 *
 * @ParamName	A parameter name referring to a feature that the recipes should have.
 * @Value	The associated value of the feature (parameter name).
 * @RecipeIDs	The recipes that need to be filtered.
 * @FilteredRecipes The recipes that have the required feature.
**/
applyFilterCheck(ParamName, Value, RecipeIDsIn, RecipeIDsOut) :-
	is_list(Value), [H | T] = Value,
	applyFilter(ParamName, H, RecipeIDsIn, RecipeIDsIntermediate),
	applyFilterCheck(ParamName, T, RecipeIDsIntermediate, RecipeIDsOut).
	
applyFilterCheck(_, [], RecipeIDsIn, RecipeIDsIn).
	
applyFilterCheck(ParamName, Value, RecipeIDsIn, RecipeIDsOut) :-
	not(is_list(Value)),
	applyFilter(ParamName, Value, RecipeIDsIn, RecipeIDsOut).

%%%
% Apply filter checking that a recipe is from a particular cuisine.
%
% Project Assignment: Capability 5: Filter Recipes
% Instruction: Add a clause for applyFilter('cuisine', Cuisine, RecipeIDsIn, RecipeIDsOut)

applyFilter('cuisine', CuisineIn, RecipeIDsIn, RecipeIDsOut) :- 
    downcase_atom(CuisineIn, Cuisine),
	findall(RecipeID, (member(RecipeID, RecipeIDsIn), once(cuisine(RecipeID, Cuisine))), RecipeIDsOut).

applyFilter('excludecuisine', CuisineIn, RecipeIDsIn, RecipeIDsOut) :- 
    downcase_atom(CuisineIn, Cuisine),
    findall(RecipeID, (member(RecipeID, RecipeIDsIn), not(cuisine(RecipeID, Cuisine))), RecipeIDsOut).
	
applyFilter('mealType', TypeIn, RecipeIDsIn, RecipeIDsOut) :-
    downcase_atom(TypeIn, Type),
    findall(R, (member(R, RecipeIDsIn), once(mealType(R, Type))), RecipeIDsOut).

applyFilter('excludemealtype', TypeIn, RecipeIDsIn, RecipeIDsOut) :-
    downcase_atom(TypeIn, Type),
    findall(R, (member(R, RecipeIDsIn), not(mealType(R, Type))), RecipeIDsOut).

% Normalize ingredient value before filtering (removes prefixes like "with ", "containing ", etc.)
% Uses normalize_ingredient_value from dialogflow.pl to handle values like "with eggs" -> "eggs"
applyFilter('ingredient', IngredientIn, RecipeIDsIn, RecipeIDsOut) :-
    normalize_ingredient_value(IngredientIn, NormalizedIngredient),
    findall(R, (member(R, RecipeIDsIn), once(hasIngredient(R, NormalizedIngredient))), RecipeIDsOut).

applyFilter('excludeingredient', IngredientIn, RecipeIDsIn, RecipeIDsOut) :-
    normalize_ingredient_value(IngredientIn, NormalizedIngredient),
    findall(R, (member(R, RecipeIDsIn), not(hasIngredient(R, NormalizedIngredient))), RecipeIDsOut).

applyFilter('ingredienttype', IngredientTypeIn, RecipeIDsIn, RecipeIDsOut) :-
    downcase_atom(IngredientTypeIn, IngredientType),
    findall(R, (member(R, RecipeIDsIn), once(hasIngredient(R, IngredientType))), RecipeIDsOut).

applyFilter('excludeingredienttype', IngredientTypeIn, RecipeIDsIn, RecipeIDsOut) :-
    downcase_atom(IngredientTypeIn, IngredientType),
    findall(R, (member(R, RecipeIDsIn), not(hasIngredient(R, IngredientType))), RecipeIDsOut).

applyFilter('dietaryrestriction', DietIn, RecipeIDsIn, RecipeIDsOut) :-
    downcase_atom(DietIn, Diet),
    findall(R, (member(R, RecipeIDsIn), once(diet(R, Diet))), RecipeIDsOut).

applyFilter('excludedietaryrestriction', DietIn, RecipeIDsIn, RecipeIDsOut) :-
    downcase_atom(DietIn, Diet),
    findall(R, (member(R, RecipeIDsIn), not(diet(R, Diet))), RecipeIDsOut).

applyFilter('tag', TagIn, RecipeIDsIn, RecipeIDsOut) :-
    downcase_atom(TagIn, Tag),
    findall(R, (member(R, RecipeIDsIn), once(tag(R, Tag))), RecipeIDsOut).

applyFilter('excludetag', TagIn, RecipeIDsIn, RecipeIDsOut) :-
    downcase_atom(TagIn, Tag),
    findall(R, (member(R, RecipeIDsIn),
                not(tag(R, Tag)),
                (Tag = breakfast -> not(mealType(R, breakfast)) ; true)),
            RecipeIDsOut).

applyFilter('duration', MaxMinutesIn, RecipeIDsIn, RecipeIDsOut) :-
    (atom(MaxMinutesIn) -> atom_number(MaxMinutesIn, MaxMinutes) ; MaxMinutes = MaxMinutesIn),
    findall(R, (
        member(R, RecipeIDsIn),
        time(R, Duration),
        Duration =< MaxMinutes
    ), RecipeIDsOut).

applyFilter('servings', ValueIn, RecipeIDsIn, RecipeIDsOut) :-
    (atom(ValueIn) -> atom_number(ValueIn, Value) ; Value = ValueIn),
    findall(R, (
        member(R, RecipeIDsIn),
        servings(R, S),
        S >= Value
    ), RecipeIDsOut).

applyFilter('nrOfIngredients', ValueIn, RecipeIDsIn, RecipeIDsOut) :-
    (atom(ValueIn) -> atom_number(ValueIn, Value) ; Value = ValueIn),
    findall(R, (
        member(R, RecipeIDsIn),
        nrOfIngredients(R, N),
        N =< Value
    ), RecipeIDsOut).

applyFilter('nrOfSteps', ValueIn, RecipeIDsIn, RecipeIDsOut) :-
    (atom(ValueIn) -> atom_number(ValueIn, Value) ; Value = ValueIn),
    findall(R, (
        member(R, RecipeIDsIn),
        nrOfSteps(R, N),
        N =< Value
    ), RecipeIDsOut).

applyFilter('fast', _, RecipeIDsIn, RecipeIDsOut) :-
    applyFilter('duration', 30, RecipeIDsIn, RecipeIDsOut).

applyFilter('easy', _, RecipeIDsIn, RecipeIDsOut) :-
    applyFilter('duration', 45, RecipeIDsIn, R1),
    applyFilter('nrOfSteps', 18, R1, R2),
    applyFilter('nrOfIngredients', 15, R2, RecipeIDsOut).

% Project Assignment: Capability 7: Filter on Dietary Restrictions
% Helper predicate diet(RecipeID, DietaryRestriction)
diet(RecipeID, 'spicy') :-
    hasIngredient(RecipeID, 'spicy'), !.

diet(RecipeID, 'spice') :-
    hasIngredient(RecipeID, 'spicy'), !.

diet(RecipeID, 'healthy') :-
    mealType(RecipeID, 'healthy'), !.

diet(RecipeID, Restriction) :-
    Restriction \= 'spicy',
    Restriction \= 'spice',
    Restriction \= 'healthy',
    downcase_atom(Restriction, LowRestriction),
    findall(Ing, ingredient(RecipeID, Ing), RawIngredients), 
    ingredientsMeetDiet(RawIngredients, LowRestriction), !.

ingredientsMeetDiet([], _).
ingredientsMeetDiet([Ingredient | Rest], Restriction) :-
    typeIngredient(Ingredient, Restriction),
    ingredientsMeetDiet(Rest, Restriction).

%%%
% Comprehensive aliases for applyFilter to seamlessly support camelCase / snake_case / NLU slot names
applyFilter('dietaryRestriction', Diet, In, Out) :- applyFilter('dietaryrestriction', Diet, In, Out).
applyFilter('dietary_restriction', Diet, In, Out) :- applyFilter('dietaryrestriction', Diet, In, Out).
applyFilter('diet', Diet, In, Out) :- applyFilter('dietaryrestriction', Diet, In, Out).
applyFilter('dietary', Diet, In, Out) :- applyFilter('dietaryrestriction', Diet, In, Out).

applyFilter('excludeDietaryRestriction', Diet, In, Out) :- applyFilter('excludedietaryrestriction', Diet, In, Out).
applyFilter('exclude_dietary_restriction', Diet, In, Out) :- applyFilter('excludedietaryrestriction', Diet, In, Out).
applyFilter('excludediet', Diet, In, Out) :- applyFilter('excludedietaryrestriction', Diet, In, Out).

applyFilter('excludeIngredient', Ingr, In, Out) :- applyFilter('excludeingredient', Ingr, In, Out).
applyFilter('exclude_ingredient', Ingr, In, Out) :- applyFilter('excludeingredient', Ingr, In, Out).
applyFilter('excludeingredients', Ingr, In, Out) :- applyFilter('excludeingredient', Ingr, In, Out).

applyFilter('excludeCuisine', C, In, Out) :- applyFilter('excludecuisine', C, In, Out).
applyFilter('exclude_cuisine', C, In, Out) :- applyFilter('excludecuisine', C, In, Out).

applyFilter('excludeMealType', M, In, Out) :- applyFilter('excludemealtype', M, In, Out).
applyFilter('exclude_meal_type', M, In, Out) :- applyFilter('excludemealtype', M, In, Out).
applyFilter('excludemeal', M, In, Out) :- applyFilter('excludemealtype', M, In, Out).

applyFilter('mealtype', M, In, Out) :- applyFilter('mealType', M, In, Out).
applyFilter('meal_type', M, In, Out) :- applyFilter('mealType', M, In, Out).
applyFilter('MealType', M, In, Out) :- applyFilter('mealType', M, In, Out).
applyFilter('meal', M, In, Out) :- applyFilter('mealType', M, In, Out).

applyFilter('ingredientType', T, In, Out) :- applyFilter('ingredienttype', T, In, Out).
applyFilter('ingredient_type', T, In, Out) :- applyFilter('ingredienttype', T, In, Out).

applyFilter('excludeIngredientType', T, In, Out) :- applyFilter('excludeingredienttype', T, In, Out).
applyFilter('exclude_ingredient_type', T, In, Out) :- applyFilter('excludeingredienttype', T, In, Out).

applyFilter('excludeTag', T, In, Out) :- applyFilter('excludetag', T, In, Out).
applyFilter('exclude_tag', T, In, Out) :- applyFilter('excludetag', T, In, Out).

applyFilter('nrofingredients', V, In, Out) :- applyFilter('nrOfIngredients', V, In, Out).
applyFilter('nr_of_ingredients', V, In, Out) :- applyFilter('nrOfIngredients', V, In, Out).
applyFilter('max_ingredients', V, In, Out) :- applyFilter('nrOfIngredients', V, In, Out).

applyFilter('nrofsteps', V, In, Out) :- applyFilter('nrOfSteps', V, In, Out).
applyFilter('nr_of_steps', V, In, Out) :- applyFilter('nrOfSteps', V, In, Out).
applyFilter('nrSteps', V, In, Out) :- applyFilter('nrOfSteps', V, In, Out).
applyFilter('steps', V, In, Out) :- applyFilter('nrOfSteps', V, In, Out).
applyFilter('max_steps', V, In, Out) :- applyFilter('nrOfSteps', V, In, Out).

applyFilter('easyKeyWord', _, In, Out) :- applyFilter('easy', _, In, Out).
applyFilter('easykeyword', _, In, Out) :- applyFilter('easy', _, In, Out).
applyFilter('easy_key_word', _, In, Out) :- applyFilter('easy', _, In, Out).
applyFilter('difficulty', _, In, Out) :- applyFilter('easy', _, In, Out).

applyFilter('quick', _, In, Out) :- applyFilter('fast', _, In, Out).
applyFilter('shorttimekeyword', _, In, Out) :- applyFilter('fast', _, In, Out).
applyFilter('short_time', _, In, Out) :- applyFilter('fast', _, In, Out).

applyFilter('time', V, In, Out) :- applyFilter('duration', V, In, Out).
applyFilter('cooking_time', V, In, Out) :- applyFilter('duration', V, In, Out).
applyFilter('cookingtime', V, In, Out) :- applyFilter('duration', V, In, Out).
applyFilter('max_duration', V, In, Out) :- applyFilter('duration', V, In, Out).

applyFilter('serving', V, In, Out) :- applyFilter('servings', V, In, Out).
applyFilter('portion', V, In, Out) :- applyFilter('servings', V, In, Out).
applyFilter('portions', V, In, Out) :- applyFilter('servings', V, In, Out).

applyFilter('ingredients', I, In, Out) :- applyFilter('ingredient', I, In, Out).
applyFilter('tags', T, In, Out) :- applyFilter('tag', T, In, Out).
applyFilter('cuisines', C, In, Out) :- applyFilter('cuisine', C, In, Out).

