"""Tree-walking interpreter over an `AnalyzedProgram`.

Execution is a program counter over the flattened line list: stage directions mutate the Stage,
dialogue runs its statements against the current speaker/addressee, and gotos set the counter.
The interpreter depends on no vocabulary — constants were already folded to `Number` by the
analyzer. It raises `RuntimeSplError` for the dynamic faults (see ADR-0001).
"""

from __future__ import annotations

import math

from spl.backend.analyzer import AnalyzedProgram
from spl.backend.io import IO, StdIO
from spl.backend.state import Character, Stage
from spl.errors import RuntimeSplError
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
    Number,
    OutputChar,
    OutputNumber,
    PronounValue,
    Question,
    Statement,
    UnaryOp,
)


def _trunc_div(a: int, b: int) -> int:
    """Integer division truncated toward zero (C / spl2c semantics)."""
    quotient = abs(a) // abs(b)
    return quotient if (a < 0) == (b < 0) else -quotient


class Interpreter:
    def __init__(self, program: AnalyzedProgram, io: IO | None = None) -> None:
        self.program = program
        self.io: IO = io if io is not None else StdIO()
        self.characters: dict[str, Character] = {name: Character() for name in program.characters}
        self.stage = Stage()
        self.last_question: bool | None = None

    def run(self) -> None:
        pc = 0
        lines = self.program.lines
        while 0 <= pc < len(lines):
            jump = self._run_line(pc, lines[pc])
            pc = jump if jump is not None else pc + 1

    # ---- lines ----

    def _run_line(self, pc: int, line: Line) -> int | None:
        match line:
            case Enter(characters):
                self.stage.enter(*characters)
            case Exit(character):
                self.stage.exit_character(character)
            case Exeunt(characters):
                self.stage.exeunt(*characters)
            case Dialogue(speaker, statements):
                return self._run_dialogue(pc, speaker, statements)
            case Breakpoint():
                pass  # a debugger marker; nothing to execute
        return None

    def _run_dialogue(self, pc: int, speaker: str, statements: tuple[Statement, ...]) -> int | None:
        if speaker not in self.stage.on_stage():
            raise RuntimeSplError(f"{speaker} speaks but is not on stage")
        for statement in statements:
            jump = self._run_statement(pc, speaker, statement)
            if jump is not None:
                return jump  # a goto fired; skip the rest of the line
        return None

    # ---- statements ----

    def _run_statement(self, pc: int, speaker: str, stmt: Statement) -> int | None:
        match stmt:
            case Assignment(value):
                self._addressed(speaker).value = self._eval(speaker, value)
            case OutputNumber():
                self.io.write_number(self._addressed(speaker).value)
            case OutputChar():
                self.io.write_char(self._addressed(speaker).value)
            case InputNumber():
                self._addressed(speaker).value = self.io.read_number()
            case InputChar():
                self._addressed(speaker).value = self.io.read_char()
            case Question(left, right, comparison, negated):
                self.last_question = self._compare(
                    self._eval(speaker, left), self._eval(speaker, right), comparison, negated
                )
            case Conditional(on_true, body):
                if self.last_question is None:
                    raise RuntimeSplError("conditional without a preceding question")
                if self.last_question == on_true:
                    return self._run_statement(pc, speaker, body)
            case Goto(kind, number):
                return self._goto(pc, kind, number)
        return None

    def _goto(self, pc: int, kind: str, number: int) -> int:
        if kind == "act":
            return self.program.act_starts[number]
        return self.program.scene_starts[(self.program.line_acts[pc], number)]

    # ---- expressions ----

    def _eval(self, speaker: str, expr: Expr) -> int:
        match expr:
            case Number(value):
                return value
            case PronounValue(person):
                name = speaker if person == "first" else self._addressee(speaker)
                return self.characters[name].value
            case CharacterRef(name):
                return self.characters[name].value
            case BinaryOp(op, left, right):
                return self._binary(op, self._eval(speaker, left), self._eval(speaker, right))
            case UnaryOp(op, operand):
                return self._unary(op, self._eval(speaker, operand))
            case Constant():  # pragma: no cover - analyzer folds every constant to a Number
                raise AssertionError("constant was not folded by the analyzer")

    def _binary(self, op: str, left: int, right: int) -> int:
        match op:
            case "sum":
                return left + right
            case "difference":
                return left - right
            case "product":
                return left * right
            case "quotient":
                if right == 0:
                    raise RuntimeSplError("division by zero")
                return _trunc_div(left, right)
            case "remainder":
                if right == 0:
                    raise RuntimeSplError("modulo by zero")
                return left - _trunc_div(left, right) * right
            case _:  # pragma: no cover
                raise AssertionError(f"unknown binary operator {op!r}")

    def _unary(self, op: str, operand: int) -> int:
        match op:
            case "twice":
                return 2 * operand
            case "square":
                return operand * operand
            case "cube":
                return operand**3
            case "sqrt":
                if operand < 0:
                    raise RuntimeSplError("square root of a negative number")
                return math.isqrt(operand)
            case _:  # pragma: no cover
                raise AssertionError(f"unknown unary operator {op!r}")

    def _compare(self, left: int, right: int, comparison: str, negated: bool) -> bool:
        match comparison:
            case "eq":
                result = left == right
            case "gt":
                result = left > right
            case "lt":
                result = left < right
            case _:  # pragma: no cover
                raise AssertionError(f"unknown comparison {comparison!r}")
        return not result if negated else result

    # ---- stage helpers ----

    def _addressee(self, speaker: str) -> str:
        return self.stage.addressee(speaker)

    def _addressed(self, speaker: str) -> Character:
        return self.characters[self._addressee(speaker)]
