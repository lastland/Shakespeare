# Character names with a lowercase leading article (`the Ghost`)

Status: resolved

Some canonical character names begin with an article — e.g. `The Ghost` — and appear in source with
the article lowercased: `[Enter the Ghost and Juliet]` and, in value position,
`Art thou more cunning than the Ghost?`. This was the sole remaining blocker for `primes.spl`
(discovered while adding the reference programs, issue 04 — the original handoff did not anticipate
it).

The analyzer already matches Character names case-insensitively (`_match_character` casefolds), so
the gap was purely lexical: our `NAME` terminal is `/[A-Z][a-z]+.../`, so a lowercase `the`
tokenizes separately from `Ghost`.

## Resolution

Scoped to a leading lowercase article before a **capitalized** name — `NAME` stays purely
capitalized (we did *not* make it case-insensitive, which would dissolve the `NAME`/`WORD` split and
let `romeo` lex as a name). Two narrow handlers (see ADR-0002 consequences):

1. **Stage directions:** the `name` *rule* takes an optional leading article (`the`/`a`/`an`); the
   transformer normalizes the join the way the reference's `normalize_name` does
   (`.title().replace(" Of ", " of ")`), idempotent on already-correct names.
2. **Value position:** the `constant` rule drops the determiner, so the analyzer — after a bare
   character match fails and before the noun-phrase fallback — retries the match with `the`
   re-prepended. The declared-vs-undeclared decision stays the analyzer's: `the King` (no such
   Character) folds to a Constant; `the Ghost` (declared) becomes a Character reference.

Verified: no new grammar ambiguity (explicit-ambiguity counts unchanged), full suite green, and all
five sample programs (incl. `primes.spl`) byte-match the `shakespearelang` oracle.
