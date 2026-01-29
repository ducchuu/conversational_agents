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

% Intent: contextMismatch(Intent)

text(contextMismatch(_), "I am not sure what that means in this context.").

% Intent: farewell
text(farewell, "Goodbye! Happy cooking.").
text(farewell, "See you later!").
text(farewell, "Bye bye.").

% Intent: greeting

text(greeting, "Hey there!").
text(greeting, "Hello!").
text(greeting, "Hi there!").
text(greeting, "Welcome!").

% Intent: paraphraseRequest

text(paraphraseRequest, "What do you mean?").
text(paraphraseRequest, "I'm sorry, I didn't catch that.").
text(paraphraseRequest, "Could you say that again?").

% Intent: selfIdentification (for self-identification of the agent)

text(selfIdentification, Txt) :-
    agentName(Name),
    string_concat("My name is ", Name, Txt).

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
	
% Intent: featureInquiry

text(featureInquiry, "What kind of recipe would you like?") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 800.

text(featureInquiry, "What other preference would you like to add?") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 15,
    N =< 800,
    not(memoryKeyValue('show', 'true')). 

%
text(featureInquiry, "There are no recipes matching these criteria, please remove more requirements.") :-
    recipesFiltered([]).


text(featureInquiry, "Here are some recipes that fit your requirements.") :-
    recipesFiltered(Recipes), length(Recipes, N),
    N > 0,
    (
        N =< 15 ;
        memoryKeyValue('show', 'true')
    ).

% Intent: featureRemovalRequest

text(featureRemovalRequest, "Can you have a look again and remove one of your recipe requirements?").


% Intent: noRecipesLeft

text(noRecipesLeft, "I added your request but I could not find a recipe that matches all of your preferences combined.").


% Intent: pictureGranted

text(pictureGranted, "Okay. Here is a list of recipes that you can choose from.").


% Intent: pictureNotGranted

text(pictureNotGranted, "Sorry, there are still too many recipes left to show them all. Please add more preferences.").


% Intent: recipeChoiceReceipt (acknowledge user's choice of recipe)

text(recipeChoiceReceipt, Txt) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat(Name, ' is a great choice!', Txt).


% Intent: recommend (a recipe)

text(recommend, Output) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat("What about ", Name, TempString),
    string_concat(TempString, "?", Output).


% Intent: recipeCheck

text(a50recipeSelect, contextMismatch(Intent), Txt) :-
    recipesFiltered(Recipes), length(Recipes, L), L>0,
    convertIntent(Intent, IntentString),
    string_concat("I'm not sure I got what you said. ", IntentString, Txt1),
    string_concat(Txt1, ", but I was expecting you to add or remove recipe preferences.", Txt).


% Intent: specifyGoal (asking a user about recipe features they are looking for)

text(specifyGoal, "What recipe would you like to cook?").
text(specifyGoal, "What would you like to cook today?").
text(specifyGoal, "What kind of recipe are you looking for today today?").


% Intent: ackFilterEnd (User said No -> Show list)
text(ackFilterEnd, "Okay! Have a look at the recipes I found for you.").

% Intent: tooManyRecipesLeft (User said No -> List too long)
text(tooManyRecipesLeft, "I still have quite a few recipes left. It might be easier if you add one more preference, like a main ingredient or cuisine.").

%%% C3.0: Describe Capabilities
% Response when the user asks "What can you do?".
text(describeCapability, "I can help you select a meal to cook. You can ask for a specific recipe, or filter recipes by ingredients, cuisine, or diet.").


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