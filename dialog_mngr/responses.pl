%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Responses
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
:- dynamic text/2, text/3.

flagResponse('mic', 'Please press Start first') :- flag('mic'), waitingForEvent('start').
flagResponse('mic', 'I am already listening') :- flag('mic'), listening.
flagResponse('mic', "Please, I'm talking") :- flag('mic'), talking.
flagResponse('mic', 'Not available right now') :- flag('mic'), not(waitingForEvent(_)).
flagResponse(_, '').

text_generator(Intent, SelectedText) :-
	currentTopLevel(PatternId),
	findall(Text, text(PatternId, Intent, Text), Texts),
	random_select(SelectedText, Texts, _).
text_generator(Intent, SelectedText) :-
	findall(Text, text(Intent, Text), Texts), random_select(SelectedText, Texts, _).

text(greeting, "Hey there!").
text(greeting, "Hello!").
text(greeting, "Hi there!").
text(greeting, "Welcome!").

text(selfIdentification, Txt) :-
    agentName(Name),
    string_concat("My name is ", Name, Txt).

% Intent: ackFilter
text(ackFilter, Txt) :-
	not(recipesFiltered([])),
	getParamsPatternInitiatingIntent(user, addFilter, Params),
	filters_to_text(Params, TxtPart2),
	string_concat("Here are recipes that ", TxtPart2, Txt1),
	string_concat(Txt1, ". Anything else I should add?", Txt).

% Intent: ackFilterEnd (User said No -> Show list)
text(ackFilterEnd, "Okay! Have a look at the recipes I found for you.").

% Intent: tooManyRecipesLeft (User said No -> List too long)
text(tooManyRecipesLeft, "I still have quite a few recipes left. It might be easier if you add one more preference, like a main ingredient or cuisine.").

% Intent: noRecipesLeft
text(noRecipesLeft, "I added your request but I could not find a recipe that matches all of your preferences combined.").

% Intent: featureRemovalRequest
text(featureRemovalRequest, "Can you have a look again and remove one of your recipe requirements?").

text(recipeChoiceReceipt, Txt) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat(Name, ' is a great choice!', Txt).

text(recommend, Output) :-
    currentRecipe(RecipeID),
    recipeName(RecipeID, Name),
    string_concat("What about ", Name, TempString),
    string_concat(TempString, "?", Output).

text(specifyGoal, "What recipe would you like to cook?").
text(specifyGoal, "What would you like to cook today?").
text(specifyGoal, "What kind of recipe are you looking for today today?").

text(clearMemory, ".").