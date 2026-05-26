# Articled-name retry mis-resolves a non-`the` determiner (or bare noun) to a `The X` character

Status: ready-for-human

## Parent

Follow-up to [12](12-articled-character-names.md) (articled character names). Found in the Phase 2 code review.

## What to build

In value position the `constant` rule drops **every** determiner (`a`, `an`, `the`, `my`, `his`,
…), then the analyzer blindly re-prepends `the` to retry the character match. Because the original
determiner is unrecoverable, a non-`the` determiner — or no determiner at all — in front of a word
that matches a declared `The X` character resolves to that **character**.

Repro (verified): with `The Ghost` declared, the values `his Ghost`, `a Ghost`, and bare `Ghost` all
fold to `CharacterRef("The Ghost")`.

This is **latent** today: no canonical `The X` character's suffix (`Ghost`, `Apothecary`, the Dukes,
…) is itself a noun, so there is no active collision. It's a correctness-hardening **decision**: the
determiner is currently discarded by the grammar, so a fix must preserve enough of it (in the
grammar/AST) to know whether it was `the`, then settle the intended semantics — e.g. only `the X`
resolves to a `The X` character, while `his X` / bare `X` fall through to noun/error.

## Acceptance criteria

- [ ] Decision recorded on the intended semantics for a non-`the` determiner (or no determiner) before a `The X` name.
- [ ] Only a genuine leading `the` (or no determiner, if so decided) resolves to a `The X` character; a different determiner does not.
- [ ] Tests for `the Ghost` (→ character) vs `his Ghost` (→ per the decision), with `The Ghost` declared.
- [ ] `primes.spl` (which uses `the Ghost`) stays byte-exact; full + differential suite green.

## Blocked by

None - can start immediately. (Related: [20](20-name-article-absorbs-a-an.md), same articled-name area.)
