"""Typed error hierarchy for the SPL interpreter.

Three failure stages, mirroring the pipeline:
- `ParseError`     — the source text is not a well-formed play (frontend).
- `AnalysisError`  — static analysis failed: undeclared/duplicate character, unresolved goto
                     target, or an unknown/miscategorised word (backend analyzer).
- `RuntimeSplError`— a dynamic fault during interpretation: division/modulo by zero, addressing
                     a character not on stage, more than two characters interacting, or
                     character-output of a value outside valid Unicode (backend interpreter).

See ADR-0001 for why these are raised strictly rather than coerced.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    """A 1-based position in the source text, attached to an error when available."""

    line: int
    column: int

    def __str__(self) -> str:
        return f"line {self.line}, column {self.column}"


class SplError(Exception):
    """Base class for every error raised by the interpreter."""

    def __init__(self, message: str, location: Location | None = None) -> None:
        super().__init__(message if location is None else f"{message} (at {location})")
        self.message = message
        self.location = location


class ParseError(SplError):
    """The source text could not be parsed into a play."""


class AnalysisError(SplError):
    """Static analysis rejected the program before execution."""


class RuntimeSplError(SplError):
    """A dynamic error occurred while interpreting the program."""
