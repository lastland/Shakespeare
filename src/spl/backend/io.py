"""The interpreter's I/O abstraction.

SPL programs read and write through four primitives, each a stage line:
- "Listen to your heart"  -> read a base-10 integer            (`read_number`)
- "Open your mind"        -> read one character as a codepoint  (`read_char`)
- "Open your heart"       -> emit an integer as text            (`write_number`)
- "Speak your mind"       -> emit a codepoint as a character    (`write_char`)

I/O is dependency-injected via the `IO` protocol so the interpreter can be tested without
touching real stdin/stdout: `StdIO` wraps real text streams, `BufferIO` is an in-memory double.

Per ADR-0001 the undefined cases are handled strictly: EOF on a read yields -1, and writing a
character whose value is not a valid Unicode code point raises `RuntimeSplError` rather than
coercing it.
"""

from __future__ import annotations

import io
import sys
from typing import Protocol, TextIO, runtime_checkable

from spl.errors import RuntimeSplError

# Inclusive bounds of the surrogate range, which `chr` accepts but which is not a scalar value.
_SURROGATE_MIN = 0xD800
_SURROGATE_MAX = 0xDFFF
# Largest valid Unicode code point.
_UNICODE_MAX = 0x10FFFF


@runtime_checkable
class IO(Protocol):
    """The four-primitive I/O surface the interpreter depends on."""

    def read_number(self) -> int:
        """Read a base-10 integer from input; -1 on EOF or if no number is found."""
        ...

    def read_char(self) -> int:
        """Read one character; return its codepoint, or -1 on EOF."""
        ...

    def write_number(self, value: int) -> None:
        """Emit `value` as decimal text, with no trailing newline."""
        ...

    def write_char(self, value: int) -> None:
        """Emit `chr(value)`; raise `RuntimeSplError` if `value` is not a valid code point."""
        ...


def _check_codepoint(value: int) -> str:
    """Return `chr(value)`, raising `RuntimeSplError` for non-scalar values (ADR-0001)."""
    if value < 0 or value > _UNICODE_MAX or _SURROGATE_MIN <= value <= _SURROGATE_MAX:
        raise RuntimeSplError(f"character value {value} is not a valid Unicode code point")
    return chr(value)


class _CharReader:
    """A `TextIO` wrapped with a one-character pushback buffer.

    `read_number` must look one character past the digits to know the number has ended; that
    terminator has to remain available to the next read. A pushback buffer gives us this without
    relying on `seek`/`tell`, which a real (terminal) stdin does not support.
    """

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream
        self._pending: str | None = None

    def _next(self) -> str:
        """Return the next character, or "" at EOF."""
        if self._pending is not None:
            ch = self._pending
            self._pending = None
            return ch
        return self._stream.read(1)

    def _push_back(self, ch: str) -> None:
        """Put `ch` (a non-empty single char) back so the next read sees it first."""
        self._pending = ch

    def read_char(self) -> int:
        ch = self._next()
        if ch == "":
            return -1
        return ord(ch)

    def read_number(self) -> int:
        """Skip leading whitespace, parse an optional sign then base-10 digits.

        The terminating non-digit is pushed back so it stays available. Returns -1 on EOF before
        any digit, or when a sign is not followed by a digit.
        """
        # Skip leading whitespace.
        ch = self._next()
        while ch != "" and ch.isspace():
            ch = self._next()
        if ch == "":
            return -1

        sign = 1
        if ch in "+-":
            if ch == "-":
                sign = -1
            ch = self._next()

        digits: list[str] = []
        while ch != "" and ch.isascii() and ch.isdigit():
            digits.append(ch)
            ch = self._next()

        # Push back the terminator (or the char after a lone sign) so it can be reread.
        if ch != "":
            self._push_back(ch)

        if not digits:
            return -1
        return sign * int("".join(digits))


class StdIO:
    """`IO` backed by real text streams, defaulting to stdin/stdout."""

    def __init__(self, input: TextIO | None = None, output: TextIO | None = None) -> None:
        self._reader = _CharReader(input if input is not None else sys.stdin)
        self._output: TextIO = output if output is not None else sys.stdout

    def read_number(self) -> int:
        return self._reader.read_number()

    def read_char(self) -> int:
        return self._reader.read_char()

    def write_number(self, value: int) -> None:
        self._output.write(str(value))

    def write_char(self, value: int) -> None:
        self._output.write(_check_codepoint(value))


class BufferIO:
    """In-memory `IO` test double: reads consume `input_text`, writes accumulate in `output`."""

    def __init__(self, input_text: str = "") -> None:
        self._reader = _CharReader(io.StringIO(input_text))
        self._output = io.StringIO()

    @property
    def output(self) -> str:
        """Everything written so far."""
        return self._output.getvalue()

    def read_number(self) -> int:
        return self._reader.read_number()

    def read_char(self) -> int:
        return self._reader.read_char()

    def write_number(self, value: int) -> None:
        self._output.write(str(value))

    def write_char(self, value: int) -> None:
        self._output.write(_check_codepoint(value))
