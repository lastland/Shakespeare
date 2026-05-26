# Verify "If so / If not" with no preceding question against the reference

Status: needs-info

`src/spl/backend/interpreter.py` raises `RuntimeSplError("conditional without a preceding
question")` when an `If so` / `If not` runs before any question has set the boolean register.

This is a defensible strict choice, but we have not confirmed what `shakespearelang` does (it may
treat the register as a default, e.g. false, or also error).

## Action

Probe the reference; align (raise vs default-false) or record the divergence in the allow-list
(issue 06). Low priority — well-formed programs always ask a question first.
