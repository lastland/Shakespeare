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
- Capitalized SPL nouns (`Lord`, `King`, `Heaven`) currently collide with `NAME` and are not yet
  usable in constants — a known phase-1 limitation tracked for phase 1.5.
