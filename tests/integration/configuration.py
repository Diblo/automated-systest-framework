import logging
import random
import re
import shlex
import shutil
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

import pytest
from behave.configuration import OPTIONS as BEHAVE_OPTIONS
from behave.exception import ConfigError
from pytest_mock.plugin import MockerFixture

from src.systest.constants import (
    ENV_EXCLUDED_OPTIONS,
    OPTIONS,
    SUITE_CONFIG_FILE,
    SUITE_FEATURES_FOLDER,
    SUITE_SUPPORT_FOLDER,
    VERSION,
)
from src.systest.systest_behave.configuration import Configuration, iter_behave_options

# --- Types ---


class ConfigAttr(NamedTuple):
    """
    Represents a configuration attribute to be tested.

    Args:
        name (str): The name of the attribute on the Configuration object.
        value (Union[str, int, bool, Path, re.Pattern, List[Any]]): The expected value of the attribute
                                                                     after parsing and setup.
    """

    name: str
    value: Union[str, int, bool, Path, re.Pattern, List[Any]]


@dataclass(frozen=True)
class OptionConfig:
    """
    Defines a command-line option and its expected parsing result for testing.

    This class serves as the core test data structure, mapping command-line/environment
    input to the expected final attribute value on the Configuration object.

    Args:
        arg (str): The command-line argument string (e.g., '--suite').
        attr (ConfigAttr): The expected configuration attribute name and value.
        input (Optional[str]): The value provided on the command line, if any.
        multi_values (bool): Flag if the argument accepts multiple space-separated values.
    """

    arg: str
    attr: ConfigAttr
    input: Optional[str] = None
    sequence: bool = False

    @property
    def env(self) -> str:
        """Generates the environment variable name (e.g., SYSTEST_COLOR).

        Returns:
            str: The generated environment variable name.
        """
        attr_name = self.attr.name.upper()
        # All environment variables are prefixed with SYSTEST_
        return f"SYSTEST_{attr_name}"

    @property
    def env_input(self) -> str:
        """Generates the string value that should be set for the environment variable.

        Returns:
            str: The string value for the environment variable.
        """
        attr_value = self.attr.value
        # For booleans, the string representation of the boolean value is used.
        if isinstance(attr_value, bool):
            return str(attr_value)

        # Use the explicit input if provided, otherwise the expected final attribute value.
        arg_value = self.input
        if arg_value is None:
            return str(attr_value)

        return arg_value

    @property
    def arg_list(self) -> List[str]:
        """Generates a list of command-line argument components.

        Returns:
            List[str]: A list of command-line argument strings.
        """
        arg_value = self.input

        # Flag-only argument (e.g., ['--version'])
        if arg_value is None:
            return [self.arg]

        # Argument with multiple space-separated values (e.g., ['--name', 'A', '--name', 'B'])
        if self.sequence is True:
            # shlex.split handles quoted inputs correctly
            value_list = shlex.split(arg_value)
            # Handle arguments that can be specified multiple times and
            # flatten the list.
            return [item for v in value_list for item in [self.arg, v]]

        # Standard argument with a single value
        return [self.arg, arg_value]


OptionsMap = Tuple[OptionConfig, ...]


# --- Constants ---

TEST_VERSION = f"{VERSION}.test"
TEST_FEATURES_FOLDER = f"{SUITE_FEATURES_FOLDER}.test"
TEST_SUPPORT_FOLDER = f"{SUITE_SUPPORT_FOLDER}.test"
TEST_SCRIPT_NAME = "systest"

# Arguments that are implicitly covered by default systest usage
# or require special handling
TEST_EXCLUDED_ARGS = {"--suite", "--suites-dir", "--config"}

TEST_OPTIONS_MAP: OptionsMap = (
    # --- Systest Options ---
    # NOTE: The arguments '-s', '--suite' and '--suites-dir' are implicitly
    #       covered by default systest useage
    OptionConfig(
        arg="--create-suite", input="new_suite_name", attr=ConfigAttr(name="create_suite_name", value="new_suite_name")
    ),
    OptionConfig(arg="--cycle-id", input="SIR-1745", attr=ConfigAttr(name="cycle_id", value="SIR-1745")),
    # --- Verbosity, Color, and Metadata ---
    OptionConfig(arg="--version", attr=ConfigAttr(name="version", value=True)),
    OptionConfig(arg="--verbose", attr=ConfigAttr(name="verbose", value=True)),
    OptionConfig(arg="--quiet", attr=ConfigAttr(name="quiet", value=True)),
    OptionConfig(arg="--tags-help", attr=ConfigAttr(name="tags_help", value=True)),
    OptionConfig(arg="--lang-list", attr=ConfigAttr(name="lang_list", value=True)),
    OptionConfig(arg="--lang-help", input="fr", attr=ConfigAttr(name="lang_help", value="fr")),
    OptionConfig(arg="--lang", input="fr", attr=ConfigAttr(name="lang", value="fr")),
    OptionConfig(arg="--no-color", attr=ConfigAttr(name="color", value="off")),
    OptionConfig(arg="--color", input="always", attr=ConfigAttr(name="color", value="always")),
    # --- Execution Control and Filtering ---
    OptionConfig(arg="--dry-run", attr=ConfigAttr(name="dry_run", value=True)),
    OptionConfig(arg="--stop", attr=ConfigAttr(name="stop", value=True)),
    OptionConfig(arg="--jobs", input="10", attr=ConfigAttr(name="jobs", value=10)),
    OptionConfig(
        arg="--exclude", input="^cli_temp_.*", attr=ConfigAttr(name="exclude_re", value=re.compile(r"^cli_temp_.*"))
    ),
    OptionConfig(
        arg="--include",
        input=".*cli_service.*",
        attr=ConfigAttr(name="include_re", value=re.compile(r".*cli_service.*")),
    ),
    OptionConfig(
        arg="--name",
        input='"^CLI_Scenario: Test$" "^CLI_Scenario: Test2$"',
        sequence=True,
        attr=ConfigAttr(name="name", value=["^CLI_Scenario: Test$", "^CLI_Scenario: Test2$"]),
    ),
    OptionConfig(
        arg="--tags",
        input='@t1 "@t2 and @t3" "@t4"',
        sequence=True,
        attr=ConfigAttr(name="tags", value=["@t1", "@t2 and @t3", "@t4"]),
    ),
    OptionConfig(arg="--wip", attr=ConfigAttr(name="wip", value=True)),
    OptionConfig(arg="--stage", input="STAGE", attr=ConfigAttr(name="stage", value="STAGE")),
    # --- Output and Reporting ---
    OptionConfig(
        arg="--format",
        input='plain "progress"',
        sequence=True,
        attr=ConfigAttr(name="format", value=["plain", "progress"]),
    ),
    OptionConfig(
        arg="--outfile",
        input='dir_1 "dir_2"',
        sequence=True,
        attr=ConfigAttr(name="outfiles", value=["dir_1", "dir_2"]),
    ),
    OptionConfig(arg="--junit", attr=ConfigAttr(name="junit", value=True)),
    OptionConfig(arg="--no-junit", attr=ConfigAttr(name="junit", value=False)),
    OptionConfig(arg="--junit-directory", input="REPORTS", attr=ConfigAttr(name="junit_directory", value="REPORTS")),
    OptionConfig(arg=("--steps-catalog"), attr=ConfigAttr(name="steps_catalog", value=True)),
    # --- Display/Formatting (Snippets, Source, Timings) ---
    OptionConfig(arg="--no-snippets", attr=ConfigAttr(name="show_snippets", value=False)),
    OptionConfig(arg="--snippets", attr=ConfigAttr(name="show_snippets", value=True)),
    OptionConfig(arg="--no-source", attr=ConfigAttr(name="show_source", value=False)),
    OptionConfig(arg="--show-source", attr=ConfigAttr(name="show_source", value=True)),
    OptionConfig(arg="--no-timings", attr=ConfigAttr(name="show_timings", value=False)),
    OptionConfig(arg="--show-timings", attr=ConfigAttr(name="show_timings", value=True)),
    OptionConfig(arg="--no-multiline", attr=ConfigAttr(name="show_multiline", value=False)),
    OptionConfig(arg="--multiline", attr=ConfigAttr(name="show_multiline", value=True)),
    OptionConfig(arg="--no-summary", attr=ConfigAttr(name="summary", value=False)),
    OptionConfig(arg="--summary", attr=ConfigAttr(name="summary", value=True)),
    OptionConfig(arg="--no-skipped", attr=ConfigAttr(name="show_skipped", value=False)),
    OptionConfig(arg="--show-skipped", attr=ConfigAttr(name="show_skipped", value=True)),
    # --- Runner ---
    OptionConfig(arg="--runner", input="cli.custom:Runner", attr=ConfigAttr(name="runner", value="cli.custom:Runner")),
    # --- Data Definition ---
    # Testing a special case where input must be parsed into a tuple list [("NAME", "VALUE")]
    OptionConfig(
        arg="--define",
        input="NAME=VALUE",
        sequence=True,
        attr=ConfigAttr(name="userdata_defines", value=[("NAME", "VALUE")]),
    ),
    # --- Capture ---
    OptionConfig(arg="--capture", attr=ConfigAttr(name="capture", value=True)),
    OptionConfig(arg="--no-capture", attr=ConfigAttr(name="capture", value=False)),
    OptionConfig(arg="--capture-stdout", attr=ConfigAttr(name="capture_stdout", value=True)),
    OptionConfig(arg="--no-capture-stdout", attr=ConfigAttr(name="capture_stdout", value=False)),
    OptionConfig(arg="--capture-stderr", attr=ConfigAttr(name="capture_stderr", value=True)),
    OptionConfig(arg="--no-capture-stderr", attr=ConfigAttr(name="capture_stderr", value=False)),
    OptionConfig(arg="--capture-log", attr=ConfigAttr(name="capture_log", value=True)),
    OptionConfig(arg="--no-capture-log", attr=ConfigAttr(name="capture_log", value=False)),
    OptionConfig(arg="--capture-hooks", attr=ConfigAttr(name="capture_hooks", value=True)),
    OptionConfig(arg="--no-capture-hooks", attr=ConfigAttr(name="capture_hooks", value=False)),
    # --- Logging ---
    OptionConfig(
        arg="--logging-level", input="CRITICAL", attr=ConfigAttr(name="logging_level", value=logging.CRITICAL)
    ),
    OptionConfig(
        arg="--logging-format", input="LOG_FORMAT", attr=ConfigAttr(name="logging_format", value="LOG_FORMAT")
    ),
    OptionConfig(
        arg="--logging-datefmt",
        input="LOG_DATE_FORMAT",
        attr=ConfigAttr(name="logging_datefmt", value="LOG_DATE_FORMAT"),
    ),
    OptionConfig(
        arg="--logging-filter",
        input="cli_log_a,-cli_log_b",
        attr=ConfigAttr(name="logging_filter", value="cli_log_a,-cli_log_b"),
    ),
    OptionConfig(arg="--logging-clear-handlers", attr=ConfigAttr(name="logging_clear_handlers", value=True)),
    OptionConfig(arg="--no-logging-clear-handlers", attr=ConfigAttr(name="no_logging_clear_handlers", value=False)),
)


# --- Helper Classes and Functions ---


# pylint: disable=too-many-instance-attributes
class SuiteHandler:
    """Helper class to set up, tear down, and manage the directory structure
    for a mock test suite within a temporary testing environment.
    """

    def __init__(self, tmp_path: Path):
        """
        Initializes the MockTestSuite paths based on a pytest temporary directory.

        Args:
            tmp_path (Path): The pytest temporary directory Path fixture.
        """
        self.tmp_path = tmp_path

        # Attributes set up by the setup() method
        self.suites_directory: Path = tmp_path / "test_suites"
        self.suite: str = ""
        self.suite_folder: str = ""
        self.features_folder: str = ""
        self.support_folder: str = ""

        self.suite_path: Path = Path()
        self.suite_config_file: Path = Path()
        self.suite_features_path: Path = Path()
        self.suite_support_path: Path = Path()

    def create_suite_folder_name(self, suite_name: str) -> str:
        return f"{suite_name}_suite"

    def create_suite_name(self) -> str:
        """
        Generates a random test suite name in the format 'name-version' (e.g., 'aBc-1.2.3').

        Returns:
            str: The formatted test suite name.
        """
        # Define the possible characters for the name and version
        name_chars = list(string.ascii_letters)
        version_chars = list(string.digits)

        # Generate the 'name' and 'version' part
        name = "".join([random.choice(name_chars) for _ in range(3)])
        version = ".".join([random.choice(version_chars) for _ in range(3)])

        # Return the formatted filename
        return f"{name}-{version}"

    def init(
        self,
        suite_name: Optional[str] = None,
        features_folder: Optional[str] = None,
        support_folder: Optional[str] = None,
    ) -> "SuiteHandler":
        """
        Creates a new MockTestSuite instance, and sets up its attributes.

        If `suite_name` is not provided, a unique name is generated.

        Args:
            suite_name (Optional[str]): The name of the test suite (e.g., "r2d2-0.0.1").
            features_folder (Optional[str]): Custom name for the features folder.
            support_folder (Optional[str]): Custom name for the support folder.

        Returns:
            MockTestSuite: The fully initialized and created mock test suite instance.

        Raises:
            Exception: If an attempt to generate a unique suite name fails after 15 tries.
        """
        if suite_name is None:
            # Generate a unique suite name that doesn't conflict with existing directories
            for _ in range(15):
                suite_name = self.create_suite_name()
                suite_folder = self.create_suite_folder_name(suite_name)
                if not (self.suites_directory / suite_folder).exists():
                    break
            else:
                raise RuntimeError("Failed to generate a unique suite name after 15 attempts.")

        new_instance = SuiteHandler(self.tmp_path)
        new_instance.setup(suite_name, features_folder, support_folder)
        new_instance.create()
        return new_instance

    def setup(
        self, suite_name: str, features_folder: Optional[str] = None, support_folder: Optional[str] = None
    ) -> None:
        """Defines all path attributes for the mock suite based on the name and folder customisations.

        This must be called before `create()`.

        Args:
            suite_name (str): The name of the test suite (e.g., 'r2d2-0.0.1').
            features_folder (Optional[str]): Custom features folder name. Defaults to TEST_FEATURES_FOLDER.
            support_folder (Optional[str]): Custom support folder name. Defaults to TEST_SUPPORT_FOLDER.
        """
        # Define the mock suite name and the expected suite folder name.
        self.suite = suite_name
        self.suite_folder = self.create_suite_folder_name(suite_name)
        self.features_folder = features_folder or TEST_FEATURES_FOLDER
        self.support_folder = support_folder or TEST_SUPPORT_FOLDER

        # Define all absolute paths based on the structure
        self.suite_path = self.suites_directory / self.suite_folder
        self.suite_config_file = self.suite_path / SUITE_CONFIG_FILE
        self.suite_features_path = self.suite_path / self.features_folder
        self.suite_support_path = self.suite_path / self.support_folder

    def create(self) -> None:
        """Creates the physical test suite directory structure and the configuration file.

        Raises:
            FileExistsError: If the suite directory already exists.
        """
        if self.suite_path.exists():
            raise FileExistsError(f"Suite directory already exists: {self.suite_path}")

        # Create necessary directories. 'parents=True' for if the suites directory doesn't exist.
        self.suite_features_path.mkdir(parents=True)
        self.suite_support_path.mkdir()

        # Create the suite configuration file
        config_file_content = f"""
framework_version={TEST_VERSION}
features_folder={self.features_folder}
support_folder={self.support_folder}
"""
        self.suite_config_file.write_text(config_file_content.strip(), encoding="utf-8")

    def delete(self) -> None:
        """Removes the entire test suites directory."""
        if self.suite_path.exists():
            shutil.rmtree(self.suite_path)


class ConfigurationClassHelper:
    """A helper class for handling the configuring."""

    def __init__(self, mocker: MockerFixture):
        """
        Initializes the helper with a pytest-mock fixture.

        Args:
            mocker (MockerFixture): The pytest-mock fixture used for patching.
        """
        self.mocker = mocker

    def set_args(self, args: Optional[List[str]] = None) -> None:
        """
        Patches `sys.argv` to simulate command-line arguments.

        Args:
            args (Optional[List[str]]): A list of command-line arguments (excluding script name).

        Raises:
            TypeError: If args is not a list of strings.
        """
        # Validate and prepare arguments
        if args is None:
            args = []
        elif not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
            raise TypeError("Args must be a list of strings.")

        self.mocker.patch("sys.argv", [TEST_SCRIPT_NAME] + args)

    def set_envs(self, envs: Optional[Dict[str, str]] = None) -> None:
        """Patches `os.environ` to simulate environment variables.

        Args:
            envs (Optional[Dict[str, str]]): A dictionary of environment variable names and their values.

        Raises:
            TypeError: If envs is not a dictionary of string keys and values.
        """
        # Validate and prepare environment variables
        if envs is None:
            envs = {}
        elif not isinstance(envs, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in envs.items()
        ):
            raise TypeError("Envs must be a dictionary with string keys and values.")

        # Apply patches. 'clear=True' ensures a clean environment for each test run.
        self.mocker.patch.dict("os.environ", envs, clear=True)

    def create_configuration(
        self,
        suite_handler: Optional[SuiteHandler] = None,
        args: Optional[List[str]] = None,
        envs: Optional[Dict[str, str]] = None,
    ) -> Configuration:
        """
        Configures the environment/arguments and instantiates the Configuration class.

        Args:
            mock_test_suite (MockTestSuite): The mock test suite instance to use for paths/names.
            args (Optional[List[str]]): Additional command-line arguments to include.
            envs (Optional[Dict[str, str]]): Environment variables to set.

        Returns:
            Configuration: A new instance of the Configuration class.
        """
        _args = []
        if suite_handler is not None:
            _args.extend(
                ["--suite", suite_handler.suite_data.name, "--suites-dir", str(suite_handler.suites_directory)]
            )
        if args is not None:
            _args.extend(args)

        self.set_args(_args)
        self.set_envs(envs)

        # The Configuration() initializer will read the patched sys.argv and os.environ
        return Configuration()


def validate_option(
    config: Configuration, option: OptionConfig, expected_att_value: Optional[Any] = float("inf")
) -> Optional[str]:
    attr_name = option.attr.name
    if expected_att_value == float("inf"):
        expected_att_value = option.attr.value

    # Attribute existence
    if not hasattr(config, attr_name):
        return f"Configuration object is missing expected attribute {attr_name!r}."

    att_value = getattr(config, attr_name)
    print(attr_name, "=", att_value)

    # Special handling for compiled regex patterns
    if isinstance(expected_att_value, re.Pattern):
        if isinstance(att_value, re.Pattern):
            att_pattern = getattr(att_value, "pattern", None)
            expected_pattern = getattr(expected_att_value, "pattern", None)
            if att_pattern == expected_pattern:
                return None
    # Attribute value correctness and type preservation
    elif att_value == expected_att_value:
        return None

    return (
        f"Attribute {attr_name!r} ({option.arg}) loaded incorrectly. "
        f"Got: {att_value!r} type {type(att_value)}, "
        f"Expected: {expected_att_value!r} type {type(expected_att_value)}"
    )


# --- Fixtures ---


@pytest.fixture
def test_suite_handler(tmp_path: Path) -> SuiteHandler:
    return SuiteHandler(tmp_path)


@pytest.fixture
def configuration_class_helper(mocker: MockerFixture) -> ConfigurationClassHelper:
    return ConfigurationClassHelper(mocker)


# --- Tests ---


@pytest.mark.dependency()
def test_configuration_coverage():
    """
    Tests for complete option coverage by ensuring that for every group of argument
    aliases (e.g., ('-s', '--suite')), at least one argument from that group is
    represented in the TEST_OPTIONS_MAP test data structure.

    This is a meta-test to prevent new options from being added without corresponding
    integration tests.
    """
    # 1. Collect ALL unique groups of argument aliases (Tuples of strings)
    systest_options = {arguments for arguments, _ in OPTIONS}
    behave_options = {arguments for arguments, _ in iter_behave_options(BEHAVE_OPTIONS)}
    all_option_groups = systest_options.union(behave_options)

    # 2. Iterate through all tested arguments and remove the covered group from the set
    tested_args = {option.arg for option in TEST_OPTIONS_MAP}

    for arg in tested_args.union(TEST_EXCLUDED_ARGS):
        found_group = None
        for option_group in all_option_groups:
            # Check if the argument is one of the aliases in the group
            if arg in option_group:
                found_group = option_group
                break
        if found_group is not None:
            all_option_groups.discard(found_group)

    n_groups_left = len(all_option_groups)
    assert n_groups_left == 0, (
        f"{n_groups_left} option(s) are missing from the "
        "TEST_OPTIONS_MAP. At least one flag from each option must be added to the TEST_OPTIONS_MAP."
    )


@pytest.mark.dependency(depends=["test_configuration_coverage"])
def test_configuration_basic(  # pylint: disable=redefined-outer-name
    test_suite_handler: SuiteHandler, configuration_class_helper: ConfigurationClassHelper
):
    """Tests basic Configuration initialization and successful loading of suite paths.

    This test confirms the fundamental parsing and path resolution logic is sound.

    Args:
        mock_test_suite (MockTestSuite): Fixture to set up the mock suite structure.
    """
    # Setup a mock suite with default folder names
    mock_test_suite = test_suite_handler.init(
        features_folder=SUITE_FEATURES_FOLDER, support_folder=SUITE_SUPPORT_FOLDER
    )
    # Remove the config file to ensure default (not config-loaded) version is used
    mock_test_suite.suite_config_file.unlink()

    # Initialize Configuration
    config = configuration_class_helper.create_configuration(mock_test_suite)

    # 3. Assertions
    # Check that paths were correctly resolved
    assert (
        config.suites_directory == mock_test_suite.suites_directory
    ), f"Expected suites_directory {mock_test_suite.suites_directory!r}, got {config.suites_directory!r}"

    assert config.suite == mock_test_suite.suite, f"Expected suite name {mock_test_suite.suite!r}, got {config.suite!r}"
    assert (
        config.suite_path == mock_test_suite.suite_path
    ), f"Expected suite_path {mock_test_suite.suite_path!r}, got {config.suite_path!r}"

    # Check that default feature/support folder names were used
    assert (
        config.suite_features_path == mock_test_suite.suite_features_path
    ), f"Expected suite_features_path {mock_test_suite.suite_features_path!r}, got {config.suite_features_path!r}"
    assert (
        config.suite_support_path == mock_test_suite.suite_support_path
    ), f"Expected suite_support_path {mock_test_suite.suite_support_path!r}, got {config.suite_support_path!r}"

    # framework_version should fall back to the application default VERSION as config file was removed.
    assert config.run_version == VERSION, f"Expected default framework_version {VERSION!r}, got {config.run_version!r}"


@pytest.mark.dependency(depends=["test_configuration_basic"])
class TestConfigurationSources:
    """Integration tests for configuration inputs from CLI, suite config, and env."""

    def test_attributes_loaded_from_cli(  # pylint: disable=redefined-outer-name
        self, test_suite_handler: SuiteHandler, configuration_class_helper: ConfigurationClassHelper
    ):
        """Tests that all non-excluded command-line arguments are correctly parsed and
        set as attributes on the Configuration object.

        This confirms the correct type conversion and attribute assignment for CLI inputs.

        Args:
            mock_test_suite (MockTestSuite): Fixture to set up the mock suite structure.
            arg_env_setter (ArgEnvSetter): Fixture to set command-line arguments.
        """
        mock_test_suite = test_suite_handler.init()

        failed_assertions = []

        # Iterate over the map and test each non-excluded option
        for option in TEST_OPTIONS_MAP:
            # Initialize Configuration
            config = configuration_class_helper.create_configuration(mock_test_suite, args=option.arg_list)

            result = validate_option(config, option)
            if result is not None:
                failed_assertions.append(result)

        # ----------------------------------------------------------------------
        # FINISH: Final assertion
        # ----------------------------------------------------------------------
        assert not failed_assertions, f"\n{len(failed_assertions)} total failures found.\n" + "\n".join(
            failed_assertions
        )

    @pytest.mark.dependency(depends=["TestConfigurationSources::test_attributes_loaded_from_cli"])
    def test_suite_config(  # pylint: disable=redefined-outer-name
        self, test_suite_handler: SuiteHandler, configuration_class_helper: ConfigurationClassHelper
    ):
        """Tests that configuration values from the suite config file are correctly loaded.

        Args:
            mock_test_suite (MockTestSuite): Fixture to set up the mock suite structure.
            arg_env_setter (ArgEnvSetter): Fixture to set command-line arguments.
        """
        # Setup suite with the config file defining custom versions and folders
        mock_test_suite = test_suite_handler.init()

        # Initialize Configuration
        config = configuration_class_helper.create_configuration(mock_test_suite)

        # 3. Assertions: Check that path resolution used values from the config file
        assert (
            config.suite_features_path == mock_test_suite.suite_features_path
        ), f"Expected suite_features_path {mock_test_suite.suite_features_path!r}, got {config.suite_features_path!r}"
        assert (
            config.suite_support_path == mock_test_suite.suite_support_path
        ), f"Expected suite_support_path {mock_test_suite.suite_support_path!r}, got {config.suite_support_path!r}"

        # Check that the framework version was loaded from the config file
        assert (
            config.run_version == TEST_VERSION
        ), f"Expected framework_version {TEST_VERSION!r} from config file, got {config.run_version!r}"

    @pytest.mark.dependency(depends=["TestConfigurationSources::test_attributes_loaded_from_cli"])
    def test_attributes_loaded_from_env(  # pylint: disable=redefined-outer-name
        self, test_suite_handler: SuiteHandler, configuration_class_helper: ConfigurationClassHelper
    ):
        """Tests that all non-excluded environment variables are correctly parsed and
        set as attributes on the Configuration object.

        This confirms the correct type conversion and attribute assignment for ENV inputs.

        Args:
            mock_test_suite (MockTestSuite): Fixture to set up the mock suite structure.
            arg_env_setter (ArgEnvSetter): Fixture to set environment variables.
        """
        mock_test_suite = test_suite_handler.init()

        failed_assertions = []

        # Iterate over the map and test each non-excluded environment variable
        for option in TEST_OPTIONS_MAP:
            if option.attr.name not in ENV_EXCLUDED_OPTIONS:
                envs = {option.env: option.env_input}
                # Initialize Configuration
                config = configuration_class_helper.create_configuration(mock_test_suite, envs=envs)

                result = validate_option(config, option)
                if result is not None:
                    failed_assertions.append(result)

        # ----------------------------------------------------------------------
        # FINISH: Final assertion
        # ----------------------------------------------------------------------
        assert not failed_assertions, f"\n{len(failed_assertions)} total failures found.\n" + "\n".join(
            failed_assertions
        )


@pytest.mark.dependency(
    depends=[
        "TestConfigurationSources::test_attributes_loaded_from_cli",
        "TestConfigurationSources::test_suite_config",
        "TestConfigurationSources::test_attributes_loaded_from_env",
    ]
)
class TestConfigurationOthers:
    """Integration tests for configuration precedence and utility modes."""

    def test_configuration_priority(  # pylint: disable=redefined-outer-name
        self, test_suite_handler: SuiteHandler, configuration_class_helper: ConfigurationClassHelper
    ):
        """Tests the priority of configuration loading, confirming that CLI overrides ENV.

        For multi-input options (like tags, name), the CLI value should be prepended
        to the ENV value, as is common for the behave module.

        Args:
            mock_test_suite (MockTestSuite): Fixture to set up the mock suite structure.
            arg_env_setter (ArgEnvSetter): Fixture to set command-line arguments and environment variables.
        """
        mock_test_suite = test_suite_handler.init()

        failed_assertions = []

        # Iterate over the map and test each non-excluded option
        for option in TEST_OPTIONS_MAP:
            if option.attr.name in ENV_EXCLUDED_OPTIONS:
                continue

            arg_name = option.arg
            arg_value = option.input
            att_value = option.attr.value

            # Initialize expected_att_value with the CLI value first
            expected_att_value = att_value

            # Define the ENV value to be different from CLI
            if option.sequence is True:  # multiple space-separated values
                # Define the ENV value and ensure the expected_att_value is prepended with CLI's list
                if arg_name == "--define":
                    env_value = "test=env_value"
                    env_parsed_value = [("test", "env_value")]
                else:
                    if arg_name == "--format":
                        # Format requires a known format
                        env_value = "json"
                        env_parsed_value = [env_value]
                    else:
                        env_value = "env_value"
                        env_parsed_value = [env_value]

                # Accumulating option: CLI list + ENV list
                expected_att_value = env_parsed_value + att_value

            elif arg_value is None:  # boolean arg (e.g., --verbose)
                env_value = str(not att_value).lower()

            elif arg_value.isnumeric():  # integer arg (e.g., --jobs)
                # 01110100 (t) + 01100101 (e) + 01110011 (s) + 01110100 (t) = 111000000 = 448
                env_value = "448"

            else:  # string arg
                env_value = "test_env_value"

            # Initialize Configuration
            config = configuration_class_helper.create_configuration(
                mock_test_suite, option.arg_list, {option.env: env_value}
            )

            result = validate_option(config, option, expected_att_value)
            if result is not None:
                failed_assertions.append(result)

        # ----------------------------------------------------------------------
        # FINISH: Final assertion
        # ----------------------------------------------------------------------
        assert not failed_assertions, f"\n{len(failed_assertions)} total failures found.\n" + "\n".join(
            failed_assertions
        )

    def test_suite_config_strict_load(  # pylint: disable=redefined-outer-name
        self, test_suite_handler: SuiteHandler, configuration_class_helper: ConfigurationClassHelper
    ):
        """Tests that the suite config file strictly sets suite setup values,
        which cannot be overridden by ENV or CLI, ensuring suite integrity.

        Args:
            mock_test_suite (MockTestSuite): Fixture to set up the mock suite structure.
            arg_env_setter (ArgEnvSetter): Fixture to set command-line arguments and environment variables.
        """
        # Setup Suite
        mock_test_suite = test_suite_handler.init()

        # Setup ENV to attempt overriding the Config File settings
        envs = {
            # These are the attribute names. Setting them via ENV should not
            # affect the final setup of the test suite.
            "SYSTEST_RUN_VERSION": "8.8.8.env",
            "SYSTEST_SUITE_FEATURES_PATH": "feature_env",
            "SYSTEST_SUITE_SUPPORT_PATH": "support_env",
        }

        # Initialize Configuration
        config = configuration_class_helper.create_configuration(mock_test_suite, envs=envs)

        # --- Assertions ---
        # The value must come from the config file (TEST_VERSION), ignoring ENV/CLI attempts to override.
        assert (
            config.run_version == TEST_VERSION
        ), f"Suite config version was incorrectly overridden. Expected {TEST_VERSION!r}, got {config.run_version!r}"

        # Asserting that the correct paths were loaded (based on config file), ignoring ENV
        assert (
            mock_test_suite.suite_features_path == config.suite_features_path
        ), "Features path mismatch: Expected path from suite config, but was overridden."
        assert (
            mock_test_suite.suite_support_path == config.suite_support_path
        ), "Support path mismatch: Expected path from suite config, but was overridden."

    def test_utility_mode(  # pylint: disable=redefined-outer-name
        self, configuration_class_helper: ConfigurationClassHelper, capsys: pytest.CaptureFixture
    ):
        """Tests that help/utility arguments are correctly handled:
        1. --help causes a SystemExit (code 0) and print help message.
        2. Other utility flags bypass the mandatory suite check.

        Args:
            arg_env_setter (ArgEnvSetter): Fixture to set command-line arguments.
            capsys (pytest.CaptureFixture): Pytest fixture to capture stdout/stderr output.
        """
        # ----------------------------------------
        # 1. Test: --help (Exit and print usage)
        # ----------------------------------------
        # Configuration should exit gracefully due to --help
        with pytest.raises(SystemExit) as excinfo:
            configuration_class_helper.create_configuration(args=["--help"])

        assert excinfo.value.code == 0, "The --help flag did not exit gracefully (code 0)."

        captured = capsys.readouterr()
        if not re.search(rf"usage: {TEST_SCRIPT_NAME}", captured.out):
            pytest.fail("Help output not found.")

        # ----------------------------------------
        # 2. Test: Other Utility Flags (Bypass suite check)
        # ----------------------------------------
        utility_options = [
            OptionConfig(arg="--version", attr=ConfigAttr(name="version", value=True)),
            OptionConfig(arg="--tags-help", attr=ConfigAttr(name="tags_help", value=True)),
            OptionConfig(arg="--lang", input="help", attr=ConfigAttr(name="lang", value="help")),
            OptionConfig(arg="--lang-list", attr=ConfigAttr(name="lang_list", value=True)),
            OptionConfig(arg="--lang-help", input="fr", attr=ConfigAttr(name="lang_help", value="fr")),
            OptionConfig(arg="--format", input="help", sequence=True, attr=ConfigAttr(name="format", value=["help"])),
        ]

        failed_assertions: List[str] = []

        for option in utility_options:
            # Initialize Configuration
            config = configuration_class_helper.create_configuration(args=option.arg_list)

            result = validate_option(config, option)
            if result is not None:
                failed_assertions.append(result)

        assert not failed_assertions, f"\n{len(failed_assertions)} total failures found.\n" + "\n".join(
            failed_assertions
        )


@pytest.mark.dependency(
    depends=[
        "TestConfigurationOthers::test_configuration_priority",
        "TestConfigurationOthers::test_suite_config_strict_load",
        "TestConfigurationOthers::test_utility_mode",
    ]
)
class TestConfigurationErrors:
    """Integration tests for configuration error handling and validation failures."""

    def test_excluded_env(  # pylint: disable=redefined-outer-name
        self, test_suite_handler: SuiteHandler, configuration_class_helper: ConfigurationClassHelper
    ):
        """
        Tests that environment variables which are explicitly excluded (listed in
        ENV_EXCLUDED_OPTIONS) correctly raise a ConfigError when an attempt is made to set them.

        Args:
            mock_test_suite (MockTestSuite): Fixture to set up the mock suite structure.
            arg_env_setter (ArgEnvSetter): Fixture to set environment variables.
        """
        mock_test_suite = test_suite_handler.init()
        excluded_options = [option for option in TEST_OPTIONS_MAP if option.attr.name in ENV_EXCLUDED_OPTIONS]

        # Iterate over the excluded options and try to set them via ENV
        for option in excluded_options:
            env_name = option.env
            attr_name = option.attr.name

            match = f"ENV[{env_name}]: Setting {attr_name!r} cannot be specified as environment var."
            with pytest.raises(ConfigError, match=re.escape(match)):
                configuration_class_helper.create_configuration(mock_test_suite, envs={env_name: option.env_input})

    def test_missing_suite_arg(  # pylint: disable=redefined-outer-name
        self, configuration_class_helper: ConfigurationClassHelper
    ):
        """Tests that Configuration raises SystemExit when the required '--suite' argument is missing.

        Args:
            configuration_class_helper (ConfigurationClassHelper): Helper for configuring Configuration instances.
        """
        # Expected behavior: argparse.error is called, raising SystemExit with a non-zero code.
        with pytest.raises(SystemExit) as excinfo:
            configuration_class_helper.create_configuration()

        assert excinfo.value.code != 0, "Expected SystemExit with error code, got success code."

    def test_suite_path_errors(  # pylint: disable=redefined-outer-name
        self, test_suite_handler: SuiteHandler, configuration_class_helper: ConfigurationClassHelper
    ):
        """Tests that Configuration raises a ConfigError when required suite paths
        (suites directory, suite folder, features folder, support folder) are missing
        on the filesystem.

        Args:
            mock_test_suite (MockTestSuite): Fixture to set up the mock suite structure.
            arg_env_setter (ArgEnvSetter): Fixture to set command-line arguments.
        """
        mock_test_suite = test_suite_handler.init()

        def _run(remove_path: Path, match: str):
            """Helper to run a single test case for a missing path."""
            # Re-create the full structure before removing the target directory
            mock_test_suite.delete()
            mock_test_suite.create()

            # Remove the target path to simulate it being missing
            shutil.rmtree(remove_path, ignore_errors=True)

            # Expect ConfigError with a specific error message
            with pytest.raises(ConfigError, match=re.escape(match)):
                configuration_class_helper.create_configuration(mock_test_suite)

        # Test 1: Suites Directory is missing
        _run(mock_test_suite.suites_directory, f"Suites directory not found: {mock_test_suite.suites_directory!r}")

        # Test 2: The Test Suite Directory is missing ('path_error-0.0.1_suite')
        _run(
            mock_test_suite.suite_path,
            "The test suite directory was not found for the test suite "
            f"{mock_test_suite.suite!r} (expected: {mock_test_suite.suite_path!r})",
        )

        # Test 3: The Test Suite Features Directory is missing
        _run(
            mock_test_suite.suite_features_path,
            "The test suite features directory was not found for the test suite "
            f"{mock_test_suite.suite!r} (expected: {mock_test_suite.suite_features_path!r})",
        )

        # Test 4: The Test Suite Support Directory is missing
        _run(
            mock_test_suite.suite_support_path,
            "The test suite support directory was not found for the test suite "
            f"{mock_test_suite.suite!r} (expected: {mock_test_suite.suite_support_path!r})",
        )

    def test_unrecognized_argument(  # pylint: disable=redefined-outer-name
        self, configuration_class_helper: ConfigurationClassHelper, capsys: pytest.CaptureFixture
    ):
        """Tests that passing an unrecognized command-line argument causes the parser
        to exit immediately with a non-zero error code and print the corresponding error message.

        Args:
            arg_env_setter (ArgEnvSetter): Fixture to set command-line arguments.
            capsys (pytest.CaptureFixture): Pytest fixture to capture stdout/stderr output.
        """
        unrecognized_arg = "--g"

        # 1. Assert: Expect SystemExit with non-zero exit code.
        with pytest.raises(SystemExit) as excinfo:
            # Should exit immediately due to the parser error
            configuration_class_helper.create_configuration(args=[unrecognized_arg])

        # 2. Assert Exit Code
        assert excinfo.value.code != 0, "Parser did not exit with an error code (Expected non-zero, Got 0)."

        # 3. Capture Output: The error message is sent to stderr.
        captured = capsys.readouterr()

        # 4. Assert Error Message Content
        expected_error_pattern = re.escape(f"{TEST_SCRIPT_NAME}: error: unrecognized arguments: {unrecognized_arg}")

        if not re.search(expected_error_pattern, captured.err):
            pytest.fail("Unknown argument message not found in output.")
