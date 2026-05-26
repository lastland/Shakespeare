# Strict typed errors for spec-undefined runtime cases

The SPL spec leaves many runtime cases undefined and existing interpreters disagree on them.
We resolve them strictly: division/modulo by zero, addressing a Character not on stage, more than
two Characters interacting on stage, and character-output of a value outside valid Unicode all
raise a typed `RuntimeSplError`. EOF on input yields −1 (matching `shakespearelang` and `spl2c`).

We chose strict errors over the alternatives (be bug-compatible with `shakespearelang`, or be
lenient and coerce — e.g. div-by-zero → 0) because this is a teaching interpreter where surfacing
the fault loudly is more valuable than silently continuing. This is surprising to a reader who
knows other interpreters return 0, and it is hard to reverse because the test suite encodes these
outcomes as expected behavior.

## Consequences

- Programs that rely on lenient coercion (or on `shakespearelang`'s exact quirks) will raise where
  another interpreter would limp along. The planned future "live differential testing in CI" must
  carry an allow-list of these intentional divergences.
