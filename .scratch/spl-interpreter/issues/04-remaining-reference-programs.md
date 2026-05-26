# Add the remaining shakespearelang sample programs as golden tests

Status: needs-triage

We run `hi.spl` and `hello_world.spl` (byte-matching the reference). The other samples
(`shakespearelang/tests/sample_plays/`) should become golden tests under `tests/programs/`, each
confirmed against the `shakespearelang` oracle. Feature scan:

| program        | needs                          | blocked by |
| -------------- | ------------------------------ | ---------- |
| echo.spl       | numeric input only             | issue 09 (input-error semantics); otherwise ready |
| primes.spl     | goto, cube/sqrt, input         | issue 01 (multi-line comment); features otherwise supported |
| catch.spl      | stacks                         | issue 02 |
| reverse.spl    | stacks, goto, breakpoint, input| issue 02 |
| sierpinski.spl | stacks, goto, input            | issue 02 |

## Action

Triage into per-program tasks as their blockers land. `primes.spl` should work right after issue 01;
`echo.spl` after issue 09 is decided. The stack-based three follow issue 02.
