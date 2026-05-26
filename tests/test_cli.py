"""Tests for the command-line entry point."""

from __future__ import annotations

from pathlib import Path

import pytest

from spl.cli import main

_GREETING = Path(__file__).parent / "programs" / "greeting.spl"


def test_runs_a_program_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(_GREETING)]) == 0
    assert capsys.readouterr().out == "HI"


def test_missing_file_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(_GREETING.parent / "does_not_exist.spl")]) == 2
    assert "cannot read" in capsys.readouterr().err


def test_wrong_arg_count_returns_2() -> None:
    assert main([]) == 2


def test_program_error_returns_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.spl"
    # A real character used but not declared in the Dramatis Personae → AnalysisError.
    bad.write_text(
        "A Test.\n\nRomeo, a person.\n\nAct I: a.\nScene I: s.\n"
        "[Enter Romeo]\nHamlet: You are nothing.\n"
    )
    assert main([str(bad)]) == 1
    assert "spl:" in capsys.readouterr().err
