%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Responses when a flag has been set for a button.					%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% responses for NEW dialog agent 		   %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


flagResponse('mic', 'Please press Start first') :- flag('mic'), waitingForEvent('start').

flagResponse('mic', 'I am already listening') :- flag('mic'), listening.

% We might have just stopped listening but still waiting for results from intention
% detection; so case above does not apply but we still need user to be patient. Order of
% these rules therefore is also important.
%flagResponse('mic', 'Wait a second') :-
%	flag('mic'), waitingForEvent('IntentDetectionDone'). % WAIT A SECOND BUG

flagResponse('mic', "Please, I'm talking") :- flag('mic'), talking.
flagResponse('mic', 'Not available right now') :- flag('mic'), not(waitingForEvent(_)).
% In all other cases, flags generate an 'empty' response.
flagResponse(_, '').


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Text generator that generates something to say from scripted text and phrases for 	%%%
%%% intents that the agent will generate (use).						%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

/**
 * text(+Intent:atom, -Txt:string)
 *
 * Generates a string expression for an agent intent label.
 *
 * @Intent	Intent label.
 * @Txt		Textual response for agent to perform intent.
**/

/**
 * text(+PatternID:atom, +Intent:atom, -Txt:string)
 *
 * Generates a string expression for an agent intent in the context of an active pattern.
 *
 * @PatternID	A pattern identifier, must be at top level (see generator below).
 * @Intent	Intent label.
 * @Txt		Textual response for agent to perform intent.
**/

:- dynamic text/2, text/3.



% Text generator that takes dialog context into account.
% We use top level dialog context, e.g.:
% - greeting (c10)
% - recipe selection (a50recipeSelect)
% - recipe choice confirmation (a50recipeConfirm)
% - closing (c40)

text_generator(Intent, SelectedText) :-
	currentTopLevel(PatternId),
	findall(Text, text(PatternId, Intent, Text), Texts),
	random_select(SelectedText, Texts, _).
	
% Text generator that does not take dialog context into account.
text_generator(Intent, SelectedText) :-
	findall(Text, text(Intent, Text), Texts), random_select(SelectedText, Texts, _).
	
	
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Scripted text and phrases for ** GENERIC ** intents (sorted on intent name)		%%%
%%% Text is only provided for those intents that the agent will generate (use). 	%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Intent: appreciationReceipt

text(appreciationReceipt, "You're welcome.").
text(appreciationReceipt, "No problem!").
text(appreciationReceipt, "Happy to help.").
text(appreciationReceipt, "It's my pleasure.").
text(appreciationReceipt, "Glad I could be of assistance.").

% Intent: contextMismatch(Intent)

text(contextMismatch(_), "I am not sure what that means in this context.").
text(contextMismatch(_), "That doesn't seem to fit what we were just discussing.").
text(contextMismatch(_), "I'm a bit confused by that remark given our current topic.").
text(contextMismatch(_), "I didn't quite catch how that relates to what we are doing.").
text(contextMismatch(_), "Could you stick to the current step? I didn't understand that.").

% Intent: farewell (Last Topic Check: mention restart option)
text(farewell, "Goodbye! Happy cooking. (Or say 'start over' if you want to find another recipe!)").
text(farewell, "See you later! (Or say 'start over' if you want to find another recipe!)").
text(farewell, "Bye bye. (Or say 'start over' if you want to find another recipe!)").
text(farewell, "Have a great meal! (Or say 'start over' if you want to find another recipe!)").
text(farewell, "Take care and enjoy your food! (Or say 'start over' if you want to find another recipe!)").

% Intent: greeting

text(greeting, "Hey there!").
text(greeting, "Hello!").
text(greeting, "Hi there!").
text(greeting, "Welcome!").
text(greeting, "Good to see you!").

% Intent: paraphraseRequest

text(paraphraseRequest, "What do you mean?").
text(paraphraseRequest, "I'm sorry, I didn't catch that.").
text(paraphraseRequest, "Could you say that again?").
text(paraphraseRequest, "I missed that, could you repeat it?").
text(paraphraseRequest, "Sorry, I didn't hear you clearly.").

% Intent: selfIdentification (for self-identification of the agent)

text(selfIdentification, Txt) :-
    agentName(Name),
    string_concat("My name is ", Name, Txt).
text(selfIdentification, Txt) :-
    agentName(Name),
    string_concat("I am called ", Name, Txt).
text(selfIdentification, Txt) :-
    agentName(Name),
    string_concat("You can call me ", Name, Txt).
text(selfIdentification, Txt) :-
    agentName(Name),
    string_concat("Hello, I am ", Name, Txt).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Scripted text and phrases for ** DOMAIN SPECIFIC ** intents (sorted on intent name)	%%%
%%% Text is only provided for those intents that the agent will generate (use). 	%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Intent: ackFilter (acknowledge filters added; there are recipes that satisfy all filters)
	
text(ackFilter, Txt) :-
    not(recipesFiltered([])),
    getParamsPatternInitiatingIntent(user, addFilter, Params),
    filters_to_text(Params, TxtPart2),
    string_concat("Here are recipes that ", TxtPart2, Txt1),
    string_concat(Txt1, ". Anything else I should add?", Txt).

text(ackFilter, Txt) :-
    not(recipesFiltered([])),
    getParamsPatternInitiatingIntent(user, addFilter, Params),
    filters_to_text(Params, TxtPart2),
    string_concat("I've found dishes that ", TxtPart2, Txt1),
    string_concat(Txt1, ". Do you want to filter more?", Txt).

text(ackFilter, Txt) :-
    not(recipesFiltered([])),
    getParamsPatternInitiatingIntent(user, addFilter, Params),
    filters_to_text(Params, TxtPart2),
    string_concat("Okay, filtering for recipes that ", TxtPart2, Txt1),
    string_concat(Txt1, ". Any other preferences?", Txt).

text(ackFilter, Txt) :-
    not(recipesFiltered([])),
    getParamsPatternInitiatingIntent(user, addFilter, Params),
    filters_to_text(Params, TxtPart2),
    string_concat("Got it. Looking for meals that ", TxtPart2, Txt1),
    string_concat(Txt1, ". What else?", Txt).

text(ackFilter, Txt) :-
    not(recipesFiltered([])),
    getParamsPatternInitiatingIntent(user, addFilter, Params),
    filters_to_text(Params, TxtPart2),
    string_concat("So far I have options that ", TxtPart2, Txt1),
    string_concat(Txt1, ". Do you have more constraints?", Txt).
	
% Intent: featureInquiry

text(featureInquiry, "What kind of recipe would you like?") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 800.
text(featureInquiry, "We have so many options! What cuisine do you fancy?") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 800.
text(featureInquiry, "There are thousands of recipes. Any specific diet that you are looking for?") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 800.
text(featureInquiry, "To narrow it down, what main ingredients do you have available at home?") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 800.

% 15 < N =< 800

text(featureInquiry, "What other preference would you like to add?") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 15,
    N =< 800,
    not(memoryKeyValue('show', 'true')). 
text(featureInquiry, "How else should we filter this list?") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 15,
    N =< 800,
    not(memoryKeyValue('show', 'true')). 
text(featureInquiry, "Do you have any dietary restrictions to add?") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 15,
    N =< 800,
    not(memoryKeyValue('show', 'true')). 
text(featureInquiry, "Any specific cuisine you are in the mood for?") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 15,
    N =< 800,
    not(memoryKeyValue('show', 'true')). 
text(featureInquiry, "We still have quite a few. What ingredients do you dislike?") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 15,
    N =< 800,
    not(memoryKeyValue('show', 'true')).

%
text(featureInquiry, "There are no recipes matching these criteria, please remove more requirements.") :-
    recipesFiltered([]).
text(featureInquiry, "Nothing matches all those criteria. Maybe delete a restriction?") :-
    recipesFiltered([]).
text(featureInquiry, "Zero results found. You might need to be less specific.") :-
    recipesFiltered([]).
text(featureInquiry, "I can't find anything that matches everything. Try removing a constraint.") :-
    recipesFiltered([]).


% 0 < N =< 15
text(featureInquiry, "Here are some recipes that fit your requirements.") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 0,
    (
        N =< 15 ;
        memoryKeyValue('show', 'true')
    ).
text(featureInquiry, "Check out these options I found for you.") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 0,
    (
        N =< 15 ;
        memoryKeyValue('show', 'true')
    ).
text(featureInquiry, "I think you'll like these results. Take a look.") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 0,
    (
        N =< 15 ;
        memoryKeyValue('show', 'true')
    ).
text(featureInquiry, "Here is the selection based on what you told me.") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 0,
    (
        N =< 15 ;
        memoryKeyValue('show', 'true')
    ).
text(featureInquiry, "Please have a look at these matching dishes.") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 0,
    (
        N =< 15 ;
        memoryKeyValue('show', 'true')
    ).

% Intent: featureRemovalRequest

text(featureRemovalRequest, "Can you have a look again and remove one of your recipe requirements?").
text(featureRemovalRequest, "It's a bit too specific. Could you remove a filter?").
text(featureRemovalRequest, "Please delete one preference so I can find matches.").
text(featureRemovalRequest, "Try taking back one of your requirements.").
text(featureRemovalRequest, "We need to broaden the search. Which filter should go?").


% Intent: noRecipesLeft

text(noRecipesLeft, "I added your request but I could not find a recipe that matches all of your preferences combined.").
text(noRecipesLeft, "That combination resulted in zero recipes found.").
text(noRecipesLeft, "I couldn't find a single recipe matching all those combined details.").
text(noRecipesLeft, "It seems those preferences conflict, as I found no matches.").
text(noRecipesLeft, "I searched the database, but nothing fits all those specific needs.").


% Intent: pictureGranted

text(pictureGranted, "Okay. Here is a list of recipes that you can choose from.").
text(pictureGranted, "Showing you the matching recipes now.").
text(pictureGranted, "Alright, take a look at what I found.").
text(pictureGranted, "Here is the list based on your preferences.").
text(pictureGranted, "I've updated the list for you to browse.").


% Intent: pictureNotGranted

text(pictureNotGranted, "Sorry, there are still too many recipes left to show them all. Please add more preferences.").
text(pictureNotGranted, "The list is still too long to display. Please refine your search.").
text(pictureNotGranted, "I have too many matches to show pictures yet. Add another filter?").
text(pictureNotGranted, "Please narrow it down further so I can show you the list.").
text(pictureNotGranted, "There are too many options to display just yet. What else do you want?").


% Intent: recipeChoiceReceipt (acknowledge user's choice of recipe)

text(recipeChoiceReceipt, Txt) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat(Name, ' is a great choice!', Txt).
text(recipeChoiceReceipt, Txt) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat(Name, ' sounds delicious!', Txt).
text(recipeChoiceReceipt, Txt) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat(Name, ' is an excellent selection.', Txt).
text(recipeChoiceReceipt, Txt) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat(Name, ' is a tasty option.', Txt).
text(recipeChoiceReceipt, Txt) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat(Name, ' will be fun to cook!', Txt).


% Intent: recommend (a recipe)

text(recommend, Output) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat("What about ", Name, TempString),
    string_concat(TempString, "?", Output).
text(recommend, Output) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat("How does ", Name, TempString),
    string_concat(TempString, " sound?", Output).
text(recommend, Output) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat("Would you like to try ", Name, TempString),
    string_concat(TempString, "?", Output).
text(recommend, Output) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat("I suggest cooking ", Name, TempString),
    string_concat(TempString, ".", Output).
text(recommend, Output) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat("Do you fancy ", Name, TempString),
    string_concat(TempString, "?", Output).


% Intent: recipeCheck

text(a50recipeSelect, contextMismatch(Intent), Txt) :-
    recipesFiltered(Recipes), length(Recipes, L), L>0,
    convertIntent(Intent, IntentString),
    string_concat("I'm not sure I got what you said. ", IntentString, Txt1),
    string_concat(Txt1, ", but I was expecting you to add or remove recipe preferences.", Txt).

text(a50recipeSelect, contextMismatch(Intent), Txt) :-
    recipesFiltered(Recipes), length(Recipes, L), L>0,
    convertIntent(Intent, IntentString),
    string_concat("That doesn't fit here. ", IntentString, Txt1),
    string_concat(Txt1, ". Please tell me if you want to modify your search.", Txt).

text(a50recipeSelect, contextMismatch(Intent), Txt) :-
    recipesFiltered(Recipes), length(Recipes, L), L>0,
    convertIntent(Intent, IntentString),
    string_concat("I'm confused. ", IntentString, Txt1),
    string_concat(Txt1, ". We are currently filtering recipes.", Txt).

text(a50recipeSelect, contextMismatch(Intent), Txt) :-
    recipesFiltered(Recipes), length(Recipes, L), L>0,
    convertIntent(Intent, IntentString),
    string_concat("Please stick to the recipe search. ", IntentString, Txt1),
    string_concat(Txt1, ", but I need a recipe preference.", Txt).

text(a50recipeSelect, contextMismatch(Intent), Txt) :-
    recipesFiltered(Recipes), length(Recipes, L), L>0,
    convertIntent(Intent, IntentString),
    string_concat("I didn't understand that within this context. ", IntentString, Txt1),
    string_concat(Txt1, ". Do you want to add a filter?", Txt).


% Intent: specifyGoal (asking a user about recipe features they are looking for)

text(specifyGoal, "What recipe would you like to cook?").
text(specifyGoal, "What would you like to cook today?").
text(specifyGoal, "What kind of recipe are you looking for today?").
text(specifyGoal, "What are you in the mood for?").
text(specifyGoal, "How can I help you pick a meal?").


% Intent: ackFilterEnd (User said No -> Show list)
text(ackFilterEnd, "Okay! Have a look at the recipes I found for you.").
text(ackFilterEnd, "Understood. Here is the final list.").
text(ackFilterEnd, "Great, let's look at the results.").
text(ackFilterEnd, "Alright, here is what I found.").
text(ackFilterEnd, "Check out these matching dishes.").

% Intent: tooManyRecipesLeft (User said No -> List too long)
text(tooManyRecipesLeft, "I still have quite a few recipes left. It might be easier if you add one more preference, like a main ingredient or cuisine.").
text(tooManyRecipesLeft, "There are still a lot of options. Maybe specify a cuisine?").
text(tooManyRecipesLeft, "I need a bit more detail before showing the list. Any dietary needs?").
text(tooManyRecipesLeft, "To give you a good list, I need one more filter.").
text(tooManyRecipesLeft, "Please help me narrow this down a bit more first.").

%%% C3.0: Describe Capabilities
% Response when the user asks "What can you do?".
text(describeCapability, "I can help you select a meal to cook. You can ask for a specific recipe, or filter recipes by ingredients, cuisine, or diet.").
text(describeCapability, "I am a recipe assistant. I can find meals based on your preferences.").
text(describeCapability, "My job is to find you the perfect recipe based on ingredients or diet.").
text(describeCapability, "Ask me for a recipe name, or tell me what ingredients you have.").
text(describeCapability, "I can filter a database of recipes to help you decide what to cook.").


%%% B1.2: Paraphrase Request (Fallback)
% Responses when the agent does not recognize the user's speech at all.


%%% B1.3: Out of Context Responses
% Helper: Convert Intent to a human-readable string 

convertIntent(appreciation, "You were expressing an appreciation").
convertIntent(checkCapability, "You asked what I can do for you").
convertIntent(greeting, "You were saying Hi").
convertIntent(requestRecommendation, "You were asking me to pick a recipe for you").
convertIntent(recipeRequest, "You were asking for a specific recipe").

convertIntent(_, "You said something I recognized"). 


text(clearMemory, ".").