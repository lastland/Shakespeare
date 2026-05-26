"""Static analysis: validate the AST as far as statically possible and prepare it for execution.

Responsibilities (everything checkable before running):
  * every declared character is a real SPL character name; no duplicate declarations;
  * every character used on stage / as a speaker was declared;
  * every word in a constant is a known noun/adjective, and the constant is folded to its value;
  * every goto resolves to an existing act (or a scene within the goto's own act).

It flattens the acts/scenes into one ordered line list plus label maps, so the interpreter can
run a simple program counter. Vocabulary lives here (not in the interpreter), per ADR-0002.
"""

from __future__ import annotations

from dataclasses import dataclass

from spl.backend.vocabulary import Vocabulary, load
from spl.errors import AnalysisError
from spl.frontend.ast import (
    Assignment,
    BinaryOp,
    Breakpoint,
    CharacterRef,
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
    Line,
    MoreComparative,
    Number,
    OutputChar,
    OutputNumber,
    Program,
    PronounValue,
    Question,
    Recall,
    Remember,
    Statement,
    UnaryOp,
)

_ZERO_WORDS = frozenset({"nothing", "zero"})


@dataclass(frozen=True)
class AnalyzedProgram:
    """An execution-ready program: a flat line list, label maps, and the declared characters.

    `lines[i]` runs at program-counter `i`; `line_acts[i]` is the act it belongs to (so a scene
    goto resolves within the current act). All constants in the lines are folded to `Number`.
    """

    characters: frozenset[str]
    lines: tuple[Line, ...]
    line_acts: tuple[int, ...]
    act_starts: dict[int, int]
    scene_starts: dict[tuple[int, int], int]


def analyze(program: Program, vocab: Vocabulary | None = None) -> AnalyzedProgram:
    return _Analyzer(vocab if vocab is not None else load()).run(program)


class _Analyzer:
    def __init__(self, vocab: Vocabulary) -> None:
        self.vocab = vocab
        self.declared: set[str] = set()
        self.lines: list[Line] = []
        self.line_acts: list[int] = []
        self.act_starts: dict[int, int] = {}
        self.scene_starts: dict[tuple[int, int], int] = {}

    def run(self, program: Program) -> AnalyzedProgram:
        self._collect_personae(program)
        self._flatten(program)
        self._check_gotos()
        return AnalyzedProgram(
            characters=frozenset(self.declared),
            lines=tuple(self.lines),
            line_acts=tuple(self.line_acts),
            act_starts=self.act_starts,
            scene_starts=self.scene_starts,
        )

    # ---- personae ----

    def _collect_personae(self, program: Program) -> None:
        for persona in program.personae:
            if not self.vocab.is_character_name(persona.name):
                raise AnalysisError(f"unknown character: {persona.name!r}")
            if persona.name in self.declared:
                raise AnalysisError(f"character declared twice: {persona.name!r}")
            self.declared.add(persona.name)

    def _require_declared(self, name: str) -> None:
        if name not in self.declared:
            raise AnalysisError(f"character used but not in the Dramatis Personae: {name!r}")

    # ---- flattening + constant folding ----

    def _flatten(self, program: Program) -> None:
        for act in program.acts:
            self.act_starts[act.number] = len(self.lines)
            for scene in act.scenes:
                self.scene_starts[(act.number, scene.number)] = len(self.lines)
                for line in scene.lines:
                    self.lines.append(self._analyze_line(line))
                    self.line_acts.append(act.number)

    def _analyze_line(self, line: Line) -> Line:
        match line:
            case Enter(characters) | Exeunt(characters):
                for name in characters:
                    self._require_declared(name)
                return line
            case Exit(character):
                self._require_declared(character)
                return line
            case Dialogue(speaker, statements):
                self._require_declared(speaker)
                return Dialogue(speaker, tuple(self._fold_statement(s) for s in statements))
            case Breakpoint():
                return line

    def _fold_statement(self, stmt: Statement) -> Statement:
        match stmt:
            case Assignment(value):
                return Assignment(self._fold_expr(value))
            case Question(left, right, comparison):
                return Question(
                    self._fold_expr(left),
                    self._fold_expr(right),
                    self._resolve_comparison(comparison),
                )
            case Conditional(on_true, body):
                return Conditional(on_true, self._fold_statement(body))
            case Remember(value):
                return Remember(self._fold_expr(value))
            case OutputNumber() | OutputChar() | InputNumber() | InputChar() | Goto() | Recall():
                return stmt

    def _fold_expr(self, expr: Expr) -> Expr:
        match expr:
            case Constant(words, leading_the):
                return self._fold_constant(words, leading_the)
            case BinaryOp(op, left, right):
                return BinaryOp(op, self._fold_expr(left), self._fold_expr(right))
            case UnaryOp(op, operand):
                return UnaryOp(op, self._fold_expr(operand))
            case PronounValue() | Number() | CharacterRef():
                return expr

    def _resolve_comparison(self, comparison: str | MoreComparative) -> str:
        """Resolve a `more <adjective> than` marker to "gt"/"lt"; pass plain strings through.

        Direction follows the adjective's sign: a negative adjective means less-than, a positive
        adjective means greater-than. A neutral adjective is rejected (raises), matching the
        reference, which admits `more` only with a positive/negative adjective (issue 15); an
        unknown (non-adjective) word also raises, matching the strict treatment of unknown
        adjectives in constants (ADR-0001).
        """
        if isinstance(comparison, MoreComparative):
            adjective = comparison.adjective
            if self.vocab.is_negative_adjective(adjective):
                return "lt"
            if self.vocab.is_positive_adjective(adjective):
                return "gt"
            raise AnalysisError(f"unknown adjective: {adjective!r}")
        return comparison

    def _fold_constant(self, words: tuple[str, ...], leading_the: bool) -> Expr:
        """Fold to a value (noun phrase) or a CharacterRef (words naming a declared character)."""
        joined = " ".join(words)
        if joined.casefold() in _ZERO_WORDS:
            return Number(0)
        character = self._match_character(joined)
        if character is not None:
            return CharacterRef(character)
        # Articled character name (issue 09, facet 2): in value position the determiner of a name
        # like "the Ghost" is dropped by the constant rule, leaving just "Ghost". A leading "the"
        # only ever distinguishes a "The X" character (the reference has no "A X" names), so retry
        # the match with "the" re-prepended BEFORE the noun-phrase fallback. This retry is gated on
        # the source literally having written "the" (issue 18): `his Ghost` / `a Ghost` / bare
        # `Ghost` must NOT resolve to `The Ghost`, matching the reference, whose character value is
        # the full literal name. The retry runs only after a bare match fails, so an ordinary noun
        # like "the King" (no such character declared) still falls through to its constant value.
        if leading_the:
            articled = self._match_character(f"the {joined}")
            if articled is not None:
                return CharacterRef(articled)
        return Number(self._noun_phrase_value(words))

    def _match_character(self, text: str) -> str | None:
        folded = text.casefold()
        return next((name for name in self.declared if name.casefold() == folded), None)

    def _noun_phrase_value(self, words: tuple[str, ...]) -> int:
        # The noun is the longest trailing run that the vocabulary recognises (handles multi-word
        # nouns like "summer's day"); the words before it must all be adjectives.
        count = len(words)
        for k in range(count, 0, -1):
            value = self.vocab.noun_value(" ".join(words[count - k :]))
            if value is not None:
                adjectives = words[: count - k]
                for adjective in adjectives:
                    if not self.vocab.is_adjective(adjective):
                        raise AnalysisError(f"unknown adjective: {adjective!r}")
                return value * (2 ** len(adjectives))
        raise AnalysisError(f"unknown noun: {' '.join(words)!r}")

    # ---- goto resolution ----

    def _check_gotos(self) -> None:
        for index, line in enumerate(self.lines):
            if isinstance(line, Dialogue):
                for statement in line.statements:
                    self._check_goto(statement, self.line_acts[index])

    def _check_goto(self, stmt: Statement, act_no: int) -> None:
        match stmt:
            case Goto("act", number):
                if number not in self.act_starts:
                    raise AnalysisError(f"goto to undefined act {number}")
            case Goto("scene", number):
                if (act_no, number) not in self.scene_starts:
                    raise AnalysisError(f"goto to undefined scene {number} in act {act_no}")
            case Conditional(_, body):
                self._check_goto(body, act_no)
            case _:
                pass
