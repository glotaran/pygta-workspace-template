# pygta-workspace-template

This repository is a GitHub template for creating a pyglotaran analysis and development
workspace in VS Code. A generated repository is not a single Python package. It combines
analysis projects, local helper code, and editable checkouts of upstream pyglotaran
repositories in one place.

Use this template if you want to:

- keep notebooks, model YAML files, data, and results together per experiment
- add shared workspace-specific helpers in `pygta-local-extras`
- develop or test changes against local clones of `pyglotaran` and `pyglotaran-extras`
- bootstrap the full environment with one command and keep it aligned to configured branches

If you only want to install and use pyglotaran as a library, you probably do not need this
workspace template.

## Use This Template

1. Create a new repository from this template.
2. Clone your new repository locally.
3. Run `uv run bootstrap.py` to clone the editable upstream dependencies and initialize the
  environment.
4. On first bootstrap, the root project name is normalized automatically by removing the trailing `-template`. Interactive runs show a menu with four choices: `pygta-workspace`, the repository folder name, `[github-username]-workspace`, or a custom name.

## Prerequisites

- `git` ([git for windows](https://git-scm.com/install/windows))
- `uv` ([install](https://docs.astral.sh/uv/getting-started/installation/))
- Python 3.10+

One-time tool setup:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install pre-commit --with pre-commit-uv --force-reinstall --force
uv tool install ruff
```

## Bootstrap Workspace

Run from the repository root:

```bat
uv run bootstrap.py
```

Common variants:

```bat
uv run bootstrap.py --update          # align clones to repos.toml branches
uv run bootstrap.py --all-extras      # clone optional repos too
uv run bootstrap.py --use-repository-name  # set project name from the repo folder
uv run bootstrap.py --project-name my-workspace  # set an explicit project name
uv run bootstrap.py --skip-sync       # skip uv sync
uv run bootstrap.py --reset           # reset clones
uv run bootstrap.py --full-reset      # delete and re-clone everything
```

To use a fork or non-default branch, edit [repos.toml](repos.toml) and re-run
`uv run bootstrap.py --update`.

## After Generation

- review [repos.toml](repos.toml) if you want to work from forks instead of the canonical
  `glotaran` repositories
- update `pyproject.toml` if you want a project name other than the bootstrap-selected value
- keep experiment data and generated results inside per-project folders at the repository root
- document data provenance in each project's `README.md`

## Workspace Layout

| Path | Purpose |
| ---- | ------- |
| Project folders (root) | Notebooks, models, data, results for each experiment |
| [pygta-local-extras](pygta-local-extras) | Editable local helper package |
| [external](external) | Editable clones of upstream pyglotaran repos |
| [scripts](scripts) | Workspace automation |

## Further Reading

- [CONTRIBUTING.md](CONTRIBUTING.md) — workflows, commands, where code goes
- [CODING_GUIDELINES.md](CODING_GUIDELINES.md) — style and validation reference
- [AGENTS.md](AGENTS.md) — workspace rules for LLM agents
