# Live differential testing against shakespearelang in CI

Status: resolved

Deferred feature from decision D8. Today the golden outputs are committed files (confirmed against
the reference once, by hand). A CI job could run each in-spec program through both our interpreter
and `shakespearelang` and compare, catching regressions automatically.

## Work

- Add a CI-only test (or marker) that runs both interpreters on the programs in `tests/programs/`.
- Maintain an explicit allow-list of intentional divergences (see ADR-0001 and issues 08/09/10):
  strict errors on spec-undefined cases, EOF/non-numeric input handling, division sign convention.
- Keep `shakespearelang` as a CI-only dependency; the normal suite must stay reference-free.
