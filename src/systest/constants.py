"""Shared constants for systest framework."""

from pathlib import Path
from typing import Set

from .types import Options

try:
    _version: str = (Path(__file__).parent / "VERSION").read_text().strip()
except FileNotFoundError:
    _version: str = "0.0.0-dev"

VERSION: str = _version
"""Current systest framework version."""

OPTIONS: Options = [
    (
        (
            "-s",
            "--suite",
        ),
        {
            "dest": "suite",
            "action": "store",
            "type": str,
            "help": "The test suite to execute (e.g., 'mock', 'r2d2-3.2.1').",
        },
    ),
    (
        ("--suites-dir",),
        {
            "dest": "suites_directory",
            "action": "store",
            "type": Path,
            "help": "The directory containing all test suites folders.",
        },
    ),
    (
        ("--create-suite",),
        {
            "dest": "create_suite_name",
            "action": "store",
            "type": str,
            "help": "Creates a new test suite directory structure, named by the argument.",
        },
    ),
    (
        ("--cycle-id",),
        {"dest": "cycle_id", "action": "store", "type": str, "help": "Zephyr test cycle id/key (e.g., SIR-R3)."},
    ),
    (
        ("--config",),
        {"dest": "config", "action": "store", "type": str, "help": "Specify the path to a configuration file."},
    ),
]
"""Systest CLI options."""

ENV_SEQUENCE_OPTIONS: Set = {"name", "tags", "format", "outfiles", "userdata_defines", "paths"}
"""Option names that accept sequence values in environment variables."""

ENV_EXCLUDED_OPTIONS: Set = {
    "suite",
    "create_suite_name",
    "config",
    "help",
    "tags_help",
    "lang_list",
    "lang_help",
    "verbose",
    "version",
}
"""Option names that are not permitted as environment variables."""

USER_CONFIG: str = ".systest"
"""Filename for user-level systest configuration."""

DEFAULT_SUITES_PATH = Path.cwd()
"""Default path for locating suites."""

SUITE_SUFFIX = "_suite"
"""Suffix appended to suite directory names."""

SUITE_FEATURES_FOLDER: str = "features"
"""Default folder name for feature files."""

SUITE_SUPPORT_FOLDER: str = "support"
"""Default folder name for support files."""

SUITE_CONFIG_FILE: str = "suite.conf"
"""Default configuration filename for suites."""

SUITE_REQUIREMENTS_FILE: str = "requirements.txt"
"""Default requirements filename for suites."""

SUITE_LIB_FOLDER: str = ".lib"
"""Default local dependency folder for suites."""

SUITE_ENV_FILE: str = ".env"
"""Default environment filename for suites."""

SUITE_DEFAULT_CONFIG_CONTENT = """# Specifies the framework version the test suite is guaranteed to support.
# The framework uses this to ensure compatibility before execution.
# framework_version=0.0.1

# Defines the name of the directory that contains all feature area directories for the test suite.
# The default is usually features.
# features_folder=features

# Defines the name of the directory containing the shared utility modules and helper functions.
# The default is usually support.
# support_folder=support
"""
"""Template content for a new suite configuration file."""

SUITE_DEFAULT_REQUIREMENTS_CONTENT = """# Specific Python dependencies required for running this test suite.
#
# Examples:
#
# Exact version
# requests==2.0.1
#
# Minimum required version
# requests>=2.0.1
#
# Compatible release (Recommended)
# requests~=2.0.1      # >= 2.0.1, but < 2.1.0
# requests~=2.0        # >= 2.0.0, but < 3.0.0
# requests<3.0,>=2.0.1 # >= 2.0.1, but < 3.0.0
"""
"""Template content for a new suite requirements file."""

SYSTEST_FORMATS = [
    # e.g ("test",   "systest.systest_behave.formatter.test:Test")
]
"""Additional behave formatter registrations."""

DEFAULT_RUNNER = "systest.systest_behave.runner:SystestRunner"
"""Default runner path."""
