# Input error semantics: non-numeric / EOF input returns -1 vs reference error

Status: needs-triage

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
