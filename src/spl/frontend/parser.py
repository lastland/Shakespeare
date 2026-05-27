"""Public frontend entry point: SPL source text → typed AST."""

from __future__ import annotations

from functools import cache
from importlib.resources import files

from lark import Lark, Token, Tree
from lark.exceptions import LarkError

from spl.errors import ParseError
from spl.frontend.transformer import ToAst

# Load the grammar via importlib.resources rather than `__file__` so it resolves whether the
# package is installed as a wheel, run from source, or imported from a zip — not just editable.
_GRAMMAR = files("spl.frontend").joinpath("grammar.lark").read_text(encoding="utf-8")

# Extra start symbols let tests parse individual constructs (a value, a line) in isolation.
_START_SYMBOLS = ["play", "value", "line", "name", "sentence"]


@cache
def _parser() -> Lark:
    # The dynamic lexer is contextual (maximal-munch): at each point it offers only the terminals
    # the grammar allows there. Two things keep a generic WORD from mis-tokenising:
    #   * Determiners (and `not`) are RESERVED out of WORD (see the WORD terminal in the grammar),
    #     so `the`/`a`/... lex ONLY as their keyword terminal. Without this `the` matches both THE
    #     and WORD on the same span and `constant` is ambiguous for every determiner (ADR-0002).
    #   * Other keywords (SUM, OF, ...) DO coexist with WORD on the same span, but `expression` and
    #     the pronouns outrank `constant` by RULE PRIORITY, so `the sum of ...` resolves to the
    #     operation while `a flower` stays a constant.
    # WORD therefore enumerates no vocabulary.
    return Lark(
        _GRAMMAR,
        parser="earley",
        lexer="dynamic",
        start=_START_SYMBOLS,
        maybe_placeholders=False,
    )


def parse(source: str, *, start: str = "play") -> object:
    """Parse SPL source into an AST node, raising `ParseError` on malformed input."""
    try:
        # lark's `parse` signature is only partially typed; pin the result and isolate the
        # untyped boundary here rather than relaxing strict mode project-wide.
        tree: Tree[Token] = _parser().parse(  # pyright: ignore[reportUnknownMemberType]
            source, start=start
        )
    except LarkError as exc:
        raise ParseError(str(exc)) from exc
    return ToAst().transform(tree)
