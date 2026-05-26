# `more <neutral adjective> than` resolves to greater-than instead of being rejected

Status: ready-for-human

## Parent

Follow-up to [03](03-richer-comparatives.md) (richer comparatives). Found in the Phase 2 code review.

## What to build

`more <adjective> than` resolves its direction as "negative adjective → less-than, **anything else**
→ greater-than", which lumps the ~20 NEUTRAL adjectives (`big`, `huge`, `large`, `small`, `tiny`,
`little`, …) in with the positive ones. So `more tiny than` resolves to greater-than (semantically
backwards) and `more huge than` is accepted — whereas the reference admits `more` only with a
**positive** or a **negative** adjective; a neutral adjective after `more` is a parse error in the
oracle.

This is a **conformance decision**:

- **(a) Reject** `more <neutral adjective> than` to match the reference (raise, like an unknown adjective); or
- **(b) Keep** the permissive superset, but record it as an allowed divergence and decide the neutral-adjective direction deliberately (not as an accident of the "else → gt" fallback).

Likely an ADR update alongside the other conformance decisions ([07](07-goto-target-scope.md)–[10](10-conditional-without-question.md)).

Repro (verified): `Am I more tiny than you?` resolves to `comparison='gt'`; the reference
`shakespeare run` parse-errors on `more huge than`.

## Acceptance criteria

- [ ] Decision recorded (reject vs. documented superset); ADR added/updated.
- [ ] If rejecting: `more <neutral adjective> than` raises a clear analysis/parse error; a test covers it.
- [ ] If keeping: `tests/test_differential.py` gains an `ALLOWED_DIVERGENCES` entry for the neutral-after-`more` case, and the chosen direction is tested.
- [ ] `more <negative adjective> than` → lt and `more <positive adjective> than` → gt still hold.
- [ ] Full + differential suite green.

## Blocked by

None - can start immediately. (Related: [13](13-negated-question-drops-negation.md) touches the same comparison grammar.)
