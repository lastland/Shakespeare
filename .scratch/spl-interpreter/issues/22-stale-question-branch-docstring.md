# Stale docstring in the `_question_branch` test helper

Status: resolved

## Parent

Test maintenance (no parent feature). Found in the Phase 2 code review.

## What to build

The `_question_branch` helper in the interpreter tests has a docstring saying it asks
`"Am I <comparative> you?"`, but the code actually emits `"Are you <comparative> <romeo>?"`. No
runtime effect — the tests are correct — but the docstring misdescribes which operand is which and
will mislead a maintainer reading it.

## Acceptance criteria

- [ ] The docstring matches what the helper actually generates (the `Are you …` form and the Romeo/Juliet operand roles).
- [ ] No behaviour change; tests still pass.

## Blocked by

None - can start immediately.

## Resolution

Rewrote the `_question_branch` docstring to describe the `Are you <comparative> <romeo>?` form the
helper actually emits, and to name the operand roles correctly: the left operand is "you" (the
Addressee, Juliet, holding `juliet`) and the right operand is the Constant `romeo`. Docstring-only
change; the suite still passes.
