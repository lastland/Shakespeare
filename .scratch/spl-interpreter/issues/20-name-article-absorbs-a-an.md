# `_name_article` absorbs `a`/`an` into character names too broadly

Status: resolved

## Parent

Follow-up to [12](12-articled-character-names.md) (articled character names). Found in the Phase 2 code review.

## What to build

The leading-article handling for names (added so `the Ghost` resolves to `The Ghost`) also accepts
`a`/`an`. But the reference has no `A X`/`An X` character names — only `The X`. So `[Enter a Ghost]`
parses the name as `A Ghost`, which matches no declared character and yields a confusing error.

Narrow the `name` rule's optional leading article to `the` only. This also removes an inconsistency:
the analyzer's value-position path already re-prepends only `the`, so the name rule should match.

Repro (verified): `parse("a Ghost", start="name")` → `"A Ghost"`; `parse("an Ghost", start="name")`
→ `"An Ghost"`.

## Acceptance criteria

- [ ] The `name` rule's optional leading article accepts only `the` (not `a`/`an`).
- [ ] `[Enter the Ghost]` still works; `a`/`an` before a name no longer folds into the name.
- [ ] Test asserting `a`/`an` is not absorbed into a name.
- [ ] `primes.spl` stays byte-exact; full + differential suite green.

## Blocked by

None - can start immediately. (Related: [18](18-articled-name-determiner-mismatch.md), same articled-name area.)

## Resolution

Narrowed the grammar's `_name_article` from `A | AN | THE` to just `THE`, matching the reference
(only `The X` character names exist and the analyzer's value path only re-prepends `the`). Added
`test_name_article_only_absorbs_the_not_a_or_an`: `the Ghost` still normalizes to `"The Ghost"`,
while `a Ghost`/`an Ghost` no longer fold into a name (they now `ParseError` as a name in
isolation). `primes.spl` and the full + differential suites stay byte-exact.
