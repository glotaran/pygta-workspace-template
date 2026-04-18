---
name: pygta-project
description: Scaffold a new pyglotaran analysis project with standard folder structure and starter notebook. Don't use when modifying an existing project or changing the scaffold script itself
---

Create a new analysis project folder in the workspace root.

See [references/PROJECT_ANATOMY.md](references/PROJECT_ANATOMY.md) for the expected project anatomy after scaffolding.

The project name is provided in $ARGUMENTS. If no name is given, ask the user for one.

## Steps

1. Confirm you are operating from the workspace root, the folder that contains `AGENTS.md` and `scripts/new_project.py`.

2. Run the scaffold script from that workspace root:
   ```
   uv run --script ./scripts/new_project.py $ARGUMENTS
   ```

3. Confirm what was created and remind the user of next steps:
   - Place data files in `<name>/data/`
   - Create model YAML files in `<name>/models/`
   - Open the starter notebook `<name>/<name>.ipynb`

## Expected Output

- A new `<name>/` folder at the workspace root
- Subdirectories: `<name>/data/`, `<name>/models/`, and `<name>/results/`
- A project README at `<name>/README.md`
- `.gitignore` files in `<name>/data/` and `<name>/results/`
- A starter notebook at `<name>/<name>.ipynb`, unless `--no-notebook` is passed

## Options

- `--description "..."` adds a description to the notebook header
- `--no-notebook` creates the folder structure without a starter notebook

## Example

```
/new-project PSI_TA_streak --description "PSI core target analysis"
```

This skill wraps the shared scaffold script.
