# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "tomli; python_version < '3.11'",
# ]
# ///

from __future__ import annotations

import argparse
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10 only.
    import tomli as tomllib  # pyright: ignore[reportMissingImports]


@dataclass(frozen=True)
class RepoSpec:
    name: str
    directory: str
    preferred_owner: str
    repo: str
    branch: str
    is_python_package: bool
    include_in_uv_workspace: bool
    notes: str


@dataclass(frozen=True)
class Config:
    canonical_owner: str
    clone_protocol: str
    fallback_branch: str
    core: list[RepoSpec]
    extras: list[RepoSpec]


@dataclass(frozen=True)
class CheckoutTarget:
    url: str
    branch: str
    description: str
    source_label: str
    warning: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap the workspace root and clone configured external repositories.",
    )
    reset_group = parser.add_mutually_exclusive_group()
    reset_group.add_argument(
        "--clean",
        action="store_true",
        help="Remove uv.lock and .python-version, then exit.",
    )
    reset_group.add_argument(
        "--reset",
        action="store_true",
        help="Run --clean first, then continue with bootstrap initialization.",
    )
    reset_group.add_argument(
        "--full-reset",
        action="store_true",
        help=(
            "Run a reset and also delete the contents of external/ after an extra confirmation, "
            "then continue with bootstrap initialization."
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Answer yes to the destructive confirmation required by --full-reset.",
    )
    parser.add_argument(
        "--python-version",
        help=(
            "Minimum supported Python version for the root project. "
            "Must be 3.x or 3.x.y with x >= 10."
        ),
    )
    parser.add_argument(
        "--project-name",
        help=(
            "Set [project].name in pyproject.toml during bootstrap. "
            "If omitted, bootstrap removes any trailing '-template'."
        ),
    )
    parser.add_argument(
        "--use-repository-name",
        action="store_true",
        help=(
            "Set [project].name from the repository folder name on first bootstrap, "
            "after removing any trailing '-template'."
        ),
    )
    parser.add_argument(
        "--all-extras",
        action="store_true",
        help="Clone repositories listed under [extras] in repos.toml as well.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help=(
            "Fetch configured repository branches and align clean local checkouts when possible."
        ),
    )
    parser.add_argument(
        "--git-name",
        help="Global Git user.name to set if it is currently missing.",
    )
    parser.add_argument(
        "--git-email",
        help="Global Git user.email to set if it is currently missing.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fail instead of prompting for missing required values.",
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip the final uv sync step.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent

    reset_result = handle_reset_options(root, args)
    if reset_result is not None:
        return reset_result

    try:
        config = load_config(root / "repos.toml")
        require_command("git")
        require_command("uv")
        ensure_root_git_repo(root)
        ensure_global_git_identity(args)
        python_version = resolve_python_version(args)
        include_extras = resolve_include_extras(args, config)
        ensure_workspace_pyproject(root, python_version, args)
        ensure_bootstrap_artifacts_are_trackable(root)
        ensure_python_version_file(root, python_version)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    repositories = list(config.core)
    if include_extras:
        repositories.extend(config.extras)

    print_repository_summary(repositories, config)

    external_root = root / "external"
    external_root.mkdir(exist_ok=True)

    failures = 0
    for repo in repositories:
        success = clone_or_update_repo(
            repo=repo,
            config=config,
            external_root=external_root,
            update_existing=args.update,
        )
        if not success:
            failures += 1

    try:
        ensure_project_dependencies(root, external_root, python_version)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.skip_sync:
        print("\nSkipping uv sync (--skip-sync).")
    else:
        try:
            run_uv_sync(root, python_version)
        except RuntimeError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2

    if failures:
        print(f"\nCompleted with {failures} repository failure(s).")
    else:
        print("\nCompleted successfully.")
    return 0


def handle_reset_options(root: Path, args: argparse.Namespace) -> int | None:
    if args.clean:
        print_clean_summary(delete_external=False, mode_name="clean")
        clean_workspace(root, delete_external=False)
        print("\nClean completed.")
        return 0

    if args.reset:
        print_clean_summary(delete_external=False, mode_name="reset")
        clean_workspace(root, delete_external=False)
        print("Reset cleanup completed. Re-initializing workspace.")
        return None

    if args.full_reset:
        print_clean_summary(delete_external=True, mode_name="full-reset")
        if args.yes:
            confirmed = True
        else:
            if args.non_interactive:
                raise RuntimeError(
                    "--full-reset requires interactive confirmation unless --yes is provided."
                )
            confirmed = prompt_yes_no(
                (
                    "Full reset will delete uv.lock, "
                    ".python-version, and all contents of external/. Are you sure"
                ),
                default=False,
            )
        if not confirmed:
            print("Full reset cancelled.")
            return 1
        clean_workspace(root, delete_external=True)
        print("Full reset cleanup completed. Re-initializing workspace.")
        return None

    return None


def print_clean_summary(delete_external: bool, mode_name: str) -> None:
    print(f"Starting {mode_name}: this will remove uv.lock and .python-version.")
    if delete_external:
        print("Starting full-reset: this will also remove all contents of external/.")
    else:
        print("external/ contents will be kept.")


def clean_workspace(root: Path, delete_external: bool) -> None:
    for path in (root / "uv.lock", root / ".python-version"):
        if not path.exists():
            continue
        delete_path(path)
        print(f"Removed {path.name}.")

    if not delete_external:
        return

    external_root = root / "external"
    if not external_root.exists():
        return

    for child in external_root.iterdir():
        delete_path(child)
        print(f"Removed external content: {child.name}")


def delete_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, onerror=handle_remove_readonly)
        return
    make_path_writable(path)
    path.unlink()


def handle_remove_readonly(
    func: Callable[[str], object],
    target: str,
    exc_info: tuple[type[BaseException], BaseException, object],
) -> None:
    if not issubclass(exc_info[0], PermissionError):
        raise exc_info[1]

    make_path_writable(Path(target))
    func(target)


def make_path_writable(path: Path) -> None:
    if not path.exists():
        return
    path.chmod(stat.S_IWRITE | stat.S_IREAD)


def load_config(config_path: Path) -> Config:
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)

    defaults = data.get("defaults", {})
    canonical_owner = defaults.get("canonical_owner")
    clone_protocol = defaults.get("clone_protocol", "https")
    fallback_branch = str(defaults.get("fallback_branch", "main")).strip()
    if not canonical_owner:
        raise RuntimeError(f"Missing defaults.canonical_owner in {config_path.name}.")
    if clone_protocol not in {"https", "ssh"}:
        raise RuntimeError("defaults.clone_protocol must be 'https' or 'ssh'.")
    if not fallback_branch:
        raise RuntimeError("defaults.fallback_branch must be a non-empty branch name.")

    return Config(
        canonical_owner=canonical_owner,
        clone_protocol=clone_protocol,
        fallback_branch=fallback_branch,
        core=[parse_repo_spec(item) for item in data.get("core", [])],
        extras=[parse_repo_spec(item) for item in data.get("extras", [])],
    )


def parse_repo_spec(item: dict[str, object]) -> RepoSpec:
    required_keys = {
        "name",
        "directory",
        "preferred_owner",
        "repo",
        "branch",
        "is_python_package",
        "include_in_uv_workspace",
        "notes",
    }
    missing = sorted(required_keys - item.keys())
    if missing:
        raise RuntimeError(f"Invalid repos.toml entry; missing keys: {', '.join(missing)}")

    preferred_owner = str(item["preferred_owner"]).strip()
    repo = str(item["repo"]).strip()
    branch = str(item["branch"]).strip()
    if not preferred_owner or not repo or not branch:
        raise RuntimeError(
            "Invalid repos.toml entry; preferred_owner, repo, and branch "
            "must be non-empty strings."
        )

    return RepoSpec(
        name=str(item["name"]),
        directory=str(item["directory"]),
        preferred_owner=preferred_owner,
        repo=repo,
        branch=branch,
        is_python_package=bool(item["is_python_package"]),
        include_in_uv_workspace=bool(item["include_in_uv_workspace"]),
        notes=str(item["notes"]),
    )


def require_command(command: str) -> None:
    if shutil.which(command) is None:
        raise RuntimeError(f"Required command '{command}' was not found on PATH.")


def ensure_root_git_repo(root: Path) -> None:
    existing_repo = run_command(["git", "rev-parse", "--show-toplevel"], cwd=root)
    if existing_repo.returncode == 0:
        repo_root = Path(existing_repo.stdout.strip()).resolve()
        if repo_root == root.resolve():
            print("Workspace Git repository already exists.")
            return
        raise RuntimeError(
            "Workspace root is inside another Git repository "
            f"({repo_root}) but is not itself a repository."
        )

    result = run_command(["git", "init"], cwd=root)
    if result.returncode != 0:
        raise RuntimeError(render_command_error("git init", result))
    message = result.stdout.strip() or result.stderr.strip() or "git repository ready"
    print(message)


def ensure_global_git_identity(args: argparse.Namespace) -> None:
    current_name = git_config_get("user.name")
    current_email = git_config_get("user.email")

    if args.git_name:
        if current_name:
            print("Global Git user.name is already set; leaving it unchanged.")
        else:
            set_global_git_config("user.name", args.git_name)
            print(f"Configured global Git user.name as '{args.git_name}'.")

    if args.git_email:
        if current_email:
            print("Global Git user.email is already set; leaving it unchanged.")
        else:
            set_global_git_config("user.email", args.git_email)
            print(f"Configured global Git user.email as '{args.git_email}'.")

    missing_keys: list[str] = []
    if not current_name and not args.git_name:
        missing_keys.append("user.name")
    if not current_email and not args.git_email:
        missing_keys.append("user.email")

    if missing_keys:
        joined_keys = ", ".join(missing_keys)
        print(
            "Warning: global Git identity is incomplete "
            f"({joined_keys}). Cloning will work, but commits may fail until you set it."
        )


def resolve_python_version(args: argparse.Namespace) -> str:
    if args.python_version is not None:
        return validate_python_version(args.python_version)
    if args.non_interactive:
        return "3.10"
    return prompt_for_python_version()


def prompt_for_python_version() -> str:
    prompt = "Minimum supported Python version for the root project (blank defaults to 3.10)"
    while True:
        value = input(f"{prompt}: ").strip()
        if not value:
            return "3.10"
        try:
            return validate_python_version(value)
        except RuntimeError as error:
            print(error)


def validate_python_version(value: str) -> str:
    normalized = value.strip()
    match = re.fullmatch(r"3\.(\d+)(?:\.(\d+))?", normalized)
    if not match:
        raise RuntimeError(
            "Python version must be in the format 3.x or 3.x.y, for example 3.10 or 3.10.14."
        )

    minor = int(match.group(1))
    if minor < 10:
        raise RuntimeError("Python version must be 3.10 or newer.")
    return normalized


def resolve_include_extras(args: argparse.Namespace, config: Config) -> bool:
    if args.all_extras:
        return True
    if not config.extras:
        return False
    if args.non_interactive:
        return False
    return prompt_yes_no("Also clone the optional extras repositories", default=False)


def prompt_for_value(prompt: str, allow_empty: bool, non_interactive: bool) -> str | None:
    if non_interactive:
        if allow_empty:
            return None
        raise RuntimeError(f"{prompt}. Provide a flag or run interactively.")

    while True:
        value = input(f"{prompt}: ").strip()
        if value or allow_empty:
            return value or None
        print("A value is required.")


def prompt_yes_no(prompt: str, default: bool) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        value = input(f"{prompt} {suffix}: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def git_config_get(key: str) -> str | None:
    result = run_command(["git", "config", "--global", "--get", key])
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def set_global_git_config(key: str, value: str) -> None:
    result = run_command(["git", "config", "--global", key, value])
    if result.returncode != 0:
        raise RuntimeError(render_command_error(f"git config --global {key}", result))


def ensure_workspace_pyproject(root: Path, python_version: str, args: argparse.Namespace) -> None:
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.exists():
        raise RuntimeError(
            "Missing pyproject.toml in the workspace root. Restore the checked-in file and "
            "rerun bootstrap."
        )

    ensure_project_name(pyproject_path, root, args)
    ensure_requires_python(pyproject_path, python_version)


def ensure_project_name(pyproject_path: Path, root: Path, args: argparse.Namespace) -> None:
    content = pyproject_path.read_text(encoding="utf-8")
    current_name = read_project_name(content, pyproject_path)
    desired_name = resolve_project_name(current_name, root, args)

    if desired_name == current_name:
        print(f"pyproject.toml project name is '{current_name}'.")
        return

    updated = re.sub(
        r'(^name\s*=\s*")([^"]+)(")',
        rf"\g<1>{desired_name}\g<3>",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    pyproject_path.write_text(updated, encoding="utf-8")
    print(f"Updated pyproject.toml project name from '{current_name}' to '{desired_name}'.")


def read_project_name(content: str, pyproject_path: Path) -> str:
    project_match = re.search(
        r"^\[project\]\n(?P<body>.*?)(?:^\[|\Z)",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    if project_match is None:
        raise RuntimeError(f"No [project] table found in {pyproject_path.name}.")

    name_match = re.search(
        r'^name\s*=\s*"(?P<name>[^"]+)"',
        project_match.group("body"),
        flags=re.MULTILINE,
    )
    if name_match is None:
        raise RuntimeError(f"No project name found in {pyproject_path.name}.")
    return name_match.group("name")


def resolve_project_name(current_name: str, root: Path, args: argparse.Namespace) -> str:
    default_name = strip_template_suffix(current_name)
    repository_name = normalize_project_name(root.name)
    repository_name = strip_template_suffix(repository_name)
    github_workspace_name = resolve_github_workspace_name(root)

    if args.project_name:
        return normalize_project_name(args.project_name)

    if args.use_repository_name and repository_name:
        return repository_name

    if current_name == default_name:
        return current_name

    if args.non_interactive:
        return default_name

    return prompt_for_project_name_choice(
        default_name=default_name,
        repository_name=repository_name,
        github_workspace_name=github_workspace_name,
    )


def prompt_for_project_name_choice(
    *,
    default_name: str,
    repository_name: str,
    github_workspace_name: str | None,
) -> str:
    print("Choose the project name for pyproject.toml:")
    print(f"1. {default_name} [default]")
    print(f"2. {repository_name}")
    if github_workspace_name is None:
        print("3. [github-username]-workspace")
    else:
        print(f"3. {github_workspace_name}")
    print("4. Type it yourself")

    while True:
        choice = input("Select 1-4 [1]: ").strip()
        if not choice or choice == "1":
            return default_name
        if choice == "2":
            return repository_name
        if choice == "3":
            if github_workspace_name is not None:
                return github_workspace_name
            github_username = prompt_for_value(
                prompt="GitHub username",
                allow_empty=False,
                non_interactive=False,
            )
            return normalize_project_name(f"{github_username}-workspace")
        if choice == "4":
            while True:
                custom_name = prompt_for_value(
                    prompt="Project name",
                    allow_empty=False,
                    non_interactive=False,
                )
                try:
                    return normalize_project_name(custom_name or "")
                except RuntimeError as error:
                    print(error)

        print("Please choose 1, 2, 3, or 4.")


def resolve_github_workspace_name(root: Path) -> str | None:
    github_owner = get_origin_github_owner(root)
    if not github_owner:
        return None
    return normalize_project_name(f"{github_owner}-workspace")


def get_origin_github_owner(root: Path) -> str | None:
    result = run_command(["git", "remote", "get-url", "origin"], cwd=root)
    if result.returncode != 0:
        return None

    remote_url = result.stdout.strip()
    match = re.search(
        r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
        remote_url,
    )
    if match is None:
        return None
    return match.group("owner")


def strip_template_suffix(value: str) -> str:
    if value.endswith("-template"):
        return value[: -len("-template")]
    return value


def normalize_project_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower())
    normalized = normalized.strip("-._")
    if not normalized:
        raise RuntimeError("Project name must contain at least one letter or number.")
    return normalized


def ensure_bootstrap_artifacts_are_trackable(root: Path) -> None:
    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        return

    ignored_artifacts = {".python-version", "uv.lock"}
    template_notice = (
        "# Template-only bootstrap artifacts. bootstrap.py removes these entries in "
        "derived workspaces."
    )
    lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    kept_lines: list[str] = []
    removed_lines: list[str] = []
    removed_notice = False

    for line in lines:
        if line.strip() == template_notice:
            removed_notice = True
            continue
        if line.strip() in ignored_artifacts:
            removed_lines.append(line.strip())
            continue
        kept_lines.append(line)

    while kept_lines and kept_lines[-1] == "":
        kept_lines.pop()

    if not removed_lines and not removed_notice:
        print(".gitignore already allows .python-version and uv.lock to be committed.")
        return

    gitignore_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
    removed_parts: list[str] = []
    if removed_lines:
        removed_parts.append(", ".join(sorted(set(removed_lines))))
    if removed_notice:
        removed_parts.append("template notice")
    removed_summary = ", ".join(removed_parts)
    print(f"Removed template-only entries from .gitignore: {removed_summary}.")


def ensure_python_version_file(root: Path, python_version: str) -> None:
    python_version_path = root / ".python-version"
    desired_content = f"{python_version}\n"
    current_content = (
        python_version_path.read_text(encoding="utf-8") if python_version_path.exists() else None
    )

    if current_content == desired_content:
        print(f".python-version already pins Python {python_version}.")
        return

    python_version_path.write_text(desired_content, encoding="utf-8")
    print(f"Pinned project Python version to {python_version} in .python-version.")


def ensure_requires_python(pyproject_path: Path, python_version: str) -> None:
    content = pyproject_path.read_text(encoding="utf-8")
    required_line = f'requires-python = ">={python_version}"'
    if required_line in content:
        print(f"pyproject.toml already requires Python >= {python_version}.")
        return

    if re.search(r'^requires-python\s*=\s*"[^"]+"', content, flags=re.MULTILINE):
        updated = re.sub(
            r'^requires-python\s*=\s*"[^"]+"',
            required_line,
            content,
            count=1,
            flags=re.MULTILINE,
        )
        pyproject_path.write_text(updated, encoding="utf-8")
        print(f"Updated requires-python to >= {python_version}.")
        return

    if "[project]" not in content:
        raise RuntimeError(f"No [project] table found in {pyproject_path.name}.")

    updated = content.replace("[project]\n", f"[project]\n{required_line}\n", 1)
    pyproject_path.write_text(updated, encoding="utf-8")
    print(f"Added requires-python >= {python_version}.")


def ensure_project_dependencies(root: Path, external_root: Path, python_version: str) -> None:
    pyglotaran_path = external_root / "pyglotaran"
    extras_path = external_root / "pyglotaran-extras"
    local_extras_path = root / "pygta-local-extras"

    missing_paths = [
        str(path.relative_to(root))
        for path in (pyglotaran_path, extras_path, local_extras_path)
        if not path.exists()
    ]
    if missing_paths:
        missing = ", ".join(missing_paths)
        raise RuntimeError(
            "Cannot initialize project dependencies because required local paths are missing: "
            f"{missing}"
        )

    add_standard_dependency(root, "ipykernel", python_version)
    add_editable_dependencies(
        root,
        [
            f"./{pyglotaran_path.relative_to(root).as_posix()}",
            f"./{extras_path.relative_to(root).as_posix()}",
            f"./{local_extras_path.relative_to(root).as_posix()}",
        ],
        python_version,
    )


def add_standard_dependency(root: Path, dependency: str, python_version: str) -> None:
    print(f"Ensuring dependency: {dependency}")
    result = run_command(
        ["uv", "add", "--python", python_version, "--no-sync", dependency], cwd=root
    )
    if result.returncode != 0:
        raise RuntimeError(render_command_error(f"uv add {dependency}", result))


def add_editable_dependencies(
    root: Path, dependency_paths: list[str], python_version: str
) -> None:
    joined_paths = ", ".join(dependency_paths)
    print(f"Ensuring editable dependencies: {joined_paths}")
    for dependency_path in dependency_paths:
        result = run_command(
            [
                "uv",
                "add",
                "--python",
                python_version,
                "--no-sync",
                "--no-workspace",
                "--editable",
                dependency_path,
            ],
            cwd=root,
        )
        if result.returncode != 0:
            raise RuntimeError(
                render_command_error(f"uv add editable dependency {dependency_path}", result)
            )


def print_repository_summary(
    repositories: list[RepoSpec],
    config: Config,
) -> None:
    print("\nRepositories to manage:")
    for repo in repositories:
        membership = (
            "workspace member" if repo.include_in_uv_workspace else "not a workspace member"
        )
        preferred_checkout = f"{repo.preferred_owner}/{repo.repo}@{repo.branch}"
        fallback_checkout = f"{config.canonical_owner}/{repo.repo}@{config.fallback_branch}"
        checkout_policy = f"preferred {preferred_checkout}"
        if preferred_checkout != fallback_checkout:
            checkout_policy += f"; fallback {fallback_checkout}"
        print(f"- {repo.name} -> external\\{repo.directory} ({membership}; {checkout_policy})")
    print(
        "Checkout policy: use each repo's preferred owner/branch, then fall back "
        "to the canonical branch when needed."
    )


def clone_or_update_repo(
    repo: RepoSpec,
    config: Config,
    external_root: Path,
    update_existing: bool,
) -> bool:
    target = external_root / repo.directory
    canonical_url = build_remote_url(config.clone_protocol, config.canonical_owner, repo.repo)

    print(f"\n==> {repo.name}")
    print(f"Target: {target}")

    if target.exists():
        if not is_git_repo(target):
            print("Status: skipped (target exists but is not a Git repository).")
            return False
        if update_existing:
            return update_repo(repo, config, target)
        status = "already exists; run --update to align with the configured checkout"
    else:
        checkout_target = resolve_checkout_target(repo, config)
        if checkout_target is None:
            print("Status: failed (preferred checkout and canonical fallback are unavailable).")
            return False

        if checkout_target.warning is not None:
            print(checkout_target.warning)

        result = run_command(
            [
                "git",
                "clone",
                "--branch",
                checkout_target.branch,
                "--single-branch",
                checkout_target.url,
                str(target),
            ]
        )
        if result.returncode != 0:
            print(
                f"Status: failed to clone {checkout_target.description}. "
                f"{render_command_error('git clone', result)}"
            )
            return False

        if checkout_target.source_label == "preferred" and canonical_url != checkout_target.url:
            add_upstream_remote(target, canonical_url)

        status = f"cloned {checkout_target.description}"

    if not update_submodules(target):
        return False

    print(f"Status: {status}; submodules updated.")
    return True


def update_repo(repo: RepoSpec, config: Config, target: Path) -> bool:
    checkout_target = resolve_checkout_target(repo, config)
    if checkout_target is None:
        print("Status: failed (preferred checkout and canonical fallback are unavailable).")
        return False

    if checkout_target.warning is not None:
        print(checkout_target.warning)

    fetch_result = fetch_checkout_target(target, checkout_target)
    if fetch_result.returncode != 0:
        print(
            f"Status: failed during fetch. "
            f"{render_command_error(f'git fetch {checkout_target.description}', fetch_result)}"
        )
        return False

    canonical_url = build_remote_url(config.clone_protocol, config.canonical_owner, repo.repo)
    if checkout_target.source_label == "preferred" and canonical_url != checkout_target.url:
        add_upstream_remote(target, canonical_url)

    status = determine_update_repo_status(target, checkout_target)
    if status is None:
        return False

    if not update_submodules(target):
        return False

    print(f"Status: {status}; submodules updated.")
    return True


def determine_update_repo_status(target: Path, checkout_target: CheckoutTarget) -> str | None:
    branch_result = run_command(["git", "branch", "--show-current"], cwd=target)
    if branch_result.returncode != 0:
        return (
            f"fetched {checkout_target.description} only. "
            f"{render_command_error('git branch --show-current', branch_result)}"
        )

    branch_name = branch_result.stdout.strip()

    status_result = run_command(["git", "status", "--porcelain"], cwd=target)
    if status_result.returncode != 0:
        return (
            f"fetched {checkout_target.description} only. "
            f"{render_command_error('git status --porcelain', status_result)}"
        )
    if status_result.stdout.strip():
        return (
            f"fetched {checkout_target.description}; working tree is dirty, "
            "skipping checkout alignment"
        )

    actions: list[str] = []
    if branch_name != checkout_target.branch:
        if not checkout_local_branch(target, checkout_target.branch):
            return None
        actions.append(f"checked out {checkout_target.branch}")

    merge_result = run_command(["git", "merge", "--ff-only", "FETCH_HEAD"], cwd=target)
    if merge_result.returncode != 0:
        print(
            f"Status: fetched {checkout_target.description}; fast-forward failed. "
            f"{render_command_error('git merge --ff-only FETCH_HEAD', merge_result)}"
        )
        return None

    if actions:
        actions.append(f"aligned local branch {checkout_target.branch}")
        return f"fetched {checkout_target.description}; " + " and ".join(actions)
    return (
        f"fetched {checkout_target.description} and aligned local branch {checkout_target.branch}"
    )


def update_submodules(target: Path) -> bool:
    result = run_command(["git", "submodule", "update", "--init", "--recursive"], cwd=target)
    if result.returncode != 0:
        print(
            "Status: repository checkout is present, but submodule initialization failed. "
            f"{render_command_error('git submodule update --init --recursive', result)}"
        )
        return False
    return True


def is_git_repo(path: Path) -> bool:
    result = run_command(["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0 and result.stdout.strip() == "true"


def resolve_checkout_target(repo: RepoSpec, config: Config) -> CheckoutTarget | None:
    preferred_url = build_remote_url(config.clone_protocol, repo.preferred_owner, repo.repo)
    canonical_url = build_remote_url(config.clone_protocol, config.canonical_owner, repo.repo)
    preferred_description = f"{repo.preferred_owner}/{repo.repo}@{repo.branch}"
    fallback_description = f"{config.canonical_owner}/{repo.repo}@{config.fallback_branch}"

    if probe_remote_branch(preferred_url, repo.branch, preferred_description, "preferred"):
        return CheckoutTarget(
            url=preferred_url,
            branch=repo.branch,
            description=preferred_description,
            source_label="preferred",
        )

    if probe_remote_branch(
        canonical_url, config.fallback_branch, fallback_description, "fallback"
    ):
        warning = None
        if preferred_description != fallback_description:
            warning = (
                f"Warning: preferred checkout {preferred_description} is unavailable; "
                f"using {fallback_description}."
            )
        return CheckoutTarget(
            url=canonical_url,
            branch=config.fallback_branch,
            description=fallback_description,
            source_label="fallback",
            warning=warning,
        )

    return None


def probe_remote_branch(url: str, branch: str, description: str, label: str) -> bool:
    result = run_command(
        ["git", "ls-remote", "--exit-code", "--heads", url, f"refs/heads/{branch}"]
    )
    if result.returncode == 0:
        print(f"Probe {label}: found {description}")
        return True

    if result.returncode == 2:
        print(f"Probe {label}: missing {description}")
        return False

    detail = result.stderr.strip() or result.stdout.strip() or "not reachable"
    print(f"Probe {label}: unavailable ({detail})")
    return False


def fetch_checkout_target(
    target: Path, checkout_target: CheckoutTarget
) -> subprocess.CompletedProcess[str]:
    return run_command(
        ["git", "fetch", "--no-tags", checkout_target.url, f"refs/heads/{checkout_target.branch}"],
        cwd=target,
    )


def local_branch_exists(target: Path, branch: str) -> bool:
    result = run_command(["git", "rev-parse", "--verify", f"refs/heads/{branch}"], cwd=target)
    return result.returncode == 0


def checkout_local_branch(target: Path, branch: str) -> bool:
    if local_branch_exists(target, branch):
        command = ["git", "checkout", branch]
    else:
        command = ["git", "checkout", "-b", branch, "FETCH_HEAD"]

    result = run_command(command, cwd=target)
    if result.returncode != 0:
        print(f"Status: failed during checkout. {render_command_error(' '.join(command), result)}")
        return False
    return True


def add_upstream_remote(target: Path, url: str) -> None:
    check_result = run_command(["git", "remote", "get-url", "upstream"], cwd=target)
    if check_result.returncode == 0:
        print("Upstream remote already exists.")
        return

    add_result = run_command(["git", "remote", "add", "upstream", url], cwd=target)
    if add_result.returncode != 0:
        print(
            "Upstream remote was not added. "
            f"{render_command_error('git remote add upstream', add_result)}"
        )
        return

    print(f"Added upstream remote: {url}")


def build_remote_url(protocol: str, owner: str | None, repo: str) -> str:
    if not owner:
        raise RuntimeError(f"Missing owner for repository '{repo}'.")
    if protocol == "ssh":
        return f"git@github.com:{owner}/{repo}.git"
    return f"https://github.com/{owner}/{repo}.git"


def run_uv_sync(root: Path, python_version: str) -> None:
    result = run_command(["uv", "sync", "--python", python_version], cwd=root)
    if result.returncode != 0:
        raise RuntimeError(render_command_error("uv sync", result))
    print("uv sync completed.")


def run_command(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def render_command_error(label: str, result: subprocess.CompletedProcess[str]) -> str:
    detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
    return f"{label} failed: {detail}"


if __name__ == "__main__":
    raise SystemExit(main())
