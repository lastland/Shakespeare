"""Enable `python -m spl <program.spl>`."""

from __future__ import annotations

from spl.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
