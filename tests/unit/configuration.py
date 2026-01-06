import re
from typing import Any, Iterator, Sequence, Tuple

import pytest
from behave.exception import ConfigError
from pytest_mock import MockerFixture

from src.systest.systest_behave import configuration


def check_output(output_lines: Sequence[str], expected_line: str, error_message: str) -> None:
    """Helper to assert that an expected line is present in the captured output.

    Args:
        output_lines (Sequence[str]): A sequence (list or tuple) of captured, stripped print output lines.
        expected_line (str): The exact string expected to be found in the output.
        error_message (str): The assertion failure message displayed if the expected line is not found.
    """
    assert any(line == expected_line for line in output_lines), error_message


class ModuleHelper:
    def __init__(self, mocker: MockerFixture, module):
        """Initializes the helper with a mocker fixture and the target module for testning.

        Args:
            mocker (MockerFixture): The pytest-mock fixture used for patching.
            module (types.ModuleType): The module object whose functions/constants will be patched.
        """
        self.mocker = mocker
        self.module = module

        # Patch builtins.print and store the mock object
        self.mock_print = self.mocker.patch("builtins.print")

    def iter_mock_output(self) -> Iterator[str]:
        """
        Iterates over the positional arguments of the mocked print calls and yields
        each argument after stripping leading/trailing whitespace.

        Yields:
            Iterator[str]: The captured and stripped string content of each print call.
        """
        for call in self.mock_print.call_args_list:
            # call[0][0] is the first positional argument (the string passed to print)
            yield call[0][0].strip()

    def get_output_lines(self) -> Tuple[str, ...]:
        """Returns all captured mock print output lines as a tuple of stripped strings."""
        return tuple(self.iter_mock_output())

    def mock_func(self, name: str, return_value: Any) -> None:
        """Mocks a function within the module and sets its return value.

        Args:
            name (str): The name of the function to mock (e.g., 'build_environment_values').
            return_value (Any): The value the mocked function should return.
        """
        target = f"{self.module.__name__}.{name}"
        self.mocker.patch(target, return_value=return_value)

    def mock_constant(self, name: str, value: Any) -> None:
        """Mocks a module-level constant (e.g., set, list, variable) by replacing its value.

        Args:
            name (str): The name of the constant to mock (e.g., 'ENV_EXCLUDED_OPTIONS').
            value (Any): The new value for the constant.
        """
        target = f"{self.module.__name__}.{name}"
        self.mocker.patch(target, new=value)


class ConfigurationModuleHelper(ModuleHelper):
    """Specialized helper class dedicated to testing the 'configuration' module."""

    # This hint helps static analysis tools understand the specific module type
    module: configuration

    def __init__(self, mocker: MockerFixture):
        """Initializes the helper, automatically targeting the 'configuration' module."""
        super().__init__(mocker, configuration)


# --- Fixtures ---


@pytest.fixture
def configuration_module_helper(mocker: MockerFixture) -> ConfigurationModuleHelper:
    """Provides a ConfigurationModuleHelper instance for patching the configuration module."""
    return ConfigurationModuleHelper(mocker)


# --- TESTS ---


class TestLoadEnvironmentSettings:
    """Unit tests for the load_environment_settings function, which populates
    a dictionary with values from SYSTEST_-prefixed environment variables.
    """

    def test_load_various_types_correctly(  # pylint: disable=redefined-outer-name
        self, configuration_module_helper: ConfigurationModuleHelper
    ):
        """Test loading string, boolean, integer, sequence, and user data types correctly.

        Args:
            configuration_module_helper (ConfigurationModuleHelper): Helper for patching configuration.
        """
        defaults = {"other_key": "initial_value"}

        configuration_module_helper.mock_func(
            "build_environment_values",
            {
                # Simple types (string, boolean, integer)
                "SYSTEST_STRING_SETTING": "some_value",
                "SYSTEST_IS_ENABLED": "True",
                "SYSTEST_TIMEOUT": "120",
                # Sequence values: values are shlex-split into a list of strings
                "SYSTEST_FORMAT": 'a "c d" "e"',
                "SYSTEST_NAME": 'f "g h" "i"',
                "SYSTEST_PATHS": 'j "k l" "m"',
                "SYSTEST_TAGS": '@t1 "@t2 and @t3" "@t4"',
                "SYSTEST_OUTFILES": "-",
                # User data: values are split and converted to a list of (key, value) tuples
                "SYSTEST_USERDATA_DEFINES": 'key1=value1 key2="value2" "key3=value3"',
            },
        )

        configuration_module_helper.module.load_environment_settings(defaults)

        assert defaults == {
            "other_key": "initial_value",
            "string_setting": "some_value",
            "is_enabled": True,
            "timeout": 120,
            "format": ["a", "c d", "e"],
            "name": ["f", "g h", "i"],
            "paths": ["j", "k l", "m"],
            "tags": ["@t1", "@t2 and @t3", "@t4"],
            "outfiles": ["-"],
            "userdata_defines": [("key1", "value1"), ("key2", "value2"), ("key3", "value3")],
        }, "Loaded environment settings did not match expected dictionary structure or type conversion failed."

    def test_skip_non_systest_vars(  # pylint: disable=redefined-outer-name
        self, configuration_module_helper: ConfigurationModuleHelper
    ):
        """Test that environment variables without the SYSTEST_ prefix are ignored.

        Args:
            configuration_module_helper (ConfigurationModuleHelper): Helper for patching configuration.
        """
        defaults = {}
        configuration_module_helper.mock_func(
            "build_environment_values",
            {
                "SYSTEST_SETTING_A": "value_A",
                "OTHER_VAR": "should_be_ignored",
                "SYSTEST_SETTING_B": "value_B",
            },
        )

        configuration_module_helper.module.load_environment_settings(defaults)

        assert "other_var" not in defaults, "Defaults dictionary was polluted by a non-SYSTEST_ environment variable."
        assert defaults == {
            "setting_a": "value_A",
            "setting_b": "value_B",
        }, "Only SYSTEST_ prefixed variables should be loaded into defaults."

    def test_skip_empty_or_whitespace_values(  # pylint: disable=redefined-outer-name
        self, configuration_module_helper: ConfigurationModuleHelper
    ):
        """Test that environment variables with empty strings or whitespace-only values are skipped.

        Args:
            configuration_module_helper (ConfigurationModuleHelper): Helper for patching configuration.
        """
        defaults = {}
        configuration_module_helper.mock_func(
            "build_environment_values",
            {
                "SYSTEST_VAR_1": "valid",
                "SYSTEST_VAR_2": "",
                "SYSTEST_VAR_3": "   ",
                "SYSTEST_VAR_4": "  valid_again  ",
            },
        )

        configuration_module_helper.module.load_environment_settings(defaults)

        # Only VAR_1 and VAR_4 should be loaded (with stripped whitespace)
        assert defaults == {
            "var_1": "valid",
            "var_4": "valid_again",
        }, "Empty or whitespace-only environment variables were incorrectly loaded or stripped."

    def test_raise_error_on_excluded_options(  # pylint: disable=redefined-outer-name
        self, configuration_module_helper: ConfigurationModuleHelper
    ):
        """Test that using an option listed in ENV_EXCLUDED_OPTIONS raises ConfigError.

        Args:
            configuration_module_helper (ConfigurationModuleHelper): Helper for patching configuration.
        """
        defaults = {}
        configuration_module_helper.mock_func(
            "build_environment_values",
            {
                "SYSTEST_EXCLUDED": "should_fail",
            },
        )
        # Mock the exclusion set to include the tested variable name
        configuration_module_helper.mock_constant("ENV_EXCLUDED_OPTIONS", {"excluded"})

        match = re.escape("ENV[SYSTEST_EXCLUDED]: Setting 'excluded' cannot be specified as environment var.")
        with pytest.raises(ConfigError, match=match):
            configuration_module_helper.module.load_environment_settings(defaults)

    def test_handle_empty_config_name(  # pylint: disable=redefined-outer-name
        self, configuration_module_helper: ConfigurationModuleHelper
    ):
        """Test handling of environment variable with only the prefix (SYSTEST_).

        Args:
            configuration_module_helper (ConfigurationModuleHelper): Helper for patching configuration.
        """
        defaults = {}
        configuration_module_helper.mock_func(
            "build_environment_values",
            {
                "SYSTEST_": "some_value",
            },
        )

        configuration_module_helper.module.load_environment_settings(defaults)

        # The variable name (after stripping 'SYSTEST_') is empty, so it should be skipped
        assert not defaults, "Malformed SYSTEST_ environment variable polluted the defaults dictionary."

    @pytest.mark.run(order=999)
    def test_verbose_output(  # pylint: disable=redefined-outer-name
        self, configuration_module_helper: ConfigurationModuleHelper
    ):
        """Test that verbose logging is triggered and formatted correctly.

        Args:
            configuration_module_helper (ConfigurationModuleHelper): Helper for patching configuration.
        """
        defaults = {}

        # Define environment variables covering all test cases:
        configuration_module_helper.mock_func(
            "build_environment_values",
            {
                "SYSTEST_VAR": "",  # Skipped: empty value
                "SYSTEST_SETTING": "test_value",  # Loaded: standard value
                "SYSTEST_": "some_value",  # Skipped: malformed key
            },
        )

        configuration_module_helper.module.load_environment_settings(defaults, verbose=True)

        # CORRECTED: Get the output lines using the helper method
        output_lines = configuration_module_helper.get_output_lines()

        # --- Check the successfully loaded variable (SYSTEST_SETTING) ---
        expected_output_success = "setting         = 'test_value' (ENV[SYSTEST_SETTING] = 'test_value')"
        check_output(
            output_lines,
            expected_output_success,
            "Successful load message for 'SYSTEST_SETTING' was not found in verbose output.",
        )

        # --- Check skipped empty/whitespace variable (SYSTEST_VAR) ---
        expected_output_skip_empty = "Skipping ENV[SYSTEST_VAR]: Value is empty or whitespace."
        check_output(output_lines, expected_output_skip_empty, "Skipping message for 'SYSTEST_VAR' not found.")

        # --- Check skipped malformed variable (SYSTEST_) ---
        expected_output_start = (
            "Skipping ENV[SYSTEST_]: Configuration name is empty after stripping prefix ('SYSTEST_')."
        )
        check_output(output_lines, expected_output_start, "Skipping message for malformed key 'SYSTEST_' not found.")

        # Final sanity check: Ensure only the correct variable was loaded into defaults
        assert defaults == {
            "setting": "test_value"
        }, "Configuration defaults were incorrectly set or polluted by skipped environment variables."
