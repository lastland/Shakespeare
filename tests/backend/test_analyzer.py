"""Tests for the static analyzer: constant folding, name checks, goto resolution, flattening."""

from __future__ import annotations

from typing import cast

import pytest

from spl.backend.analyzer import AnalyzedProgram, analyze
from spl.errors import AnalysisError
from spl.frontend.ast import (
    Assignment,
    BinaryOp,
    CharacterRef,
    Conditional,
    Dialogue,
    Goto,
    Number,
    Program,
    Question,
)
from spl.frontend.parser import parse


def _analyze(body: str, personae: tuple[str, ...] = ("Romeo", "Juliet")) -> AnalyzedProgram:
    persona_block = "\n".join(f"{name}, a person." for name in personae)
    play = f"A Test.\n\n{persona_block}\n\nAct I: first.\nScene I: only.\n{body}\n"
    return analyze(cast(Program, parse(play)))


def _first_statement(program: AnalyzedProgram) -> object:
    dialogue = next(line for line in program.lines if isinstance(line, Dialogue))
    return dialogue.statements[0]


def test_declares_characters() -> None:
    program = _analyze("Romeo: You are nothing.")
    assert program.characters == {"Romeo", "Juliet"}


def test_folds_constant_arithmetic() -> None:
    program = _analyze("Romeo: You are the sum of a flower and a pig.")
    # flower = +1 (positive), pig = -1 (negative)
    assert _first_statement(program) == Assignment(BinaryOp("sum", Number(1), Number(-1)))


def test_adjective_doubles() -> None:
    program = _analyze("Romeo: You are an amazing cat.")
    # cat = +1 (neutral), one adjective doubles → 2
    assert _first_statement(program) == Assignment(Number(2))


def test_nothing_is_zero() -> None:
    program = _analyze("Romeo: You are nothing.")
    assert _first_statement(program) == Assignment(Number(0))


def test_character_name_folds_to_reference() -> None:
    program = _analyze("Romeo: You are Juliet.")
    assert _first_statement(program) == Assignment(CharacterRef("Juliet"))


def test_articled_character_name_in_value_folds_to_reference() -> None:
    # "the Ghost" in value position: the determiner "the" is re-prepended to match the declared
    # character "The Ghost" (issue 09, facet 2). Used in primes.spl ("more cunning than the Ghost").
    program = _analyze("Romeo: You are the Ghost.", personae=("Romeo", "Juliet", "The Ghost"))
    assert _first_statement(program) == Assignment(CharacterRef("The Ghost"))


def test_article_before_undeclared_capitalized_word_stays_a_constant() -> None:
    # Negative case: when the capitalized word after an article does NOT name a declared character,
    # it must fold as a constant noun, not a character reference. "King" is a positive noun (=1);
    # here no character "The King" is declared, so "the King" stays the constant 1. The leading-the
    # retry fails to find a character and falls through to the noun value rather than erroring.
    program = _analyze("Romeo: You are the King.")
    assert _first_statement(program) == Assignment(Number(1))


def test_non_the_determiner_does_not_resolve_to_articled_character() -> None:
    # Issue 18: only a literal leading "the" may match a "The X" character. With "The Ghost"
    # declared, "his Ghost" must NOT fold to that character; it falls through to noun-phrase
    # resolution, and "ghost" is not a noun, so it raises an unknown-noun error.
    with pytest.raises(AnalysisError, match="unknown noun: 'Ghost'"):
        _analyze("Romeo: You are his Ghost.", personae=("Romeo", "Juliet", "The Ghost"))


def test_bare_name_does_not_resolve_to_articled_character() -> None:
    # Issue 18: a bare "Ghost" (no determiner) is not the "The Ghost" character either; it falls
    # through to noun-phrase resolution and raises unknown-noun ("ghost" is not a noun).
    with pytest.raises(AnalysisError, match="unknown noun: 'Ghost'"):
        _analyze("Romeo: You are Ghost.", personae=("Romeo", "Juliet", "The Ghost"))


def test_a_determiner_does_not_resolve_to_articled_character() -> None:
    # Issue 18: "a Ghost" (a non-"the" determiner) is likewise not the character.
    with pytest.raises(AnalysisError, match="unknown noun: 'Ghost'"):
        _analyze("Romeo: You are a Ghost.", personae=("Romeo", "Juliet", "The Ghost"))


def test_the_before_bare_character_name_still_resolves() -> None:
    # Issue 18 regression: a leading "the" is harmless when the bare form already names a character.
    # "the Romeo" resolves to CharacterRef("Romeo") via the bare match, before the the-retry.
    program = _analyze("Juliet: You are the Romeo.")
    assert _first_statement(program) == Assignment(CharacterRef("Romeo"))


def test_capitalized_noun() -> None:
    program = _analyze("Romeo: You are a King.")  # King is a positive noun, not a character here
    assert _first_statement(program) == Assignment(Number(1))


def test_multiword_noun_with_adjective() -> None:
    # noun is the multi-word "summer's day" (=1), doubled by the adjective "lovely"
    program = _analyze("Romeo: You are a lovely summer's day.")
    assert _first_statement(program) == Assignment(Number(2))


def test_possessive_determiner_is_ignored() -> None:
    program = _analyze("Romeo: You are his horse.")  # horse = +1
    assert _first_statement(program) == Assignment(Number(1))


def test_thine_possessive_determiner_is_ignored() -> None:
    # `thine` is a second-person possessive determiner (not an adjective); it is dropped, leaving
    # the noun. (sierpinski.spl uses "thine goat".) goat = -1 (negative noun).
    program = _analyze("Romeo: You are thine goat.")
    assert _first_statement(program) == Assignment(Number(-1))


def test_polarity_mismatch_positive_adjective_negative_noun_is_accepted() -> None:
    # ADR-0007 (issue 25): the reference parse-errors on a polarity mismatch (positive adjective on
    # a negative noun), but our analyzer never checks adjective polarity — it accepts the phrase and
    # folds it. "happy" (positive adjective) + "coward" (negative noun) -> -1 * 2^1 = -2. Pinned so
    # the intentional superset cannot silently regress.
    program = _analyze("Romeo: You are a happy coward.")
    assert _first_statement(program) == Assignment(Number(-2))


def test_polarity_mismatch_negative_adjective_positive_noun_is_accepted() -> None:
    # ADR-0007 (issue 25): the mirror case. "evil" (negative adjective) + "King" (positive noun) is
    # a polarity mismatch the reference rejects; we accept it and fold to +1 * 2^1 = 2.
    program = _analyze("Romeo: You are an evil King.")
    assert _first_statement(program) == Assignment(Number(2))


def test_unknown_noun_raises() -> None:
    with pytest.raises(AnalysisError, match="unknown noun"):
        _analyze("Romeo: You are a florp.")


def test_unknown_adjective_raises() -> None:
    with pytest.raises(AnalysisError, match="unknown adjective"):
        _analyze("Romeo: You are a florpy cat.")


def test_undeclared_speaker_raises() -> None:
    # Hamlet is a real character but is not in this play's Dramatis Personae.
    with pytest.raises(AnalysisError, match="not in the Dramatis Personae"):
        _analyze("Hamlet: You are nothing.")


def test_unknown_character_in_personae_raises() -> None:
    with pytest.raises(AnalysisError, match="unknown character"):
        _analyze("Romeo: You are nothing.", personae=("Romeo", "Florp"))


def test_duplicate_persona_raises() -> None:
    with pytest.raises(AnalysisError, match="declared twice"):
        _analyze("Romeo: You are nothing.", personae=("Romeo", "Romeo"))


# ---- `more <adjective> than` resolution (issue 03) ----


def _first_question(body: str) -> Question:
    program = _analyze(body)
    dialogue = next(line for line in program.lines if isinstance(line, Dialogue))
    question = next(s for s in dialogue.statements if isinstance(s, Question))
    return question


def test_more_positive_adjective_resolves_to_gt() -> None:
    # "cunning" is a positive adjective -> greater-than.
    question = _first_question("Romeo: Am I more cunning than you?")
    assert question.comparison == "gt"


@pytest.mark.parametrize("word", ["big", "huge", "tiny", "little", "small"])
def test_more_neutral_adjective_is_rejected(word: str) -> None:
    # The reference admits `more` only with a positive/negative adjective; a neutral adjective
    # there is rejected, the same strict way an unknown adjective is (issue 15). Previously these
    # fell into the "else -> gt" branch (e.g. `more tiny than` -> gt, backwards).
    with pytest.raises(AnalysisError, match="unknown adjective"):
        _analyze(f"Romeo: Am I more {word} than you?")


def test_more_negative_adjective_resolves_to_lt() -> None:
    # "rotten" is a negative adjective -> less-than.
    question = _first_question("Romeo: Am I more rotten than you?")
    assert question.comparison == "lt"


def test_simile_with_non_adjective_word_analyzes_to_eq() -> None:
    # ADR-0007 (issue 26): the reference's `as ADJ as` requires a known adjective and parse-errors
    # on a noun there; we admit any vocabulary word and discard it (the simile means equality
    # regardless). "cat" is a NOUN, yet `Are you as cat as a King?` analyzes cleanly to an `eq`
    # question — the analyzer never classifies the discarded word. Pinned so the superset can't
    # silently regress.
    question = _first_question("Romeo: Are you as cat as a King?")
    assert question.comparison == "eq"


def test_more_unknown_adjective_raises() -> None:
    with pytest.raises(AnalysisError, match="unknown adjective"):
        _analyze("Romeo: Am I more florpy than you?")


# ---- gotos + flattening across multiple scenes ----

_TWO_SCENES = """A Test.

Romeo, a person.
Juliet, a person.

Act I: first.
Scene I: opening.
[Enter Romeo and Juliet]
Romeo: You are nothing. If so, let us proceed to scene II.
Scene II: closing.
Juliet: Open your heart.
"""


def test_label_maps_and_flattening() -> None:
    program = analyze(cast(Program, parse(_TWO_SCENES)))
    assert program.act_starts == {1: 0}
    assert program.scene_starts == {(1, 1): 0, (1, 2): 2}
    # 3 flattened lines: Enter, Romeo's dialogue, Juliet's dialogue
    assert len(program.lines) == 3
    assert program.line_acts == (1, 1, 1)


def test_valid_goto_inside_conditional_resolves() -> None:
    program = analyze(cast(Program, parse(_TWO_SCENES)))
    romeo = program.lines[1]
    assert isinstance(romeo, Dialogue)
    assert romeo.statements[1] == Conditional(True, Goto("scene", 2))


def test_goto_to_undefined_scene_raises() -> None:
    with pytest.raises(AnalysisError, match="undefined scene"):
        _analyze("Romeo: You are nothing. If so, let us proceed to scene V.")


def test_goto_to_undefined_act_raises() -> None:
    with pytest.raises(AnalysisError, match="undefined act"):
        _analyze("Romeo: You are nothing. If so, let us return to act IX.")
