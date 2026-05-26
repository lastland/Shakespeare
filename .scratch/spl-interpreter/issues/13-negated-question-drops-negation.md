# Negated question drops the negation on a non-pronoun left operand

Status: ready-for-human

## Parent

Follow-up to [03](03-richer-comparatives.md) (richer comparatives). Found in the Phase 2 code review.

## What to build

A negated question (`Is X not worse than Y?`) only behaves correctly when its left value is a
pronoun. When the left value is a **character** or a **noun phrase**, the greedy `constant` rule
absorbs the lowercase `not` as just another noun-phrase word, the Earley ambiguity resolves to the
**un-negated** tree, and the negation is silently dropped — the program then dies with a misleading
"unknown noun" analysis error.

The reference grammar has no negated questions at all, so our negated question is a local superset.
This is a **decision**:

- **(a) Keep & fix** — restructure so `not` cannot be swallowed by `constant` (e.g. let the `NOT`
  comparator win over a bare `WORD` here), so negated questions work for every operand kind; or
- **(b) Drop** negated questions entirely to match the reference.

Pick one and record it (an ADR if (a) keeps the superset, alongside the other conformance decisions).

Repro (verified): `Is Romeo not worse than Juliet?` parses to
`Question(left=Constant(('Romeo','not')), comparison='lt', negated=False)`, then analysis raises
`AnalysisError: unknown noun: 'Romeo not'`. The pronoun form `Are you not worse than Juliet?`
correctly yields `negated=True`, which is why the existing tests (all pronoun-first) pass.

## Decision

b

## Acceptance criteria

- [ ] Decision recorded (keep-and-fix vs. drop negated questions); ADR added/updated if the superset is kept.
- [ ] If kept: a negated question with a **character** left operand (`Is Romeo not worse than Juliet?`) and a **noun-phrase** left operand (`Is the King not worse than Juliet?`) evaluates with the negation applied — no "unknown noun" error and no dropped negation.
- [ ] If kept: pronoun-first negated questions still behave as before.
- [ ] Unit test covering a negated question with a non-pronoun left operand (the currently-missing case).
- [ ] Full suite + differential suite green.

## Blocked by

None - can start immediately. (Related: touches the same comparison grammar as [15](15-more-neutral-adjective-comparative.md).)
