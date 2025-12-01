%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Responses when a flag has been set for a button.					%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% responses for NEW dialog agent 		   %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

flagResponse('mic', 'Please press Start first') :- flag('mic'), waitingForEvent('start').
flagResponse('mic', 'I am already listening') :-
	flag('mic'), listening.
% We might have just stopped listening but still waiting for results from intention
% detection; so case above does not apply but we still need user to be patient. Order of
% these rules therefore is also important.
%flagResponse('mic', 'Wait a second') :-
%	flag('mic'), waitingForEvent('IntentDetectionDone'). % WAIT A SECOND BUG
flagResponse('mic', "Please, I'm talking") :-
	flag('mic'), talking.
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


% Intent: contextMismatch(Intent)


% Intent: describeCapability


% Intent: farewell


% Intent: greeting
text(greeting, "Hey there!").

% Intent: paraphraseRequest


% Intent: selfIdentification (for self-identification of the agent)


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% Scripted text and phrases for ** DOMAIN SPECIFIC ** intents (sorted on intent name)	%%%
%%% Text is only provided for those intents that the agent will generate (use). 	%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Intent: ackFilter (acknowledge filters added; there are recipes that satisfy all filters)


% Intent: featureInquiry


% Intent: featureRemovalRequest


% Intent: noRecipesLeft


% Intent: pictureGranted


% Intent: pictureNotGranted


% Intent: recipeChoiceReceipt (acknowledge user's choice of recipe)


% Intent: recommend (a recipe)


% Intent: recipeCheck


% Intent: specifyGoal (asking a user about recipe features they are looking for)


text(clearMemory, ".").
