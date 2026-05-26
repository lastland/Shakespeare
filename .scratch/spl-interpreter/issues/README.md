# SPL interpreter — issue index

Local-markdown issue tracker (see `docs/agents/issue-tracker.md`). One file per issue; the
`Status:` line uses the triage vocabulary in `docs/agents/triage-labels.md` (extended with
`resolved` for closed items).

Issues [01](01-multiline-comments-break-parsing.md)–[12](12-articled-character-names.md) are
**resolved**. The interpreter runs the canonical `shakespearelang` sample programs and byte-matches
the oracle on all eight committed programs (`hi`, `hello_world`, `greeting`, `echo`, `catch`,
`reverse`, `sierpinski`, `primes`).

Issues [13](13-negated-question-drops-negation.md)–[22](22-stale-question-branch-docstring.md) are
follow-ups filed from the Phase 2 code review — gaps in the features that issues 01/02/03/09/12
delivered. The six agent-ready (AFK) items are **resolved** (fixed by coding agents, all suites
green), and the maintainer's decisions on 13 (drop negated questions) and 15 (reject neutral-after-
`more`) are now **resolved** too (see ADR-0004). Two conformance decisions remain `ready-for-human`
(18, 19).

## Phase 2 code-review follow-ups

Comparisons (gaps in [03](03-richer-comparatives.md)):
- [13](13-negated-question-drops-negation.md) — negated question drops the negation on a non-pronoun left operand — **resolved** (decision (b): dropped negated questions entirely; `not` reserved out of `WORD` — ADR-0004)
- [15](15-more-neutral-adjective-comparative.md) — `more <neutral adjective> than` resolves to `gt` instead of being rejected — **resolved** (decision: reject; added `positive_adjectives` so neutral-after-`more` raises — ADR-0004)

Parsing fidelity:
- [14](14-breakpoints-dropped-from-ast.md) — `[A pause]` breakpoints dropped from the scene AST — **resolved** (added `Breakpoint` to the scene line allow-list)

COMMENT terminator vs. the reference's `text_before_punctuation` (gaps around [01](01-multiline-comments-break-parsing.md)/[02](02-implement-stacks.md)):
- [17](17-recall-comment-executes-statements.md) — Recall comment text after a `?` is executed as statements — **resolved** (dedicated `RECALL_COMMENT` terminal spanning `?` but stopping at `!`/`.`/`[`/`]`; shared `COMMENT` untouched, so 19 stays open)
- [19](19-title-question-mark-terminator.md) — title/section labels accept `?` as a terminator; the reference does not — **ready-for-human**

Input I/O (gaps in [09](09-input-error-semantics.md)):
- [16](16-read-number-crlf-handling.md) — `read_number` leaks a carriage return on CRLF input — **resolved** (trailing `\r\n` consumed as one terminator)
- [21](21-read-number-discards-char-on-error.md) — `read_number` discards the consumed terminator on the non-numeric error path — **resolved** (offending char pushed back before raising)

Articled names (gaps in [12](12-articled-character-names.md)):
- [18](18-articled-name-determiner-mismatch.md) — articled-name retry mis-resolves a non-`the` determiner / bare noun to a `The X` character — **ready-for-human**
- [20](20-name-article-absorbs-a-an.md) — `_name_article` absorbs `a`/`an` into names too broadly — **resolved** (article narrowed to `the`)

Test maintenance:
- [22](22-stale-question-branch-docstring.md) — stale docstring in the `_question_branch` test helper — **resolved** (docstring corrected)

## Bugs
- [01](01-multiline-comments-break-parsing.md) — multi-line comments break parsing — **resolved** (dropped the `\n` exclusion from `COMMENT`)

## Phase 2 language features
- [02](02-implement-stacks.md) — stacks (Remember/Recall) — **resolved** (both target the addressee; empty Recall raises, per ADR-0001)
- [03](03-richer-comparatives.md) — full comparative set — **resolved** (full reference set incl. `more ADJ than`; no `less`)

## Reference-program coverage
- [04](04-remaining-reference-programs.md) — remaining sample programs as golden tests — **resolved** (echo/catch/reverse/sierpinski/primes committed with stdin fixtures; all byte-match the oracle)

## Conformance decisions (vs shakespearelang / the spec)
- [07](07-goto-target-scope.md) — goto act+scene vs scene-only — **resolved** (keep act+scene; spec-faithful — ADR-0002)
- [08](08-division-sign-convention.md) — division/remainder sign — **resolved** (exact-int truncate-toward-zero; matches the reference's convention, more precise)
- [09](09-input-error-semantics.md) — non-numeric/EOF input — **resolved** (numeric input raises on EOF/non-numeric; spl2c-faithful parsing; char EOF→-1 — ADR-0003, ADR-0001)
- [10](10-conditional-without-question.md) — If so/If not with no question — **resolved** (keep strict raise; spec-silence alone → strict — ADR-0001)

## Naming
- [12](12-articled-character-names.md) — character names with a lowercase leading article (`the Ghost`) — **resolved** (scoped leading-article handling; unblocked `primes.spl` — ADR-0002)

## Infrastructure
- [05](05-package-data-for-wheel.md) — package data files for wheel installs — **resolved** (`importlib.resources` + `uv_build source-include`; verified from a clean-venv wheel)
- [06](06-differential-ci-testing.md) — live differential testing — **resolved** (opt-in `pytest -m differential` harness + allow-list; GitHub Actions YAML deferred until a remote exists)
- [11](11-write-readme.md) — write the README — **resolved** (drafted; pending human wording review)
