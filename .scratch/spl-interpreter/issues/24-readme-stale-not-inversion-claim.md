# Fix README's false "`not` inversion" comparative claim

Status: ready-for-agent

## What to build

The README's "Supported language" section describes the comparative set as including "with `not`
inversion". That is false: negated questions were deliberately removed (ADR-0004 / issue 13), a `not`
inside a question now fails to parse, and the reference grammar has no negated questions either. The
only surviving use of `not` is the separate `If not, …` conditional, already listed in the same
sentence. Correct the documentation so it matches the implemented language.

## Acceptance criteria

- [ ] The README no longer claims `not` inversion is part of the comparative set (the rest of the
      comparative list is preserved verbatim)
- [ ] A grep confirms no other doc claims negated / `not` comparisons
- [ ] No code or test change

## Blocked by

None - can start immediately
