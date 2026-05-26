# SPL interpreter — issue index

Local-markdown issue tracker (see `docs/agents/issue-tracker.md`). One file per issue; the
`Status:` line uses the triage vocabulary in `docs/agents/triage-labels.md`.

## Bugs
- [01](01-multiline-comments-break-parsing.md) — multi-line comments break parsing — **ready-for-agent**

## Phase 2 language features
- [02](02-implement-stacks.md) — stacks (Remember/Recall) — **ready-for-agent**
- [03](03-richer-comparatives.md) — full comparative set — **ready-for-agent**

## Reference-program coverage
- [04](04-remaining-reference-programs.md) — remaining sample programs as golden tests — **needs-triage**

## Conformance decisions (vs shakespearelang)
- [07](07-goto-target-scope.md) — goto act+scene vs scene-only — **needs-triage**
- [08](08-division-sign-convention.md) — division/remainder sign — **needs-info**
- [09](09-input-error-semantics.md) — non-numeric input: -1 vs error — **needs-triage**
- [10](10-conditional-without-question.md) — If so/If not with no question — **needs-info**

## Infrastructure
- [05](05-package-data-for-wheel.md) — package data files for wheel installs — **ready-for-agent**
- [06](06-differential-ci-testing.md) — live differential CI testing — **ready-for-agent**
- [11](11-write-readme.md) — write the README — **ready-for-human**
