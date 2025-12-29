import os
import sys
import traceback
from contextlib import contextmanager
from typing import Generator, Optional

from behave import __version__ as behave_version
from behave.__main__ import run_behave
from behave.exception import ConfigError, NotSupportedWarning, TagExpressionError

from .constants import VERSION
from .exceptions import PipError, SuiteManagerError
from .suite_manager import create_suite, install_suite_dependencies
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
        create_suite(config.create_suite_name, config.suites_directory)
        return 0

    return None


@contextmanager
def handle_test_environment(config: Configuration) -> Generator[None, None, None]:
    """
    Context manager that sets up and tears down the test environment.
    """
    # --- SETUP ---
    # Update system env var
    os.environ["SYSTEST_RUN_VERSION"] = config.run_version

    # Install dependencies
    install_suite_dependencies(config.suite_lib_path, config.suite_requirements_file, config.verbose)

    # Add suite path to sys.path so 'support' can be imported by 'steps'
    suite_path_str = str(config.suite_path)
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
    """
    Runs the system tests using the behave framework.

    Args:
        config (Configuration): The system test configuration object.

    Returns:
        int: The exit status code: 0 if all tests pass, > 0 if any test fails.
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
    """
    Main entry point for the systest command-line utility.

    Returns:
        int: The exit status code (0 for success, 1 for any failure).
    """
    try:
        config = Configuration(load_config=False)
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
