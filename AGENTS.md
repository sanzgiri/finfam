# Repository Guidelines

## Project Structure & Module Organization

- `finfam.py` is the core script that fetches mortgage and treasury data and appends to the CSV.
- `data/` contains generated output like `data/mortgage_daily.csv`.
- `requirements.txt` lists Python dependencies.
- `README.md` documents setup and usage.

## Build, Test, and Development Commands

- `uv venv` and `source .venv/bin/activate` set up the local virtual environment.
- `uv pip install -r requirements.txt` installs dependencies.
- `python3 finfam.py` runs the data collection once.
- `uv run python3 finfam.py` runs the script using uv without activating a shell.

## Coding Style & Naming Conventions

- Python 3.12+ with standard library typing (e.g., `dict[str, Any]`).
- 4-space indentation; keep functions small and purpose-driven.
- `snake_case` for functions/variables, `UPPER_CASE` for constants.
- Prefer type hints and dataclasses where they improve clarity.
- No formatter or linter is configured yet; keep style consistent with `finfam.py`.

## Testing Guidelines

- No automated tests are present. If adding tests, use `pytest` with a `tests/` directory.
- Name tests `test_*.py`, and prefer small unit tests for parsing helpers like `extract_first_float`.
- Manual sanity check: run `python3 finfam.py` and confirm `data/mortgage_daily.csv` updates.

## Commit & Pull Request Guidelines

- The current history shows a single commit with a descriptive subject line. Follow a similar style: concise, imperative (e.g., “Add Yahoo fallback handling”).
- Include a brief PR description, what data sources were touched, and any behavior changes.
- If output format changes, mention the new/changed CSV columns and update `README.md` if needed.

## Configuration & Data Notes

- External data comes from FinFam, Zillow, Bankrate, FRED, and Yahoo Finance via HTTP.
- Output is written to `data/mortgage_daily.csv`; avoid committing large or sensitive data files unless required.
