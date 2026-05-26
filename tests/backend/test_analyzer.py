"""Tests for the static analyzer: constant folding, name checks, goto resolution, flattening."""

from __future__ import annotations

from typing import cast

import pytest

from spl.backend.analyzer import AnalyzedProgram, analyze
from spl.errors import AnalysisError
from spl.frontend.ast import (
    Assignment,
    BinaryOp,
    Conditional,
    Dialogue,
    Goto,
    Number,
    Program,
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
