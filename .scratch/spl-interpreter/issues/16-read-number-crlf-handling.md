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

**Reverted — the original premise above was a misdiagnosis (conformance regression).**

The first fix made `read_number` consume a trailing `\r\n` as one terminator (and drop a lone `\r`).
A later max-effort review proved this *diverges* from the reference. `shakespearelang` does **not**
treat a `\r` as a numeric terminator either: it leaves the `\r` in the stream, so the next character
read returns codepoint 13. Verified end-to-end on a number-then-character program (`Listen to your
heart` / `Open your mind` / `Open your heart`):

| raw stdin | `spl` after the fix | `spl` pre-fix (`16e2ebe`) | `shakespeare` oracle |
| --- | --- | --- | --- |
| `42\r\nX` | `X` (88) ✗ | `\r` (13) ✓ | `\r` (13) |
| `42\rX`   | `X` (88) ✗ | `\r` (13) ✓ | `\r` (13) |

So the pre-fix interpreter already matched the oracle; the "fix" was a regression. The differential
suite never caught it because no bundled `.in` uses CRLF **and** the harness reads `.in` via
`Path.read_text` (universal newlines), which strips `\r` before feeding either side — so the suite
is structurally blind to CRLF divergence.

The CRLF branch has been reverted: `read_number` again consumes one bare `\n` and pushes any other
terminator (including `\r`) back, matching the reference. The three CRLF unit tests were replaced
with conformance guards that pin the `\r` as *preserved*: `test_buffer_read_number_leaves_carriage_return`,
`test_buffer_read_number_leaves_cr_before_lf`, `test_buffer_read_number_carriage_return_at_eof`, and
the `StdIO` mirror `test_stdio_read_number_leaves_carriage_return`. Issue 21's error-path pushback
(a separate, behaviorally-inert change to the same method) is unaffected. Full + differential suites
green.
