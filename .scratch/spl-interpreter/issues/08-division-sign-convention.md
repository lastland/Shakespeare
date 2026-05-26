# Verify integer division / remainder sign convention against the reference

Status: resolved

`src/spl/backend/interpreter.py` implements `quotient` with `_trunc_div` (truncation toward zero,
C / spl2c semantics) and `remainder` as `left - trunc_div(left, right) * right`. Python's own `//`
and `%` floor toward negative infinity, which differs for mixed-sign operands.

We have not confirmed which convention `shakespearelang` uses. For non-negative operands (Hello
World, the current golden programs) it doesn't matter.

## Action

Read `shakespearelang`'s `_operation.py`, or run a differential probe with negative operands
(e.g. `the quotient between nothing-minus-seven and a flower-pair`), and align our convention or
record the divergence in the differential-testing allow-list (issue 06).
