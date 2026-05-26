# `read_number` leaks a carriage return on CRLF input

Status: resolved

## Parent

Follow-up to [09](09-input-error-semantics.md) (input error semantics). Found in the Phase 2 code review.

## What to build

Numeric input (`read_number`) consumes only a bare `\n` as the trailing terminator after the digits.
On CRLF-terminated input the digit run stops at `\r`, which is *not* `\n`, so it is pushed back and
leaks into the next character read — desyncing every subsequent interleaved read. A program that
interleaves numeric and character input from a Windows/CRLF-authored file emits a spurious carriage
return and misreads everything after it.

Repro (verified): input `"42\r\nX"` → `read_number()` returns `42`, then `read_char()` returns `13`
(`\r`) instead of `ord('X')`. With `"42\nX"` it correctly returns `'X'`.

Fix direction: recognise `\r\n` (and a bare `\n`) as a single trailing newline to consume, so the
`\r` does not leak.

## Acceptance criteria

- [ ] After reading a number, a trailing `\r\n` is consumed as one terminator (a bare `\n` still works as today).
- [ ] `read_number()` then `read_char()` on CRLF input returns the next *real* character.
- [ ] `echo.spl` (which relies on single-`\n` consumption) stays byte-exact against the oracle.
- [ ] Test covering numeric-then-character reads on CRLF input.
- [ ] Full + differential suite green.

## Blocked by

None - can start immediately. (Related: same reader as [21](21-read-number-discards-char-on-error.md).)

## Resolution

`_CharReader.read_number` now treats a trailing `\r\n` as one terminator: when the digit run ends
on `\r` it looks one char past it; if that char is `\n` both are consumed, otherwise the lookahead
char is pushed back and the lone `\r` (itself whitespace, never a real datum) is dropped rather than
leaked. A bare `\n` still works unchanged, so `echo.spl` stays byte-exact. Added
`test_buffer_read_number_consumes_trailing_crlf` (the `"42\r\nX"` repro now reads `X`), plus
`test_buffer_read_number_lone_cr_does_not_leak`, `test_buffer_read_number_trailing_cr_at_eof`, and a
`StdIO` mirror. Full + differential suites green.
