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

## The last unimplemented reference construct: `the factorial of` (now implemented)

The reference `unary_operation` admits `twice`, `square`, `cube`, `square root`, **and
`factorial`**. `the factorial of` was for a time the sole construct the reference defined that we
did not — the only ❌ in the gap analysis. It was **implemented by issue 23**: a word-boundaried
`FACTORIAL` terminal and a `THE FACTORIAL OF value -> factorial` alternative (ADR-0002), folding to
`UnaryOp(op='factorial', …)`, computed over exact integers in `_unary` (`0! = 1`, `n! = n·(n-1)!`),
with a negative operand raising `RuntimeSplError` per the strict posture of ADR-0001. With this in
place, the interpreter implements every construct the reference EBNF defines; the reference gap is
closed.

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
- **ADR-0007** — recorded grammar supersets over the reference: **noun/adjective polarity is not
  enforced** (the magnitude is always correct, only parse-time agreement is unchecked), **`as <word>
  as` admits any vocabulary word** as the inert simile adjective, and **nested conditionals parse**.

## Consequences

- The conformance question has a single, citable answer: we target `shakespearelang`'s
  `shakespeare.ebnf`; with `the factorial of` implemented (issue 23) there is no remaining gap to it.
  The gap to the *original* spec is now just negated comparisons.
- All three grammar supersets over the reference are now **decided and recorded** in ADR-0007:
  noun/adjective polarity is not enforced (issue 25 — we keep it because the folded magnitude is
  always correct and only the reference's parse-time polarity *agreement* goes unenforced), `as
  <word> as` admits any vocabulary word as the inert simile adjective, and nested conditionals parse
  (both issue 26, which extended ADR-0007). The triage decision in each case was to keep the superset
  and record it; **no undocumented supersets remain**.
- This ADR is an index, so it stays correct only if new divergence ADRs add themselves to the list
  above.
