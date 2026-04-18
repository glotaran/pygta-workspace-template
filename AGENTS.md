# Project Guidelines

See also: [CONTRIBUTING.md](CONTRIBUTING.md), [CODING_GUIDELINES.md](CODING_GUIDELINES.md),
[pygta-local-extras/AGENTS.md](pygta-local-extras/AGENTS.md).

## Architecture

- Analysis work stays in project folders at the repository root, or in `local` or in `projects`; keep notebooks, model YAML, data, and results with the project they belong to.
- Reusable helper code goes in [pygta-local-extras](pygta-local-extras) unless the user
  explicitly asks for an upstream change.
- Do not modify anything under [external](external) unless the user explicitly asks for an
  upstream change.

## Build and Test

- Initialize or repair the workspace with `bootstrap.bat` (double-click) or `uv run bootstrap.py`;
  use `uv run bootstrap.py --update` to align existing clones to the branches configured in
  [repos.toml](repos.toml).
- Run `uv sync` after dependency metadata changes.
- Validate changes by running `pre-commit run --all-files` in the relevant package directory (or the workspace root for local helpers).
  - If hooks are not yet installed, run `pre-commit install` first (only needed once per repo clone).
  - After any turn that generates or edits Python, YAML, or notebook files, run `pre-commit run --all-files` as a quick automated review and fix any reported issues before finishing.
- Test the local helper package with `cd pygta-local-extras; uv run pytest`.
- On Windows terminals, verify `git` and `uv` resolve in the current session before assuming
  profile-provided PATH entries are available.

## Conventions

- Treat notebooks and model or parameter YAML files as scientific artifacts; avoid cleanup or
  restructuring that was not requested.
- Prefer importing directly from `pygta_local_extras` instead of adding new logic to
  compatibility wrappers in [scripts](scripts).
- Keep reusable workspace helpers in `pygta_local_extras` small and stable; when working in
  that package, also follow [pygta-local-extras/AGENTS.md](pygta-local-extras/AGENTS.md).
