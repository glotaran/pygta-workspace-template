# Project Anatomy

Use this note when the `pygta-project` skill needs a quick reminder of the scaffolded layout.

Expected scaffold result for a new project `<name>`:

- `<name>/data/` for raw or copied experiment input files
- `<name>/models/` for model and parameter YAML files
- `<name>/results/` for generated output files
- `<name>/README.md` for experiment goal, data provenance, and model notes
- `<name>/<name>.ipynb` as the starter analysis notebook, unless the user requested `--no-notebook`

After scaffolding, remind the user to put data in `data/`, create model files in `models/`, and begin analysis in the starter notebook.
