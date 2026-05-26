"""Command-line entry point: read an SPL source file, then parse → analyze → interpret."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

from spl.backend.analyzer import analyze
from spl.backend.interpreter import Interpreter
from spl.errors import SplError
from spl.frontend.ast import Program
from spl.frontend.parser import parse


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: spl <program.spl>", file=sys.stderr)
        return 2

    path = Path(args[0])
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"spl: cannot read {path}: {exc}", file=sys.stderr)
        return 2

    try:
        program = analyze(cast(Program, parse(source)))
        Interpreter(program).run()
    except SplError as exc:
        print(f"spl: {exc}", file=sys.stderr)
        return 1
    return 0
