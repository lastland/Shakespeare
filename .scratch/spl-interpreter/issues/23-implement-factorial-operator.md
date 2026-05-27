# Implement the `the factorial of` unary operator

Status: resolved

## What to build

End-to-end support for the `the factorial of <value>` unary operator — the single construct the
`shakespearelang` reference defines that this interpreter does not (see `docs/gap-analysis.md` gap
G1, ADR-0006). A program using it currently fails to parse. After this slice, a play can compute and
output a factorial.

Reference semantics: `0! = 1`, `n! = n·(n-1)!` for `n ≥ 0`, computed over exact integers. A negative
operand is spec-undefined and should raise (strict posture of ADR-0001, like the negative-`√` guard).

## Acceptance criteria

- [ ] `the factorial of <value>` parses, producing a `UnaryOp("factorial", …)` node alongside the
      existing `square`/`cube`/`square root`/`twice` forms (named, word-boundaried terminal per ADR-0002)
- [ ] The interpreter evaluates `0!` → 1 and a small `n!` correctly over exact integers
- [ ] A negative operand raises `RuntimeSplError`
- [ ] Unit tests cover: the parse, `0!`, a small `n!`, and the negative-operand raise
- [ ] `README.md` "Known gaps" line and the ❌ factorial row in `docs/gap-analysis.md` are removed;
      ADR-0006 is updated so factorial is no longer "the sole unimplemented construct"
- [ ] Existing test suite, `ruff check`, and `pyright` stay green

## Blocked by

None - can start immediately
