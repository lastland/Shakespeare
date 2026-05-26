# Title/section labels accept `?` as a terminator; the reference does not

Status: resolved

## Parent

Follow-up to [01](01-multiline-comments-break-parsing.md) (COMMENT terminal). Found in the Phase 2 code review.

## What to build

`_title_end` accepts `?` (as well as `.`/`!`) to terminate the play title, persona descriptions, and
act/scene labels, and the shared `COMMENT` terminal stops at `?`. The reference terminates these
labels only on `!`/`.` — its `text_before_punctuation` reads straight past a `?` — so a
`?`-terminated title parses to a **different program** than the oracle. This is a deliberate, tested
superset.

This is a **conformance decision**:

- **(a) Keep** the `?`-terminator superset (it is friendlier) and record it as an allowed divergence; or
- **(b) Align** with the reference: titles/labels terminate only on `!`/`.`.

Coordinate with [17](17-recall-comment-executes-statements.md): both concern the `COMMENT`
terminal's treatment of `?`, and the chosen approach should be consistent.

Repro (verified): title `What is love?` → for us, title is `"What is love"` with personae intact;
the reference reads past the `?` and swallows the following first persona into the title text.

## Acceptance criteria

- [ ] Decision recorded (keep superset vs. align); ADR / divergence note updated.
- [ ] If keeping: an `ALLOWED_DIVERGENCES` entry (or explicit doc) covers `?`-terminated labels; the existing parser test stays.
- [ ] If aligning: `_title_end` accepts only `.`/`!`, and the related tests are updated to the reference behaviour.
- [ ] Consistent with the resolution of [17](17-recall-comment-executes-statements.md).
- [ ] Full + differential suite green.

## Blocked by

None - can start immediately. (Related: shares the COMMENT `?` root cause with [17](17-recall-comment-executes-statements.md).)

## Decision

Keep `?` as a label terminator (option a) — a friendly superset over the reference.

## Resolution

Kept as-is: `_title_end` already accepts `.`/`!`/`?` and the shared `COMMENT` terminal stops at `?`,
so a title / persona / Act / Scene label may end with `?`. `.` and `!` match the reference; `?` is
our intentional superset (the reference's `text_before_punctuation` treats `?` as label text and
reads past it — demonstrated: a `?`-terminated scene label makes the oracle swallow the scene body
into the label name, while we terminate the label at `?`). The `?`-as-question-terminator
(`Am I better than you?`) is unrelated and fully reference-conformant; this decision concerns only
`?` ending a *label*. Recorded in ADR-0005 and the README's intentional-divergences list, and
registered as the `title-question-terminator` category in the differential harness. Decoupled from
[17](17-recall-comment-executes-statements.md) by that issue's separate `RECALL_COMMENT` terminal,
so Recall comments stay reference-conformant (span `?`) while labels keep the `?` terminator. The
existing parser test `test_title_and_section_terminators_allow_bang_and_question` locks the
behaviour in. No code change; full + differential suites green (8/8).
