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
python build_box.py
python build_box.py --model commander_100
python build_box.py --model constructed_60_15
python build_box.py --model uno_36
python build_box.py --model color_addicted_40
python build_box.py --model commander_100 --no-viewer-output
```

- Sem `--model`, o script abre um seletor interativo no terminal.
- Por padrao, o script exporta um arquivo `.step` da montagem para CAD viewer.

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

- Running with `/opt/homebrew/bin/python3 build_box.py` without activating `.venv` will fail with `ModuleNotFoundError: cadquery`.
- STL files are exported with model slug + version in the filename.
- In VSCode, select interpreter:
  - `Python: Select Interpreter` -> `/Users/matheuslmpereira/Workspace/cadquery-deckbox/.venv/bin/python`
