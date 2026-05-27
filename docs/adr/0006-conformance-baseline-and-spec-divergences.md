# Conformance baseline and deliberate divergences from full SPL

This record fixes *what "the language" means* for this interpreter, and indexes the deliberate ways
we diverge from a full implementation. The individual divergences are decided in their own ADRs;
this one names the yardstick and the one known unimplemented construct so a reader does not have to
reverse-engineer the conformance posture from five separate records. See `docs/gap-analysis.md` for
the full, evidence-backed comparison.

## The baseline is the `shakespearelang` reference EBNF

There are two "full SPL"s, and they differ:

- The **original language** (Hasselström & Åslund report / esolangs), and
- the **de-facto reference**, `zmbc/shakespearelang`, whose `shakespeare.ebnf` is a strict *subset*
  of the original (it never implemented negated comparisons, and restricts gotos to scenes).

We take the **reference EBNF as the conformance baseline**: it is what the differential harness
checks against, the eight golden programs byte-match it, and the vocabulary data files were
extracted from it (`vocabulary.py`). Where we intentionally exceed or tighten the reference, we say
so in an ADR. "Original-spec but not in the reference" is therefore *not* a conformance bug for us;
it is a documented gap (see negated comparisons below).

## The one unimplemented reference construct: `the factorial of`

The reference `unary_operation` admits `twice`, `square`, `cube`, `square root`, **and
`factorial`**. We implement the first four; `the factorial of` is absent from the grammar, analyzer,
and interpreter (a program using it raises a `ParseError`). This is the sole construct the reference
defines that we do not. It is tracked by issue 23 and is the only ❌ in the gap analysis.

## Negated comparisons: dropped to track the reference

The original language can invert a test ("not as good as", "not better than"). The reference grammar
has no negated questions, so neither do we (ADR-0004 / issue 13 removed our buggy local version).
Re-adding them would mean diverging from the reference *toward* the original spec — a deliberate
choice we are not making. The `NOT` terminal survives only for the separate `If not, …` conditional.

## The deliberate divergences (decided elsewhere)

We do not re-litigate these here; this is the index:

- **ADR-0001** — strict `RuntimeSplError` for spec-undefined runtime cases (div/mod by zero,
  off-stage, >2 on stage, negative `√`, bad numeric input, dangling conditional), plus exact-integer
  division/`√`. One carve-out: character-input EOF → −1.
- **ADR-0002** — generic-`WORD` parsing; **gotos accept an act *or* a scene** (superset; follows the
  official report) where the reference allows scenes only.
- **ADR-0003** — numeric-input parsing (spl2c-faithful) with strict errors.
- **ADR-0004** — drop negated questions; reject `more <neutral adjective> than` (the latter *matches*
  the reference).
- **ADR-0005** — title/section labels may end with `?` (superset).

## Consequences

- The conformance question has a single, citable answer: we target `shakespearelang`'s
  `shakespeare.ebnf`; the gap to it is exactly `the factorial of` (issue 23). The gap to the
  *original* spec additionally includes negated comparisons.
- A few **undocumented** supersets remain (noun/adjective polarity not enforced; `as <word> as`
  admits non-adjectives; nested conditionals parse). The triage decision is to keep them as
  intentional supersets and record them: polarity is tracked by issue 25, and the `as <word> as` /
  nested-conditional pair by issue 26. Once those land, this list moves from "undocumented" to
  "decided".
- This ADR is an index, so it stays correct only if new divergence ADRs add themselves to the list
  above.
