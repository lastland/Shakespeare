# Support the full set of comparatives

Status: ready-for-agent

Phase 1 supports only `better than` (>), `worse than` (<), and `as ADJ as` (==). The reference
grammar (`shakespeare.ebnf`) has more:

- positive comparatives (→ `>`): `better`, `bigger`, `fresher`, `friendlier`, `nicer`, `jollier`,
  and `more <positive adjective>`.
- negative comparatives (→ `<`): `punier`, `worse`, ... and `less <negative adjective>`.
- equality (→ `==`): `as <adjective> as` (any adjective).

## Work

- Grammar: extend `comp_kind` with the comparative-adjective words and the `more/less ADJ than`
  forms. Keep the named-terminal + word-boundary convention.
- Map each to gt / lt / eq in the analyzer or transformer.
- Add unit tests; verify against the reference where a program uses them.
