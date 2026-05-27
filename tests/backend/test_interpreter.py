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


_GOTO_ACT = """Return to Act.

Romeo, a person.
Juliet, a person.

Act I: first.
Scene I: only.
[Enter Romeo and Juliet]
Romeo: You are a flower. Let us return to act II.
Romeo: You are nothing. Open your heart!

Act II: second.
Scene I: only.
Romeo: Open your heart!
"""


def test_goto_act_jumps_to_act_start() -> None:
    # ADR-0002 (ACT_TARGET_GOTO): we accept act targets as a spec-faithful superset; the oracle
    # parse-errors on them, so this cannot be a differential fixture. The goto fires before "You are
    # nothing", so Juliet keeps the flower (1) set just before the jump and Act II prints it. Were
    # the act goto a no-op, the intervening "You are nothing" would run and the output would be "0".
    assert run_play(_GOTO_ACT) == "1"


def test_cube() -> None:
    # cat=1, doubled by "happy" = 2, cubed = 8
    out = run_scene(
        "[Enter Romeo and Juliet]\nRomeo: You are the cube of a happy cat. Open your heart!"
    )
    assert out == "8"


def test_square_root() -> None:
    # cat=1, doubled twice = 4, square root = 2
    out = run_scene(
        "[Enter Romeo and Juliet]\n"
        "Romeo: You are the square root of a happy happy cat. Open your heart!"
    )
    assert out == "2"


def test_character_reference_reads_value() -> None:
    # Juliet := flower(1); then Juliet := Juliet(1) + flower(1) = 2, referencing Juliet by name.
    out = run_scene(
        "[Enter Romeo and Juliet]\n"
        "Romeo: You are a flower. You are the sum of Juliet and a flower. Open your heart!"
    )
    assert out == "2"


def test_breakpoint_is_ignored() -> None:
    out = run_play(
        "A Test.\n\nRomeo, a person.\nJuliet, a person.\n\nAct I: a.\nScene I: s.\n"
        "[Enter Romeo and Juliet]\n[A pause]\nRomeo: You are a flower. Open your heart!\n"
    )
    assert out == "1"


# ---- full comparative set (issue 03) ----


def _question_branch(comparative: str, *, romeo: str, juliet: str) -> str:
    """Set Juliet := `juliet`, then ask `Are you <comparative> <romeo>?`.

    The Question's left operand is "you" (the Addressee, Juliet, holding `juliet`) and its right
    operand is the Constant `romeo`; the true branch outputs Juliet's value. We drive both operands
    through known Constants so each comparative kind is exercised against known values.
    """
    return run_scene(
        "[Enter Romeo and Juliet]\n"
        f"Romeo: You are {juliet}. "
        f"Are you {comparative} {romeo}? If so, open your heart!"
    )


def test_bigger_than_is_greater_than() -> None:
    # you(Juliet)=2 ; "a cat"=1 ; 2 > 1 true -> prints 2
    assert _question_branch("bigger than", romeo="a cat", juliet="a happy cat") == "2"


def test_smaller_than_is_less_than() -> None:
    # you=1 ; "a happy cat"=2 ; 1 < 2 true -> prints 1
    assert _question_branch("smaller than", romeo="a happy cat", juliet="a cat") == "1"


def test_punier_than_is_less_than() -> None:
    assert _question_branch("punier than", romeo="a happy cat", juliet="a cat") == "1"


def test_worse_than_is_less_than() -> None:
    assert _question_branch("worse than", romeo="a happy cat", juliet="a cat") == "1"


def test_fresher_friendlier_nicer_jollier_are_greater_than() -> None:
    for word in ("fresher than", "friendlier than", "nicer than", "jollier than"):
        assert _question_branch(word, romeo="a cat", juliet="a happy cat") == "2"


def test_neutral_as_adjective_as_is_equality() -> None:
    # you=1 ; "a cat"=1 ; equal -> prints 1
    assert _question_branch("as good as", romeo="a cat", juliet="a cat") == "1"


def test_more_positive_adjective_is_greater_than() -> None:
    # you=2 > 1 -> true
    assert _question_branch("more cunning than", romeo="a cat", juliet="a happy cat") == "2"


def test_more_negative_adjective_is_less_than() -> None:
    # you=1 < 2 -> true
    assert _question_branch("more rotten than", romeo="a happy cat", juliet="a cat") == "1"


# ---- stacks: Remember / Recall (issue 02) ----


def test_remember_then_recall_roundtrips_through_the_stack() -> None:
    # Romeo addresses Juliet: push 1 onto Juliet's stack, overwrite her value with 5, then Recall
    # pops the stack back into her value. Output 1.
    out = run_scene(
        "[Enter Romeo and Juliet]\n"
        "Romeo: You are a flower. Remember you! "  # push Juliet's value (1) onto Juliet's stack
        "You are the sum of a flower and the sum of a flower and the sum of a flower and a flower. "
        "Recall your buried memory! Open your heart!"
    )
    assert out == "1"


def test_recall_is_lifo() -> None:
    # Push 1 then 2 onto Juliet's stack; two Recalls pop 2 then 1.
    out = run_scene(
        "[Enter Romeo and Juliet]\n"
        "Romeo: You are a flower. Remember you! "  # push 1
        "You are the sum of a flower and a flower. Remember you! "  # push 2
        "Recall it! Open your heart! "  # pop 2
        "Recall it! Open your heart!"  # pop 1
    )
    assert out == "21"


def test_recall_from_empty_stack_raises() -> None:
    with pytest.raises(RuntimeSplError, match="empty stack"):
        run_scene("[Enter Romeo and Juliet]\nRomeo: Recall your nonexistent past!")


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


def test_modulo_by_zero_raises() -> None:
    with pytest.raises(RuntimeSplError, match="modulo by zero"):
        run_scene(
            "[Enter Romeo and Juliet]\n"
            "Romeo: You are the remainder of the quotient between a flower and nothing. "
            "Open your heart!"
        )


def test_square_root_of_negative_raises() -> None:
    with pytest.raises(RuntimeSplError, match="square root of a negative"):
        run_scene(
            "[Enter Romeo and Juliet]\n"
            "Romeo: You are the square root of the difference between nothing and a flower. "
            "Open your heart!"
        )


def test_conditional_without_preceding_question_raises() -> None:
    # ADR-0001 (DANGLING_CONDITIONAL): with no prior Question the boolean register has no defined
    # value, so we raise rather than default it false. The oracle defaults false and runs the "If
    # not" branch, so this is a documented intentional divergence -- and because we raise it cannot
    # be a golden/differential fixture; it only lives here as a unit test.
    with pytest.raises(RuntimeSplError, match="conditional without a preceding question"):
        run_scene("[Enter Romeo and Juliet]\nRomeo: If so, open your heart!")
