# Record the `as <word> as` and nested-conditional over-acceptances as intentional supersets

Status: ready-for-agent

## What to build

Two further grammar over-acceptances relative to the `shakespearelang` reference (see
`docs/gap-analysis.md`, "Undocumented supersets"):

- **`as <word> as` admits any vocabulary word** as the equality adjective; the reference restricts
  it to a known adjective. This is harmless — in a simile the adjective is semantically inert (the
  form just means equality) — so `Are you as cat as a King?` analyzes cleanly and tests equality.
- **Nested conditionals parse:** `If so, if not, …` is accepted because a conditional may guard
  another conditional; the reference allows exactly one condition prefix per operation.

Following the same posture as the polarity superset (#25), **keep both and record them** rather than
tightening. This slice documents and pins them.

## Acceptance criteria

- [ ] The superset ADR introduced by #25 is extended to cover the `as <word> as` admission and the
      nested-conditional admission, each with a one-line rationale
- [ ] Tests pin `Are you as cat as a King?` as accepted and `If so, if not, …` as parsing
- [ ] `docs/gap-analysis.md` moves these two items from "Undocumented supersets" into the
      recorded-divergence list
- [ ] Existing test suite stays green

## Blocked by

- #25 (this extends the same superset ADR; let that one create it first)
