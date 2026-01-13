"""Suite management helpers for creating and configuring systest suites."""

import importlib.metadata
import site
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from .constants import (
    SUITE_CONFIG_FILE,
    SUITE_DEFAULT_CONFIG_CONTENT,
    SUITE_DEFAULT_REQUIREMENTS_CONTENT,
    SUITE_FEATURES_FOLDER,
    SUITE_REQUIREMENTS_FILE,
    SUITE_SUFFIX,
    SUITE_SUPPORT_FOLDER,
)
from .exceptions import PipError, SuiteManagerError

__all__ = ["install_suite_dependencies", "create_suite"]


def _call_pip(args: List[str], verbose: bool = False) -> None:
    """
    Executes a pip command via subprocess and handles standard errors.

    Args:
        args (List[str]): List of arguments to pass to pip.
        verbose (bool): If True, prints the stdout of the pip command.

    Raises:
        PipError: If pip command fails or pip executable is not found.
    """
    try:
        # sys.executable ensures the correct environment is used
        pip_cmd = [sys.executable, "-m", "pip"]

        # Run the command. 'check=True' ensures a CalledProcessError is raised
        # if pip returns a non-zero exit code (i.e., installation failed).
        result = subprocess.run(args=pip_cmd + args, check=True, capture_output=True, text=True)
        if verbose:
            print(result.stdout.strip())

    except FileNotFoundError as e:
        # pip3 executable not found in PATH
        raise PipError(
            "Error: 'pip3' command not found. Ensure Python 3 and pip 3 are installed "
            "and accessible in your environment PATH."
        ) from e
    except subprocess.CalledProcessError as e:
        # This occurs if pip failed to resolve or install dependencies.
        print("\n--- ERROR ---")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"Return Code: {e.returncode}")
        print("STDOUT:")
        print(e.stdout)
        print("STDERR:")
        print(e.stderr)

        raise PipError("Pip 3 failed performing the request. Check logs above.") from e


def _is_empty_or_only_comments(file_path: Path) -> bool:
    """
    Checks if a file is empty or if all non-empty lines start with '#'.

    Args:
        file_path (Path): The path to the file to check.

    Returns:
        bool: True if the file is empty or contains only comments, False otherwise.
    """
    with open(file_path, "r") as f:
        for line in f:
            stripped_line = line.strip()
            if stripped_line and not stripped_line.startswith("#"):
                return False
        return True


def _parse_packages(lib_path: str) -> Iterator[Tuple[str, str]]:
    """Yield package names and versions from the lib path and sys.path.

    Args:
        lib_path (str): Path to local library folder.

    Yields:
        Tuple[str, str]: Package name and version string.
    """
    # lib_path highest priority, sys.path fallback
    for dist in importlib.metadata.distributions(path=[lib_path] + sys.path):
        key_map = {k.lower(): k for k in dist.metadata}
        if "name" in key_map:
            yield dist.metadata[key_map["name"]], dist.version


def _parse_requirement_file(requirements_file: Path) -> Iterator[Requirement]:
    """Yield parsed Requirement entries from a requirements.txt file.

    Args:
        requirements_file (Path): Path to requirements.txt.

    Yields:
        Requirement: Parsed requirement entries.
    """
    with open(requirements_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                yield Requirement(line)


def _is_requirements_satisfied(requirements_file: Path, lib_path: str) -> bool:
    """
    Checks if all requirements in the file are satisfied by the packages
    in the lib_path or system path without installing them.

    Args:
        requirements_file (Path): Path to requirements.txt.
        lib_path (str): Path to local library folder.

    Returns:
        bool: True if all requirements are satisfied, False otherwise.
    """
    available_versions: Dict[str, str] = {}
    for name, version in _parse_packages(lib_path):
        key = canonicalize_name(name)
        if key not in available_versions:
            available_versions[key] = version

    for req in _parse_requirement_file(requirements_file):
        if req.marker and not req.marker.evaluate():
            return False

        key = canonicalize_name(req.name)
        if key not in available_versions:
            return False

        if req.specifier and not req.specifier.contains(available_versions[key], prereleases=True):
            return False

    return True


def install_suite_dependencies(lib_path: Path, requirements_file: Path = None, verbose: bool = False) -> None:
    """
    Installs the Python dependencies declared in the target test suite's requirements file
    into a local directory within the suite folder. It then adds this directory to sys.path
    to make dependencies immediately available to the current process.

    Args:
        lib_path (Path): The directory path where dependencies should be installed (e.g., suite/.lib).
        requirements_file (Path, optional): The path to the requirements.txt file.
        verbose (bool): If True, provides detailed output during installation checks.

    Raises:
        PipError: If the 'pip' command fails.
    """
    # Define local lib path inside the suite
    lib_path_str = str(lib_path.resolve())

    # Validation Checks
    if requirements_file is None or not requirements_file.is_file() or _is_empty_or_only_comments(requirements_file):
        if verbose:
            if requirements_file is None:
                print("Skipping: requirements file not found in the Test Suite.")
            elif not requirements_file.is_file():
                print(f"Skipping: {requirements_file.name!r} not found in the Test Suite.")
            else:
                print(f"Skipping: The Test Suite's {requirements_file.name!r} file is empty or comments only.")
        return

    print("Checking Test Suite dependencies...")

    if _is_requirements_satisfied(requirements_file, lib_path_str):
        print("Dependencies already satisfied.")
    else:
        print("Installing dependencies...")

        _call_pip(
            [
                "install",
                "--upgrade",
                "--upgrade-strategy",
                "only-if-needed",
                "-r",
                str(requirements_file),
                "--target",
                lib_path_str,
            ],
            verbose,
        )

        print(f"Dependencies successfully installed to {lib_path_str!r}.")

    # Inject into path for CURRENT process so imports work immediately
    # We do this AFTER install to ensure we load the newly installed versions if any
    site.addsitedir(lib_path_str)
    if lib_path_str not in sys.path:
        sys.path.insert(0, lib_path_str)
        if verbose:
            print(f"Added {lib_path_str!r} to system path.")


def create_suite(suite_name: str, suites_path: Path) -> None:
    """
    Creates a new, empty test suite directory structure with necessary manifest files.

    Args:
        suite_name (str): The name of the test suite (e.g., 'r2d2-4.0.0').
        suites_path (Path): The root directory where test suites are located.

    Raises:
        SuiteManagerError: If the Test Suite directory already exists.
    """
    if not suite_name.endswith(SUITE_SUFFIX):
        suite_name = f"{suite_name}{SUITE_SUFFIX}"

    suite_path = suites_path / suite_name

    if suite_path.exists():
        raise SuiteManagerError(f"The Test Suite already exists: {str(suite_path)!r}")

    # Create mandatory suite directories
    (suite_path / SUITE_FEATURES_FOLDER).mkdir(parents=True)
    (suite_path / SUITE_SUPPORT_FOLDER).mkdir()

    # Create and Populate Placeholder Files
    with open(suite_path / SUITE_CONFIG_FILE, "w") as f:
        f.write(SUITE_DEFAULT_CONFIG_CONTENT)

    with open(suite_path / SUITE_REQUIREMENTS_FILE, "w") as f:
        f.write(SUITE_DEFAULT_REQUIREMENTS_CONTENT)

    (suite_path / SUITE_SUPPORT_FOLDER / "__init__.py").touch()

    print(f"Successfully created new Test Suite: {str(suite_path)!r}")
