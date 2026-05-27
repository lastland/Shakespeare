"""Tests for the typed error hierarchy (src/spl/errors.py).

`Location` and `SplError`'s optional `location` are public API (the module docstring describes the
rendering contract: a location is "attached to an error when available"). No production path wires
a location through yet, so these tests lock the documented `(at line N, column M)` format directly.
"""

from __future__ import annotations

from spl.errors import Location, SplError


def test_location_str_renders_line_and_column() -> None:
    assert str(Location(line=1, column=2)) == "line 1, column 2"


def test_spl_error_appends_location_when_present() -> None:
    err = SplError("boom", Location(line=3, column=4))
    assert str(err) == "boom (at line 3, column 4)"
    assert err.message == "boom"
    assert err.location == Location(line=3, column=4)


def test_spl_error_without_location_is_bare_message() -> None:
    err = SplError("boom")
    assert str(err) == "boom"
    assert err.location is None
