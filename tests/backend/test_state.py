"""Tests for the runtime character + stage model.

The stage enforces the project's "at most two interact" rule via `addressee`, and the
entry/exit bookkeeping (enter/exit/exeunt) per the SPL stage directions. Dynamic faults
raise `RuntimeSplError` (ADR-0001).
"""

from __future__ import annotations

import pytest

from spl.backend.state import Character, Stage
from spl.errors import RuntimeSplError


def test_character_defaults() -> None:
    c = Character()
    assert c.value == 0
    assert c.stack == []


def test_character_is_mutable() -> None:
    c = Character(value=5)
    c.value = 9
    c.stack.append(3)
    assert c.value == 9
    assert c.stack == [3]


def test_character_stacks_are_independent() -> None:
    a = Character()
    b = Character()
    a.stack.append(1)
    assert b.stack == []


def test_enter_then_on_stage_in_entry_order() -> None:
    stage = Stage()
    stage.enter("Romeo")
    stage.enter("Juliet")
    assert stage.on_stage() == ("Romeo", "Juliet")


def test_enter_multiple_at_once() -> None:
    stage = Stage()
    stage.enter("Romeo", "Juliet")
    assert stage.on_stage() == ("Romeo", "Juliet")


def test_enter_already_on_stage_raises() -> None:
    stage = Stage()
    stage.enter("Romeo")
    with pytest.raises(RuntimeSplError):
        stage.enter("Romeo")


def test_enter_duplicate_within_one_call_raises() -> None:
    stage = Stage()
    with pytest.raises(RuntimeSplError):
        stage.enter("Romeo", "Romeo")


def test_exit_character_removes_one() -> None:
    stage = Stage()
    stage.enter("Romeo", "Juliet")
    stage.exit_character("Romeo")
    assert stage.on_stage() == ("Juliet",)


def test_exit_character_not_on_stage_raises() -> None:
    stage = Stage()
    stage.enter("Romeo")
    with pytest.raises(RuntimeSplError):
        stage.exit_character("Juliet")


def test_exeunt_named_removes_those() -> None:
    stage = Stage()
    stage.enter("Romeo", "Juliet")
    stage.exeunt("Romeo")
    assert stage.on_stage() == ("Juliet",)


def test_exeunt_named_must_all_be_on_stage() -> None:
    stage = Stage()
    stage.enter("Romeo", "Juliet")
    with pytest.raises(RuntimeSplError):
        stage.exeunt("Romeo", "Macbeth")
    # nothing should have left
    assert stage.on_stage() == ("Romeo", "Juliet")


def test_exeunt_no_names_clears_stage() -> None:
    stage = Stage()
    stage.enter("Romeo", "Juliet")
    stage.exeunt()
    assert stage.on_stage() == ()


def test_addressee_returns_the_other() -> None:
    stage = Stage()
    stage.enter("Romeo", "Juliet")
    assert stage.addressee("Romeo") == "Juliet"
    assert stage.addressee("Juliet") == "Romeo"


def test_addressee_speaker_not_on_stage_raises() -> None:
    stage = Stage()
    stage.enter("Romeo", "Juliet")
    with pytest.raises(RuntimeSplError):
        stage.addressee("Macbeth")


def test_addressee_one_on_stage_raises() -> None:
    stage = Stage()
    stage.enter("Romeo")
    with pytest.raises(RuntimeSplError):
        stage.addressee("Romeo")


def test_addressee_three_on_stage_raises() -> None:
    stage = Stage()
    stage.enter("Romeo", "Juliet", "Macbeth")
    with pytest.raises(RuntimeSplError):
        stage.addressee("Romeo")


def test_reenter_after_exit_is_allowed() -> None:
    stage = Stage()
    stage.enter("Romeo", "Juliet")
    stage.exit_character("Romeo")
    stage.enter("Romeo")
    assert stage.on_stage() == ("Juliet", "Romeo")
