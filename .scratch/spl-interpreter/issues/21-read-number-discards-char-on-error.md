# `read_number` discards the consumed terminator on the non-numeric error path

Status: resolved

## Parent

Follow-up to [09](09-input-error-semantics.md) (input error semantics). Found in the Phase 2 code review.

## What to build

When numeric input has no digits (a lone sign, or a non-digit where a number was expected),
`read_number` raises **before** pushing back the character it already consumed, so that character is
lost from the stream. This diverges from the spl2c `scanf("%d")` model the module docstring claims to
follow (which leaves the offending characters in the stream). Low impact, because the error is
normally fatal — but it is incorrect per the stated model.

Repro (verified): `BufferIO("-x5")` → `read_number()` raises, then `read_char()` returns `ord('5')`
— the `x` was consumed and lost.

Resolve either by pushing the terminator back before raising (so reads stay recoverable and the
scanf model holds), or by correcting the docstring to state that a failed numeric read is fatal and
does not preserve the stream. Prefer the push-back if it is cheap and consistent.

## Acceptance criteria

- [ ] Either: the consumed terminator is pushed back before raising, and a test asserts the offending character is still readable after a failed `read_number`; or: the docstring is corrected to match the actual (fatal, stream-consuming) behaviour.
- [ ] No regression to the EOF / no-numeric-input error semantics from [09](09-input-error-semantics.md).
- [ ] Full + differential suite green.

## Blocked by

None - can start immediately. (Related: same reader as [16](16-read-number-crlf-handling.md).)

## Resolution

Chose the push-back fix (preferred option): on the non-numeric error path `read_number` now pushes
the already-consumed offending character back before raising, so it stays in the stream and the
`scanf("%d")` model (ADR-0003) holds. At EOF there is nothing to push back, so the
raise-on-EOF / raise-on-non-numeric contract is preserved. Added
`test_buffer_read_number_error_preserves_offending_char` (the `"-x5"` repro now leaves `x` then `5`
readable), `test_buffer_read_number_non_numeric_char_recoverable`, and a `StdIO` mirror; updated the
module / `IO` / `read_number` docstrings. Full + differential suites green.
