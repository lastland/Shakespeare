# Numeric input: spl2c-faithful parsing, strict errors

The SPL spec is silent on how numeric input (`Listen to your heart`) is parsed and what happens at
end of file or on non-numeric input — the official report only says it "inputs a number." The two
reference implementations disagree, so we had to choose a contract deliberately.

- **spl2c** (the original compiler) generates `scanf("%d", &var)`. C `%d` skips leading
  whitespace, accepts an optional sign (so negatives parse), reads digits, and on EOF / match
  failure leaves the variable unchanged (silent). Its character input is `scanf(" %c")`, which also
  skips leading whitespace.
- **shakespearelang** reads a line, consumes a leading digit run only (no sign, no whitespace
  skip), swallows one trailing newline, and *raises* on EOF ("End of file encountered.") and on
  non-numeric input ("No numeric input was given.").

## Decision

We take a deliberate blend — the most permissive *parsing* with the strictest *error* behaviour:

- **Parsing follows spl2c / `scanf("%d")`**: skip leading whitespace, accept an optional sign
  (negatives parse), read the digit run. This is faithful to the original implementation;
  `shakespearelang` is the one that narrowed it.
- **Errors follow the strict posture of ADR-0001**: numeric input *raises* a `RuntimeSplError` at
  EOF and on non-numeric input, rather than returning a sentinel. (This is also what
  `shakespearelang` does.)
- **One trailing newline is consumed** after the digits (matching `shakespearelang`). This is
  observably equivalent to spl2c's behaviour — spl2c leaves the newline in the stream but its
  character input skips leading whitespace, so neither reference ever returns a number's trailing
  newline as the next character. Without this, our character-by-character reader would leak the
  newline into the following character read and diverge from both references (this is what made
  `echo.spl` fail to byte-match).
- **Character input keeps the EOF → −1 carve-out** from ADR-0001; it is the EOF protocol the
  looping programs depend on.

## Why this blend

Choosing "spl2c parsing + shakespearelang errors" maximises the valid input we accept (signs,
whitespace — faithful to the language's own first implementation) while refusing to invent a value
for an undefined state (EOF, garbage), consistent with ADR-0001. The earlier draft of ADR-0001
wrongly claimed EOF yielded −1 "matching shakespearelang and spl2c"; this ADR supersedes that claim
for numeric input.

## Consequences

- Hard to reverse: the io unit tests and the `echo.spl` golden test encode this contract.
- Differential-testing allow-list (issue 06): our numeric reader accepts signed / whitespace-led
  input that `shakespearelang` would reject — a spec-faithful superset, not cross-checkable against
  the oracle for those inputs. The raise-on-EOF / raise-on-non-numeric behaviour *does* match the
  oracle.
