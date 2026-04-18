# Coding Guidelines

Reference for writing quality code in this workspace. The workspace root and
`pygta-local-extras` intentionally use lighter checks than the upstream packages in
`external/`, but following these conventions makes eventual upstream contributions
easier.

## General Python Style

- **Line length**: 99 characters
- **Python target**: 3.10+ (use `X | Y` unions, `match`, etc.)
- **Future annotations**: start every module with `from __future__ import annotations`
- **Absolute imports only** (no relative imports)
- **Single import per line**
- **Docstrings**: NumPy format (see example below)
- **Type annotations**: on all function signatures in library code
- **No `print()`** in library code (use `logging` or `warnings`)
- **No commented-out code** in library code (remove dead code)

### NumPy Docstring Example

```python
def optimize_model(
    scheme: Scheme,
    *,
    max_nfev: int = 100,
    raise_exception: bool = False,
) -> Result:
    """Optimize a kinetic model against experimental data.

    Parameters
    ----------
    scheme : Scheme
        The optimization scheme containing model, parameters, and data.
    max_nfev : int
        Maximum number of function evaluations. Default is 100.
    raise_exception : bool
        Whether to raise an exception on optimization failure.

    Returns
    -------
    Result
        The optimization result containing fitted data and parameters.

    Raises
    ------
    OptimizationError
        If optimization fails and ``raise_exception`` is True.
    """
```

## Validation Commands

Each package has its own pre-commit config. The workspace-root checks are lighter than
the upstream package suites. Run these from the workspace root:

```powershell
Push-Location external/pyglotaran
pre-commit run --all-files   # black, isort, flake8, mypy, codespell
Pop-Location

Push-Location external/pyglotaran-extras
pre-commit run --all-files   # ruff, mypy (strict), docformatter, 100% docstring coverage
Pop-Location

pre-commit run --all-files   # lighter workspace-root checks for pygta-local-extras and analysis projects
```

```powershell
Push-Location pygta-local-extras
uv run pytest   # local tests
Pop-Location
```

## pygta-local-extras

`pygta-local-extras` is intentionally less strict than the upstream packages. Prefer the
general style above, rely on the workspace-root checks during normal development, and use
upstream-level cleanup when promoting code out of this package.

### Promotion Path

When `pygta-local-extras` code matures for upstream:

1. Add complete NumPy docstrings and type annotations
2. Add tests with good coverage
3. Run the upstream pre-commit suite to verify compliance
4. Move to `external/pyglotaran-extras/` (or `external/pyglotaran/`)
5. Submit as a PR

## Analysis Projects (notebooks)

Notebooks are working scientific documents — style rules are relaxed:

- Correctness and clarity matter more than formatting
- Use standard import patterns from [CONTRIBUTING.md](CONTRIBUTING.md)
- Keep data paths relative to the project folder
- Commented-out cells are acceptable (they record exploration)
- No docstring or type annotation requirements
