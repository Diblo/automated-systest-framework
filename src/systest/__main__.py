"""CLI entry point for the systest test runner."""

import os
import sys
import traceback
from contextlib import contextmanager
from typing import Generator, Optional

from behave import __version__ as behave_version
from behave.__main__ import run_behave
from behave.exception import ConfigError, NotSupportedWarning, TagExpressionError

from .completion import autocomplete, is_argcomplete_request
from .constants import VERSION
from .exceptions import PipError, SuiteManagerError
from .suite_manager import create_suite, install_suite_dependencies
from .systest_behave.configuration import Configuration

__all__ = ["main", "run_systest"]


def handle_utility_functions(config: Configuration) -> Optional[int]:
    """Run CLI utility actions when flagged.

    Args:
        config (Configuration): The system test configuration.

    Returns:
        Optional[int]: Exit code if a utility action was performed, otherwise None.
    """
    if config.version:
        print(f"systest {VERSION} & behave {behave_version}")
        return 0

    if config.create_suite_name is not None:
        create_suite(config.create_suite_name, config.suites_directory)
        return 0

    return None


@contextmanager
def handle_test_environment(config: Configuration) -> Generator[None, None, None]:
    """Set up and tear down the test environment.

    Args:
        config (Configuration): The system test configuration.

    Yields:
        None: This context manager does not yield a value.
    """
    # --- SETUP ---
    # Update system env var
    os.environ["SYSTEST_RUN_VERSION"] = config.run_version

    # Install dependencies
    install_suite_dependencies(config.suite_data.lib_path, config.suite_data.requirements_file, config.verbose)

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
    """Run system tests using the Behave framework.

    Args:
        config (Configuration): The system test configuration.

    Returns:
        int: Exit status code (0 for success, >0 for failure).
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
    """Run the systest command-line utility.

    Returns:
        int: Exit status code (0 for success, 1 for failure).
    """
    try:
        if is_argcomplete_request():
            autocomplete(sys.argv[1:])
            return 0

        config = Configuration(load_config=False)
        return run_systest(config)
    except ConfigError as e:
        exception_class_name = e.__class__.__name__
        print(f"{exception_class_name}: {e}")
    except TagExpressionError as e:
        print(f"TagExpressionError: {e}")
    except (NotSupportedWarning, PipError, SuiteManagerError) as e:
        print(e)
    except Exception:  # pylint: disable=broad-exception-caught
        # Catch and report any unhandled exceptions during execution
        traceback.print_exc()

    return 1  # FAILED


if __name__ == "__main__":
    sys.exit(main())
