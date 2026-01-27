%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Basic rules for retrieving information about recipes from the recipe database	%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
:- dynamic recipeCounter/1.


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

applyFilter('cuisine', Cuisine, RecipeIDsIn, RecipeIDsOut) :- 
	findall(RecipeID, (member(RecipeID, RecipeIDsIn), cuisine(RecipeID, Cuisine)), RecipeIDsOut).
	
applyFilter('mealType', Type, RecipeIDsIn, RecipeIDsOut) :-
    findall(R, (member(R, RecipeIDsIn), mealType(R, Type)), RecipeIDsOut).

% Normalize ingredient value before filtering (removes prefixes like "with ", "containing ", etc.)
% Uses normalize_ingredient_value from dialogflow.pl to handle values like "with eggs" -> "eggs"
applyFilter('ingredient', Ingredient, RecipeIDsIn, RecipeIDsOut) :-
    normalize_ingredient_value(Ingredient, NormalizedIngredient),
    findall(R, (member(R, RecipeIDsIn), hasIngredient(R, NormalizedIngredient)), RecipeIDsOut).





%%% 
% Apply filter that excludes recipes that are of a particular cuisine.
% Example: the user wants recipes that are NOT Japanese.
%
% Project Assignment: Capability 8: Filter Recipes by Excluding Features
%
% Instruction: Add a clause for 
%		applyFilter('excludecuisine', Ingredient, RecipeIDsIn, RecipeIDsOut)

applyFilter('excludecuisine', Cuisine, RecipeIDsIn, RecipeIDsOut) :- 
    findall(RecipeID, (member(RecipeID, RecipeIDsIn), not(cuisine(RecipeID, Cuisine))), RecipeIDsOut).


%%%
% Apply filter checking that a recipe meets a dietary restriction such as vegetarian.
%
% Project Assignment: Capability 7: Filter on Dietary Restrictions
%
% Instruction: Add a clause for 
%		applyFilter('dietaryrestriction', Restriction, RecipeIDsIn, RecipeIDsOut)

applyFilter('dietaryrestriction', Diet, RecipeIDsIn, RecipeIDsOut) :-
    findall(R, (member(R, RecipeIDsIn), diet(R, Diet)), RecipeIDsOut).


%%% 
% Apply filter that excludes recipes that have a dietary restriction.
% Example: the user wants recipes that are NOT vegan.
%
% Project Assignment: Capability 8: Filter Recipes by Excluding Features
%
% Instruction: Add a clause for 
%		applyFilter('excludedietaryrestriction', Ingredient, RecipeIDsIn, RecipeIDsOut)
applyFilter('excludeingredient', Ingredient, RecipeIDsIn, RecipeIDsOut) :-
    normalize_ingredient_value(Ingredient, NormalizedIngredient),
    findall(R, (member(R, RecipeIDsIn), not(hasIngredient(R, NormalizedIngredient))), RecipeIDsOut).


% Project Assignment: Capability 7: Filter on Dietary Restrictions
%
% Instruction: Add a clause for the helper predicate diet(RecipeID, DietaryRestriction).

diet(RecipeID, 'spicy') :-
    hasIngredient(RecipeID, 'spicy').

diet(RecipeID, Restriction) :-
    Restriction \= 'spicy',
    findall(Ing, ingredient(RecipeID, Ing), RawIngredients), 
    ingredientsMeetDiet(RawIngredients, Restriction).



% Project Assignment: Capability 7: Filter on Dietary Restrictions
%
% Instruction: Define a base and recursive clause for the helper predicate
% 		ingredientsMeetDiet(IngredientList, DietaryRestriction).

ingredientsMeetDiet([], _).

ingredientsMeetDiet([Ingredient | Rest], Restriction) :-
    typeIngredient(Ingredient, Restriction),
    ingredientsMeetDiet(Rest, Restriction).

    
%%%
% Apply filter to filter for easy recipes.
% A recipe is easy when:
% - they can be made within 45 minutes,
% - have less than 18 steps, and
% - less than 15 ingredients.

applyFilter('fast', _, RecipeIDsIn, RecipeIDsOut) :-
    applyFilter('duration', 30, RecipeIDsIn, RecipeIDsOut).
    
    
applyFilter('easy', _, RecipeIDsIn, RecipeIDsOut) :-
    applyFilter('duration', 45, RecipeIDsIn, R1),
    applyFilter('nrOfSteps', 18, R1, R2),
    applyFilter('nrOfIngredients', 15, R2, RecipeIDsOut).
    
    
applyFilter('tag', Tag, RecipeIDsIn, RecipeIDsOut) :-
    findall(R, (member(R, RecipeIDsIn), tag(R, Tag)), RecipeIDsOut).


%%%
% Apply filter checking that a recipe uses a specific ingredient (included in the ingredient list)
%
% Project Assignment: Capability 5: Filter Recipes by Ingredients
%
% Instruction: Add a clause for 
%		applyFilter('ingredient', Ingredient, RecipeIDsIn, RecipeIDsOut)

applyFilter('ingredient', Ingredient, RecipeIDsIn, RecipeIDsOut) :-
    normalize_ingredient_value(Ingredient, NormalizedIngredient),
    findall(R, (member(R, RecipeIDsIn), hasIngredient(R, NormalizedIngredient)), RecipeIDsOut).


%%% 
% Apply filter that excludes recipes that use a specific ingredient.
% Example: the user wants recipes that do NOT include the ingredient tahini.
%
% Project Assignment: Capability 8: Filter Recipes by Excluding Features
%
% Instruction: Add a clause for 
%		applyFilter('excludeingredient', Ingredient, RecipeIDsIn, RecipeIDsOut)

applyFilter('excludeingredient', Ingredient, RecipeIDsIn, RecipeIDsOut) :-
    normalize_ingredient_value(Ingredient, NormalizedIngredient),
    findall(R, (member(R, RecipeIDsIn), not(hasIngredient(R, NormalizedIngredient))), RecipeIDsOut).



%%%
% Apply filter checking that a recipe uses an ingredient type.
%
% Project Assignment: Capability 5: Filter Recipes by Ingredients
%
% Instruction: Add a clause for 
%		applyFilter('ingredienttype', IngredientType, RecipeIDsIn, RecipeIDsOut)

applyFilter('ingredienttype', IngredientType, RecipeIDsIn, RecipeIDsOut) :-
    findall(R, (member(R, RecipeIDsIn), hasIngredient(R, IngredientType)), RecipeIDsOut).


%%% 
% Apply filter that excludes recipes that use a specific ingredient type.
% Example: the user wants recipes that do NOT include the ingredient pasta.
%
% Project Assignment: Capability 8: Filter Recipes by Excluding Features
%
% Instruction: Add a clause for 
%		applyFilter('excludeingredienttype', Ingredient, RecipeIDsIn, RecipeIDsOut)

applyFilter('excludeingredienttype', IngredientType, RecipeIDsIn, RecipeIDsOut) :-
    findall(R, (member(R, RecipeIDsIn), not(hasIngredient(R, IngredientType))), RecipeIDsOut).
 
applyFilter('dietaryrestriction', Diet, RecipeIDsIn, RecipeIDsOut) :-
    findall(R, (member(R, RecipeIDsIn), diet(R, Diet)), RecipeIDsOut).
    

applyFilter('excludedietaryrestriction', Diet, RecipeIDsIn, RecipeIDsOut) :-
    findall(R, (member(R, RecipeIDsIn), not(diet(R, Diet))), RecipeIDsOut).
    
%%%
% Apply a filter on meal type (e.g., breakfast).

		
%%% 
% Apply filter to filter recipes on maximum number of ingredients.
%
% Project Assignment: Capability 6: Filter Recipes on Number of Ingredients
%
% Instruction: Add a clause for 
%		applyFilter('nrOfIngredients', Value, RecipeIDsIn, RecipeIDsOut)

applyFilter('nrOfIngredients', Value, RecipeIDsIn, RecipeIDsOut) :-
    findall(R, (
        member(R, RecipeIDsIn),
        nrOfIngredients(R, N),
        N =< Value
    ), RecipeIDsOut).

% You first may want to define a helper for counting the number of ingredients in a list of ingredients. Define this at the top of 
% the file, where we defined ingredients/2. Then return here to define applyFilter('nrOfIngredients', Value, RecipeIDsIn, RecipeIDsOut).


%%% 
% Apply filter to filter recipes on maximum number of recipe instruction steps.
%
% Project Assignment: Capability 6: Filter Recipes on Number of Recipe Steps
%
% Instruction: Add a clause for 
%		applyFilter('nrOfSteps', Value, RecipeIDsIn, RecipeIDsOut)
% You may also want to define a helper for counting the number of steps in a list of steps using Again, define this at the top of 
% the file. Then return here to define applyFilter('nrOfSteps', Value, RecipeIDsIn, RecipeIDsOut)

applyFilter('nrOfSteps', Value, RecipeIDsIn, RecipeIDsOut) :-
    findall(R, (
        member(R, RecipeIDsIn),
        nrOfSteps(R, N),
        N =< Value
    ), RecipeIDsOut).


%%% 
% Apply filter to filter recipes on maximum duration.
%
% Project Assignment: Capability 6: Filter Recipes on Duration
%
% Instruction: Add a clause for 
%		applyFilter('duration', MaxMinutes, RecipeIDsIn, RecipeIDsOut)


applyFilter('duration', MaxMinutes, RecipeIDsIn, RecipeIDsOut) :-
    findall(R, (
        member(R, RecipeIDsIn),
        time(R, Duration),
        Duration =< MaxMinutes
    ), RecipeIDsOut).
    
%%%
% Apply filter to select recipes that can be made fast (meaning e.g. under 30 minutes).


%%%
% Apply filter to filter on number of servings.
%
% Project Assignment: Capability 6: Filter Recipes on Number of Servings
%
% Instruction: Add a clause for 
%		applyFilter('servings', Value, RecipeIDsIn, RecipeIDsOut)

applyFilter('servings', Value, RecipeIDsIn, RecipeIDsOut) :-
    findall(R, (
        member(R, RecipeIDsIn),
        servings(R, S),
        S >= Value
    ), RecipeIDsOut).


%%%
% Apply filter to filter recipes on their tags.
% Example: the user wants to filter on "pizza" dishes (recipes that have the "pizza" tag).
% Check out the tart/2 predicate in the recipe database file.

