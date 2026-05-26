"""Interpreter semantics: arithmetic, I/O, conditionals, gotos, and the dynamic errors (D2)."""

from __future__ import annotations

from typing import cast

import pytest

from spl.backend.analyzer import analyze
from spl.backend.interpreter import Interpreter
from spl.backend.io import BufferIO
from spl.errors import RuntimeSplError
from spl.frontend.ast import Program
from spl.frontend.parser import parse


def run_play(play: str, stdin: str = "") -> str:
    program = analyze(cast(Program, parse(play)))
    io = BufferIO(stdin)
    Interpreter(program, io).run()
    return io.output


def run_scene(
    body: str, *, personae: tuple[str, ...] = ("Romeo", "Juliet"), stdin: str = ""
) -> str:
    persona_block = "\n".join(f"{name}, a person." for name in personae)
    play = f"A Test.\n\n{persona_block}\n\nAct I: a.\nScene I: s.\n{body}\n"
    return run_play(play, stdin)


def test_arithmetic_number_output() -> None:
    # flower = 1; "a happy cat" = cat(1) doubled by one adjective = 2; sum = 3.
    out = run_scene(
        "[Enter Romeo and Juliet]\n"
        "Romeo: You are the sum of a flower and a happy cat. Open your heart!"
    )
    assert out == "3"


def test_character_io_roundtrip() -> None:
    # Read a number into Juliet, then print it as a character: 65 -> 'A'.
    out = run_scene(
        "[Enter Romeo and Juliet]\nRomeo: Listen to your heart. Speak your mind!", stdin="65"
    )
    assert out == "A"


def test_negative_value_via_difference() -> None:
    out = run_scene(
        "[Enter Romeo and Juliet]\n"
        "Romeo: You are nothing. You are the difference between you and a flower. Open your heart!"
    )
    assert out == "-1"


def test_conditional_true_branch_runs() -> None:
    out = run_scene(
        "[Enter Romeo and Juliet]\n"
        "Romeo: You are a flower. Are you better than nothing? If so, open your heart!"
    )
    assert out == "1"


def test_conditional_false_branch_skipped() -> None:
    out = run_scene(
        "[Enter Romeo and Juliet]\n"
        "Romeo: You are nothing. Are you better than a flower? If so, open your heart!"
    )
    assert out == ""


_COUNTDOWN = """Countdown.

Romeo, a person.
Juliet, a person.

Act I: counting.
Scene I: setup.
[Enter Romeo and Juliet]
Romeo: You are the sum of a flower and the sum of a flower and a flower.
Scene II: loop.
Romeo: Open your heart! You are the difference between you and a flower.
Are you better than nothing? If so, let us return to scene II.
"""


def test_goto_loop_counts_down() -> None:
    # Juliet starts at 3, prints then decrements while > 0: 3, 2, 1.
    assert run_play(_COUNTDOWN) == "321"


# ---- dynamic errors (D2) ----


def test_division_by_zero_raises() -> None:
    with pytest.raises(RuntimeSplError, match="division by zero"):
        run_scene(
            "[Enter Romeo and Juliet]\n"
            "Romeo: You are the quotient between a flower and nothing. Open your heart!"
        )


def test_more_than_two_on_stage_raises() -> None:
    with pytest.raises(RuntimeSplError):
        run_scene(
            "[Enter Romeo and Juliet and Hamlet]\nRomeo: Open your heart!",
            personae=("Romeo", "Juliet", "Hamlet"),
        )


def test_invalid_character_output_raises() -> None:
    with pytest.raises(RuntimeSplError):
        run_scene(
            "[Enter Romeo and Juliet]\n"
            "Romeo: You are nothing. "
            "You are the difference between you and a flower. Speak your mind!"
        )


def test_speaker_not_on_stage_raises() -> None:
    with pytest.raises(RuntimeSplError, match="not on stage"):
        run_scene("[Enter Romeo]\nJuliet: Open your heart!")
