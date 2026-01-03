import argparse
import logging
import os
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

from behave.configuration import COLOR_CHOICES
from behave.configuration import OPTIONS as BEHAVE_OPTIONS
from behave.configuration import Configuration as BehaveConfiguration
from behave.exception import ConfigError
from behave.formatter.base import StreamOpener
from behave.reporter.base import Reporter
from dotenv import dotenv_values

from ..suite_manager import SuiteData, create_suite_data

from ..constants import (
    DEFAULT_RUNNER,
    DEFAULT_SUITES_PATH,
    EXCLUDED_OPTION_DEFAULTS,
    SEQUENCE_OPTIONS,
    OPTIONS,
    USER_CONFIG,
)
from ..types import CommandArgs, DefaultValues, Options, override
from .reporter.zephyr import ZephyrReporter
from .wrapper import ReporterWrapper

__all__ = ["Configuration"]


def build_environment_values(cli_file: Optional[Path] = None, verbose: Optional[bool] = None) -> Dict[str, Union[str, None]]:
    """Builds the complete configuration dictionary by loading values from environment
    and configuration sources in ascending order of precedence (lowest to highest).

    The order of loading (lowest precedence first) is:
    1. OS Environment Variables (Lowest)
    2. User Home Config (~/.systest)
    3. Project .env File (only in source mode)
    4. Specified Config File (CLI argument) (Highest)

    Args:
        cli_file: Optional path to a configuration file specified via CLI.
        verbose: If True, prints status messages about file loading.

    Returns:
        A dictionary containing all environment key-value pairs.
    """
    # The loading order ensures correct precedence (Lowest Priority to Highest Priority).

    # OS Environment Variables (Priority 1)
    env_values = cast(Dict[str, Union[str, None]], os.environ.copy())

    # User Home Config (~/.systest) (Priority 2)
    user_config_file = Path.home() / USER_CONFIG
    if user_config_file.exists():
        if verbose:
            print("Load user config file.")
        env_values.update(dotenv_values(user_config_file))
    elif verbose:
        print("Skipping: User config file not found.")

    # Project `.env` File (Priority 3 - Only loaded if running from source)
    if os.environ.get("_SYSTEST_SOURCE") == "true":
        project_config_file = Path(__file__).absolute().parents[3] / ".env"
        if project_config_file.exists():
            if verbose:
                print("Load project config file.")
            env_values.update(dotenv_values(project_config_file))
        elif verbose:
            print("Skipping: Project config file not found.")
    elif verbose:
        print("Skipping: Loading project config file is omitted in production mode.")

    # Specified Config File (CLI argument) (Priority 4)
    if cli_file is not None:
        if not cli_file.exists():
            raise FileNotFoundError(
                f"The CLI specified config file not found at {str(cli_file)!r}.")
        if verbose:
            print("Load CLI config file.")
        env_values.update(dotenv_values(cli_file))
    elif verbose:
        print("Skipping: CLI config file was not specified.")

    return env_values


def _unqote(text: str):
    """Strip pair of leading and trailing quotes from text."""
    # -- QUOTED: Strip single-quote or double-quote pair.
    if ((text.startswith('"') and text.endswith('"')) or
            (text.startswith("'") and text.endswith("'"))):
        text = text[1:-1]
    return text


def parse_user_define(text: str) -> Tuple[str, str]:
    """Parse a user-defined data.

    Args:
        text (str): Text to parse (as string)

    SUPPORTED SCHEMA:

      * "{name}={value}"
      * "{name}"                (boolean flag; value="true")
      * '"{name}={value}"'      (double-quoted name-value pair)
      * "'{name}={value}'"      (single-quoted name-value pair)
      * '{name}="{value}"'      (double-quoted value)
      * "{name}='{value}'"      (single-quoted value)
      * "  {name} = {value}  "  (whitespace padded)

    Returns:
        Tuple[str, str]: A tuple `(name, value)` where `name` is the definition
                         key and `value` is the associated value.
    """
    text = text.strip()
    if "=" in text:
        text = _unqote(text)
        name, value = text.split("=", 1)
        name = name.strip()
        value = _unqote(value.strip())
    else:
        # -- ASSUMPTION: Boolean definition (as flag)
        name = text
        value = "true"
    return (name, value)


def load_configuration(cli_file: Optional[Path] = None, verbose: Optional[bool] = None) -> DefaultValues:
    """Loads configuration settings from sources (ENV, config files)
    and applies them to the default valuess dictionary.

    The function first builds the complete environment dictionary, then iterates
    over variables prefixed with 'SYSTEST_' to parse their values (boolean, int,
    list, or string).

    Args:
        cli_file: Optional path to a configuration file specified via CLI.
        verbose: If True, prints status messages about environment variable loading and parsing.
    """
    defaults: DefaultValues = {}
    env_values = _build_environment_values(cli_file, verbose)

    # The subsequent loop ensures the variables are correctly parsed and applied to 'defaults'.
    for env_var, env_value in env_values.items():
        # Key filtering and extraction
        env_var_lowered = env_var.lower()
        if not env_var_lowered.startswith("systest_"):
            continue

        config_name = env_var_lowered[8:]
        if not config_name:
            if verbose:
                print(
                    f"Skipping ENV[{env_var}]: Configuration name is empty after stripping prefix ('SYSTEST_').")
            continue

        if config_name in EXCLUDED_OPTION_DEFAULTS:
            raise ConfigError(
                f"ENV[{env_var}]: Setting {config_name!r} cannot be specified as environment var.")

        if not env_value:
            if verbose:
                print(
                    f"Skipping ENV[{env_var}]: Value is empty or whitespace.")
            continue

        # Value parsing
        env_parsed_value = env_value.strip()

        env_value_lowered = env_parsed_value.lower()
        if env_value_lowered in ["true", "false"]:
            defaults[config_name] = env_value_lowered == "true"
        elif env_parsed_value.isnumeric():
            defaults[config_name] = int(env_parsed_value)
        elif config_name in SEQUENCE_OPTIONS:
            # Sequence value parsing
            # Note: shlex.split handles quoted strings correctly for complex list elements.
            env_split_values = shlex.split(env_parsed_value)

            if config_name == "userdata_defines":
                # Sequence value with userdata parsing
                defaults[config_name] = [parse_user_define(
                    element) for element in env_split_values]
            else:
                defaults[config_name] = env_split_values
        else:
            # Final application to defaults
            defaults[config_name] = env_parsed_value

        if verbose:
            print(
                f"{config_name:<15} = {env_parsed_value!r} (ENV[{env_var}] = {env_value!r})")

    return defaults


def auto_discover(command_args: Optional[CommandArgs] = None, verbose: Optional[bool] = None) -> Tuple[Optional[Path], bool]:
    # Config file from command-line args.
    cli_config = None
    if command_args and "--config" in command_args:
        config_arg_pos = command_args.index("--config")
        next_arg = command_args[config_arg_pos + 1]
        if os.path.exists(next_arg):
            cli_config = Path(next_arg)

    # Verbose mode from command-line args.
    if verbose is None and command_args is not None:
        verbose = ("-v" in command_args) or ("--verbose" in command_args)
    else:
        verbose = False

    return cli_config, verbose


class Parser:
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

    def __init__(self, defaults: DefaultValues | None = None) -> None:
        self.systest_options: Options = []
        self.systest_dest: List[str] = []
        self.systest_defaults: DefaultValues = {
            "suites_directory": DEFAULT_SUITES_PATH,
            "suite": None,
            "create_suite_name": None,
            "cycle_id": None,
        }

        self.behave_options: Options = []
        self.behave_dest: List[str] = ["paths"]
        self.behave_defaults: DefaultValues = {
            **BehaveConfiguration.defaults,
            "runner": DEFAULT_RUNNER,
            "logging_level": logging.ERROR,
            "lang": "en",
        }

        self._load_options()

        if defaults:
            for key, value in defaults.items():
                if key in EXCLUDED_OPTION_DEFAULTS:
                    continue
                if key in self.systest_dest:
                    self.systest_defaults[key] = value
                elif key in self.behave_dest:
                    self.behave_defaults[key] = value

        self.parser = self._create_parser()

    def _load_options(self) -> None:
        def _resolve_dest(args: tuple[str, ...], keywords: dict[str, Any]) -> str:
            parser = argparse.ArgumentParser(add_help=False)
            action = parser.add_argument(*args, **keywords)
            return action.dest

        systest_arguments: Set[str] = set()

        # Systest options
        for args, keywords in OPTIONS:
            self.systest_options.append((args, keywords))
            systest_arguments.update(args)

            dest = _resolve_dest(args, keywords)
            self.systest_dest.append(dest)

            if "default" in keywords:
                self.systest_defaults[dest] = keywords["default"]

        # Behave options (filtered)
        for args, keywords in cast(Options, BEHAVE_OPTIONS):
            if not args or set(args) & systest_arguments:
                continue

            if "config_help" in keywords:
                # NOTE: We copy the keywords dictionary before modification to avoid
                # side effects on the original Behave OPTIONS list.
                keywords = keywords.copy()
                del keywords["config_help"]

            self.behave_options.append((args, keywords))

            dest = _resolve_dest(args, keywords)
            self.behave_dest.append(dest)

            if "default" in keywords:
                self.behave_defaults[dest] = keywords["default"]

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog=self.prog,
            usage=self.usage,
            description=self.description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        for arguments, keywords in self.systest_options:
            parser.add_argument(*arguments, **keywords)

        for arguments, keywords in self.behave_options:
            parser.add_argument(*arguments, **keywords)

        parser.add_argument(
            "paths",
            nargs="*",
            help=(
                "Feature directories, files, scenarios (FILE:LINE), or @files. Defaults to all features if unspecified."
            ),
        )

        parser.set_defaults(**self.systest_defaults, **self.behave_defaults)

        return parser

    def parse_args(self, command_args: CommandArgs) -> Tuple[argparse.Namespace, CommandArgs]:
        # Validate and provide help/errors based on the full option set
        self.parser.parse_args(command_args)

        # Parse systest-only args, leave behave args untouched
        parser = argparse.ArgumentParser(add_help=False)
        for arguments, keywords in self.systest_options:
            parser.add_argument(*arguments, **keywords)

        parser.set_defaults(**self.systest_defaults)
        return parser.parse_known_args(command_args)

    def error(self, message: str) -> None:
        self.parser.error(message)


class Configuration(BehaveConfiguration):
    """
    Central configuration class for the systest framework.
    Extends behave Configuration to manage systest-specific settings.
    """
    version: Optional[bool] = None
    verbose: Optional[bool] = None
    environment_file: str = ""
    steps_dir: str = ""
    use_nested_step_modules: bool = False
    paths: List[str] = []
    outputs: List[StreamOpener] = []
    stop: bool = False
    reporters: List[Union[Reporter, ReporterWrapper]] = []
    format: List[str] = []
    lang: str = ""

    # This will be set by the runner
    base_dir: str = ""

    @override
    def __init__(self, command_args: Optional[CommandArgs] = None, verbose: Optional[bool] = None):
        """Initializes configuration by loading defaults, kwargs, config file,
        env vars, and parsing CLI arguments.

        Args:
            command_args (CommandArgs): List of command-line arguments (defaults to sys.argv[1:]).
            verbose (Optional[bool]): Overrides the verbosity setting (Defaults to None).
        """
        command_args = self.make_command_args(command_args, verbose)
        cli_config, verbose = auto_discover(command_args, verbose)

        defaults = load_configuration(cli_config, verbose)

        parser = Parser(defaults)
        systes_parsed_args, behave_command_args = parser.parse_args(
            command_args)

        # 4. Initialize Behave Configuration
        super(Configuration, self).__init__(
            command_args=behave_command_args,
            load_config=False,
            verbose=verbose,
            **parser.systest_defaults,
            **parser.behave_defaults
        )

        # 5. Apply the parsed arguments
        for dest in parser.systest_dest:
            setattr(self, dest, getattr(systes_parsed_args, dest))

        # 6. Finalize setup
        self.setup_suites()
        self.setup_create_suite(parser)
        self.setup_suite(parser)
        self.setup_systest_reporters()
        self.wrap_reporters()

    @override
    def init(self, verbose: Optional[bool] = None, **kwargs: DefaultValues):
        """Initializes internal state.

        Args:
            verbose (Optional[bool], optional): Verbosity setting. Defaults to None.
            **kwargs (DefaultValues): Hand-over configuration dictionary.
        """
        super(Configuration, self).init(verbose=verbose, **kwargs)

        # Initialize other required attributes
        self.suites_directory: Union[str, Path] = Path()
        self.suites_directory_path: Path = Path()
        self.suite: Optional[str] = None
        self.create_suite_name: Optional[str] = None
        self.cycle_id: Optional[str] = None

        self.suite_data: SuiteData = SuiteData()

    @override
    def make_command_args(self, command_args: Optional[CommandArgs] = None, verbose: Optional[bool] = None) -> CommandArgs:
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

        return super(Configuration, self).make_command_args(command_args=command_args, verbose=verbose)

    def setup_suites(self):
        if isinstance(self.suites_directory, str):
            self.suites_directory_path = Path(self.suites_directory).absolute()
        else:
            self.suites_directory_path = self.suites_directory.absolute()

        if not self.suites_directory_path.is_dir():
            raise ConfigError(
                f"Suites directory not found: {self.suites_directory!r}")

    def setup_create_suite(self, parser: Parser):
        if self.create_suite_name is None:
            return

        if not self.create_suite_name:
            parser.error("No Test Suite name is specified.")

        suite_path = self.suites_directory_path / self.create_suite_name
        if suite_path.exists():
            parser.error(f"The Test Suite already exists: {suite_path!r}")

    def setup_suite(self, parser: Parser):
        is_utility_mode = any(
            [
                self.version,
                self.tags_help,
                self.lang == "help",
                self.lang_list,
                self.lang_help,
                "help" in self.format,
                self.create_suite_name is not None,
            ]
        )

        if is_utility_mode or self.suite is None or not self.suite.strip():
            if not is_utility_mode:
                parser.error(
                    "No Test Suite specified. Use --help for more info.")
            return

        self.suite_data = create_suite_data(
            self.suite, self.suites_directory_path)

        # Suite Directory
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

    def setup_systest_reporters(self):
        if self.cycle_id:
            self.reporters.append(ZephyrReporter(self))

    def wrap_reporters(self):
        self.reporters = [ReporterWrapper(
            reporter) for reporter in self.reporters if isinstance(reporter, Reporter)]
