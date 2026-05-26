# Title/section labels accept `?` as a terminator; the reference does not

Status: ready-for-human

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
