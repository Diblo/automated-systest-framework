import os
from enum import Enum

from packaging.version import parse


def run_version() -> str:
    """Retrieves the system test running version string from the environment.

    :raises RuntimeError: If the 'SYSTEST_RUN_VERSION' environment variable is not set,
                          indicating the required application environment setup is missing.
    :returns: The string value of SYSTEST_RUN_VERSION.
    """
    version = os.environ.get("SYSTEST_RUN_VERSION")

    if not version:
        raise RuntimeError("The 'SYSTEST_RUN_VERSION' environment variable must be set before calling this function.")

    return version


class CompareVersion(Enum):
    """Represents the result of comparing two versions."""

    LESS: int = -1
    """Indicates that version 1 is chronologically older than version 2 (v1 < v2)."""

    EQUAL: int = 0
    """Indicates that version 1 is chronologically the same as version 2 (v1 == v2)."""

    GREATER: int = 1
    """Indicates that version 1 is chronologically newer than version 2 (v1 > v2)."""

    def __str__(self):
        return self.name


def compare_versions(version1: str, version2: str) -> CompareVersion:
    """Compares two version and returns an enumeration member representing
    the result.

    Args:
        version1 (str): The first version string to compare.
        version2 (str): The second version string to compare against.

    Returns:
        CompareVersion: The result of the comparison (LESS, EQUAL, or GREATER).

    Examples:
        >>> compare_versions("1.0.0", "1.0.1")
        CompareVersion.LESS
        >>> compare_versions("2.0.0", "1.9.9")
        CompareVersion.GREATER
    """
    v1 = parse(version1)
    v2 = parse(version2)

    if v1 < v2:
        return CompareVersion.LESS
    if v1 > v2:
        return CompareVersion.GREATER
    return CompareVersion.EQUAL


class VersionDiff(Enum):
    """Represents the semantic type of difference between two versions."""

    NONE = 0
    """Versions are identical."""

    PATCH = 1
    """Only the patch number has changed (e.g., 1.0.0 to 1.0.1)."""

    MINOR = 2
    """The minor number has changed (e.g., 1.0.0 to 1.1.0)."""

    MAJOR = 3
    """The major number has changed (e.g., 1.1.0 to 2.0.0)."""

    def __str__(self):
        return self.name


def version_difference(version1: str, version2: str) -> VersionDiff:
    """Determines the semantic difference level (Major, Minor, or Patch)
    between two version strings.

    The comparison follows the strict Major.Minor.Patch structure.

    Args:
        version1 (str): The base version string.
        version2 (str): The comparison version string.

    Returns:
        VersionDiff: The highest level of difference found (MAJOR, MINOR, PATCH, or NONE).

    Examples:
        >>> version_difference("1.0.0", "2.0.0")
        VersionDiff.MAJOR
        >>> version_difference("1.1.5", "1.2.0")
        VersionDiff.MINOR
        >>> version_difference("1.2.0", "1.2.1")
        VersionDiff.PATCH
    """
    v1 = parse(version1)
    v2 = parse(version2)

    # Check for Major difference first
    if v1.major != v2.major:
        return VersionDiff.MAJOR

    # Check for Minor difference
    if v1.minor != v2.minor:
        return VersionDiff.MINOR

    # Check for Patch difference (if major/minor are the same, any difference
    # in the remaining release tuple is considered a patch/build difference)
    if v1.release != v2.release:
        return VersionDiff.PATCH

    return VersionDiff.NONE
