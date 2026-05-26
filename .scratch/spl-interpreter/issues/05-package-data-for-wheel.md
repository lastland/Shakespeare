# Package grammar.lark and vocabulary data files for wheel installs

Status: resolved

`src/spl/frontend/parser.py` loads `grammar.lark` and `src/spl/backend/vocabulary.py` loads
`backend/data/*.txt` via `Path(__file__).parent`. This works for an editable `uv sync` install but
a built wheel will not contain the `.lark` / `.txt` files unless they are declared as package data.

## Work

- Configure the `uv_build` backend (in `pyproject.toml`) to include `*.lark` and `backend/data/*.txt`
  in the wheel.
- Switch the loaders to `importlib.resources.files("spl.frontend") / "grammar.lark"` etc. so they
  work from an installed wheel as well as editable mode.
- Verify with `uv build` + install into a clean venv + run `spl tests/programs/greeting.spl`.
