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
    # The dynamic lexer is contextual (maximal-munch, no character splitting): at each point it
    # offers only the terminals the grammar allows there. Because arithmetic lives in its own
    # `expression` rule, the state after `the` offers both the arithmetic keywords and WORD, and
    # keyword terminals outrank the generic WORD regex — so `the sum of ...` tokenises as the
    # operation while `a flower` stays a constant. WORD therefore needs no keyword enumeration.
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
