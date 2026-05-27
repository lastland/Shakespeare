# Outputting a very large integer crashes with an unwrapped ValueError

Status: needs-triage

## What's wrong

`write_number` does `str(value)` to render a numeric output (`Open your heart`). Since Python 3.11
the default integer→string conversion is capped at 4300 digits, so `str(value)` raises a raw
`ValueError: Exceeds the limit (4300 digits) for integer string conversion` for any register value
with more than ~4300 decimal digits. `ValueError` is **not** a `SplError`, so it escapes the CLI's
`except SplError` handler and crashes the interpreter with a bare Python traceback — the same
ADR-0001 contract violation we just fixed on the *compute* side, but on the **output** side.

This is **pre-existing and not specific to factorial**: any value with >4300 digits trips it. It is
reachable today via repeated squaring (`the square of the square of …`), and `the factorial of`
(issue 23) makes it trivial — e.g. `2000!` has ~5736 digits and computes quickly, then `Open your
heart` crashes. (Distinct from issue 23's guard, which converts the `OverflowError` for an operand
above `sys.maxsize` into a clean `RuntimeSplError` at compute time; this issue is about *rendering*
an already-computed large value.)

A secondary, related symptom: computing a large-but-in-range bignum (e.g. `10**6` factorial, or deep
squaring) can hang for several seconds with no feedback before any output is attempted.

## Decision needed (why needs-triage)

The policy is a maintainer call:

- **(a) Guard `write_number`** — refuse output beyond a digit threshold with a clean
  `RuntimeSplError`. Keeps the SplError contract; rejects astronomically large output.
- **(b) Raise the limit** — `sys.set_int_max_str_digits(0)` (or a high cap) to allow arbitrary-size
  output; removes the crash but keeps the slowness.
- **(c) Minimal wrap** — `try/except ValueError` around the `str()` re-raising as `RuntimeSplError`;
  smallest change, clean error instead of a crash, no behavior change for normal values.

Whether to also bound compute time (the hang) is a separate sub-question; any bound is an arbitrary
cap and should be decided explicitly.

## Acceptance criteria

- [ ] Rendering a large numeric value never escapes as a non-`SplError`; the CLI reports it cleanly
- [ ] A test pins the chosen behavior (e.g. outputting a >4300-digit value)
- [ ] The decision (a/b/c, and any compute bound) is recorded in an ADR or the relevant ADR note

## Blocked by

None - can start once the policy above is decided
