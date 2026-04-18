---
name: pygta-validate
description: Run validation across the workspace root and configured external repos with changes.
---

Run validation only where there are local changes, treating the workspace root and each
repository under `external/` as separate git repositories.

Use [CODING_GUIDELINES.md](../../../CODING_GUIDELINES.md) for the meaning of each validation tier and
[repos.toml](../../../repos.toml) as the source of truth for configured external checkouts.

## Procedure

1. Discover changed repositories before running any checks.
   - Check the workspace root repo with `git status --porcelain` from the workspace root.
   - Read `repos.toml` to find configured repositories under `external/`.
   - For each configured external repo that exists locally, check it independently with
     `git -C external/<directory> status --porcelain`.
   - Do not rely on the workspace-root git status to detect changes under `external/`, because
     `external/` is ignored by the root repository and nested repos are tracked separately.

2. Build the validation plan from the dirty repos.
   - If the workspace root repo has changes, run `pre-commit run --all-files` from the workspace root.
   - If `external/pyglotaran` has changes, run `pre-commit run --all-files` in `external/pyglotaran`.
   - If `external/pyglotaran-extras` has changes, run `pre-commit run --all-files` in
     `external/pyglotaran-extras`.
   - If `pygta-local-extras` files changed in the workspace root repo, also run `uv run pytest` from
     `pygta-local-extras`.
   - Ignore configured external repos that are absent locally; report them as not checked rather than failed.

3. Run all applicable validations.
   - Continue through every relevant repo even if one validation fails, so the user gets one complete report.
   - If no relevant repo has changes, report `nothing to validate` and stop.

4. Report results in a fixed summary.
   - Repositories checked
   - Commands run
   - Pre-commit pass/fail per repo
   - `pygta-local-extras` test pass/fail when tests were run
   - Missing checkouts or setup problems separately from lint/test failures

## Notes

- This skill exists to choose the right validations for a multi-repo workspace, not to restate the docs.
- The workspace root repo and repos under `external/` must be treated as separate SCM units.
- `pygta-local-extras` tests are only required when that package changed.
- Missing `pre-commit`, `uv`, or absent external checkouts are environment/setup issues and should be
  reported distinctly.
