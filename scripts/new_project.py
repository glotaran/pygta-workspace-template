# /// script
# requires-python = ">=3.10"
# dependencies = ["nbformat>=5.9"]
# ///
"""Scaffold a new pyglotaran analysis project folder.

Usage:
    uv run --script scripts/new_project.py MyExperiment
    uv run --script scripts/new_project.py MyExperiment --description "PSI TA analysis"

Creates:
    MyExperiment/
        data/
        models/
        results/
        MyExperiment.ipynb       (starter notebook with standard imports)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

NOTEBOOK_TEMPLATE = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3 (ipykernel)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0",
        },
    },
    "cells": [],
}


_cell_counter = 0


def _next_cell_id() -> str:
    global _cell_counter
    _cell_counter += 1
    return f"cell-{_cell_counter:04d}"


def make_markdown_cell(source: str) -> dict:
    return {
        "id": _next_cell_id(),
        "cell_type": "markdown",
        "metadata": {},
        "source": source.strip().splitlines(keepends=True),
    }


def make_code_cell(source: str) -> dict:
    return {
        "id": _next_cell_id(),
        "cell_type": "code",
        "metadata": {},
        "source": source.strip().splitlines(keepends=True),
        "outputs": [],
        "execution_count": None,
    }


def create_starter_notebook(project_name: str, description: str) -> dict:
    """Build a starter notebook dict with standard pyglotaran imports."""
    nb = {**NOTEBOOK_TEMPLATE, "cells": []}

    nb["cells"].append(make_markdown_cell(f"# {project_name}\n\n{description}"))

    nb["cells"].append(
        make_code_cell(
            """\
from __future__ import annotations

import matplotlib.pyplot as plt
from glotaran.io import load_dataset, load_model, load_parameters, save_result
from glotaran.optimization.optimize import optimize
from glotaran.project.scheme import Scheme
from pyglotaran_extras import plot_data_overview
from pyglotaran_extras.plotting.plot_overview import plot_overview
from pyglotaran_extras.plotting.plot_traces import plot_fitted_traces
from pyglotaran_extras.plotting.plot_traces import select_plot_wavelengths"""
        )
    )

    nb["cells"].append(make_markdown_cell("## Inspect data"))

    nb["cells"].append(
        make_code_cell(
            """\
# DATA_PATH = "data/your_data_file.ascii"
# plot_data_overview(DATA_PATH, nr_of_data_svd_vectors=4, linlog=True, linthresh=1)"""
        )
    )

    nb["cells"].append(make_markdown_cell("## Model and parameters"))

    nb["cells"].append(
        make_code_cell(
            '# model_path = "models/model.yml"\n# parameters_path = "models/parameters.yml"'
        )
    )

    nb["cells"].append(make_markdown_cell("## Optimize"))

    nb["cells"].append(
        make_code_cell(
            """\
# scheme = Scheme(
#     model=model_path,
#     parameters=parameters_path,
#     maximum_number_function_evaluations=99,
#     data={
#         "dataset1": DATA_PATH,
#     },
# )
# scheme.validate()
# result = optimize(scheme, raise_exception=True)"""
        )
    )

    nb["cells"].append(make_markdown_cell("## Results"))

    nb["cells"].append(
        make_code_cell(
            """\
# plot_overview(result.data["dataset1"], linlog=True, linthresh=1)"""
        )
    )

    nb["cells"].append(
        make_code_cell(
            """\
# save_result(result=result, result_path="results", format_name="folder", allow_overwrite=True)"""
        )
    )

    return nb


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a new pyglotaran analysis project",
    )
    parser.add_argument(
        "name",
        help="Project name (used as folder name and notebook title)",
    )
    parser.add_argument(
        "--description",
        default="",
        help="Short description for the notebook header",
    )
    parser.add_argument(
        "--no-notebook",
        action="store_true",
        help="Create folder structure only, skip starter notebook",
    )

    args = parser.parse_args()
    name: str = args.name
    description: str = args.description or f"Analysis project: {name}"

    project_dir = WORKSPACE_ROOT / name

    if project_dir.exists():
        print(f"ERROR: {project_dir} already exists")
        return 1

    # Create directory structure
    dirs = [
        project_dir / "data",
        project_dir / "models",
        project_dir / "results",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {d.relative_to(WORKSPACE_ROOT)}/")

    # Generate README for project
    readme_path = project_dir / "README.md"
    readme_content = f"""# {name}

{description}

## Experiment Goal
*Briefly describe what this experiment intends to prove or analyze.*

## Data Provenance
*Explain where the data came from, what measurement it represents, or provide*
*download instructions if large.*
*Put data files in the `data/` directory.*

## Models
*Document which models/parameter files in `models/` represent the current best fit.*
"""
    readme_path.write_text(readme_content, encoding="utf-8")
    print(f"  Created: {readme_path.relative_to(WORKSPACE_ROOT)}")

    # Add .gitignore files to big directories
    data_gitignore = project_dir / "data" / ".gitignore"
    data_gitignore.write_text("*\n!.gitignore\n", encoding="utf-8")

    results_gitignore = project_dir / "results" / ".gitignore"
    results_gitignore.write_text("*\n!.gitignore\n", encoding="utf-8")

    print("  Created: .gitignore in data/ and results/ to prevent large file commits")

    # Create starter notebook
    if not args.no_notebook:
        try:
            import nbformat
        except ImportError:
            print("  WARNING: nbformat not available, writing notebook as JSON")
            import json

            nb = create_starter_notebook(name, description)
            nb_path = project_dir / f"{name}.ipynb"
            nb_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
            print(f"  Created: {nb_path.relative_to(WORKSPACE_ROOT)}")
        else:
            nb_dict = create_starter_notebook(name, description)
            nb = nbformat.from_dict(nb_dict)
            nb_path = project_dir / f"{name}.ipynb"
            nbformat.write(nb, str(nb_path))
            print(f"  Created: {nb_path.relative_to(WORKSPACE_ROOT)}")

    print(f"\nProject '{name}' scaffolded at {project_dir.relative_to(WORKSPACE_ROOT)}/")
    print("\nNext steps:")
    print(f"  1. Place your data files in {name}/data/")
    print(f"  2. Create model YAML files in {name}/models/")
    print(f"  3. Open {name}/{name}.ipynb and start your analysis")

    return 0


if __name__ == "__main__":
    sys.exit(main())
