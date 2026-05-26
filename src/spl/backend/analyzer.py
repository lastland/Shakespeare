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
    Number,
    OutputChar,
    OutputNumber,
    Program,
    PronounValue,
    Question,
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

    def _fold_statement(self, stmt: Statement) -> Statement:
        match stmt:
            case Assignment(value):
                return Assignment(self._fold_expr(value))
            case Question(left, right, comparison, negated):
                return Question(self._fold_expr(left), self._fold_expr(right), comparison, negated)
            case Conditional(on_true, body):
                return Conditional(on_true, self._fold_statement(body))
            case OutputNumber() | OutputChar() | InputNumber() | InputChar() | Goto():
                return stmt

    def _fold_expr(self, expr: Expr) -> Expr:
        match expr:
            case Constant(words):
                return Number(self._constant_value(words))
            case BinaryOp(op, left, right):
                return BinaryOp(op, self._fold_expr(left), self._fold_expr(right))
            case UnaryOp(op, operand):
                return UnaryOp(op, self._fold_expr(operand))
            case PronounValue() | Number():
                return expr

    def _constant_value(self, words: tuple[str, ...]) -> int:
        *adjectives, noun = words
        if noun.casefold() in _ZERO_WORDS:
            base = 0
        else:
            value = self.vocab.noun_value(noun)
            if value is None:
                raise AnalysisError(f"unknown noun: {noun!r}")
            base = value
        for adjective in adjectives:
            if not self.vocab.is_adjective(adjective):
                raise AnalysisError(f"unknown adjective: {adjective!r}")
        return base * (2 ** len(adjectives))

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
