"""Test utilities."""

from pathlib import Path


def get_project_root_dir() -> Path:
    """Return the absolute project root directory.

    Returns:
        Path: The absolute path to the project root.
    """
    return Path(__file__).parents[1].absolute()


def get_src_dir() -> Path:
    """Return the absolute path to the src directory.

    Returns:
        Path: The absolute path to the src directory.
    """
    return get_project_root_dir() / "src"


def get_test_dir() -> Path:
    """Return the absolute path to the tests directory.

    Returns:
        Path: The absolute path to the tests directory.
    """
    return get_project_root_dir() / "tests"
