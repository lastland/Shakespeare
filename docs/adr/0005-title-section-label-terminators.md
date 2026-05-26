# Title/section label terminators: accept `?` as a friendly superset

A title or section label (the play title, a Dramatis Personae description, an Act or Scene name) is
terminated by a sentence-ending mark. The reference grammar (the dev-dependency `shakespearelang`'s
`shakespeare.ebnf`) defines a label as `… text_before_punctuation ("!" | ".")` with
`text_before_punctuation = /[^!\.]*/` — so the reference admits **only** `!` and `.` as label
terminators. A `?` is ordinary label text: the parser reads straight past it until the next `!`/`.`.

Our grammar's `_title_end` accepts `.`, `!`, **and** `?`, and the shared `COMMENT` terminal stops at
`?`, so we terminate a label at a `?`.

## Decision

Keep the `?` label terminator (issue 19). `.` and `!` match the reference; `?` is an intentional
superset. It is friendlier — a label phrased as a question (`What is love?`) ends where a reader
expects, instead of swallowing the following structure.

This is solely about `?` ending a **label**. The `?` that ends a **question** sentence
(`Am I better than you?`) is unrelated and fully reference-conformant — the reference's `question`
production ends in `?`, and so does ours.

## Demonstration

For a scene whose label ends in `?` (`Scene I: A scene?`), the reference reads past the `?` and
absorbs the scene body — the `[Enter …]` direction and the dialogue — into the label *name* (its
parsed events collapse to whatever follows the next `.`); we terminate the label at `?` and the
scene body is intact. So the two parse a `?`-terminated label into different programs.

## Consequences

- A `?`-terminated label parses differently from the oracle. Registered as the
  `title-question-terminator` divergence category in the differential harness; no bundled program
  uses a `?`-terminated label, so the differential suite stays 8/8 byte-exact.
- Decoupled from issue 17 (Recall comments). That issue gave Recall its own `RECALL_COMMENT`
  terminal, which **spans** `?` to stay reference-conformant (a Recall comment's trailing text is
  ignorable up to `!`/`.`). Because Recall no longer shares the `COMMENT` terminal, labels can keep
  the `?` terminator while Recall comments span `?` — the two `?` behaviours are intentionally
  different per construct.
- `!` and `.` label terminators remain reference-conformant; only `?` is the superset.
- No code change was needed — the grammar already terminates labels at `?`; this ADR records the
  decision to keep it. `test_title_and_section_terminators_allow_bang_and_question` locks it in.
