"""Frontend parser/transformer tests, construct by construct, plus a full play."""

from __future__ import annotations

import pytest

from spl.errors import ParseError
from spl.frontend.ast import (
    Act,
    Assignment,
    BinaryOp,
    Breakpoint,
    Conditional,
    Constant,
    Dialogue,
    Enter,
    Exeunt,
    Exit,
    Goto,
    InputChar,
    InputNumber,
    MoreComparative,
    OutputChar,
    OutputNumber,
    Persona,
    Program,
    PronounValue,
    Question,
    Recall,
    Remember,
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


def test_thine_is_a_possessive_determiner() -> None:
    # `thine` is a second-person possessive (reference EBNF); like any determiner it is dropped,
    # leaving the noun. Used in sierpinski.spl as "thine goat".
    assert parse("thine goat", start="value") == Constant(("goat",))


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


def test_factorial_parses_to_unary_op() -> None:
    # `the factorial of <value>` is a unary op alongside square/cube/square-root/twice (issue 23).
    assert parse("the factorial of a happy cat", start="value") == UnaryOp(
        "factorial", Constant(("happy", "cat"))
    )


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


# ---- articled character names (issue 09): "the Ghost" -> "The Ghost" ----


def test_enter_allows_leading_lowercase_article_and_normalizes() -> None:
    # "[Enter the Ghost and Juliet]" (primes.spl): the lowercase article is absorbed into the
    # name and normalized to the declared form "The Ghost".
    assert parse("[Enter the Ghost and Juliet]", start="line") == Enter(("The Ghost", "Juliet"))


def test_exit_allows_leading_article() -> None:
    assert parse("[Exit the Ghost]", start="line") == Exit("The Ghost")


def test_exeunt_allows_leading_article() -> None:
    assert parse("[Exeunt the Ghost and Juliet]", start="line") == Exeunt(("The Ghost", "Juliet"))


def test_articled_name_in_value_position_keeps_the_flag() -> None:
    # In value position "the Ghost" parses as the determiner "the" + the noun/name "Ghost". The
    # frontend keeps the raw words AND records that the leading determiner was literally "the"
    # (leading_the=True) so the analyzer may re-prepend it to match a "The X" character (issue 18).
    assert parse("the Ghost", start="value") == Constant(("Ghost",), leading_the=True)


def test_non_the_determiner_in_value_position_does_not_set_the_flag() -> None:
    # Any other determiner is dropped with leading_the=False: it can never name a "The X" character,
    # so the analyzer will not retry the character match (issue 18).
    assert parse("his Ghost", start="value") == Constant(("Ghost",), leading_the=False)
    assert parse("a Ghost", start="value") == Constant(("Ghost",), leading_the=False)
    assert parse("Ghost", start="value") == Constant(("Ghost",), leading_the=False)


def test_name_article_only_absorbs_the_not_a_or_an() -> None:
    # Only "the" folds into a name ("the Ghost" -> "The Ghost"); the reference has no "A X"/"An X"
    # character names, so "a"/"an" must NOT be absorbed (issue 20) — they fail to parse as a name.
    assert parse("the Ghost", start="name") == "The Ghost"
    with pytest.raises(ParseError):
        parse("a Ghost", start="name")
    with pytest.raises(ParseError):
        parse("an Ghost", start="name")


# ---- statements ----


def test_io_statements() -> None:
    assert parse("Open your heart.", start="sentence") == OutputNumber()
    assert parse("Speak your mind.", start="sentence") == OutputChar()
    assert parse("Listen to your heart.", start="sentence") == InputNumber()
    assert parse("Open your mind.", start="sentence") == InputChar()


def test_question_relative_and_equality() -> None:
    assert parse("Am I better than you?", start="sentence") == Question(
        PronounValue("first"), PronounValue("second"), "gt"
    )
    assert parse("Are you as good as me?", start="sentence") == Question(
        PronounValue("second"), PronounValue("first"), "eq"
    )


@pytest.mark.parametrize(
    "word",
    ["better", "bigger", "fresher", "friendlier", "nicer", "jollier"],
)
def test_positive_comparatives_parse_to_gt(word: str) -> None:
    assert parse(f"Am I {word} than you?", start="sentence") == Question(
        PronounValue("first"), PronounValue("second"), "gt"
    )


@pytest.mark.parametrize("word", ["worse", "punier", "smaller"])
def test_negative_comparatives_parse_to_lt(word: str) -> None:
    assert parse(f"Am I {word} than you?", start="sentence") == Question(
        PronounValue("first"), PronounValue("second"), "lt"
    )


def test_neutral_comparative_parses_to_eq() -> None:
    assert parse("Am I as good as you?", start="sentence") == Question(
        PronounValue("first"), PronounValue("second"), "eq"
    )


@pytest.mark.parametrize(
    "source",
    [
        # Negated questions were dropped (issue 13): a `not` inside a question no longer parses,
        # regardless of operand kind (pronoun vs. character/noun-phrase left operand).
        "Are you not as good as me?",
        "Am I not worse than you?",
        "Am I not more rotten than you?",
        "Is Romeo not worse than Juliet?",
        "Is the King not worse than Juliet?",
    ],
)
def test_negated_question_does_not_parse(source: str) -> None:
    with pytest.raises(ParseError):
        parse(source, start="sentence")


def test_more_adjective_than_carries_unresolved_adjective() -> None:
    # `more <adj> than` cannot be classified gt/lt without the vocabulary, so the frontend keeps
    # the raw adjective in a MoreComparative marker; the analyzer resolves it (see analyzer tests).
    assert parse("Am I more cunning than you?", start="sentence") == Question(
        PronounValue("first"), PronounValue("second"), MoreComparative("cunning")
    )


def test_conditional_guards_a_goto() -> None:
    assert parse("If so, let us proceed to scene II.", start="sentence") == Conditional(
        True, Goto("scene", 2)
    )
    assert parse("If not, we shall return to act I.", start="sentence") == Conditional(
        False, Goto("act", 1)
    )


def test_simile_admits_a_non_adjective_word() -> None:
    # ADR-0007 (issue 26): the reference's `as ADJ as` requires a known adjective; we admit any
    # vocabulary word as the simile adjective and discard it, since the form means equality
    # regardless of the word. "cat" is a NOUN, yet `as cat as` parses to the equality question.
    assert parse("Are you as cat as a King?", start="sentence") == Question(
        PronounValue("second"), Constant(("King",)), "eq"
    )


def test_nested_conditional_parses() -> None:
    # ADR-0007 (issue 26): the reference attaches at most one condition prefix per operation; we let
    # a conditional guard another conditional (a `conditional` body may itself be a `conditional`),
    # so `If so, if not, ...` parses to a nested Conditional. Pinned so the superset cannot regress.
    assert parse("If so, if not, Thou art a King.", start="sentence") == Conditional(
        True, Conditional(False, Assignment(Constant(("King",))))
    )


# ---- stacks: Remember / Recall (issue 02) ----


def test_remember_pushes_a_value() -> None:
    # "Remember me!" pushes the speaker's own value (first-person) onto the addressee's stack.
    assert parse("Remember me!", start="sentence") == Remember(PronounValue("first"))


def test_remember_a_constant() -> None:
    assert parse("Remember a happy cat.", start="sentence") == Remember(Constant(("happy", "cat")))


def test_recall_with_trailing_comment_text() -> None:
    # The text after Recall is an ignorable comment; the node carries no payload.
    assert parse("Recall your imminent demise!", start="sentence") == Recall()


def test_recall_keyword_wins_over_name_at_statement_position() -> None:
    # "Recall" is capitalized and could collide with NAME; the keyword must win.
    assert parse("Recall me.", start="sentence") == Recall()


def test_recall_without_comment_text() -> None:
    assert parse("Recall.", start="sentence") == Recall()


def test_recall_comment_spans_question_mark() -> None:
    # A "?" inside a Recall comment is comment text, not a sentence terminator: the whole
    # "is this real? Speak your mind" is one ignorable recall comment that runs to the final "."
    # (issue 17). The trailing "Speak your mind" must NOT split off as an OutputChar.
    assert parse("Romeo: Recall is this real? Speak your mind.", start="line") == Dialogue(
        "Romeo", (Recall(),)
    )


def test_malformed_input_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        parse("Romeo: Glab the florp of.", start="line")


# ---- comments span lines (issue 01) ----

# A persona description that wraps across two lines (as in the primes.spl sample): the COMMENT
# terminal runs to the next sentence terminator regardless of line breaks.
_MULTILINE_PERSONA_PLAY = """A Test.

Hamlet, a limiting factor (and by a remarkable coincidence also
        Romeo's father).
Juliet, a young woman.

Act I: a.
Scene I: s.
[Enter Hamlet and Juliet]
Juliet: You are nothing.
"""


def test_multiline_persona_description_parses() -> None:
    program = parse(_MULTILINE_PERSONA_PLAY)
    assert isinstance(program, Program)
    assert program.personae == (Persona("Hamlet"), Persona("Juliet"))


# ---- title / section terminators accept ! ? . (FIX A) ----

# A title or section label may end with ".", "!", or "?". The "." and "!" match the reference EBNF
# (text_before_punctuation ("!" | ".")); "?" is our intentional superset (ADR-0005) — the reference
# reads past a "?" as label text. (Unrelated to "?" ending a question, which is reference-standard.)
_BANGED_TITLES_PLAY = """A Test!

Romeo, a person?
Juliet, a person.

Act I: a thing!
Scene I: Romeo must die!
[Enter Romeo and Juliet]
Romeo: You are nothing.
"""


def test_title_and_section_terminators_allow_bang_and_question() -> None:
    program = parse(_BANGED_TITLES_PLAY)
    assert isinstance(program, Program)
    assert program.title == "A Test"
    assert program.personae == (Persona("Romeo"), Persona("Juliet"))
    assert program.acts[0].number == 1
    assert program.acts[0].scenes[0].number == 1


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


# ---- breakpoints survive into the scene AST (issue 14) ----

_BREAKPOINT_PLAY = """A Test.

Romeo, a person.
Juliet, a person.

Act I: a.
Scene I: s.
[Enter Romeo and Juliet]
Romeo: You are nothing!
[A pause]
Juliet: You are nothing!
[Exeunt]
"""


def test_breakpoint_survives_in_scene_lines() -> None:
    # "[A pause]" parses to a Breakpoint that must be kept in scene.lines at its source position
    # (issue 14): the scene line-filter formerly omitted Breakpoint, silently dropping it.
    program = parse(_BREAKPOINT_PLAY)
    assert isinstance(program, Program)
    lines = program.acts[0].scenes[0].lines
    assert lines == (
        Enter(("Romeo", "Juliet")),
        Dialogue("Romeo", (Assignment(Constant(("nothing",))),)),
        Breakpoint(),
        Dialogue("Juliet", (Assignment(Constant(("nothing",))),)),
        Exeunt(()),
    )
