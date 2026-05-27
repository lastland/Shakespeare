# Gap analysis: this interpreter vs. a full implementation of SPL

How far is this interpreter from a *full* implementation of the Shakespeare Programming Language?
This document records the gap, with evidence. The short answer: against the de-facto reference, the
interpreter now implements **every** construct (the last one, `the factorial of`, landed in issue
23); every remaining difference is a deliberate, recorded divergence (mostly a superset) — plus one
stale doc claim. No over-acceptance remains undocumented.

## Baselines & method

"Full" is measured against two baselines, because they differ:

- **Primary — the de-facto reference.** `zmbc/shakespearelang`'s `shakespeare.ebnf`. This project
  *declares* it the conformance target (`README.md`, every ADR), and the eight golden programs
  byte-match its output. This is the right yardstick for "did we implement the language".
- **Secondary — the original language.** The Hasselström & Åslund report / esolangs / Wikipedia
  description, which is a strict *superset* of the reference (it has at least one form the reference
  never implemented). Used to flag where even the reference is incomplete.

Method: the reference EBNF was diffed, rule by rule, against `src/spl/frontend/grammar.lark`,
`src/spl/backend/analyzer.py`, and `src/spl/backend/vocabulary.py` + `src/spl/backend/data/*.txt`.
Every empirical claim below was probed against the live parser/analyzer.

## Summary

| Area | Reference (full) | This interpreter | Verdict |
| --- | --- | --- | --- |
| Binary arithmetic (sum/difference/product/quotient/remainder) | 5 | 5 | ✅ complete |
| Unary arithmetic (twice/square/cube/square-root/factorial) | 5 | 5 | ✅ complete (factorial: issue 23) |
| Comparatives (bare ±, `more ADJ than`, `as ADJ as`) | all | all | ✅ complete |
| Negated comparisons (`not better than`) | original-spec only | none | ➖ gap vs *original*, matches reference |
| I/O (4 forms) | 4 | 4 | ✅ complete |
| Stacks (Remember/Recall) | yes | yes | ✅ complete |
| Conditionals / gotos / stage directions | yes | yes | ✅ complete (goto is a superset) |
| Vocabulary (nouns/adjectives/names) | fixed lists | reference-exact | ✅ complete |
| Runtime semantics for spec-undefined cases | mostly undefined | strict errors | ⚙️ deliberate (ADR-0001/0003) |

Legend: ✅ complete · ❌ genuine gap · ➖ gap only vs the original spec · ⚙️ deliberate divergence.

## G1 — `the factorial of` (closed by issue 23)

The reference `unary_operation` admits `the cube of`, `the factorial of`, `the square of`,
`the square root of`, and `twice`. This interpreter now implements all five. The `expression` rule
carries the `THE FACTORIAL OF value -> factorial` alternative with a word-boundaried `FACTORIAL`
terminal (`grammar.lark`, following ADR-0002); the transformer maps it to `UnaryOp(op='factorial',
…)`, and the interpreter's `_unary` computes it over exact integers (`0! = 1`, `n! = n·(n-1)!`).

Reference semantics: `0! = 1`, `n! = n·(n-1)!` for `n ≥ 0`. A negative operand is spec-undefined,
so it raises a `RuntimeSplError` (strict posture of ADR-0001, mirroring the negative-`√` guard).

## G2 — Negated comparisons (gap vs the *original* spec only)

The original language can invert a test — "not as good as", "not better than". **Both** this
interpreter (ADR-0004 / issue 13) and the `shakespearelang` reference omit negated questions
entirely. So the interpreter is *reference-conformant* but not *original-spec-complete* here. The
`NOT` terminal survives only for the separate `If not, …` conditional (`grammar.lark:99`). Adding
negated questions would mean diverging from the reference toward the original spec — a product
decision, not a bug; see ADR-0004 for why it was dropped (it hosted a silent-drop bug).

## Deliberate divergences (recorded — not gaps)

These are intentional and each has an ADR. Most make the accepted language a *superset* of the
reference; the runtime ones make it *stricter*.

- **Goto targets an act *or* a scene** (`grammar.lark:116-117`); the reference allows scene only.
  Follows the official report (ADR-0002).
- **Label terminator accepts `?`** as well as `!`/`.` (ADR-0005).
- **Exact-integer division and `√`** vs the reference's float division — same sign convention, but
  precise above 2⁵³ (ADR-0001, "Conformance" notes).
- **Strict `RuntimeSplError`** for cases the spec leaves undefined: division/modulo by zero,
  off-stage reference, more than two characters on stage, `√` of a negative, EOF / non-numeric
  numeric input, and a dangling `If so`/`If not` (ADR-0001, ADR-0003). The one carve-out is
  character-input EOF → −1.
- **`more <neutral adjective> than` is rejected** — this *matches* the reference (it admits `more`
  only with a positive or negative adjective), so it is not a gap (ADR-0004).
- **Noun/adjective polarity is not enforced** (ADR-0007; was the subject of issue 25). The reference
  parses a constant as a *negative* noun phrase (adjectives ∈ negative ∪ neutral, noun negative) or a
  *positive* noun phrase (adjectives ∈ positive ∪ neutral, noun positive/neutral); a polarity
  mismatch is a parse error. The analyzer's `_noun_phrase_value` (`analyzer.py:203-215`) checks only
  that each pre-noun word *is an adjective* — never its polarity. So `a happy coward` (positive
  adjective + negative noun) folds to `-2` and `an evil King` (negative adjective + positive noun)
  folds to `+2`, both **accepted** where the reference rejects them. Safe because adjective polarity
  carries no value information — any adjective just doubles the magnitude — so the computed value
  (noun sign × 2^adjectives) is always correct; only the reference's parse-time agreement check is
  unenforced. Kept as an intentional superset and recorded in ADR-0007.
- **`as <word> as` admits any vocabulary word** as the equality ("simile") adjective (ADR-0007;
  issue 26). The reference restricts the middle word to a known adjective; `comp_kind`'s
  `AS WORD AS -> eq` alternative (`grammar.lark:86`) takes any generic `WORD`, and the transformer's
  `eq` handler discards it, returning the bare `"eq"`. So `Are you as cat as a King?` parses to an
  `eq` question and analyzes cleanly even though `cat` is a noun. Safe because the simile adjective
  is semantically inert — the form means equality regardless of the word (unlike `more <adj> than`,
  whose sign must be kept) — so every program the reference accepts here folds to the identical
  `eq`. Kept as an intentional superset and recorded in ADR-0007.
- **Nested conditionals parse** (ADR-0007; issue 26). `conditional` guards a `statement`, and
  `statement` includes `conditional` (`grammar.lark:53-61,98-99`), so `If so, if not, …` parses to a
  nested `Conditional`; the reference allows exactly one condition prefix per operation. Safe because
  the interpreter reuses the singly-guarded rule — each `Conditional` consults the single
  `last_question` flag (`interpreter.py:110-114`) — so a nested prefix needs no new evaluation rule.
  Kept as an intentional superset and recorded in ADR-0007.

## Verified complete (explicitly *not* gaps)

To bound the study: the following were checked and match the reference.

- **Comparatives:** bare positives (`better`/`bigger`/`fresher`/`friendlier`/`nicer`/`jollier`),
  bare negatives (`worse`/`punier`/`smaller`), `more <adj> than` (direction resolved from adjective
  sign in `analyzer._resolve_comparison`), and `as <adj> as` equality.
- **I/O:** all four forms — `Open your heart` (number out), `Speak your mind` (char out),
  `Listen to your heart` (number in), `Open your mind` (char in).
- **Stacks:** `Remember <value>` / `Recall …`, LIFO, addressing the addressee.
- **Control flow:** `If so`/`If not`; gotos; Enter / Exit / Exeunt / `[A pause]`.
- **Vocabulary is reference-exact.** The adjective lists partition cleanly — 36 positive, 32
  negative, 20 neutral (the remainder), 88 total, pairwise disjoint. Nouns: 13 positive, 25
  negative, 41 neutral. Neutral nouns are valued **+1**, exactly like the reference's
  `positive_or_neutral_noun` (`vocabulary.py:44-51`). 152 character names (≈ reference).

## Documentation defects found

- ~~`README.md:69` lists the comparative set as including "with `not` inversion" — **false**;
  negation was dropped (ADR-0004), and the interpreter has none.~~ → Fixed (issue 24): the
  false clause was removed from the README.
- `grammar.lark:21-23` still frames stacks and square-root/cube as "phase 2"; they are implemented.
  The phase framing now reads stale (minor; no issue).

## Bottom line

Against the project's stated yardstick (the `shakespearelang` reference), there is no longer any
missing language construct: `the factorial of` was the last one, closed by issue 23. Against the
original SPL spec, the only remaining gap is negated comparisons — a form the reference itself never
implemented. Everything else is either complete and reference-exact or a deliberate recorded
divergence; no over-acceptance remains undocumented (the last two — `as <word> as` and nested
conditionals — were recorded in ADR-0007 by issue 26).
