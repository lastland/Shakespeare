# Strict typed errors for spec-undefined runtime cases

The SPL spec (the official Hasselström & Åslund report, esolangs, Wikipedia) leaves many runtime
cases undefined. We resolve every such case strictly: it raises a typed `RuntimeSplError` rather
than coercing a value or silently continuing. The cases:

- division / modulo by zero,
- addressing a Character not on stage,
- more than two Characters interacting on stage (ambiguous second person),
- character-output of a value outside valid Unicode,
- numeric input at EOF or on non-numeric input (see ADR-0003 for the full input contract),
- a square root of a negative number,
- an "If so" / "If not" conditional with no preceding Question (the boolean register has no
  defined value yet).

**Spec-silence alone triggers strictness — we do not require that existing interpreters also
disagree.** The original framing weighed disagreement (div-by-zero: some interpreters return 0,
some error) as the justification. We have since taken the stronger line: if the *spec* does not
define a behaviour, we raise, even where the implementations happen to agree. The dangling
conditional is the motivating example — `shakespearelang` defaults its register to false and runs
"If not", and spl2c cannot even express a dangling conditional, so the implementations agree; but
the spec is silent, so we raise. This keeps the rule simple ("the spec defines it or we error")
and fits a teaching interpreter, where surfacing an undefined state loudly beats guessing.

## The one carve-out: character-input EOF → −1

Character input (`Open your mind`) returns −1 at end of file rather than raising. This is not a
fault — it is the established EOF *protocol*. The looping sample programs (`reverse`, `sierpinski`)
read characters until they observe −1, so raising would make them non-terminating instead of
correct. `shakespearelang` and spl2c both surface EOF this way for character input. Numeric input
(`Listen to your heart`) has no such protocol and so still raises at EOF.

We chose strict errors over the alternatives (be bug-compatible with `shakespearelang`, or be
lenient and coerce — e.g. div-by-zero → 0). This is surprising to a reader who knows other
interpreters return 0 or limp along, and it is hard to reverse because the test suite encodes these
outcomes as expected behaviour.

## Consequences

- Programs that rely on lenient coercion (or on another interpreter's exact quirks) will raise
  where that interpreter would continue. The differential-testing allow-list (issue 06) must carry
  these intentional divergences — notably the dangling conditional (we raise; the oracle runs the
  "If not" branch).
- The strictness principle and the EOF carve-out are deliberately asymmetric (numeric EOF raises,
  character EOF returns −1); ADR-0003 records why.

## Correction (superseding the original draft)

The first version of this ADR stated "EOF on input yields −1 (matching `shakespearelang` and
`spl2c`)." That was wrong on two counts: `shakespearelang` *raises* on numeric EOF and on
non-numeric numeric input, and the −1 sentinel is correct only for *character* input. The
numeric-input contract is now strict (raise), with character-input EOF as the sole −1 carve-out, as
above. See ADR-0003.
