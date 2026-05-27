# Parsing strategy: Earley + generic WORD classified downstream

We parse SPL with `lark`'s Earley parser (dynamic lexer). Keywords are **named, word-boundaried
terminals** (e.g. `SUM: /sum(?![a-z])/i`); the vocabulary is a single generic `WORD: /[a-z]+/`
terminal (plus a capitalized `NAME` terminal). Word classification — which words are
positive/negative/neutral nouns, adjectives, or valid character names, and the integer value of a
Constant — happens *after* parsing, in the backend analyzer, not in the grammar.

We chose this over enumerating SPL's large fixed *vocabulary* as grammar terminals (the
generated-terminals approach `spl2c` takes): enumerating thousands of words bloats the grammar and
duplicates data that belongs in files; a generic `WORD` keeps the grammar small and pushes
vocabulary concerns to data files + the analyzer. SPL programs are tiny, so Earley's asymptotics
are irrelevant.

Two refinements were needed so a generic `WORD` does not get greedily mis-tokenised:
- **Arithmetic lives in a dedicated `expression` rule**, and pronouns/`expression` outrank
  `constant` by rule priority, so `the sum of a flower and a pig` resolves to the operation rather
  than one long `WORD+` constant.
- **Keywords are word-boundaried** (`(?![a-z])`), proper keyword reservation, so a keyword cannot
  match a prefix of a vocabulary word (`an` must not eat the start of `angel`; `sum` must not eat
  `summer`). This is why `WORD` itself enumerates nothing.

This is surprising (a reader expects the vocabulary to live in the grammar) and hard to reverse
(it is the structural shape of both the grammar and the frontend/backend split), hence this record.

## Consequences

- The grammar cannot reject an unknown or miscategorised word; that check moves to the analyzer.
- Multi-word character names ("Lady Macbeth", "John of Gaunt") are matched by a single `NAME`
  terminal (capitalized words + connective "of") and validated as a joined string by the analyzer.
- Capitalized SPL nouns (`Lord`, `King`, `Heaven`) lex as `NAME` (they look like names); the
  analyzer classifies a capitalized word as a noun when it does not name a declared Character, so
  `a King` folds to a Constant. (Resolved in phase 1.5; an earlier draft listed this as an open
  limitation.)
- Gotos accept **act or scene** targets, following the official report ("there is no way to refer
  to a specific scene in another act — you have to settle for jumping to the act itself").
  `shakespearelang` restricts gotos to scenes only, so act-gotos are a spec-faithful superset that
  cannot be cross-checked against the oracle (it parse-errors on them) — see the issue-06 allow-list.
  Scene gotos resolve within the current act, matching both the spec and the oracle.
- Some character names begin with "The" (e.g. `The Ghost`) and appear lowercased in source
  (`[Enter the Ghost ...]`, `more cunning than the Ghost`). Rather than make `NAME`
  case-insensitive — which would dissolve the `NAME`/`WORD` split and let `romeo` lex as a name —
  the lowercase article is handled in two narrow places that keep `NAME` purely capitalized:
  (1) the `name` *rule* takes an optional leading article (`the`/`a`/`an`) and the
  transformer normalizes the result the way the reference's `normalize_name` does
  (`.title().replace(" Of ", " of ")`), so `the Ghost` → `The Ghost`, idempotent on already-correct
  names; (2) in value position the `constant` rule keeps a literal leading `the` as a `THE` token
  (recorded on the `Constant` node as `leading_the`) while dropping every other determiner, so the
  analyzer — after a bare character match fails and before the noun-phrase fallback — retries the
  match with `the` re-prepended *only when the source wrote `the`* (the reference has no `A X`/`An X`
  character names). The declared-vs-undeclared decision stays the analyzer's: `the King` (no such
  character) falls through to the constant value, while `the Ghost` (declared) becomes a character
  reference.
- Value-position articled-character resolution requires a *literal* leading `the` (issue 18, a
  small conformance fix in the same family as ADR-0004/0005). Carrying only the bare words was
  ambiguous — a dropped determiner let `his Ghost`, `a Ghost`, and bare `Ghost` all mis-fold to the
  `The Ghost` character. The reference's `character_name` value is the full literal name (`The
  Ghost`); a possessive/article only appears in a noun phrase. So a non-`the` determiner (or none)
  now skips the retry and falls through to noun-phrase resolution (here an "unknown noun" error,
  since `ghost` is not a noun), matching the reference.
- Determiners are reserved out of `WORD` (a negative lookahead listing the determiners alongside
  `not`), because a determiner like `the` matches BOTH its keyword terminal and the generic `WORD`
  over the same span — making `constant` (`THE (WORD|NAME)+ | _det_other? (WORD|NAME)+`) genuinely
  ambiguous for every determiner. It parsed correctly only because Lark's default ambiguity
  resolution happened to pick the determiner reading (raising terminal priority does NOT fix it);
  reserving the determiners — none of which is SPL vocabulary — removes the ambiguity at the source.
  This is also why the cheaper `dynamic` lexer suffices over `dynamic_complete`: word-boundaried
  keywords mean no keyword can match a prefix of a vocabulary word, so there are no hidden split
  tokenisations for the exhaustive lexer to discover.
