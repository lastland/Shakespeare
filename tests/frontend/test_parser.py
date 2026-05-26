"""Frontend parser/transformer tests, construct by construct, plus a full play."""

from __future__ import annotations

import pytest

from spl.errors import ParseError
from spl.frontend.ast import (
    Act,
    Assignment,
    BinaryOp,
    Conditional,
    Constant,
    Dialogue,
    Enter,
    Exeunt,
    Exit,
    Goto,
    InputChar,
    InputNumber,
    OutputChar,
    OutputNumber,
    Persona,
    Program,
    PronounValue,
    Question,
    Scene,
    UnaryOp,
)
from spl.frontend.parser import parse

# ---- values ----


def test_constant_drops_article_keeps_words() -> None:
    assert parse("a lovely sweet flower", start="value") == Constant(("lovely", "sweet", "flower"))


def test_nothing_is_a_constant() -> None:
    assert parse("nothing", start="value") == Constant(("nothing",))


def test_word_with_keyword_prefix_is_not_a_keyword() -> None:
    # "summer" must not be mis-tokenised because "sum" is a keyword.
    assert parse("a summer", start="value") == Constant(("summer",))


def test_pronoun_values() -> None:
    assert parse("you", start="value") == PronounValue("second")
    assert parse("I", start="value") == PronounValue("first")


def test_arithmetic_does_not_get_swallowed_as_a_constant() -> None:
    assert parse("the sum of a flower and a happy cat", start="value") == BinaryOp(
        "sum", Constant(("flower",)), Constant(("happy", "cat"))
    )


def test_nested_arithmetic() -> None:
    assert parse(
        "the product of twice a cat and the sum of a pig and nothing", start="value"
    ) == BinaryOp(
        "product",
        UnaryOp("twice", Constant(("cat",))),
        BinaryOp("sum", Constant(("pig",)), Constant(("nothing",))),
    )


def test_remainder_phrase() -> None:
    assert parse(
        "the remainder of the quotient between a flower and a pig", start="value"
    ) == BinaryOp("remainder", Constant(("flower",)), Constant(("pig",)))


# ---- stage directions ----


def test_enter_two_and_case_insensitive() -> None:
    assert parse("[enter Romeo and Juliet]", start="line") == Enter(("Romeo", "Juliet"))


def test_enter_groups_multi_word_names() -> None:
    assert parse("[Enter Lady Macbeth and John of Gaunt]", start="line") == Enter(
        ("Lady Macbeth", "John of Gaunt")
    )


def test_exit_and_exeunt() -> None:
    assert parse("[Exit Hamlet]", start="line") == Exit("Hamlet")
    assert parse("[Exeunt]", start="line") == Exeunt(())


# ---- statements ----


def test_io_statements() -> None:
    assert parse("Open your heart.", start="sentence") == OutputNumber()
    assert parse("Speak your mind.", start="sentence") == OutputChar()
    assert parse("Listen to your heart.", start="sentence") == InputNumber()
    assert parse("Open your mind.", start="sentence") == InputChar()


def test_question_relative_and_negated_equality() -> None:
    assert parse("Am I better than you?", start="sentence") == Question(
        PronounValue("first"), PronounValue("second"), "gt", False
    )
    assert parse("Are you not as good as me?", start="sentence") == Question(
        PronounValue("second"), PronounValue("first"), "eq", True
    )


def test_conditional_guards_a_goto() -> None:
    assert parse("If so, let us proceed to scene II.", start="sentence") == Conditional(
        True, Goto("scene", 2)
    )
    assert parse("If not, we shall return to act I.", start="sentence") == Conditional(
        False, Goto("act", 1)
    )


def test_malformed_input_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        parse("Romeo: Glab the florp of.", start="line")


# ---- whole play ----

_PLAY = """The Tragedy of Testing.

Romeo, a young man with remarkable patience.
Juliet, a lady of few words.

Act I: The beginning.
Scene I: A conversation.
[Enter Romeo and Juliet]
Romeo: You are nothing!
Juliet: You are the sum of a flower and a happy cat. Open your heart!
[Exeunt]
"""


def test_full_play_structure() -> None:
    assert parse(_PLAY) == Program(
        title="The Tragedy of Testing",
        personae=(Persona("Romeo"), Persona("Juliet")),
        acts=(
            Act(
                number=1,
                scenes=(
                    Scene(
                        number=1,
                        lines=(
                            Enter(("Romeo", "Juliet")),
                            Dialogue("Romeo", (Assignment(Constant(("nothing",))),)),
                            Dialogue(
                                "Juliet",
                                (
                                    Assignment(
                                        BinaryOp(
                                            "sum",
                                            Constant(("flower",)),
                                            Constant(("happy", "cat")),
                                        )
                                    ),
                                    OutputNumber(),
                                ),
                            ),
                            Exeunt(()),
                        ),
                    ),
                ),
            ),
        ),
    )
