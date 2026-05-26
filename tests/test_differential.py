"""Opt-in differential test: cross-check our interpreter against the `shakespearelang` oracle.

This suite is gated behind the ``differential`` pytest marker and is *deselected by default*
(see ``addopts = "-m 'not differential'"`` in ``pyproject.toml``). The default ``pytest`` run
therefore never collects, imports, or invokes ``shakespearelang``; the committed golden suite in
``test_programs.py`` keeps the default run reference-free. Run this suite explicitly with the
reference present::

    uv run --with shakespearelang pytest -m differential

For every in-spec program under ``tests/programs/`` we run our interpreter (``BufferIO`` fed the
program's optional ``.in``) and the oracle (the ``shakespeare run`` console script as a subprocess,
fed the same bytes on stdin), then assert the two outputs match -- *except* where the
``ALLOWED_DIVERGENCES`` allow-list records an intentional, documented disagreement.

The allow-list encodes the four deliberate divergences from our ADRs. None of the eight current
programs trigger any of them, so the differential PASSES for all eight; the allow-list is the
documented mechanism for admitting future programs that exercise these spec-undefined / superset
cases without weakening the cross-check for everything else:

  - ``DANGLING_CONDITIONAL`` (ADR-0001): an "If so" / "If not" with no preceding Question. We raise
    (the boolean register has no defined value); the oracle defaults the register to false and runs
    the "If not" branch.
  - ``ACT_TARGET_GOTO`` (ADR-0002): a goto whose target is an act. We accept act-or-scene targets
    (spec-faithful superset); the oracle restricts gotos to scenes and parse-errors on act targets.
  - ``EXACT_INTEGER_DIVISION`` (ADR-0001/0003): integer division / square root on huge operands. We
    are exact (Python big ints); the oracle uses floating point and loses precision -- our result is
    the more precise one, so the bytes diverge.
  - ``SIGNED_OR_WHITESPACE_NUMERIC_INPUT`` (ADR-0003): numeric input led by a sign or whitespace. We
    accept it (spl2c / ``scanf("%d")``-faithful); the oracle reads a bare leading digit run and
    rejects sign/whitespace-led input.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import cast

import pytest

# Gate the whole module on the reference being importable. In the default environment
# (`uv run pytest`, no `shakespearelang`) this skips at collection time, so the default suite
# never imports the reference -- belt-and-suspenders with the `-m 'not differential'` deselection.
pytest.importorskip("shakespearelang")

from spl.backend.analyzer import analyze
from spl.backend.interpreter import Interpreter
from spl.backend.io import BufferIO
from spl.frontend.ast import Program
from spl.frontend.parser import parse

pytestmark = pytest.mark.differential

_PROGRAMS = Path(__file__).parent / "programs"

# The intentional, ADR-documented divergence categories. Keys of `ALLOWED_DIVERGENCES` map a
# program stem to the set of categories on which that program is permitted to disagree with the
# oracle. A program absent from the dict (or with an empty set) must match the oracle byte-for-byte.
DANGLING_CONDITIONAL = "dangling-conditional"  # ADR-0001: we raise; oracle runs 'If not'.
ACT_TARGET_GOTO = "act-target-goto"  # ADR-0002: we accept; oracle parse-errors.
EXACT_INTEGER_DIVISION = "exact-integer-division"  # ADR-0001/0003: we are exact; oracle uses float.
SIGNED_OR_WHITESPACE_NUMERIC_INPUT = "signed-or-whitespace-numeric-input"  # ADR-0003: we accept.
TITLE_QUESTION_TERMINATOR = "title-question-terminator"  # ADR-0005: we end a label on '?'.

# No current program exercises a divergence, so each maps to no allowed category and the
# cross-check is strict equality for all eight. New programs that intentionally diverge get listed
# here against the matching category constant(s).
ALLOWED_DIVERGENCES: dict[str, set[str]] = {}


def _run_ours(source: str, stdin: str) -> str:
    io = BufferIO(input_text=stdin)
    Interpreter(analyze(cast(Program, parse(source))), io).run()
    return io.output


def _run_oracle(spl_path: Path, stdin: str) -> str:
    """Run the `shakespearelang` oracle on `spl_path`, feeding `stdin`, and return its stdout.

    Uses the `shakespeare` console script resolved on PATH (present inside the
    `uv run --with shakespearelang` environment). The `run` subcommand defaults to basic input and
    output styles, so stdout is exactly what the play emitted.
    """
    exe = shutil.which("shakespeare")
    if exe is None:
        pytest.skip("the `shakespeare` console script is not on PATH")
    result = subprocess.run(
        [exe, "run", str(spl_path)],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    # The oracle prints SPL errors to stderr and still exits 0; surface them if stdout is empty so
    # an unexpected oracle failure does not masquerade as an output mismatch.
    if not result.stdout and result.stderr:
        pytest.fail(f"oracle emitted no stdout; stderr was:\n{result.stderr}")
    return result.stdout


@pytest.mark.parametrize("spl_path", sorted(_PROGRAMS.glob("*.spl")), ids=lambda p: p.stem)
def test_matches_oracle(spl_path: Path) -> None:
    stdin_path = spl_path.with_suffix(".in")
    stdin = stdin_path.read_text(encoding="utf-8") if stdin_path.exists() else ""
    source = spl_path.read_text(encoding="utf-8")

    ours = _run_ours(source, stdin)
    theirs = _run_oracle(spl_path, stdin)

    allowed = ALLOWED_DIVERGENCES.get(spl_path.stem, set())
    if ours != theirs:
        if allowed:
            pytest.skip(
                f"{spl_path.stem}: intentional divergence(s) {sorted(allowed)} -- see "
                f"ALLOWED_DIVERGENCES / the ADRs"
            )
        pytest.fail(
            f"{spl_path.stem}: output differs from oracle with no allowed divergence.\n"
            f"ours={ours!r}\noracle={theirs!r}"
        )
