import site
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple, Optional, Union, cast
from dotenv import dotenv_values
import pkg_resources
from packaging.version import InvalidVersion

from .utils import parse_version
from .constants import (
    SUITE_CONFIG_FILE,
    SUITE_DEFAULT_CONFIG_CONTENT,
    SUITE_DEFAULT_REQUIREMENTS_CONTENT,
    SUITE_FEATURES_FOLDER,
    SUITE_LIB_FOLDER,
    SUITE_REQUIREMENTS_FILE,
    SUITE_SUFFIX,
    SUITE_SUPPORT_FOLDER,
    VERSION,
)
from .exceptions import PipError, SuiteManagerError

__all__ = ["install_suite_dependencies", "create_suite"]


class SuiteConfig(NamedTuple):
    framework_version: str = ""
    features_folder: str = ""
    support_folder: str = ""


def parse_suite_conf(file_path: Path) -> SuiteConfig:
    """Parses a .systestrc file.

    Args:
        file_path: The Path object pointing to the configuration file (.systestrc).

    Returns:
        A SuiteConfig instance populated with settings from the file or defaults.
    """
    if file_path.is_file():
        loaded_config = cast(dict[str, str], dotenv_values(file_path)) or {}
    else:
        loaded_config = {}

    sanitized_config: dict[str, str] = {
        "framework_version": VERSION,
        "features_folder": SUITE_FEATURES_FOLDER,
        "support_folder": SUITE_SUPPORT_FOLDER,
    }
    sanitized_config.update(loaded_config)

    version = sanitized_config["framework_version"]
    try:
        parse_version(version)
    except InvalidVersion as e:
        raise SuiteManagerError(
            f"The specified framework_version in {str(file_path)!r} is invalid: {version!r}"
        ) from e

    return SuiteConfig(**sanitized_config)


class SuiteData(NamedTuple):
    name: str = ""
    suite: str = ""
    path: Path = Path()
    features_path: Path = Path()
    support_path: Path = Path()
    requirements_file: Path = Path()
    lib_path: Path = Path()
    run_version: str = ""

    def suite_exists(self) -> bool:
        return self.path.is_dir()

    def suite_is_valide(self) -> bool:
        return self.features_path.is_dir() and self.support_path.is_dir()


def create_suite_data(suite_name: str, suites_directory: Union[str, Path]) -> SuiteData:
    """
    Creates and returns a SuiteData object populated with paths and data
    related to the specified test suite.

    Args:
        suite_name (str): The name of the test suite.
        suites_directory (Union[str, Path]): The root directory where test suites are located.

    Returns:
        SuiteData: An object containing paths and data for the test suite.
    """
    if suite_name.endswith(SUITE_SUFFIX):
        suite_name = suite_name.removesuffix(SUITE_SUFFIX)

    if isinstance(suites_directory, str):
        suites_directory = Path(suites_directory)

    suite_path = suites_directory / f"{suite_name}{SUITE_SUFFIX}"

    if suite_path.name != f"{suite_name}{SUITE_SUFFIX}":
        raise SuiteManagerError(f"The specified Test Suite name is invalid: {suite_name!r}")

    suite_config = parse_suite_conf(suite_path / SUITE_CONFIG_FILE)

    return SuiteData(
        name=suite_name,
        suite=suite_path.name,
        path=suite_path,
        features_path=suite_path / suite_config.features_folder,
        support_path=suite_path / suite_config.support_folder,
        requirements_file=suite_path / SUITE_REQUIREMENTS_FILE,
        lib_path=suite_path / SUITE_LIB_FOLDER,
        run_version=suite_config.framework_version,
    )


def has_requirements(requirements_file: Path) -> bool:
    if not requirements_file.is_file():
        return False

    with open(requirements_file, "r") as f:
        for line in f:
            stripped_line = line.strip()
            if stripped_line and not stripped_line.startswith("#"):
                return False
        return True


def is_requirements_satisfied(requirements_file: Path, lib_path: Path) -> bool:
    """
    Checks if all requirements in the file are satisfied by the packages
    in the lib_path or system path without installing them.

    Args:
        requirements_file (Path): Path to requirements.txt.
        lib_path (Path): Path to local library folder.

    Returns:
        bool: True if all requirements are satisfied, False otherwise.
    """
    lib_path_str = str(lib_path)

    # Create a WorkingSet that includes the target .lib directory
    # This allows us to "simulate" the environment to see if packages exist there
    ws = pkg_resources.WorkingSet([lib_path_str] + sys.path)

    with open(requirements_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                # require() raises DistributionNotFound or VersionConflict if not satisfied
                ws.require(line)
            except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
                return False
    return True


def install_suite_dependencies(requirements_file: Path, lib_path: Path, verbose: Optional[bool] = False) -> None:
    """
    Installs the Python dependencies declared in the target test suite's requirements file
    into a local directory within the suite folder. It then adds this directory to sys.path
    to make dependencies immediately available to the current process.

    Args:
        requirements_file (Path): The path to the requirements.txt file.
        lib_path (Path): The directory path where dependencies should be installed (e.g., suite/.lib).
        verbose (bool): If True, provides detailed output during installation checks.

    Raises:
        PipError: If the 'pip' command fails.
    """
    lib_path_str = str(lib_path)

    print("Installing dependencies...")

    try:
        # sys.executable ensures the correct environment is used
        args = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--upgrade-strategy",
            "only-if-needed",
            "-r",
            str(requirements_file),
            "--target",
            lib_path_str
        ]

        # Run the command. 'check=True' ensures a CalledProcessError is raised
        # if pip returns a non-zero exit code (i.e., installation failed).
        result = subprocess.run(args=args, check=True, capture_output=True, text=True)
        if verbose:
            print(result.stdout.strip())
    except FileNotFoundError as e:
        # pip3 executable not found in PATH
        raise PipError(
            "'pip3' command not found. Ensure Python 3 and pip 3 are installed "
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
