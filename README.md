# spl — a typed-Python Shakespeare Programming Language interpreter

[![CI](https://github.com/lastland/Shakespeare/actions/workflows/ci.yml/badge.svg)](https://github.com/lastland/Shakespeare/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/lastland/Shakespeare/branch/main/graph/badge.svg)](https://codecov.io/gh/lastland/Shakespeare)

An interpreter for the [Shakespeare Programming Language](https://esolangs.org/wiki/Shakespeare)
(Hasselström & Åslund, 2001) — an esoteric language whose programs read like Shakespeare plays.
Characters are variables, dialogue is computation, and Acts/Scenes are goto labels.

```
$ uv run spl tests/programs/hello_world.spl
Hello World!
```

It is written in typed Python (`pyright --strict`), parses with [lark](https://github.com/lark-parser/lark),
and cleanly separates a **frontend** (source → immutable typed AST) from a **backend** (a static
analyzer + a tree-walking interpreter). It was built test-first.

> **An experiment in agent-driven development.** This project is a testbed for using AI coding
> agents (Claude Code) to implement a programming-language interpreter — its grammar, static
> analyzer, tree-walking interpreter, test suite, and the conformance pass against the reference.
> Work is queued as markdown issues under
> [`.scratch/spl-interpreter/issues/`](.scratch/spl-interpreter/issues/), which double as the
> agents' task list.

## Install & run

Requires Python ≥ 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                  # install (editable) + dev tools
uv run spl path/to/program.spl           # run a program
uv run python -m spl path/to/program.spl # equivalent
```

## Architecture

```
src/spl/
  errors.py            SplError → ParseError, AnalysisError, RuntimeSplError
  frontend/
    grammar.lark       Earley grammar: named keyword terminals + a generic WORD; vocabulary
                       lives in data files, not the grammar (see ADR-0002)
    ast.py             frozen @dataclass AST nodes (the frontend/backend boundary)
    transformer.py     lark tree → AST (purely syntactic)
    parser.py          parse(source) → Program
  backend/
    vocabulary.py      loader for the word-lists
    data/*.txt         positive/negative/neutral nouns, adjectives, character names
    analyzer.py        classifies words, folds Constants to Numbers, checks names/gotos →
                       AnalyzedProgram (a flat line list + label maps)
    state.py           Character (value + LIFO stack), Stage (who is on stage)
    io.py              IO protocol + StdIO + an in-memory BufferIO test double
    interpreter.py     tree-walk with a program counter over the AnalyzedProgram
  cli.py               read file → parse → analyze → interpret
```

- **Domain glossary:** [`CONTEXT.md`](CONTEXT.md) — the vocabulary the code uses (Character, Stage,
  Speaker/Addressee, Constant, Question, Stack, …).
- **Decisions:** [`docs/adr/`](docs/adr/) — why the interpreter behaves as it does.

## Supported language

Dramatis Personae declarations; `Enter`/`Exit`/`Exeunt` and the `[A pause]` breakpoint;
assignment (with the optional `be`/`as ADJ as` flavour); Constants (`article? adjective* noun`,
incl. multi-word and capitalized nouns); Character references; the arithmetic operators
(`sum`/`difference`/`product`/`quotient`/`remainder`, `twice`, `square`, `cube`, `square root`,
`factorial`);
all four I/O forms; **stacks** (`Remember`/`Recall`); the full comparative set
(`better`/`bigger`/`worse`/`punier`/… , `more ADJ than`, `as ADJ as`) plus
`If so`/`If not`; and `goto` to an **act or scene**.

### Conformance & intentional divergences

This interpreter is cross-checked against the de-facto reference,
[`shakespearelang`](https://github.com/zmbc/shakespearelang) — the eight programs under
`tests/programs/` byte-match it (`hi`, `hello_world`, `greeting`, `echo`, `catch`, `reverse`,
`sierpinski`, `primes`). Where the spec is silent we made deliberate choices, recorded as ADRs:

- **Strict errors for spec-undefined runtime cases** ([ADR-0001](docs/adr/0001-strict-semantics-for-undefined-cases.md)):
  division/modulo by zero, off-stage reference, >2 on stage, invalid character output, a √ of a
  negative, **numeric input at EOF / non-numeric input**, and an `If so`/`If not` with no preceding
  Question all raise. The one carve-out is **character-input EOF → -1** (the EOF protocol the
  looping programs rely on).
- **Numeric input** ([ADR-0003](docs/adr/0003-input-parsing-and-error-semantics.md)): spl2c-faithful
  parsing (skips leading whitespace, accepts a sign) but strict errors — a deliberate blend.
- **Goto accepts act *or* scene** ([ADR-0002](docs/adr/0002-parsing-strategy-generic-word.md)),
  following the official report; `shakespearelang` allows scenes only.
- **Exact integer division/√**: we truncate toward zero with exact integers; the reference uses
  float division, which loses precision above 2⁵³. Same sign convention, more precise.
- **Label terminators accept `?`** ([ADR-0005](docs/adr/0005-title-section-label-terminators.md)): a
  title or Act/Scene/persona label may end with `?` as well as `!`/`.`. The reference admits only
  `!`/`.` for labels (it reads past a `?` as label text), so this is a friendly superset. (Unrelated
  to `?` ending a *question*, which is reference-standard.)
- **Recorded grammar supersets** ([ADR-0006](docs/adr/0006-conformance-baseline-and-spec-divergences.md)
  indexes the conformance baseline; [ADR-0007](docs/adr/0007-recorded-grammar-supersets-over-the-reference.md)
  details them): we intentionally accept three constructs the reference parse-errors on — a constant
  whose adjective polarity disagrees with its noun (`a happy coward`), `as <word> as` with a
  non-adjective, and nested `If so`/`If not` conditionals — because each carries the same value or
  semantics the reference would give, so tightening buys only parse-time strictness.

This interpreter now implements every construct the reference defines, including `the factorial of`
(issue 23); no sample program uses it.

## Development

```bash
uv run ruff check          # lint
uv run ruff format         # format
uv run pyright             # type-check (strict)
uv run pytest              # the test suite (reference-free)
```

The default suite has no dependency on another interpreter. An **opt-in differential harness**
cross-checks our output against `shakespearelang` (a dev-only dependency), with an allow-list of the
intentional divergences above:

```bash
uv run --with shakespearelang pytest -m differential
```

CI reports line/branch coverage to [Codecov](https://codecov.io/gh/lastland/Shakespeare)
(`uv run pytest --cov`). Coverage is measured on the **reference-free suite only**: the differential
harness re-runs the same programs through the same code, so it adds no marginal coverage. Reporting
is informational — coverage does not gate merges.

Open work and conformance notes are tracked as markdown issues under
[`.scratch/spl-interpreter/issues/`](.scratch/spl-interpreter/issues/).
