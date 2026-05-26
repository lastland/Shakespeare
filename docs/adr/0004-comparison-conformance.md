# Comparison conformance: reject `more <neutral adjective>`, drop negated questions

Two comparison forms diverged from the `shakespearelang` reference. We align both with the
reference rather than keep the local supersets. The reference grammar (the dev-dependency
`shakespearelang`'s `shakespeare.ebnf`) is the source of truth for what a comparison admits.

## Decision 1 — reject `more <neutral adjective> than` (issue 15)

The analyzer resolved a `more <adjective> than` marker as "negative adjective → less-than, *any
other* adjective → greater-than". Because the vocabulary only distinguished "adjective" from
"negative adjective", the ~20 NEUTRAL adjectives (`big`, `huge`, `large`, `small`, `tiny`,
`little`, …) fell into the greater-than branch — so `more tiny than` resolved to greater-than
(semantically backwards) and `more huge than` was wrongly accepted.

The reference admits `more` **only** with a positive or a negative adjective; a neutral adjective
there is a parse error in the oracle. We match it: `more <positive> than` → gt, `more <negative>
than` → lt, and a neutral (or unknown) adjective **raises** an `AnalysisError`, the same strict way
an unknown adjective in a constant already does (ADR-0001).

To draw the positive/neutral/negative distinction the vocabulary needed a third list. We added
`positive_adjectives` (data file + `is_positive_adjective`), mirroring `negative_adjectives`, and
sourced it from the reference EBNF's `positive_adjective` production. The three reference lists
partition the existing `adjectives.txt` exactly: positive (36) ∪ neutral (20) ∪ negative (32) = 88,
pairwise disjoint, equal to `adjectives.txt`. Neutral adjectives are not stored as a list — they are
the remainder (an adjective that is neither positive nor negative), so the partition cannot drift.

## Decision 2 — drop negated questions (issue 13)

The grammar accepted `Is X not <comparative> Y?` via a negated alternative of the `comparison` rule
(`NOT comp_kind`), producing a `Question` with `negated=True`. This worked only when the left
operand was a pronoun; with a character or noun-phrase left operand the greedy `constant` rule
swallowed the `not` as a noun-phrase word, the ambiguity resolved to the un-negated tree, the
negation was silently dropped, and analysis raised a misleading "unknown noun" error.

The reference grammar has no negated questions at all, so our negated question was a local superset
hosting a latent bug. We removed it: a question containing `not` now **fails to parse** for every
operand kind. The `negated` field is gone from the `Question` AST node and from every layer that
built or consumed it (transformer, analyzer fold, interpreter comparison), so the AST contract
reflects that negation no longer exists.

Removing the grammar alternative was necessary but **not sufficient**: with the negated alternative
gone, `Is Romeo not worse than Juliet?` still parsed, because the generic `WORD` terminal matched
`not` and the `constant` rule absorbed it (`Romeo not`), leaving an un-negated question — the same
silent-drop failure, now without negation even being expressible. The structural fix is keyword
reservation (ADR-0002): `not` is reserved out of `WORD` via a leading negative lookahead
(`(?!not(?![a-z]))`), so the lexer never offers `not` as vocabulary. `not` is never SPL vocabulary,
so this loses nothing; words that merely *contain* "not" (`nothing`, `another`, `notch`) are
unaffected thanks to the `(?![a-z])` word boundary. The `NOT` terminal stays in the grammar for the
**separate `If not, …` conditional**, which is unaffected.

## Consequences

- `more <neutral adjective> than` and any `not`-bearing question now raise/parse-error where they
  previously (mis)resolved. These are strictly *removed* acceptances, not new ones, so no reference
  program is affected: the differential suite stays 8/8 byte-exact.
- The vocabulary now exposes `positive_adjectives` / `is_positive_adjective`; the data file is
  packaged by the existing `data/*.txt` glob.
- Hard to reverse: the parser, analyzer, and interpreter tests encode "neutral-after-`more` raises"
  and "`not`-question is a ParseError" as expected behaviour.
- These follow the same posture as ADR-0001 (strictness for cases the reference does not admit) and
  ADR-0002 (keyword reservation keeps `WORD` generic without letting it eat a keyword).
