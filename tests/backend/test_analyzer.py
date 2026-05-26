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
    # here no character "The King" is declared, so "the King" stays the constant 1.
    program = _analyze("Romeo: You are the King.")
    assert _first_statement(program) == Assignment(Number(1))


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


def test_more_neutral_adjective_resolves_to_gt() -> None:
    # "big" is a neutral adjective -> greater-than (our documented superset over the reference,
    # which only allows positive adjectives after "more").
    question = _first_question("Romeo: Am I more big than you?")
    assert question.comparison == "gt"


def test_more_negative_adjective_resolves_to_lt() -> None:
    # "rotten" is a negative adjective -> less-than.
    question = _first_question("Romeo: Am I more rotten than you?")
    assert question.comparison == "lt"


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
