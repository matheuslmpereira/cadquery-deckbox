# cadquery-deckbox

## Environment

- Python: `3.11.14` (required for this setup)
- CadQuery: `2.6.1`
- OCP Viewer package: `ocp_vscode 3.0.1`
- Virtualenv interpreter:
  - `/Users/matheuslmpereira/Workspace/cadquery-deckbox/.venv/bin/python`

## Setup

```bash
cd /Users/matheuslmpereira/Workspace/cadquery-deckbox
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
python commander_deck_box.py
```

## Verify environment

```bash
which python
python --version
python -m pip show cadquery ocp_vscode | rg "^Name:|^Version:"
```

Expected:

- `which python` -> `/Users/matheuslmpereira/Workspace/cadquery-deckbox/.venv/bin/python`
- `python --version` -> `Python 3.11.14`

## Notes

- Running with `/opt/homebrew/bin/python3 commander_deck_box.py` without activating `.venv` will fail with `ModuleNotFoundError: cadquery`.
- STL files are exported with the model version in the filename.
- In VSCode, select interpreter:
  - `Python: Select Interpreter` -> `/Users/matheuslmpereira/Workspace/cadquery-deckbox/.venv/bin/python`
