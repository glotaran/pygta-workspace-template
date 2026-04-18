# Contributing

## Quick Start

```bat
uv run bootstrap.py
uv sync
```

See [AGENTS.md](AGENTS.md) for workspace rules, [CODING_GUIDELINES.md](CODING_GUIDELINES.md) for style.

## Where Changes Go

1. **Analysis work** (notebooks, models, plots) → project folder at the root
2. **Reusable helpers** (data loaders, selection utilities) → [pygta-local-extras](pygta-local-extras)
3. **Upstream extras** (mature plotting utilities) → [external/pyglotaran-extras](external/pyglotaran-extras)
4. **Core engine** (fitting, model changes) → [external/pyglotaran](external/pyglotaran)

## Typical Analysis Workflow

1. Load data with `glotaran.io.load_dataset` or `pyglotaran_extras.io.setup_case_study`
2. Inspect with `plot_data_overview()`
3. Define a `Scheme` referencing model YAML, parameters, and data
4. Run `optimize(scheme)`
5. Inspect results with `plot_overview()`, `plot_fitted_traces()`
6. Save with `save_result()`

Document data provenance and best-fit model location in each project's `README.md`.

Common imports:

```python
from __future__ import annotations

from glotaran.io import load_dataset, load_model, load_parameters, save_result
from glotaran.optimization.optimize import optimize
from glotaran.project.scheme import Scheme

from pyglotaran_extras import plot_data_overview
from pyglotaran_extras.io import setup_case_study
from pyglotaran_extras.plotting.plot_overview import plot_overview
from pyglotaran_extras.plotting.plot_traces import plot_fitted_traces
from pyglotaran_extras.plotting.plot_traces import select_plot_wavelengths

from pygta_local_extras import csv_to_dataset, slice_time_range, slice_spectral_range
```

## Common Commands

```text
uv run bootstrap.py               # first-time setup (or double-click bootstrap.bat)
uv sync                           # after dependency changes
uv run jupyter lab                # start Jupyter
pre-commit run --all-files        # lint (from workspace root or package dir)
uv run --script scripts/new_project.py <name>   # scaffold new project
cd pygta-local-extras; uv run pytest
```

## Package Notes

- For local helper rules see [pygta-local-extras/AGENTS.md](pygta-local-extras/AGENTS.md).
- Scripts in [scripts](scripts) are compatibility wrappers; prefer importing from `pygta_local_extras`.
