"""Runner for executing systest with behave."""

import glob
import os
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

from behave.exception import ConfigError
from behave.formatter._registry import make_formatters as behave_make_formatters
from behave.formatter.base import StreamOpener
from behave.model_type import FileLocation as BehaveFileLocation
from behave.pathutil import select_subdirectories
from behave.runner import Context, ModelRunner, parse_features
from behave.runner_util import exec_file, load_step_modules, reset_runtime

from .configuration import Configuration
from .wrapper import FormatterWrapper, ReporterWrapper

__all__ = ["SystestRunner"]


def iter_make_paths(path: str, base_path: Path) -> Iterator[Tuple[str, Tuple[Path, Optional[int]]]]:
    """Resolve a single path string into absolute file paths.

    Args:
        path (str): Input path string (e.g., 'features/foo.feature:10' or 'features/*.feature').
        base_path (Path): Canonical root directory for relative path resolution.

    Yields:
        Tuple[str, Tuple[Path, Optional[int]]]: Original path and resolved path/line.
    """
    # Separate the path/glob string from the optional line number suffix.
    path_str, *line_part = path.split(":", 1)
    if line_part:
        if not line_part[0].isdigit() or int(line_part[0]) < 0:
            raise ConfigError(
                f"Invalid format for file path and line number: '{path!r}'. "
                f"Line number part {line_part[0]!r} must be a positive integer."
            )
        line_number = int(line_part[0])
    else:
        line_number = None

    # Determine the search root.
    if Path(path_str).is_absolute():
        # Resolve absolute paths using glob from the file system root.
        search_root = Path("/")
    else:
        # Resolve relative paths using glob from the canonical features root.
        search_root = base_path

    if glob.has_magic(path_str):
        # If it contains wildcards, use glob for pattern matching.
        for resolved_path in search_root.glob(path_str):
            yield (path, (resolved_path.absolute(), line_number))
    else:
        # Optimization: No wildcards, so resolve the path directly.
        resolved_path = search_root / path_str
        yield (path, (resolved_path.absolute(), line_number))


def iter_paths(paths: List[str], base_path: Path) -> Iterator[Tuple[str, Tuple[Path, Optional[int]]]]:
    """Iterate over paths, supporting globs and @files.

    Args:
        paths (List[str]): List of path strings.
        base_path (Path): Canonical root directory for relative path resolution.

    Yields:
        Tuple[str, Tuple[Path, Optional[int]]]: Original path and resolved path/line.
    """
    for path_str in paths:
        if path_str.startswith("@"):
            filename = path_str[1:]

            if not os.path.isfile(filename):
                raise FileNotFoundError(f"Config file not found: {filename!r}")

            # NOTE: Added explicit encoding to match expected file handling.
            with open(filename, encoding="utf-8") as f:
                content: str = f.read()

            for line in content.splitlines():
                line_stripped = line.strip()
                # Skip empty lines and lines starting with '#'
                if line_stripped and not line_stripped.startswith("#"):
                    yield from iter_make_paths(line_stripped, base_path)
        else:
            yield from iter_make_paths(path_str, base_path)


class FileLocation(BehaveFileLocation):
    """
    A minimal extension of the Behave FileLocation class to make it hashable, allowing
    its use in a set for feature collection.
    """

    def __hash__(self) -> int:
        """Compute a hash based on filename and line."""
        return hash((self.filename, self.line))


def resolve_feature(path: Path, line_number: Optional[int]) -> List[FileLocation]:
    """Resolve a path to feature file locations based on file type.

    Args:
        path (Path): Resolved absolute path (file or directory).
        line_number (Optional[int]): Optional line number.

    Returns:
        List[FileLocation]: Feature file locations found.
    """
    if path.is_dir():
        # RULE 1: Directory targets (e.g., 'foo_bar_initialization/')
        # Collects all *.feature files within that directory.
        return [FileLocation(str(feature), line_number) for feature in path.glob("*.feature")]

    if path.is_file() and path.suffix == ".feature":
        # RULE 2: Feature file targets (e.g., 'foo_bar_initialization/test.feature')
        return [FileLocation(str(path), line_number)]

    # If not a directory or a feature file, return empty.
    return []


def make_formatters(config: Configuration, stream_openers: StreamOpener) -> List[FormatterWrapper]:
    """Build a list of formatters for the behave runner.

    Args:
        config (Configuration): Configuration object to use.
        stream_openers (StreamOpener): Stream openers for formatter outputs.

    Returns:
        list[FormatterWrapper]: Wrapped formatter instances.
    """
    # Wrap formatters to prevent premature 'close' calls
    return [FormatterWrapper(formatter) for formatter in behave_make_formatters(config, stream_openers)]


class SystestRunner(ModelRunner):
    """
    A custom runner extending Behave's ModelRunner to support test execution across
    multiple 'feature area folders'. It iteratively loads environment hooks and
    step definitions for each area, ensuring path and state context is correct.
    """

    config: Configuration
    """Systest configuration instance."""

    def __init__(self, config: Configuration):
        """Initialize the runner with a configuration instance.

        Args:
            config (Configuration): Systest configuration instance.
        """
        super().__init__(config)

        # Features are loaded per-area during run(), so this list is unused by this runner.
        self.features = []
        self.original_paths: List[str] = []
        self.feature_locations: Dict[str, List[FileLocation]] = {}

    def load_hooks(self, feature_area_path: Path) -> None:
        """Load the environment file (e.g., 'environment.py') for a feature area.

        Args:
            feature_area_path (Path): Absolute path to the feature area folder.
        """
        self.hooks = {}
        hooks_path: Path = feature_area_path / self.config.environment_file
        if hooks_path.is_file():
            exec_file(hooks_path, self.hooks)

    def load_step_definitions(self, feature_area_path: Path) -> None:
        """Load step definition modules for a feature area.

        Args:
            feature_area_path (Path): Absolute path to the feature area folder.
        """
        steps_dir: Path = feature_area_path / self.config.steps_dir

        step_paths = [steps_dir]
        if self.config.use_nested_step_modules:
            print("USE_NESTED_STEP_MODULES: yes")
            step_paths.extend(select_subdirectories(steps_dir))

        reset_runtime()
        load_step_modules(step_paths)

    def collect_feature_locations(self) -> Dict[str, List[FileLocation]]:
        """Collect and group feature files by feature area folder.

        Returns:
            Dict[str, List[FileLocation]]: Feature area names mapped to locations.
        """
        grouped_feature_files: Dict[str, Set[str]] = {}
        paths = self.config.paths[:]
        features_path = self.config.suite_data.features_path.absolute()

        if not paths:
            if self.config.verbose:
                print("No path specified, uses '*' for all features")
            paths.append("*")
        elif self.config.verbose:
            print("Supplied path:", ", ".join(f"{p!r}" for p in paths))

        for path, (resolved_path, line_number) in iter_paths(paths, features_path):
            # Existence Check (Ensures the file/directory actually exists)
            if not resolved_path.exists():
                if self.config.verbose:
                    print(f"Skipping {str(resolved_path)!r}. File or directory not found. Resolved from {path!r}")
                continue

            # Validate path is inside the features directory and determine the feature area name for grouping
            # NOTE: Validation is important as it will create problems if features are mixed between Test Suites.
            try:
                # Get path relative to the suite's features root (features_path)
                relative_path = resolved_path.relative_to(features_path)

                # Skip if the path resolves exactly to the features root itself.
                # NOTE: This shouldn't be possible. But to be on the safe side, we check if it occurs.
                # NOTE: Maybe an error should be raised instead.
                if not relative_path.parts:
                    if self.config.verbose:
                        print(f"Skipping: Path {str(resolved_path)!r} resolved to the Test Suite's feature directory.")
                    continue

                # Determine the feature area name (the first component after the features root)
                feature_area_folder = relative_path.parts[0]
            except ValueError as e:
                # Path resolves outside the feature directory. This is a hard error.
                if self.config.verbose:
                    print(
                        f"ERROR: The path {str(resolved_path)!r} is not path to a subfolder or subfile "
                        f"in the Test Suite's feature directory: {str(features_path)!r}. "
                        f"Resolved from {path!r}"
                    )
                raise ConfigError(
                    f"Path {str(resolved_path)!r} is not inside the Test Suite's "
                    f"feature directory: {str(features_path)!r}"
                ) from e

            resolved_feature_files = [
                filename
                for filename in resolve_feature(resolved_path, line_number)
                if not self.config.exclude(filename)
            ]

            if not resolved_feature_files:
                if self.config.verbose:
                    print(f"Skipping {str(resolved_path)!r}. No feature files. Resolved from {path!r}")
                continue

            # Group collected feature file locations by the feature area folder name
            grouped_feature_files.setdefault(feature_area_folder, set()).update(resolved_feature_files)

        # Finalization: Convert the dictionary of sets to a dictionary of sorted lists.
        return {area_name: sorted(list(feature_set)) for area_name, feature_set in grouped_feature_files.items()}

    def setup(self) -> None:
        """Initialize runner state before execution begins."""
        self.original_paths = self.config.paths[:]

        # Resolve features and group them by feature area
        self.feature_locations = self.collect_feature_locations()

        if not self.feature_locations:
            if self.config.verbose:
                print('ERROR: Could not find any "<name>.feature" files.')
            raise ConfigError("No feature files found.")

        self.context = Context(self)
        self.config.setup_logging()
        self.formatters = make_formatters(self.config, self.config.outputs)

    def finish(self) -> None:
        """Clean up runner state after execution."""
        # Ensuring formatters and reporters are properly closed
        for formatter in self.formatters:
            if isinstance(formatter, FormatterWrapper):
                formatter.done()

        for reporter in self.config.reporters:
            if isinstance(reporter, ReporterWrapper):
                reporter.done()

        # Restore the original input paths
        self.config.paths = self.original_paths

    def run(self) -> int:
        """Runs features, iterating over groups defined by feature area folders.

        For each feature area, the runner state (base directory, steps, hooks) is
        reloaded to ensure correct path resolution and isolation.

        Returns:
            int: Status code (0=success or 1=failure).
        """
        # NOTE: The default behave runner is designed for a single base directory, which it uses
        #       to locate all steps and the environment file (`environment.py`). Running features
        #       from multiple feature area folders breaks this mechanism because the runner state
        #       (specifically `self.config.base_dir` and `self.config.paths`) becomes ambiguous,
        #       leading to incorrect loading of area-specific resources (steps, hooks, etc.).
        self.setup()

        # Iterate over paths grouped by feature area.
        failed = 0
        for feature_area_name in self.feature_locations:
            if self.run_feature_area(feature_area_name) > 0:
                failed = 1
                if self.config.stop:
                    break

            if self.aborted:
                break

        self.finish()

        return failed

    def run_feature_area(self, name: str) -> int:
        """Execute all features belonging to a single feature area folder.

        Args:
            name (str): Feature area folder name (e.g., 'foo_bar_initialization').

        Returns:
            int: Status code (0=success or 1=failure).
        """
        feature_area_path = (self.config.suite_data.features_path / name).absolute()

        # -- STEP: Sets the context for path resolution
        self.config.base_dir = str(feature_area_path)
        self.config.paths = [self.config.base_dir]

        # -- STEP: (Re)Loads hooks and step definitions specific to this path
        self.load_hooks(feature_area_path)
        self.load_step_definitions(feature_area_path)

        # -- STEP: Parse features specific to this area
        features = parse_features(self.feature_locations[name], language=self.config.lang)

        # -- STEP: Run all features
        return self.run_model(features)
