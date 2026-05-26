"""lark parse tree → typed AST.

Purely syntactic: it shapes nodes, normalises multi-word names, and parses Roman numerals,
but performs no vocabulary classification or value computation (that is the analyzer's job).

Keyword terminals are named (see grammar.lark), so they are kept in the parse tree. Each method
therefore filters its children by type rather than by position — robust to grammar tweaks.
"""

from __future__ import annotations

from typing import cast

from lark import Token, Transformer

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
    Expr,
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
    Statement,
    UnaryOp,
)

_EXPR_TYPES = (Constant, PronounValue, BinaryOp, UnaryOp)
_LINE_TYPES = (Dialogue, Enter, Exit, Exeunt)
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _roman_to_int(numeral: str) -> int:
    total = 0
    prev = 0
    for char in reversed(numeral.upper()):
        value = _ROMAN[char]
        total += value if value >= prev else -value
        prev = max(prev, value)
    return total


def _exprs(children: list[object]) -> list[Expr]:
    return [c for c in children if isinstance(c, _EXPR_TYPES)]


def _names(children: list[object]) -> list[str]:
    # `name` returns a plain `str`; keyword/COMMENT tokens are `Token` (a str subclass).
    return [c for c in children if isinstance(c, str) and not isinstance(c, Token)]


def _words(children: list[object]) -> list[str]:
    return [str(c) for c in children if isinstance(c, Token) and c.type == "WORD"]


def _kind(children: list[object]) -> str:
    return next(c for c in children if isinstance(c, str) and not isinstance(c, Token))


def _int(children: list[object]) -> int:
    return next(c for c in children if isinstance(c, int))


class ToAst(Transformer[Token, object]):
    # ---- values ----

    def constant(self, children: list[object]) -> Constant:
        return Constant(tuple(_words(children)))

    def first_person_value(self, children: list[object]) -> PronounValue:
        return PronounValue("first")

    def second_person_value(self, children: list[object]) -> PronounValue:
        return PronounValue("second")

    def sum(self, children: list[object]) -> BinaryOp:
        left, right = _exprs(children)
        return BinaryOp("sum", left, right)

    def difference(self, children: list[object]) -> BinaryOp:
        left, right = _exprs(children)
        return BinaryOp("difference", left, right)

    def product(self, children: list[object]) -> BinaryOp:
        left, right = _exprs(children)
        return BinaryOp("product", left, right)

    def quotient(self, children: list[object]) -> BinaryOp:
        left, right = _exprs(children)
        return BinaryOp("quotient", left, right)

    def remainder(self, children: list[object]) -> BinaryOp:
        left, right = _exprs(children)
        return BinaryOp("remainder", left, right)

    def twice(self, children: list[object]) -> UnaryOp:
        return UnaryOp("twice", _exprs(children)[0])

    def square(self, children: list[object]) -> UnaryOp:
        return UnaryOp("square", _exprs(children)[0])

    # ---- comparisons ----

    def eq(self, children: list[object]) -> str:
        return "eq"

    def gt(self, children: list[object]) -> str:
        return "gt"

    def lt(self, children: list[object]) -> str:
        return "lt"

    def cmp_positive(self, children: list[object]) -> tuple[str, bool]:
        return (_kind(children), False)

    def cmp_negated(self, children: list[object]) -> tuple[str, bool]:
        return (_kind(children), True)

    # ---- statements ----

    def assignment(self, children: list[object]) -> Assignment:
        return Assignment(_exprs(children)[0])

    def output_number(self, children: list[object]) -> OutputNumber:
        return OutputNumber()

    def output_char(self, children: list[object]) -> OutputChar:
        return OutputChar()

    def input_number(self, children: list[object]) -> InputNumber:
        return InputNumber()

    def input_char(self, children: list[object]) -> InputChar:
        return InputChar()

    def question(self, children: list[object]) -> Question:
        left, right = _exprs(children)
        # The comparison result (a (kind, negated) tuple) is the child that is neither a token
        # nor an expression. Found by exclusion so its element types stay known to the checker.
        comparison_obj = next(c for c in children if not isinstance(c, (Token, *_EXPR_TYPES)))
        comparison, negated = cast("tuple[str, bool]", comparison_obj)
        return Question(left, right, comparison, negated)

    def if_so(self, children: list[object]) -> Conditional:
        return Conditional(
            True, cast(Statement, next(c for c in children if not isinstance(c, Token)))
        )

    def if_not(self, children: list[object]) -> Conditional:
        return Conditional(
            False, cast(Statement, next(c for c in children if not isinstance(c, Token)))
        )

    def scene_target(self, children: list[object]) -> Goto:
        return Goto("scene", _int(children))

    def act_target(self, children: list[object]) -> Goto:
        return Goto("act", _int(children))

    def goto(self, children: list[object]) -> Goto:
        return next(c for c in children if isinstance(c, Goto))

    # ---- stage directions ----

    def enter(self, children: list[object]) -> Enter:
        return Enter(tuple(_names(children)))

    def exit(self, children: list[object]) -> Exit:
        return Exit(_names(children)[0])

    def exeunt(self, children: list[object]) -> Exeunt:
        return Exeunt(tuple(_names(children)))

    def stage_direction(self, children: list[object]) -> object:
        return next(c for c in children if not isinstance(c, Token))

    # ---- structure ----

    def name(self, children: list[object]) -> str:
        token = next(c for c in children if isinstance(c, Token))
        return " ".join(str(token).split())

    def roman(self, children: list[object]) -> int:
        return _roman_to_int(str(children[0]))

    def sentence(self, children: list[object]) -> object:
        return next(c for c in children if not isinstance(c, Token))

    def dialogue(self, children: list[object]) -> Dialogue:
        speaker = _names(children)[0]
        statements = tuple(cast(Statement, c) for c in children if not isinstance(c, str))
        return Dialogue(speaker, statements)

    def scene(self, children: list[object]) -> Scene:
        lines = tuple(c for c in children if isinstance(c, _LINE_TYPES))
        return Scene(_int(children), lines)

    def act(self, children: list[object]) -> Act:
        scenes = tuple(c for c in children if isinstance(c, Scene))
        return Act(_int(children), scenes)

    def persona(self, children: list[object]) -> Persona:
        return Persona(_names(children)[0])

    def personae(self, children: list[object]) -> tuple[Persona, ...]:
        return tuple(c for c in children if isinstance(c, Persona))

    def play(self, children: list[object]) -> Program:
        # Grammar: COMMENT "." personae act+  → children = [title, personae, *acts]
        title = str(children[0]).strip()
        personae = cast("tuple[Persona, ...]", children[1])
        acts = tuple(c for c in children if isinstance(c, Act))
        return Program(title, personae, acts)
