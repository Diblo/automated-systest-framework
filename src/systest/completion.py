from argparse import Namespace
import os
from pathlib import Path
from typing import List, Optional

import argcomplete
from behave.configuration import COLOR_CHOICES


from .systest_behave.configuration import auto_discover, load_configuration, Parser
from .suite_manager import create_suite_data
from .constants import SUITE_SUFFIX
from .exceptions import SuiteManagerError


def is_argcomplete_request() -> bool:
    """Detect whether the current invocation is triggered by argcomplete.

    Argcomplete sets the environment variable `_ARGCOMPLETE` when it invokes
    the program to request completion candidates.

    Returns:
        bool: True if argcomplete is active, otherwise False.
    """
    return "_ARGCOMPLETE" in os.environ


def _effective_suites_dir(parsed_args: Namespace) -> Path:
    """Resolve the effective suites directory used for completion.

    Resolution order (highest to lowest precedence):
        1. CLI argument `--suites-dir`
        2. Environment variables and config files (via load_environment_settings)
        3. Fallback to current working directory

    Args:
        parsed_args (Namespace): Parsed argparse namespace, including injected
        `_command_args` during completion.

    Returns:
        Path: The resolved suites directory.
    """
    # 1) CLI overrides
    suites_dir = getattr(parsed_args, "suites_directory", None)
    if isinstance(suites_dir, Path):
        return suites_dir
    if isinstance(suites_dir, str) and suites_dir.strip():
        return Path(suites_dir)

    # 2) ENV/config
    command_args: List[str] = getattr(parsed_args, "_command_args", [])
    cli_cfg, _ = auto_discover(command_args)
    defaults = load_configuration(cli_cfg, verbose=False)

    value = defaults.get("suites_directory", None)
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value.strip():
        return Path(value)

    # 3) fallback
    return Path.cwd()


def _listdir(path: Path, prefix: str) -> List[str]:
    """List subdirectories under a path that match a given prefix.

    Returned paths are relative to `path`.

    Args:
        path (Path): Base directory to list.
        prefix (str): Prefix to filter directory paths.

    Returns:
        List[str]: Matching directory paths relative to `path`.
    """
    return sorted(set([str(child.relative_to(path)) for child in path.iterdir()
                       if child.is_dir() and str(child.absolute()).startswith(prefix)]))


def complete_suites_directory(prefix: str, **_) -> List[str]:
    """Autocomplete values for the `--suites-dir` option.

    Args:
        prefix (str): Current completion prefix.

    Returns:
        List[str]: Matching directory paths.
    """
    return _listdir(Path.cwd(), prefix)


def complete_suite(prefix: str, parsed_args: Namespace, **_) -> List[str]:
    """Autocomplete available test suite names.

    Suite directories are resolved from the effective suites directory and
    returned without the configured suite suffix.

    Args:
        prefix (str): Current completion prefix.
        parsed_args (Namespace): Parsed argparse namespace.

    Returns:
        List[str]: Matching suite names.
    """
    suites_dir = _effective_suites_dir(parsed_args)
    if not suites_dir.is_dir():
        return []
    return sorted(set([p.name.removesuffix(SUITE_SUFFIX) for p in suites_dir.iterdir()
                       if p.is_dir() and p.name.startswith(prefix) and p.name.endswith(SUITE_SUFFIX)]))


def complete_paths(prefix: str, parsed_args: Namespace, **_) -> List[str]:
    """Autocomplete feature paths within the selected test suite.

    Completion is performed relative to the suite's configured features
    directory.

    Args:
        prefix (str): Current completion prefix.
        parsed_args (Namespace): Parsed argparse namespace.

    Returns:
        List[str]: Matching feature directories or files.
    """
    suite: Optional[str] = getattr(parsed_args, "suite", None)
    if not suite:
        return []

    suites_dir = _effective_suites_dir(parsed_args)

    try:
        suite_data = create_suite_data(suite, suites_dir)
    except SuiteManagerError:
        return []

    if not suite_data.suite_exists() or not suite_data.features_path.is_dir():
        return []

    # prefix is relative to features folder
    return _listdir(suite_data.features_path, prefix)


def complete_color(prefix: str, **_) -> List[str]:
    """Autocomplete valid color values for the `--color` option.

    Args:
        prefix (str): Current completion prefix.

    Returns:
        List[str]: Matching color values.
    """
    return [color for color in COLOR_CHOICES if color.startswith(prefix)]


def autocomplete(command_args: List[str]) -> None:
    """Handle argcomplete-based shell completion.

    This function sets up the argument parser, binds completion callbacks
    to relevant arguments, and invokes argcomplete. It must be executed
    before the normal application bootstrap to avoid side effects such
    as suite validation or dependency installation.

    Args:
        command_args (List[str]): Raw command-line arguments passed to the program.
    """
    parser = Parser().parser

    # Bind completers by walking argparse actions
    for action in parser._actions:  # type: ignore[attr-defined]
        dest = getattr(action, "dest", None)

        if dest == "suite":
            action.completer = complete_suite  # type: ignore[attr-defined]
        elif dest == "suites_directory":
            action.completer = complete_suites_directory # type: ignore[attr-defined]
        elif dest == "paths":
            action.completer = complete_paths  # type: ignore[attr-defined]
        elif dest == "color":
            action.completer = complete_color  # type: ignore[attr-defined]

    # Needed so completers can access original args if desired
    parser.set_defaults(_command_args=command_args)

    argcomplete.autocomplete(parser)
    parser.parse_args(command_args)
