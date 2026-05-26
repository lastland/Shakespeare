"""Golden integration tests: run each program under tests/programs/ and diff against its `.out`.

Add a program by dropping `<name>.spl` and `<name>.out` (and an optional `<name>.in` for stdin)
into `tests/programs/`; the parametrization auto-discovers it via the `*.spl` glob. The `.out`
files are *committed* goldens, so this suite is reference-free at run time -- it runs only our
interpreter and diffs against the recorded bytes. Each golden was generated once from the
`shakespearelang` oracle (the opt-in `test_differential.py` re-derives the comparison live).
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from spl.backend.analyzer import analyze
from spl.backend.interpreter import Interpreter
from spl.backend.io import BufferIO
from spl.frontend.ast import Program
from spl.frontend.parser import parse

_PROGRAMS = Path(__file__).parent / "programs"


def _run(source: str, stdin: str) -> str:
    io = BufferIO(input_text=stdin)
    Interpreter(analyze(cast(Program, parse(source))), io).run()
    return io.output


@pytest.mark.parametrize("spl_path", sorted(_PROGRAMS.glob("*.spl")), ids=lambda p: p.stem)
def test_golden_program(spl_path: Path) -> None:
    expected = spl_path.with_suffix(".out").read_text(encoding="utf-8")
    stdin_path = spl_path.with_suffix(".in")
    stdin = stdin_path.read_text(encoding="utf-8") if stdin_path.exists() else ""
    assert _run(spl_path.read_text(encoding="utf-8"), stdin) == expected
