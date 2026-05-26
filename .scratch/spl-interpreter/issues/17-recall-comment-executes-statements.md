# Recall comment text after a `?` is executed as statements

Status: resolved

## Parent

Follow-up to [02](02-implement-stacks.md) (stacks) and [01](01-multiline-comments-break-parsing.md)
(COMMENT terminal). Found in the Phase 2 code review.

## What to build

The trailing text of a `Recall …` is meant to be an ignorable comment (matching the reference's
`recall_string`, which runs to the next `!`/`.`). But the shared `COMMENT` terminal stops at `?`
(and `[`/`]`), so a `?` inside a Recall comment ends the comment early and the remaining words are
parsed as **additional executable statements**.

Repro (verified): `Romeo: Recall is this real? Speak your mind.` parses to `[Recall, OutputChar]` —
`Speak your mind` runs and emits a character. The reference treats `is this real? Speak your mind`
as one ignorable `recall_string` (it stops only at the final `.`), emitting nothing. A `.`/`!`
inside the comment correctly splits in *both* implementations, so only `?` diverges; `[`/`]` must
stay excluded because we use brackets for stage directions.

Implementation note: this likely needs a Recall-specific comment that spans `?` but stops at `!`/`.`
(and structurally at `[`/`]`), rather than reusing the title `COMMENT` terminal. Coordinate with
[19](19-title-question-mark-terminator.md), which concerns the same `?`-in-COMMENT behaviour for titles.

## Acceptance criteria

- [ ] A `?` inside a Recall comment does not split off executable statements; trailing comment text up to the sentence terminator is ignored.
- [ ] `Recall is this real? Speak your mind.` parses to a single `Recall` (no `OutputChar`) and matches the oracle.
- [ ] Recall still pops correctly; `catch.spl` / `reverse.spl` / `sierpinski.spl` stay byte-exact.
- [ ] Test covering a Recall comment containing `?`.
- [ ] Full + differential suite green.

## Blocked by

None - can start immediately. (Related: shares the COMMENT `?` root cause with [19](19-title-question-mark-terminator.md).)

## Resolution

Gave Recall its own comment terminal `RECALL_COMMENT.6: /[^!.\[\]]+/` and switched `recall` from
`RECALL COMMENT?` to `RECALL RECALL_COMMENT?`. Unlike the shared `COMMENT` (which stops at `?`), the
new terminal spans `?` and stops only before `!`/`.` (the sentence terminator ends the Recall,
matching the reference's `pop = "Recall" recall_string ("!" | ".")`) and before `[`/`]` (so stage
directions are never absorbed). The shared `COMMENT` terminal is untouched, leaving issue 19's
title behaviour to the human owner. Verified against the oracle:
`Romeo: Recall is this real? Speak your mind.` now parses to a single `Recall` (no `OutputChar`);
`Recall foo.`/`Recall foo!`/`Recall.` still parse. Added
`test_recall_comment_spans_question_mark`; `catch.spl`/`reverse.spl`/`sierpinski.spl` and the full
+ differential suites stay byte-exact.
