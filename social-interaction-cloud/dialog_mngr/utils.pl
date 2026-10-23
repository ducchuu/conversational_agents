%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% 	Helper predicates for the conversion of atoms and input values			%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% convert_to_int(+Input, -Int)
% Convert an atom or float (e.g. 9.0 received as entity from DialogFlow) to an integer.
convert_to_int(Input, Int) :- atom(Input), atom_number(Input, Float), Int is integer(Float).
convert_to_int(Input, Int) :- number(Input), Int is integer(Input).

% convert to string
convert_to_string(Input, String) :- atom(Input), atom_string(Input, String).
convert_to_string(Input, String) :- string(Input), String = Input.
convert_to_string(Input, String) :- number(Input), number_string(Input, String).
convert_to_string(Input, String) :- is_list(Input), list_to_string(Input, String).

% duration_to_min(+Duration, -Minutes) 
% Convert duration (e.g., [amount = 2, unit = hour]) to minutes so it can be matched to the
% database. DialogFlow also has units for "wk": week, "mo": month, "yr": year, "decade",
% and "century" which are not handled here; NOTE: if any of these units are used, the agent
% will get stuck!
duration_to_min(Duration, Minutes)
	:- member('amount' = A, Duration), member('unit' = Unit, Duration),
		convert_to_int(A, Amount), 
		duration_to_min(Amount, Unit, Minutes).
duration_to_min(Amount, 's', Minutes) :- Minutes is div(Amount, 60).
duration_to_min(Amount, 'min', Amount).
duration_to_min(Amount, 'h', Minutes) :- Minutes is Amount*60.
duration_to_min(Amount, 'day', Minutes) :- Minutes is Amount*60*24.

/**
 *
**/
list_to_string([], "").
list_to_string([Input], String) :- convert_to_string(Input, String).
list_to_string([Input1, Input2 | List], String) :- 
	convert_to_string(Input1, Str1), 
	list_to_string([Input2 | List], Str2),
	string_concat(Str1, " and ", Str3),
	string_concat(Str3, Str2, String).
	
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% 	Helper predicates for the changing case of strings				%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% downcase_values(+Params, -DownCaseParams)
% This predicate downcases the input values from the user so they can be matched to the database.
downcase_values([], []).
downcase_values([Key=Value | Rest], [Key=DownValue | DownRest]) :-
	downcase_atom(Value, DownValue), downcase_values(Rest, DownRest).
	
% Make sure first character in a string is upper case
to_upper_case(AtomIn, StringOut) :-
	% make sure we have a string...
	atomics_to_string([AtomIn], StringIn),
	% now convert first character to capital case
	string_chars(StringIn, [First | Rest]),
	upcase_atom(First, UpperCase),
	string_chars(StringOut, [UpperCase | Rest]).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% 	Helper predicate for applying a template (inserting Content into the Template)	%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
applyTemplate(Template, Content, Result) :-
	atomic(Content), format(atom(Result), Template, [Content]).
applyTemplate(Template, ParameterList, Result) :-
	is_list(ParameterList), format(atom(Result), Template, ParameterList).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% 	Helper predicate for converting Prolog objects into strings for logging		%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
/**
 * log_info(+TypeString, +Term, -InfoString)
 *
 * Prefix TypeString to the Term turned into an atom to return an Info string that can be
 * fed into the log action of MARBEL.
 *
 * @TypeString: A string.
 * @Term: Any Prolog term.
 * @InfoString: String where TypeString has been prefixed to Term.
**/
log_info(TypeString, Term, InfoString) :-
	term_to_atom(Term, Atom), string_concat(TypeString, Atom, InfoString).