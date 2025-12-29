from pathlib import Path
from typing import Set

from .types import Options

VERSION: str = "0.0.0-dev"

OPTIONS: Options = [
    (
        (
            "-s",
            "--suite",
        ),
        dict(dest="suite", action="store", type=str, help="The test suite to execute (e.g., 'mock', 'r2d2-3.2.1')."),
    ),
    (
        ("--suites-dir",),
        dict(
            dest="suites_directory", action="store", type=Path, help="The directory containing all test suites folders."
        ),
    ),
    (
        ("--create-suite",),
        dict(
            dest="create_suite_name",
            action="store",
            type=str,
            help="Creates a new test suite directory structure, named by the argument.",
        ),
    ),
    (("--config",), dict(dest="config", action="store", type=str, help="Specify the path to a configuration file.")),
]

ENV_SEQUENCE_OPTIONS: Set = {"name", "tags", "format", "outfiles", "userdata_defines", "paths"}

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

USER_CONFIG: str = ".systest"

DEFAULT_SUITES_PATH = Path.cwd()

SUITE_SUFFIX = "_suite"

SUITE_FEATURES_FOLDER: str = "features"

SUITE_SUPPORT_FOLDER: str = "support"

SUITE_CONFIG_FILE: str = "suite.conf"

SUITE_REQUIREMENTS_FILE: str = "requirements.txt"

SUITE_LIB_FOLDER: str = ".lib"

SUITE_ENV_FILE: str = ".env"

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

SYSTEST_FORMATS = [
    # e.g ("test",   "systest.systest_behave.formatter.test:Test")
]

DEFAULT_RUNNER = "systest.systest_behave.runner:SystestRunner"
