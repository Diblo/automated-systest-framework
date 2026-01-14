"""Behave configuration helpers tailored to systest."""

import argparse
import logging
import os
import shlex
import sys
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple, Union

from behave.configuration import COLOR_CHOICES
from behave.configuration import OPTIONS as BEHAVE_OPTIONS
from behave.configuration import Configuration as BehaveConfiguration
from behave.exception import ConfigError
from behave.reporter.base import Reporter
from behave.userdata import parse_user_define
from dotenv import dotenv_values

from ..constants import (
    DEFAULT_RUNNER,
    DEFAULT_SUITES_PATH,
    ENV_EXCLUDED_OPTIONS,
    ENV_SEQUENCE_OPTIONS,
    OPTIONS,
    USER_CONFIG,
    VERSION,
)
from ..exceptions import UnknownVersionType
from ..suite_manager import SuiteData, create_suite_data
from ..types import CommandArgs, DefaultValues, Options, override
from ..utils import parse_version, run_from_source
from .reporter.zephyr import ZephyrReporter
from .wrapper import ReporterWrapper

__all__ = ["Configuration"]


def build_environment_values(cli_file: Optional[Path] = None, verbose: Optional[bool] = None) -> Dict[str, str]:
    """Builds the complete configuration dictionary by loading values from environment
    and configuration sources in ascending order of precedence (lowest to highest).

    The order of loading (lowest precedence first) is:
    1. OS Environment Variables (Lowest)
    2. User Home Config (~/.systest)
    3. Project .env File (only in source mode)
    4. Specified Config File (CLI argument) (Highest)

    Args:
        cli_file (Optional[Path]): Optional path to a configuration file specified via CLI.
        verbose (Optional[bool]): If True, prints status messages about file loading.

    Returns:
        Dict[str, str]: Dictionary containing all environment key-value pairs.
    """
    # The loading order ensures correct precedence (Lowest Priority to Highest Priority).

    # OS Environment Variables (Priority 1)
    env_values = os.environ.copy()

    # User Home Config (~/.systest) (Priority 2)
    user_config_file = Path.home() / USER_CONFIG
    if user_config_file.exists():
        if verbose:
            print("Load user config file.")
        loaded_config = dotenv_values(user_config_file)
        if loaded_config is not None:
            env_values.update(loaded_config)
    elif verbose:
        print("Skipping: User config file not found.")

    # Project `.env` File (Priority 3 - Only loaded if running from source)
    if run_from_source():
        project_config_file = Path(__file__).absolute().parents[3] / ".env"
        if project_config_file.exists():
            if verbose:
                print("Load project config file.")
            loaded_config = dotenv_values(project_config_file)
            if loaded_config is not None:
                env_values.update(loaded_config)
        elif verbose:
            print("Skipping: Project config file not found.")
    elif verbose:
        print("Skipping: Loading project config file is omitted in production mode.")

    # Specified Config File (CLI argument) (Priority 4)
    if cli_file is not None:
        if not cli_file.exists():
            raise FileNotFoundError(f"The CLI specified config file not found at {str(cli_file)!r}.")
        if verbose:
            print("Load CLI config file.")
        loaded_config = dotenv_values(cli_file)
        if loaded_config is not None:
            env_values.update(loaded_config)
    elif verbose:
        print("Skipping: CLI config file was not specified.")

    return env_values


def load_environment_settings(
    defaults: DefaultValues, cli_file: Optional[Path] = None, verbose: Optional[bool] = None
) -> None:
    """Loads configuration settings from sources (ENV, config files).

    Applies the parsed values to the provided defaults dictionary.

    The function first builds the complete environment dictionary, then iterates
    over variables prefixed with 'SYSTEST_' to parse their values (boolean, int,
    list, or string) and update the 'defaults' dictionary accordingly.

    Args:
        defaults (DefaultValues): Defaults dictionary to update.
        cli_file (Optional[Path]): Optional path to a configuration file specified via CLI.
        verbose (Optional[bool]): If True, prints status messages about parsing.
    """

    env_values = build_environment_values(cli_file, verbose)

    # The subsequent loop ensures the variables are correctly parsed and applied to 'defaults'.
    for env_var, env_value in env_values.items():
        # Key filtering and extraction
        env_var_lowered = env_var.lower()
        if not env_var_lowered.startswith("systest_"):
            continue

        config_name = env_var_lowered[8:]
        if not config_name:
            if verbose:
                print(f"Skipping ENV[{env_var}]: Configuration name is empty after stripping prefix ('SYSTEST_').")
            continue

        if config_name in ENV_EXCLUDED_OPTIONS:
            raise ConfigError(f"ENV[{env_var}]: Setting {config_name!r} cannot be specified as environment var.")

        # Value parsing
        env_parsed_value = env_value.strip()
        if not env_parsed_value:
            if verbose:
                print(f"Skipping ENV[{env_var}]: Value is empty or whitespace.")
            continue

        env_value_lowered = env_parsed_value.lower()
        if env_value_lowered in ["true", "false"]:
            env_parsed_value = env_value_lowered == "true"
        elif env_parsed_value.isnumeric():
            env_parsed_value = int(env_parsed_value)
        elif config_name in ENV_SEQUENCE_OPTIONS:
            # Sequence value parsing
            # Note: shlex.split handles quoted strings correctly for complex list elements.
            env_parsed_value = shlex.split(env_parsed_value)

            if config_name == "userdata_defines":
                # Sequence value with userdata parsing
                env_parsed_value = [parse_user_define(element) for element in env_parsed_value]

        # Final application to defaults
        defaults[config_name] = env_parsed_value

        if verbose:
            print(f"{config_name:<15} = {env_parsed_value!r} (ENV[{env_var}] = {env_value!r})")


def auto_discover(
    command_args: Optional[CommandArgs] = None, verbose: Optional[bool] = None
) -> Tuple[Optional[Path], bool]:
    """Discover config file and verbosity settings from CLI arguments.

    Args:
        command_args (Optional[CommandArgs]): Command-line arguments to inspect.
        verbose (Optional[bool]): Overrides verbosity detection when provided.

    Returns:
        Tuple[Optional[Path], bool]: Tuple of CLI config path and verbosity flag.
    """
    # Config file from command-line args.
    cli_config = None
    if command_args and "--config" in command_args:
        config_arg_pos = command_args.index("--config")
        next_arg = command_args[config_arg_pos + 1]
        if os.path.exists(next_arg):
            cli_config = Path(next_arg)

    # Verbose mode from command-line args.
    if verbose is None:
        verbose = ("-v" in command_args) or ("--verbose" in command_args)

    return cli_config, verbose


def iter_behave_options(behave_options: Options) -> Iterator[Options]:
    """Filters Behave's internal option list, omitting flags that are already defined
    and handled by the systest framework, or are irrelevant for ArgumentParser.

    Args:
        behave_options (Options): Iterable of Behave options as
                                  (option_flags, keyword_arguments) tuples.

    Yields:
        Options: Filtered option tuples for configuration parsing.
    """
    # Calculate the set of all flag names known and handled by systest.
    # This set is used to skip conflicting options.
    systest_options = {flag for flags, _ in OPTIONS for flag in flags}

    # NOTE: Refer to Behave's source for the specific format of the options list
    #       (`behave.configuration.setup_parser` and `behave.configuration.OPTIONS`).
    for options_flags, keywords in behave_options:
        # Check 1: Skip options with no flags defined (malformed options).
        # Check 2: Skip options where flags conflict with systest's own defined flags.
        if not options_flags or set(options_flags) & systest_options:
            continue

        # The 'config_help' keyword is used by Behave's internal Configuration but is irrelevant
        # for ArgumentParser, so it is removed.
        if "config_help" in keywords:
            # NOTE: We copy the keywords dictionary before modification to avoid
            # side effects on the original Behave OPTIONS list.
            keywords = keywords.copy()
            del keywords["config_help"]

        yield (options_flags, keywords)


def setup_main_parser() -> argparse.ArgumentParser:
    """Construct the ArgumentParser.

    It incorporates systest options, and all standard behave options.

    Returns:
        argparse.ArgumentParser: Configured ArgumentParser instance.
    """
    prog = "systest"
    usage = "%(prog)s -s SUITE [options] [paths ...]"
    description = """Run a number of feature tests with %(prog)s.

EXAMPLES:
  %(prog)s --suite r2d2-dev
  %(prog)s --suite r2d2-dev battery
  %(prog)s --suite r2d2-dev battery/levels.feature battery/healthy.feature
  %(prog)s --suite r2d2-dev battery/healthy.feature:10
  %(prog)s --suite r2d2-dev @features.txt
"""

    formatter_class = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(prog=prog, usage=usage, description=description, formatter_class=formatter_class)

    for arguments, keywords in OPTIONS:
        parser.add_argument(*arguments, **keywords)

    for arguments, keywords in iter_behave_options(BEHAVE_OPTIONS):
        parser.add_argument(*arguments, **keywords)

    parser.add_argument(
        "paths",
        nargs="*",
        help="Feature directories, files, scenarios (FILE:LINE), or @files. Defaults to all features if unspecified.",
    )

    return parser


# pylint: disable=too-many-instance-attributes
class Configuration(BehaveConfiguration):
    """
    Central configuration class for the systest framework.
    Extends behave Configuration to manage systest-specific settings.
    """

    defaults: DefaultValues = {
        **BehaveConfiguration.defaults,
        "runner": DEFAULT_RUNNER,
        "logging_level": logging.ERROR,
    }
    """Behave defaults extended with systest overrides."""

    systest_defaults: DefaultValues = {
        "suites_directory": DEFAULT_SUITES_PATH,
        "suite": None,
        "suite_create": None,
        "cycle_id": None,
    }
    """Default values for systest-specific settings."""

    # This will be set by the runner
    base_dir: str = ""
    """Base directory for the current feature area."""

    @override
    def __init__(
        self,
        command_args: Optional[CommandArgs] = None,
        load_config: bool = True,
        verbose: Optional[bool] = None,
        **kwargs: DefaultValues,
    ) -> None:
        """Initializes configuration by loading defaults, kwargs, config file,
        env vars, and parsing CLI arguments.

        Args:
            command_args (Optional[CommandArgs]): Command-line arguments (defaults to sys.argv[1:]).
            load_config (bool): If True, loads settings from config files.
            verbose (Optional[bool]): Overrides the verbosity setting.
        """
        command_args = self.make_command_args(command_args, verbose)
        cli_config, verbose = auto_discover(command_args, verbose)

        defaults = Configuration.make_defaults(**kwargs)

        # 1. Load environment settings (SYSTEST_ prefix) into defaults
        load_environment_settings(defaults, cli_config, verbose)

        # 2. Setup the Master Parser for Validation/Help.
        # This parser contains ALL options (systest + behave).
        parser = setup_main_parser()
        parser.set_defaults(**defaults)
        parser.parse_args(command_args)

        # 3. Separate systest-specific CLI args from Behave CLI args
        systes_parsed_args, behave_command_args = Configuration.parse_systest_args(command_args, **defaults)

        # 4. Initialize Behave Configuration
        super().__init__(command_args=behave_command_args, load_config=load_config, verbose=verbose, **defaults)

        # 5. Apply the parsed arguments
        for key, value in systes_parsed_args.__dict__.items():
            if key.startswith("_"):
                continue
            setattr(self, key, value)

        # 6. Finalize setup
        self.setup_suites()
        self.setup_suite_create(parser)
        self.setup_suite(parser)
        self.setup_systest_reporters()
        self.wrap_reporters()

    @override
    def init(self, verbose: Optional[bool] = None, **kwargs: DefaultValues) -> None:
        """Initializes internal state.

        Args:
            verbose (Optional[bool]): Verbosity setting.
            **kwargs (DefaultValues): Hand-over configuration dictionary.
        """
        super().init(verbose=verbose, **kwargs)

        self.lang: str = "en"

        # Initialize other required attributes
        self.suites_directory: Union[str, Path] = Path()
        self.suite: Optional[str] = None
        self.suite_data: SuiteData = SuiteData()
        self.create_suite_name: Optional[str] = None
        self.cycle_id: Optional[str] = None
        self.run_version: str = VERSION

    @override
    @classmethod
    def make_defaults(cls, **kwargs: DefaultValues) -> DefaultValues:
        """Build default values for a configuration instance.

        Args:
            **kwargs (DefaultValues): Values overriding defaults.

        Returns:
            DefaultValues: Merged defaults for Configuration.
        """
        defaults = cls.systest_defaults.copy()
        defaults.update(kwargs)
        return super().make_defaults(**defaults)

    @override
    def make_command_args(
        self, command_args: Optional[CommandArgs] = None, verbose: Optional[bool] = None
    ) -> CommandArgs:
        """Normalize command arguments before parsing.

        Args:
            command_args (Optional[CommandArgs]): Raw command arguments.
            verbose (Optional[bool]): Verbosity flag used during parsing.

        Returns:
            CommandArgs: Normalized argument list.
        """
        if command_args is None:
            command_args = sys.argv[1:]

        # HACK: The hack in parent.make_command_args() will not work with systest.
        #       To fix this for systest, the logic should be changed from checking
        #       if the next argument is an existing path (as the folder may not be resolvable)
        #       to checking if it is a valid value from the color choices.
        #
        # SUPPORTS:
        #   behave --color feature_area/some.feature        # PROBLEM-POINT
        #   behave --color=auto feature_area/some.feature   # NO_PROBLEM
        #   behave --color auto feature_area/some.feature   # NO_PROBLEM
        if "--color" in command_args:
            color_arg_pos = command_args.index("--color")
            next_arg = command_args[color_arg_pos + 1]
            if next_arg not in COLOR_CHOICES:
                command_args.insert(color_arg_pos + 1, "auto")

        return super().make_command_args(command_args=command_args, verbose=verbose)

    @classmethod
    def parse_systest_args(
        cls, command_args: CommandArgs, **kwargs: DefaultValues
    ) -> Tuple[argparse.Namespace, CommandArgs]:
        """Parse CLI arguments into systest and behave portions.

        Args:
            command_args (CommandArgs): List of command-line arguments.
            **kwargs (DefaultValues): Default values used for options.

        Returns:
            Tuple[argparse.Namespace, CommandArgs]: Parsed systest args and remaining args.
        """
        # Create a temporary parser with only the local (systest) options.
        # add_help=False is crucial to prevent this parser from exiting/printing help.
        parser = argparse.ArgumentParser(add_help=False)
        for arguments, keywords in OPTIONS:
            parser.add_argument(*arguments, **keywords)

        systest_defaults = cls.systest_defaults.copy()
        parser.set_defaults(**{key: kwargs.get(key, value) for key, value in systest_defaults.items()})

        # parse_known_args consumes the systest options, leaving the rest.
        return parser.parse_known_args(command_args)

    def setup_suites(self) -> None:
        """Validate and normalize the suites directory path."""
        if isinstance(self.suites_directory, str):
            self.suites_directory = Path(self.suites_directory)

        self.suites_directory = self.suites_directory.absolute()

        if not self.suites_directory.is_dir():
            raise ConfigError(f"Suites directory not found: {self.suites_directory!r}")

    def setup_suite_create(self, parser: argparse.ArgumentParser) -> None:
        """Validate suite creation arguments.

        Args:
            parser (argparse.ArgumentParser): Parser for reporting CLI errors.
        """
        if self.create_suite_name is None:
            return

        if not self.create_suite_name:
            parser.error("No Test Suite name is specified.")

        suite_path = self.suites_directory / self.create_suite_name
        if suite_path.exists():
            parser.error(f"The Test Suite already exists: {suite_path!r}")

    def setup_suite(self, parser: argparse.ArgumentParser) -> None:
        """Validate and resolve suite paths and configuration.

        Args:
            parser (argparse.ArgumentParser): Parser for reporting CLI errors.

        Raises:
            ConfigError: If the suite paths, folders, or version are invalid.
        """
        is_utility_mode = any(
            [
                self.version,
                self.tags_help,
                self.lang == "help",
                self.lang_list,
                self.lang_help,
                isinstance(self.format, list) and "help" in self.format,
                self.create_suite_name is not None,
            ]
        )

        if self.suite is None:
            if not is_utility_mode:
                parser.error("No Test Suite specified. Use --help for more info.")
            return

        self.suite_data = create_suite_data(self.suite, self.suites_directory)

        if not self.suite_data.suite_exists():
            raise ConfigError(
                "The test suite directory was not found for the test suite "
                f"{self.suite_data.name!r} (expected: {self.suite_data.path!r})"
            )

        if not self.suite_data.suite_is_valide():
            if not self.suite_data.features_path.is_dir():
                raise ConfigError(
                    "The test suite features directory was not found for the test suite "
                    f"{self.suite_data.name!r} (expected: {self.suite_data.features_path!r})"
                )

            raise ConfigError(
                "The test suite support directory was not found for the test suite "
                f"{self.suite_data.name!r} (expected: {self.suite_data.support_path!r})"
            )

        try:
            parse_version(self.suite_data.framework_version)
        except UnknownVersionType as e:
            raise ConfigError(
                f"The framework_version specified in {self.suite_data.name!r} "
                f"is invalid: {self.suite_data.framework_version!r}"
            ) from e
        self.run_version = self.suite_data.framework_version

    def setup_systest_reporters(self) -> None:
        """Attach systest-specific reporters based on configuration."""
        if self.cycle_id:
            self.reporters.append(ZephyrReporter(self))

    def wrap_reporters(self) -> None:
        """Wrap behave reporters to delay lifecycle end."""
        self.reporters = [ReporterWrapper(reporter) for reporter in self.reporters if isinstance(reporter, Reporter)]
