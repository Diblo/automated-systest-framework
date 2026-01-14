"""Shell completion helpers for the systest CLI."""

import os
import traceback
from argparse import Namespace
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import argcomplete

from .constants import SUITE_SUFFIX
from .exceptions import SuiteManagerError
from .suite_manager import SuiteData, create_suite_data
from .systest_behave.configuration import Configuration, auto_discover, load_environment_settings, setup_main_parser
from .types import DefaultValues
from .utils import run_from_source

_COLOR_DESCRIPTIONS = {
    "auto": "Automatically decide based on terminal support.",
    "on": "Force color output on.",
    "off": "Force color output off.",
}
# Intentionally mirrors Behave color choices, excluding "always"/"never".

_LOG_LEVEL_DESCRIPTIONS = {
    "CRITICAL": "Severe errors; may cause program to stop.",
    "FATAL": "Alias for CRITICAL.",
    "ERROR": "Errors that prevent some functions from working.",
    "WARN": "Alias for WARNING.",
    "WARNING": "Potential issues and recoverable problems.",
    "INFO": "General informational messages.",
    "DEBUG": "Verbose debugging output.",
    "NOTSET": "Use the root logger level.",
}


def _debug(message: str) -> None:
    """Append debug messages to the argcomplete log when running from source.

    Args:
        message (str): Debug message to append.
    """
    if run_from_source():
        log_path = (Path(__file__).parent / ".." / ".." / "systest-argcomplete.debug.log").resolve()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(message)
            f.write("\n")


def is_argcomplete_request() -> bool:
    """Detect whether the current invocation is triggered by argcomplete.

    Argcomplete sets the environment variable `_ARGCOMPLETE` when it invokes
    the program to request completion candidates.

    Returns:
        bool: True if argcomplete is active, otherwise False.
    """
    return "_ARGCOMPLETE" in os.environ


def _resolve_suites_path(parsed_args: Namespace) -> Optional[Path]:
    """Resolve the suites directory used for completion.

    Args:
        parsed_args (Namespace): Parsed argparse namespace

    Returns:
        Optional[Path]: Resolved suites directory.
    """
    suites_path = getattr(parsed_args, "suites_directory", None)
    if isinstance(suites_path, str) and suites_path.strip():
        suites_path = Path(suites_path.strip())

    if not isinstance(suites_path, Path) or not suites_path.is_dir():
        return None

    return suites_path.resolve()


def _list_dirs(path: Path, prefix: str) -> List[Path]:
    """List directories in a path that match a prefix.

    Args:
        path (Path): Directory to scan.
        prefix (str): Name prefix to filter on.

    Returns:
        List[Path]: Matching directory paths.
    """
    return sorted(p for p in path.iterdir() if p.is_dir() and p.name.startswith(prefix))


def _list_feature_files(path: Path, prefix: str) -> List[Path]:
    """List feature files in a path that match a prefix.

    Args:
        path (Path): Directory to scan.
        prefix (str): Filename prefix to filter on.

    Returns:
        List[Path]: Matching feature file paths.
    """
    return sorted(f for f in path.glob("*.feature") if f.name.startswith(prefix))


def _resolve_path_from_prefix(
    abs_features_path: Path, prefix: str
) -> Optional[Tuple[Path, Optional[str], Optional[str]]]:
    """Resolve a prefix into a root and up to two path segments.

    Args:
        abs_features_path (Path): Absolute path to the features folder.
        prefix (str): Current completion prefix.

    Returns:
        Optional[Tuple[Path, Optional[str], Optional[str]]]: Root path and optional
        feature area/file segments, or None if the prefix is unrelated.
    """
    prefix_path = Path(prefix) if prefix else Path()
    if prefix_path.is_absolute():
        abs_prefix_path = prefix_path.resolve()
        root = abs_features_path

        # allow partial segment matches (e.g., "/foo/bar" snaps to "/foo/bar2").
        if str(abs_features_path).startswith(prefix):
            abs_prefix_path = abs_features_path
    else:
        abs_prefix_path = (abs_features_path / prefix_path).resolve()
        root = Path()

    try:
        # get the relative parts to features path, if any
        relative_path = abs_prefix_path.relative_to(abs_features_path)
    except ValueError:
        # the prefix path must be within the features path
        return None

    # relative_path can consist of a maximum of one feature area and one feature file
    # <feature_area>/<file>.feature.
    if len(relative_path.parts) > 2:
        return None

    # extract the feature area and feature file
    def get(the_list: Tuple[str, ...], i: int) -> Optional[str]:
        try:
            return the_list[i]
        except IndexError:
            return None

    feature_area = get(relative_path.parts, 0)
    feature_file = get(relative_path.parts, 1)

    return root, feature_area, feature_file


def _resolve_suite_data(parsed_args: Namespace) -> Optional[SuiteData]:
    """Resolve SuiteData from parsed args.

    Args:
        parsed_args (Namespace): Parsed argparse namespace.

    Returns:
        Optional[SuiteData]: SuiteData for the requested suite, if available.
    """
    suite: Optional[str] = getattr(parsed_args, "suite", None)
    if suite:
        suites_dir = _resolve_suites_path(parsed_args)
        if suites_dir:
            try:
                return create_suite_data(suite, suites_dir)
            except SuiteManagerError:
                pass
    return None


def complete_suite(prefix: str, parsed_args: Namespace, **_: object) -> List[str]:
    """Autocomplete values for the `-s` or `--suite` option.

    Suite directories are resolved from the effective suites directory and
    returned without the configured suite suffix.

    Args:
        prefix (str): Current completion prefix.
        parsed_args (Namespace): Parsed argparse namespace.

    Returns:
        List[str]: Matching suite names.
    """
    suites_path = _resolve_suites_path(parsed_args)
    if not suites_path:
        return []

    return sorted(
        {p.name[: -len(SUITE_SUFFIX)] for p in _list_dirs(suites_path, prefix=prefix) if p.name.endswith(SUITE_SUFFIX)}
    )


def complete_paths(prefix: str, parsed_args: Namespace, **_: object) -> List[str]:
    """Autocomplete feature paths within the selected test suite.

    Completion is performed relative to the suite's configured features
    directory.

    Args:
        prefix (str): Current completion prefix.
        parsed_args (Namespace): Parsed argparse namespace.

    Returns:
        List[str]: Matching feature directories or files.
    """
    # _debug(f"prefix={prefix}")
    # _debug(f"parsed_args={parsed_args}")

    # Resolve suite context first.
    suite_data = _resolve_suite_data(parsed_args)
    if not suite_data or not suite_data.features_path.is_dir():
        return []

    # Resolve prefix into absolute/relative paths rooted at the features folder.
    abs_features_path = suite_data.features_path.resolve()
    resolved_prefix = _resolve_path_from_prefix(abs_features_path, prefix)
    if resolved_prefix is None:
        return []

    root, feature_area, feature_file = resolved_prefix

    # Collect folders or feature files.
    results: List[str] = []

    # If we have a feature area directory and a trailing slash, target files.
    if (
        feature_area is None
        or not (abs_features_path / feature_area).is_dir()
        or (feature_file is None and not prefix.endswith(os.sep))
    ):
        # Feature area suggestions (top-level) or partial matches.
        search_prefix = feature_area or ""

        results = sorted(
            str(root / p.name) + os.sep
            for p in _list_dirs(abs_features_path, prefix=search_prefix)
            if any(p.glob("*.feature"))
        )

    # We are looking for a file if we do not already have a file.
    elif feature_file is None or not (abs_features_path / feature_area / feature_file).is_file():
        # Suggest feature files with optional prefix.
        search_prefix = feature_file or ""

        results = sorted(
            str(root / feature_area / f.name)
            for f in _list_feature_files(abs_features_path / feature_area, prefix=search_prefix)
        )

    return results


def complete_color(prefix: str, **_: object) -> Dict[str, str]:
    """Autocomplete valid color values for the `--color` option.

    Args:
        prefix (str): Current completion prefix.

    Returns:
        Dict[str, str]: Matching color values mapped to descriptions.
    """
    return {name: description for name, description in _COLOR_DESCRIPTIONS.items() if name.startswith(prefix)}


def complete_logging_level(prefix: str, **_: object) -> Dict[str, str]:
    """Autocomplete valid logging levels for `--logging-level`.

    Args:
        prefix (str): Current completion prefix.

    Returns:
        Dict[str, str]: Matching logging level names mapped to descriptions.
    """
    return {name: description for name, description in _LOG_LEVEL_DESCRIPTIONS.items() if name.startswith(prefix)}


def autocomplete(command_args: List[str]) -> None:
    """Handle argcomplete-based shell completion.

    This function sets up the argument parser, binds completion callbacks
    to relevant arguments, and invokes argcomplete. It must be executed
    before the normal application bootstrap to avoid side effects such
    as suite validation or dependency installation.

    Args:
        command_args (List[str]): Raw command-line arguments passed to the program.
    """
    defaults: DefaultValues = Configuration.make_defaults()
    cli_cfg, _ = auto_discover(command_args)
    load_environment_settings(defaults, cli_cfg, verbose=False)

    parser = setup_main_parser()
    parser.set_defaults(**defaults)

    # Bind completers by walking argparse actions
    for action in parser._actions:  # pylint: disable=protected-access
        dest = getattr(action, "dest", None)

        if dest == "suite":
            action.completer = complete_suite  # type: ignore[attr-defined]
        elif dest == "paths":
            action.completer = complete_paths  # type: ignore[attr-defined]
        elif dest == "color":
            action.completer = complete_color  # type: ignore[attr-defined]
        elif dest == "logging_level":
            action.completer = complete_logging_level  # type: ignore[attr-defined]

    try:
        argcomplete.autocomplete(parser, always_complete_options=False)
        parser.parse_args(command_args)
    except Exception:
        _debug(f"{traceback.format_exc()}")
        raise
