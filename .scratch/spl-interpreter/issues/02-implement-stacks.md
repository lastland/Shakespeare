# Implement stacks (Remember / Recall) — phase 2

Status: resolved

Each Character has a LIFO stack in addition to its value (already noted in CONTEXT.md and the
`Character` dataclass has an unused `stack` field). Phase 1 deferred this (decision D1).

- `Remember <value>` (addressed to a character) pushes a value onto that character's stack.
- `Recall <comment text>` pops the top of the addressee's stack into the addressee's value.

## Work

- Grammar: add `push` / `pop` sentence forms (`REMEMBER value` / `RECALL text_before_punctuation`).
  `Recall` is followed by ignorable comment text up to the terminator.
- AST: `Remember(value)` / `Recall` statement nodes.
- Interpreter: push uses `Character.stack`; pop sets value from `stack.pop()`. Decide empty-stack
  behavior per ADR-0001 (recommend: raise `RuntimeSplError`; confirm against shakespearelang).
- Unblocks the stack-based reference programs (issue 04): catch.spl, reverse.spl, sierpinski.spl.
