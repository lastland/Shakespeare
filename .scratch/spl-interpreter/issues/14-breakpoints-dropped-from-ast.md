# `[A pause]` breakpoints are dropped from the scene AST

Status: resolved

## Parent

Phase 1 breakpoint parsing (no dedicated issue). Found in the Phase 2 code review.

## What to build

A `[A pause]` breakpoint is parsed into a `Breakpoint` node but then discarded when a scene is
assembled: the scene's line-filter allow-list (`_LINE_TYPES` in the transformer) is out of sync with
the `Line` type union, which *does* include `Breakpoint`. As a result no scene ever contains a
`Breakpoint`, and the interpreter's `Breakpoint` handling is dead code.

Output is unaffected (the reference also ignores breakpoints), so the test and differential suites
miss it — but it contradicts the stated design of parsing breakpoints for fidelity.

Repro (verified): parsing a play whose scene contains `[A pause]` between two lines yields
`scene.lines` with no `Breakpoint` (only `Enter, Dialogue, Dialogue, Exeunt`). Parsing `[A pause]`
directly as a line correctly yields `Breakpoint()`.

## Acceptance criteria

- [ ] `Breakpoint` is included in the scene line-assembly allow-list so breakpoints survive into `scene.lines`.
- [ ] A test parses a full play (or scene) containing `[A pause]` and asserts a `Breakpoint` node is present at the right position in the scene's lines.
- [ ] The interpreter still ignores breakpoints at runtime (output unchanged); full + differential suite green.

## Blocked by

None - can start immediately.

## Resolution

Added `Breakpoint` to the `_LINE_TYPES` allow-list in `transformer.py` so the `scene()` filter no
longer drops it. Added `test_breakpoint_survives_in_scene_lines`, which parses a full play with
`[A pause]` between two dialogue lines and asserts the `Breakpoint` node lands at the right position
in `scene.lines`. Output is unchanged (the interpreter still ignores breakpoints): full suite and
the 8-program differential suite stay byte-exact.
