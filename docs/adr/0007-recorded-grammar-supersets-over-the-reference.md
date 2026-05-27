# Recorded grammar supersets over the reference

The analyzer and grammar accept a few constructs the `shakespearelang` reference EBNF parse-errors
on. Each is a deliberate *superset*: we accept strictly more than the reference, the accepted
extras are harmless (the computed value or semantics is unchanged where the reference would also
accept, and the rejected-by-reference cases carry no surprising meaning), and tightening to the
reference would buy only parse-time strictness we do not need. This record collects those supersets
and the evidence for why keeping each is safe, one section per superset, so a reader does not have
to rediscover them from the analyzer. It follows the posture already set by ADR-0002 (act-gotos are
a spec-faithful superset) and the baseline framing of ADR-0006: where we intentionally exceed the
reference, we say so here rather than leave it undocumented.

## Noun/adjective polarity is not enforced (issue 25)

The reference grammar splits a constant into a **negative noun phrase** — adjectives drawn from the
negative ∪ neutral lists, noun drawn from the negative list — and a **positive noun phrase** —
adjectives from the positive ∪ neutral lists, noun from the positive/neutral list. The adjectives
must agree in polarity with the noun; a *mismatch* (a positive adjective on a negative noun, or a
negative adjective on a positive noun) is a parse error in the reference.

This interpreter does not enforce that agreement. `analyzer._noun_phrase_value` finds the noun (the
longest trailing run the vocabulary recognises) and then checks each preceding word only with
`vocabulary.is_adjective` — never its polarity — before computing the value as `noun-sign ×
2^(number of adjectives)`. So a mismatched phrase is accepted and folded:

- `a happy coward` — `happy` is a positive adjective, `coward` a negative noun — folds to `-2`
  (`-1 × 2^1`). The reference rejects it as a polarity mismatch.
- `an evil King` — `evil` is a negative adjective, `King` a positive noun — folds to `+2`
  (`+1 × 2^1`). The reference rejects it likewise.

Keeping this superset is safe. Adjective polarity carries **no value information**: any adjective,
of any polarity, just doubles the magnitude, and only the noun decides the sign. So the value
`_noun_phrase_value` computes is *always* the correct magnitude and sign for the noun phrase as
written — the only thing the reference enforces here and we do not is parse-time polarity
*agreement* between adjective and noun, which never changes the resulting number. The reference's
agreement check is therefore a well-formedness constraint, not a semantic one: every phrase we
accept-but-it-rejects has a single unambiguous value, and every phrase both accept folds identically.
This is the same shape as the act-goto superset (ADR-0002) — we accept a strictly larger surface
with no semantic divergence on the overlap — and is consistent with ADR-0006's baseline framing,
which treats intentional-and-recorded supersets as conformant rather than as bugs. Tightening to the
reference would mean threading adjective polarity through `_noun_phrase_value` and rejecting
mismatches purely to reproduce a parse error, for no semantic gain; the triage decision (issue 25)
is to keep the superset and record it here instead. The behavior is pinned by tests in
`tests/backend/test_analyzer.py` (`a happy coward` → −2, `an evil King` → +2 accepted) so it cannot
silently regress.

## `as <word> as` admits any vocabulary word as the simile adjective (issue 26)

The reference grammar's equality comparison — the "simile" form — is `"as" adjective "as"`, where
the middle word must be a *known adjective*. A non-adjective there (a noun, say) is a parse error in
the reference.

This interpreter does not restrict the middle word. The grammar's `comp_kind` carries the
alternative `AS WORD AS -> eq` (`grammar.lark:86`), where `WORD` is the generic vocabulary terminal
that matches any lowercase word — adjective, noun, or otherwise. The transformer's `eq` handler
discards the word entirely and returns the bare string `"eq"` (`transformer.py:132-133`); the
analyzer then resolves that to the equality comparison with no reference to the word at all
(`_resolve_comparison` passes a plain `"eq"`/`"gt"`/`"lt"` string straight through). So the simile
adjective never reaches the value computation:

- `Are you as cat as a King?` parses to `Question(PronounValue("second"), Constant(("King",)),
  "eq")` and analyzes cleanly, even though `cat` is a *noun*. The reference rejects it because `cat`
  is not an adjective.

Keeping this superset is safe. In a simile the adjective is **semantically inert**: the form
`as X as` means *equality* regardless of which adjective X is — the reference would compute the
exact same comparison (`eq`) for `as good as`, `as bad as`, or any other admissible adjective. We
discard the word at transform time precisely because it carries no value or direction information
(unlike `more <adjective> than`, where the adjective's *sign* picks gt vs lt and so must be kept and
resolved). Every program the reference accepts here, we accept with an identical `eq` result; the
only programs we additionally accept are those whose middle word is a non-adjective, and for those
the meaning is the same unambiguous equality test. Tightening to the reference would mean
classifying the simile word against the adjective vocabulary purely to reproduce a parse error, for
no semantic gain. Pinned by a parser test (`as cat as` → `eq` question) and an analyzer test
(`Are you as cat as a King?` analyzes) so it cannot silently regress.

## Nested conditionals parse (issue 26)

The reference grammar attaches at most **one** condition prefix to an operation: a conditional
(`"If so," | "If not,"`) guards a single non-conditional statement, so `If so, if not, …` is a parse
error in the reference.

This interpreter's grammar makes a conditional guard a full `statement`, and `statement` itself
lists `conditional` among its alternatives (`grammar.lark:53-61` for `?statement`, `98-99` for the
`conditional` rule). Because the guarded statement may again be a conditional, condition prefixes
nest to any depth:

- `If so, if not, Thou art a King.` parses to `Conditional(on_true=True, body=Conditional(
  on_true=False, body=Assignment(Constant(("King",)))))` — an outer `If so` guarding an inner
  `If not` guarding the assignment. The reference rejects the second prefix.

Keeping this superset is safe. A nested conditional reuses the singly-guarded evaluation rule with
no addition: the interpreter holds the most recent comparison in a single `last_question` flag, and
each `Conditional(on_true, body)` runs its `body` exactly when `last_question == on_true`, recursing
into `body` when that body is itself a `Conditional` (`interpreter.py:110-114`). So `If so, if not,
S` first checks the flag against `True`, and only then — without that flag changing — checks the
same flag against `False`; the two guards consult one flag, so `S` runs only if a fresh question is
interposed between them, and otherwise the inner guard simply does not fire. This is the obvious,
unsurprising reading of stacked prefixes against a single comparison result; no new evaluation rule
is introduced, and the body being another `Conditional` is just one more step of the same walk the
interpreter already does for a singly-guarded statement. Every singly-guarded program the reference
accepts, we accept and evaluate identically; the only programs we additionally accept are the
multiply-guarded ones, whose meaning follows directly from that one rule. Tightening to the
reference would mean forbidding `conditional` as a `conditional` body purely to reproduce a parse
error, for no semantic gain. Pinned by a parser test (`If so, if not, …` → nested `Conditional`) so
it cannot silently regress.

## Consequences

- All three grammar supersets — noun/adjective polarity (issue 25), `as <word> as` admitting any
  vocabulary word, and nested conditionals (both issue 26) — are now recorded, decided divergences
  rather than undocumented over-acceptances; `docs/gap-analysis.md` lists each under deliberate
  divergences, cross-referencing this ADR; no over-acceptance remains undocumented.
- No analyzer, transformer, grammar, or interpreter behavior changed for any section: the
  interpreter folds mismatched noun phrases exactly as before, the simile adjective is discarded at
  transform time exactly as before, and nested conditionals evaluate by the same single-flag guard
  rule as before (each prefix tests the one `last_question` flag). These slices are documentation +
  pinning tests only.
- This ADR is the home for intentional grammar supersets over the reference; any superset decided
  later extends it with its own section, each ending its rationale with the same "safe because …"
  evidence.
