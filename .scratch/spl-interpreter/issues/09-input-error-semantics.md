# Input error semantics: non-numeric / EOF input returns -1 vs reference error

Status: resolved

Per ADR-0001 our `StdIO.read_number` returns `-1` on EOF, and also on non-numeric input. The
`shakespearelang` reference instead **raises** ("No numeric input was given.").

## Repro

`printf 'Hi!' | python -m spl echo.spl` → our interpreter reads `-1` and continues;
`printf 'Hi!' | shakespeare run echo.spl` → `SPL runtime error: No numeric input was given.`

## Decision needed

- EOF → -1 is a deliberate ADR-0001 choice (matches spl2c) and should stay.
- Non-numeric-when-numeric-expected is a separate case: keep lenient (-1), or raise
  `RuntimeSplError` to match the reference. Recommend raising on non-numeric (closer to the
  reference and to our strict posture), keeping EOF → -1. Then echo.spl can be added (issue 04).
Record the resolution in the differential allow-list (issue 06).

## Comments

- 2026-05-25 (io-agent): Implemented per ADR-0003. `_CharReader.read_number` now raises
  `RuntimeSplError` at EOF / on non-numeric input (covers both StdIO and BufferIO, which share
  `_CharReader`), keeps the spl2c leading-whitespace skip + optional sign, and consumes one
  trailing newline after the digits. Character input EOF -> -1 unchanged (ADR-0001 carve-out).
  IO Protocol docstring updated. Tests in tests/backend/test_io.py updated/added (TDD).
  `pytest tests/backend/test_io.py`, `ruff check`/`format`, and `pyright` (strict) all clean.
  echo.spl byte-matches the shakespearelang oracle on `printf 'A42\nZ'` (-> `A42Z`) and
  `A7B99\nC`. Status set to ready-for-agent; remaining steps (golden test, allow-list note) are
  tasks #5/#6.
