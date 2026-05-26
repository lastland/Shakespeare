# Multi-line comments / persona descriptions fail to parse

Status: resolved

The `COMMENT` terminal in `src/spl/frontend/grammar.lark` is `/[^.!?\[\]\n]+/` — it excludes
newlines, so a title, persona description, or act/scene title that wraps across lines cannot be
parsed. This breaks real programs.

## Repro

`primes.spl` (a shakespearelang sample) has:

```
The Ghost, a limiting factor (and by a remarkable coincidence also
        Hamlet's father).
```

`python -m spl primes.spl` →
`ParseError: No terminal matches 'H' ... Expected one of: DOT` (at "Hamlet's father).").

## Fix

Drop the `\n` exclusion: `COMMENT.5: /[^.!?\[\]]+/`. SPL comments run until the next sentence
terminator regardless of line breaks. (Risk: a program missing a terminating `.` lets COMMENT eat
ahead — acceptable, that program is malformed.) Re-run the full suite and confirm `primes.spl`
parses; then see issue 04.
