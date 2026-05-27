# Record the noun/adjective polarity over-acceptance as an intentional superset

Status: ready-for-agent

## What to build

Constant folding does not enforce the reference's noun/adjective **polarity agreement**. The
reference parses a constant as a *negative* noun phrase (adjectives ∈ negative ∪ neutral, noun
negative) or a *positive* noun phrase (adjectives ∈ positive ∪ neutral, noun positive/neutral); a
mismatch is a parse error. Our analyzer only checks that each pre-noun word is *an adjective*, never
its polarity — so `a happy coward` (positive adjective + negative noun) folds to `-2` and
`an evil King` (negative adjective + positive noun) folds to `+2`, both accepted where the reference
rejects them. The computed magnitude (noun sign × 2^adjectives) is correct regardless; this is a
harmless *superset*, not a wrong value.

Decision (issue triage): **keep the superset and record it** rather than tightening to the reference.
This slice makes that decision explicit and pins it so it cannot silently regress. (Same posture as
the act-goto superset in ADR-0002.)

## Acceptance criteria

- [ ] An ADR records that constant folding intentionally does not enforce adjective/noun polarity
      agreement (a superset of the reference), with the rationale: the magnitude is always correct,
      and the reference would parse-error on the mismatch
- [ ] Tests pin `a happy coward` → −2 and `an evil King` → +2 as accepted (folded) values
- [ ] `docs/gap-analysis.md` moves the polarity item out of "Undocumented supersets" into the
      recorded-divergence list, cross-referencing the new ADR
- [ ] Existing test suite stays green

## Blocked by

None - can start immediately
