"""The interpreter's I/O abstraction.

SPL programs read and write through four primitives, each a stage line:
- "Listen to your heart"  -> read a base-10 integer            (`read_number`)
- "Open your mind"        -> read one character as a codepoint  (`read_char`)
- "Open your heart"       -> emit an integer as text            (`write_number`)
- "Speak your mind"       -> emit a codepoint as a character    (`write_char`)

I/O is dependency-injected via the `IO` protocol so the interpreter can be tested without
touching real stdin/stdout: `StdIO` wraps real text streams, `BufferIO` is an in-memory double.

Per ADR-0001/ADR-0003 the undefined cases are handled strictly. Character input keeps the EOF
-> -1 carve-out (the looping programs depend on it as a protocol). Numeric input parses like
spl2c's `scanf("%d")` (leading whitespace skip, optional sign, digit run) but *raises*
`RuntimeSplError` at EOF and on non-numeric input rather than returning a sentinel, and consumes
one bare `\n` after the digits (a `\r`, like any non-`\n` terminator, is left for the next read --
matching the reference). On the non-numeric error path the consumed sign and offending char are
pushed back before raising, leaving the unparsed numeric token in the stream. Writing a character
whose value is not a valid Unicode code point also raises rather than coercing it.
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
        """Read a base-10 integer from input.

        Parses spl2c-style (leading whitespace skip, optional sign, digit run) but raises
        `RuntimeSplError` at EOF and on non-numeric input (ADR-0003), and consumes one bare `\\n`
        after the digits (a `\\r` is left for the next read, matching the reference). On the
        non-numeric error path the consumed sign and offending character are pushed back before
        raising, leaving the unparsed numeric token readable.
        """
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
    """A `TextIO` wrapped with a small (LIFO) pushback buffer.

    `read_number` must look one character past the digits to know the number has ended; that
    terminator has to remain available to the next read. On a matching failure it also restores the
    whole consumed-but-unparsed numeric token (a consumed sign plus the offending char). A pushback
    buffer gives us this without relying on `seek`/`tell`, which a real (terminal) stdin does not
    support.
    """

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream
        self._pending: list[str] = []

    def _next(self) -> str:
        """Return the next character, or "" at EOF."""
        if self._pending:
            return self._pending.pop()
        return self._stream.read(1)

    def _push_back(self, ch: str) -> None:
        """Push `ch` (a non-empty single char) back so a later read returns it. The buffer is a LIFO
        stack, so to restore several chars in stream order, push the LATER ones first."""
        self._pending.append(ch)

    def read_char(self) -> int:
        ch = self._next()
        if ch == "":
            return -1
        return ord(ch)

    def read_number(self) -> int:
        """Skip leading whitespace, parse an optional sign then base-10 digits.

        Parsing follows spl2c's `scanf("%d")` (ADR-0003): a leading whitespace run is skipped, an
        optional sign is accepted (so negatives parse), then the digit run is read. One trailing
        bare `\\n` is consumed so it does not leak into the next character read; any other
        terminator -- including a `\\r`, which the reference does not treat as a numeric terminator
        -- is pushed back so the next character read returns it.

        Raises `RuntimeSplError` when no digit is found -- at EOF before any digit, on a sign not
        followed by a digit, or on otherwise non-numeric input. On a matching failure the consumed
        sign and the offending character are both pushed back before raising, so the failed read
        leaves the unparsed numeric token in the stream (the leading-whitespace skip is committed,
        as scanf's is); at EOF there is nothing to push back. The interpreter halts on this raise,
        so this restoration is stream hygiene for tests, not behavior any program observes.
        """
        # Skip leading whitespace.
        ch = self._next()
        while ch != "" and ch.isspace():
            ch = self._next()
        if ch == "":
            raise RuntimeSplError("no numeric input: end of file")

        sign = 1
        sign_char = ""
        if ch in "+-":
            sign_char = ch
            if ch == "-":
                sign = -1
            ch = self._next()

        digits: list[str] = []
        while ch != "" and ch.isascii() and ch.isdigit():
            digits.append(ch)
            ch = self._next()

        if not digits:
            # Matching failure: no digit where a number was expected. Restore the full unparsed
            # numeric token -- the offending char (if any) and a consumed sign (if any) -- so a
            # failed read leaves the stream as scanf would (the leading-whitespace skip is committed
            # either way). Push the offending char first; the buffer is LIFO, so the sign comes back
            # out first, restoring stream order. NB: the interpreter halts on this raise and never
            # reads the stream afterward; the restoration is for tests, not observed behavior.
            if ch != "":
                self._push_back(ch)
            if sign_char:
                self._push_back(sign_char)
            raise RuntimeSplError("no numeric input")

        # Consume exactly one bare "\n" terminator; push any other terminator back for the next
        # read. A "\r" is deliberately NOT a terminator here: the reference (shakespearelang) leaves
        # a "\r" in the stream after a number, so the next character read returns it (codepoint 13).
        # Consuming a "\r\n" pair (or dropping a lone "\r") diverges from the oracle on CR-bearing
        # input -- that was issue 16, which mistook this reference-conformant behavior for a leak.
        if ch != "" and ch != "\n":
            self._push_back(ch)

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
