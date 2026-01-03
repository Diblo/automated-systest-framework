"""systest command-line entry point.

This module provides the executable entry point for the ``systest`` CLI.
It supports normal execution (running test suites via Behave) and a special
execution path used by argcomplete for shell tab completion.
"""

import os
import sys
import traceback
from contextlib import contextmanager
from typing import Generator, Optional

from behave.version import VERSION as behave_version
from behave.__main__ import run_behave
from behave.exception import ConfigError, NotSupportedWarning, TagExpressionError

from .completion import autocomplete, is_argcomplete_request
from .constants import VERSION
from .exceptions import PipError, SuiteManagerError
from .suite_manager import create_suite, has_requirements, install_suite_dependencies, is_requirements_satisfied
from .systest_behave.configuration import Configuration

__all__ = ["main", "run_systest"]


def handle_utility_functions(config: Configuration) -> Optional[int]:
    """
    Checks for CLI flags that trigger utility actions instead of running tests.
    Returns an exit code (int) if an action was performed, otherwise None.
    """
    if config.version:
        print(f"systest {VERSION} & behave {behave_version}")
        return 0

    if config.create_suite_name is not None:
        create_suite(config.create_suite_name, config.suites_directory_path)
        return 0

    return None


@contextmanager
def handle_test_environment(config: Configuration) -> Generator[None, None, None]:
    """Prepare and clean up the test environment for a suite run.

    The context manager performs the following actions:

    - Sets the ``SYSTEST_RUN_VERSION`` environment variable to the suite's
      configured framework version.
    - Installs suite dependencies into the suite-local library directory
      only if a requirements file exists and dependencies are not already satisfied.
    - Adds the suite directory to ``sys.path`` so suite-specific support code
      can be imported by step definitions.

    Cleanup always runs, ensuring that environment variables and ``sys.path``
    modifications are reverted.

    Args:
        config (Configuration): Parsed systest configuration.

    Yields:
        None: Control to the caller while the environment is prepared.
    """
    # --- SETUP ---
    # Update system env var
    os.environ["SYSTEST_RUN_VERSION"] = config.suite_data.run_version

    # Install dependencies
    if has_requirements(config.suite_data.requirements_file):
        if not is_requirements_satisfied(config.suite_data.requirements_file, config.suite_data.lib_path):
            install_suite_dependencies(config.suite_data.requirements_file, config.suite_data.lib_path, config.verbose)
        elif config.verbose:
            print("All Test Suite dependencies are already satisfied.")
    elif config.verbose:
        print("No requirements to install for this Test Suite.")

    # Add suite path to sys.path so 'support' can be imported by 'steps'
    suite_path_str = str(config.suite_data.path)
    path_added = False

    if suite_path_str not in sys.path:
        sys.path.append(suite_path_str)
        path_added = True

    try:
        # Give control back to the 'with' block
        yield
    finally:
        # --- TEARDOWN ---
        # Cleanup system env var
        if "SYSTEST_RUN_VERSION" in os.environ:
            del os.environ["SYSTEST_RUN_VERSION"]

        # Cleanup sys.path
        if path_added and suite_path_str in sys.path:
            sys.path.remove(suite_path_str)


def run_systest(config: Configuration) -> int:
    """Run the selected system test suite using Behave.

    Utility modes (e.g. version output or suite creation) are handled first.
    If no utility action is requested, Behave is executed inside an isolated
    environment prepared by :func:`_handle_test_environment`.

    Args:
        config (Configuration): Parsed systest configuration.

    Returns:
        int: Exit status code (0 for success, non-zero for failure).
    """
    # Check for utility commands (create, version, etc.)
    result = handle_utility_functions(config)

    if result is None:
        # Run tests inside the isolated environment
        with handle_test_environment(config):
            # run_behave returns 0 for success, 1 for failure
            result = run_behave(config)

    return result


def main() -> int:
    """Main entry point for the systest command-line utility.

    This function handles both normal execution and argcomplete-based
    shell completion requests. Completion requests are handled early
    to avoid side effects such as configuration validation or dependency
    installation.

    Returns:
        int: The exit status code (0 for success, 1 for any failure).
    """
    try:
        if is_argcomplete_request():
            autocomplete(sys.argv[1:])
            return 0

        config = Configuration()
        return run_systest(config)
    except ConfigError as e:
        exception_class_name = e.__class__.__name__
        print(f"{exception_class_name}: {e}")
    except TagExpressionError as e:
        print(f"TagExpressionError: {e}")
    except (NotSupportedWarning, PipError, SuiteManagerError) as e:
        print(e)
    except Exception:
        # Catch and report any unhandled exceptions during execution
        traceback.print_exc()

    return 1  # FAILED


if __name__ == "__main__":
    sys.exit(main())
