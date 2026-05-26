"""Tests for the interpreter's I/O abstraction.

`BufferIO` is the test double (in-memory streams); `StdIO` is exercised over real
`io.StringIO` streams to prove it honors the same contract without touching sys.stdin/out.

Per ADR-0003 numeric input parses like spl2c's `scanf("%d")` (skip leading whitespace,
optional sign, digit run) but errors strictly: it *raises* `RuntimeSplError` at EOF and on
non-numeric input, and consumes one trailing newline after the digits. Character input keeps
the ADR-0001 EOF -> -1 carve-out. Invalid-codepoint output raises per ADR-0001.
"""

from __future__ import annotations

import io

import pytest

from spl.backend.io import BufferIO, StdIO
from spl.errors import RuntimeSplError


def test_buffer_write_number_no_trailing_newline() -> None:
    out = BufferIO()
    out.write_number(42)
    assert out.output == "42"


def test_buffer_write_number_negative() -> None:
    out = BufferIO()
    out.write_number(-7)
    out.write_number(0)
    assert out.output == "-70"


def test_buffer_write_char_emits_chr() -> None:
    out = BufferIO()
    out.write_char(ord("A"))
    out.write_char(0x1F600)  # astral plane is fine
    assert out.output == "A\U0001f600"


def test_buffer_write_char_rejects_negative() -> None:
    out = BufferIO()
    with pytest.raises(RuntimeSplError):
        out.write_char(-1)


def test_buffer_write_char_rejects_above_max() -> None:
    out = BufferIO()
    with pytest.raises(RuntimeSplError):
        out.write_char(0x110000)


def test_buffer_write_char_rejects_surrogate() -> None:
    out = BufferIO()
    for cp in (0xD800, 0xDABC, 0xDFFF):
        with pytest.raises(RuntimeSplError):
            out.write_char(cp)


def test_buffer_read_char_returns_codepoint() -> None:
    io_ = BufferIO("Ab")
    assert io_.read_char() == ord("A")
    assert io_.read_char() == ord("b")


def test_buffer_read_char_eof_returns_minus_one() -> None:
    io_ = BufferIO("")
    assert io_.read_char() == -1
    # stays at EOF
    assert io_.read_char() == -1


def test_buffer_read_number_plain() -> None:
    io_ = BufferIO("123")
    assert io_.read_number() == 123


def test_buffer_read_number_with_sign() -> None:
    # Sign parsing is faithful to spl2c's scanf("%d") (ADR-0003).
    assert BufferIO("-45").read_number() == -45
    assert BufferIO("+9").read_number() == 9


def test_buffer_read_number_skips_leading_whitespace() -> None:
    io_ = BufferIO("   \t\n  88rest")
    assert io_.read_number() == 88


def test_buffer_read_number_eof_raises() -> None:
    # Numeric input at EOF raises rather than returning a sentinel (ADR-0003).
    with pytest.raises(RuntimeSplError):
        BufferIO("").read_number()
    with pytest.raises(RuntimeSplError):
        BufferIO("    ").read_number()


def test_buffer_read_number_non_numeric_raises() -> None:
    # Non-numeric input where a number is expected raises (ADR-0003).
    with pytest.raises(RuntimeSplError):
        BufferIO("abc").read_number()
    with pytest.raises(RuntimeSplError):
        BufferIO("a123").read_number()
    # a lone sign with no digit following is not a number
    with pytest.raises(RuntimeSplError):
        BufferIO("-x").read_number()


def test_buffer_read_number_digit_prefix_leaves_rest() -> None:
    # "4257a123" parses the digit prefix and leaves the non-digits for the next read.
    io_ = BufferIO("4257a123")
    assert io_.read_number() == 4257
    assert io_.read_char() == ord("a")


def test_buffer_read_number_stops_at_non_digit_and_leaves_rest() -> None:
    io_ = BufferIO("12 34")
    assert io_.read_number() == 12
    # the space + remaining digits are still readable
    assert io_.read_number() == 34


def test_buffer_read_number_consumes_one_trailing_newline() -> None:
    # A number's trailing newline is consumed, not leaked into the next char read (ADR-0003).
    io_ = BufferIO("42\nX")
    assert io_.read_number() == 42
    assert io_.read_char() == ord("X")


def test_buffer_read_number_consumes_trailing_crlf() -> None:
    # A trailing "\r\n" is consumed as one terminator so the "\r" does not leak (ADR-0003).
    io_ = BufferIO("42\r\nX")
    assert io_.read_number() == 42
    assert io_.read_char() == ord("X")


def test_buffer_read_number_lone_cr_does_not_leak() -> None:
    # A lone "\r" (not followed by "\n") terminates the number; it is dropped, not leaked, and the
    # following real character is preserved.
    io_ = BufferIO("42\rX")
    assert io_.read_number() == 42
    assert io_.read_char() == ord("X")


def test_buffer_read_number_trailing_cr_at_eof() -> None:
    # A "\r" immediately before EOF terminates the number and leaves the stream at EOF.
    io_ = BufferIO("42\r")
    assert io_.read_number() == 42
    assert io_.read_char() == -1


def test_buffer_read_number_no_newline_leaves_terminator() -> None:
    # When the terminator is not a newline it is pushed back for the next read.
    io_ = BufferIO("42X")
    assert io_.read_number() == 42
    assert io_.read_char() == ord("X")


def test_buffer_read_number_error_preserves_offending_char() -> None:
    # On the non-numeric error path the consumed char is pushed back, so it stays readable and the
    # stream is faithful to the scanf("%d") model (ADR-0003).
    io_ = BufferIO("-x5")
    with pytest.raises(RuntimeSplError):
        io_.read_number()
    assert io_.read_char() == ord("x")
    assert io_.read_char() == ord("5")


def test_buffer_read_number_non_numeric_char_recoverable() -> None:
    # A leading non-digit raises but is left in the stream for a subsequent read.
    io_ = BufferIO("a123")
    with pytest.raises(RuntimeSplError):
        io_.read_number()
    # "a" is recoverable; the digits behind it then parse.
    assert io_.read_char() == ord("a")
    assert io_.read_number() == 123


def test_buffer_read_number_then_read_char_consumes_in_order() -> None:
    io_ = BufferIO("7X")
    assert io_.read_number() == 7
    assert io_.read_char() == ord("X")
    assert io_.read_char() == -1


# --- StdIO over StringIO streams (same contract, real stream plumbing) ---


def test_stdio_write_number_and_char() -> None:
    sink = io.StringIO()
    stdio = StdIO(output=sink)
    stdio.write_number(13)
    stdio.write_char(ord("!"))
    assert sink.getvalue() == "13!"


def test_stdio_write_char_invalid_raises() -> None:
    stdio = StdIO(output=io.StringIO())
    with pytest.raises(RuntimeSplError):
        stdio.write_char(0x110000)


def test_stdio_read_char_eof_returns_minus_one() -> None:
    stdio = StdIO(input=io.StringIO(""))
    assert stdio.read_char() == -1


def test_stdio_read_char_returns_codepoint() -> None:
    stdio = StdIO(input=io.StringIO("z"))
    assert stdio.read_char() == ord("z")
    assert stdio.read_char() == -1


def test_stdio_read_number_with_sign_and_whitespace() -> None:
    stdio = StdIO(input=io.StringIO("  -100x"))
    assert stdio.read_number() == -100


def test_stdio_read_number_eof_raises() -> None:
    stdio = StdIO(input=io.StringIO("   "))
    with pytest.raises(RuntimeSplError):
        stdio.read_number()


def test_stdio_read_number_consumes_one_trailing_newline() -> None:
    stdio = StdIO(input=io.StringIO("42\nX"))
    assert stdio.read_number() == 42
    assert stdio.read_char() == ord("X")


def test_stdio_read_number_consumes_trailing_crlf() -> None:
    stdio = StdIO(input=io.StringIO("42\r\nX"))
    assert stdio.read_number() == 42
    assert stdio.read_char() == ord("X")


def test_stdio_read_number_error_preserves_offending_char() -> None:
    stdio = StdIO(input=io.StringIO("-x5"))
    with pytest.raises(RuntimeSplError):
        stdio.read_number()
    assert stdio.read_char() == ord("x")
