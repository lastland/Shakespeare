"""Typed AST nodes — the frontend→backend boundary.

Nodes are immutable (`frozen=True`) and carry RAW tokens: a `Constant` keeps the literal
adjective/noun words (unclassified), and characters are raw name strings. Word classification
and value computation happen in the backend analyzer (see ADR-0002), so the AST stays purely
syntactic.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------- expressions (values) ----------------


@dataclass(frozen=True)
class Constant:
    """A value literal: the raw words `article? adjective* noun`, article already dropped.

    `("nothing",)` denotes zero. The analyzer computes the integer value.
    """

    words: tuple[str, ...]


@dataclass(frozen=True)
class PronounValue:
    """The value of the speaker (`person == "first"`) or addressee (`"second"`)."""

    person: str


@dataclass(frozen=True)
class BinaryOp:
    """`sum` / `difference` / `product` / `quotient` / `remainder` of two values."""

    op: str
    left: Expr
    right: Expr


@dataclass(frozen=True)
class UnaryOp:
    """`twice` or `square` of a value."""

    op: str
    operand: Expr


@dataclass(frozen=True)
class Number:
    """A `Constant` folded to its integer value by the analyzer.

    The frontend never produces this; the analyzer rewrites every `Constant` into a `Number`
    (or a `CharacterRef`) so the interpreter evaluates values without depending on the vocabulary.
    """

    value: int


@dataclass(frozen=True)
class CharacterRef:
    """A reference to another character's current value by name (e.g. `Romeo` in an expression).

    The frontend emits these as `Constant`s; the analyzer rewrites a constant whose words name a
    declared character into this node.
    """

    name: str


type Expr = Constant | Number | CharacterRef | PronounValue | BinaryOp | UnaryOp

# ---------------- statements ----------------


@dataclass(frozen=True)
class Assignment:
    """Set the addressee's value to `value`."""

    value: Expr


@dataclass(frozen=True)
class OutputNumber:
    """`Open your heart` — print the addressee's value as a decimal number."""


@dataclass(frozen=True)
class OutputChar:
    """`Speak your mind` — print the addressee's value as a Unicode character."""


@dataclass(frozen=True)
class InputNumber:
    """`Listen to your heart` — read a number into the addressee."""


@dataclass(frozen=True)
class InputChar:
    """`Open your mind` — read a character into the addressee."""


@dataclass(frozen=True)
class Question:
    """A comparison whose result drives the next conditional.

    `comparison` is one of `"eq"`, `"gt"`, `"lt"`; `negated` flips the outcome.
    """

    left: Expr
    right: Expr
    comparison: str
    negated: bool


@dataclass(frozen=True)
class Conditional:
    """`If so` (`on_true=True`) / `If not` (`on_true=False`) guarding a statement."""

    on_true: bool
    body: Statement


@dataclass(frozen=True)
class Goto:
    """`Let us proceed/return to` an act or scene. `kind` is `"act"` or `"scene"`."""

    kind: str
    number: int


type Statement = (
    Assignment | OutputNumber | OutputChar | InputNumber | InputChar | Question | Conditional | Goto
)

# ---------------- stage directions ----------------


@dataclass(frozen=True)
class Enter:
    """`[Enter ...]` — bring characters on stage."""

    characters: tuple[str, ...]


@dataclass(frozen=True)
class Exit:
    """`[Exit X]` — one character leaves."""

    character: str


@dataclass(frozen=True)
class Exeunt:
    """`[Exeunt ...]` — the named characters leave; empty tuple means all."""

    characters: tuple[str, ...]


@dataclass(frozen=True)
class Breakpoint:
    """`[A pause]` — a debugger breakpoint. We parse it for fidelity and otherwise ignore it."""


type Line = Dialogue | Enter | Exit | Exeunt | Breakpoint

# ---------------- structure ----------------


@dataclass(frozen=True)
class Dialogue:
    """A spoken line: `speaker` addresses the other on-stage character with `statements`."""

    speaker: str
    statements: tuple[Statement, ...]


@dataclass(frozen=True)
class Scene:
    number: int
    lines: tuple[Line, ...]


@dataclass(frozen=True)
class Act:
    number: int
    scenes: tuple[Scene, ...]


@dataclass(frozen=True)
class Persona:
    """A character declaration in the Dramatis Personae."""

    name: str


@dataclass(frozen=True)
class Program:
    title: str
    personae: tuple[Persona, ...]
    acts: tuple[Act, ...]
