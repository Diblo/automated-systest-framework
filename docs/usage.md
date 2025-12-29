# Usage

## Contents

1. [Test Execution](#test-execution)
1. [Test Execution Levels](#test-execution-levels)
1. [Advanced Test Execution](#advanced-test-execution)
1. [Command Arguments](#command-arguments)
1. [Configuration](#configuration)
1. [AT File](#at-file)

## Test Execution

To execute system tests, use the `systest` command. You must always specify a **Test Suite**, and you can optionally
limit the run to specific **paths**.

### Command Syntax

```shell
systest -s SUITE [options] [paths ...]
```

The `--suite` (or `-s`) argument tells `systest` which collection of tests to load. The command searches the current
working directory (or the path defined in `SYSTEST_SUITES_DIRECTORY`) for a matching folder.

**Example:**

```shell
systest -s mock
```

### Paths Mapping

To understand how paths map to your files, consider this structure:

```text
suites/               <-- Root Directory
└── mock/             <-- SUITE (-s mock)
    └── features/
        ├── login/    <-- Feature area (systest -s mock login)
        │   ├── valid_login.feature   (systest -s mock login/valid_login.feature)
        │   └── invalid_login.feature (systest -s mock login/invalid_login.feature)
        └── signup/   <-- Feature area (systest -s mock signup)
            └── ...
```

## Test Execution Levels

The execution level is determined by the positional arguments:

| Invocation Level           | Command                                                                                                             | Description                                                                                                           |
| :------------------------- | :------------------------------------------------------------------------------------------------------------------ | :-------------------------------------------------------------------------------------------------------------------- |
| **Entire Suite**           | `systest -s mock`                                                                                                   | Runs all features within the specified test suite.                                                                    |
| **Feature Area**           | `systest -s mock foo_bar_initialization`                                                                            | Runs all features and scenarios within the specified feature area directory (`<test suite>/features/<feature area>`). |
| **Feature Areas**          | `systest -s mock foo_bar_initialization foo_bar_setup`                                                              | Runs all features and scenarios in all specified feature area directories.                                            |
| **Specific Feature File**  | `systest -s mock foo_bar_initialization/foo_bar_initialize.feature`                                                 | Runs all scenarios within one specific feature file.                                                                  |
| **Specific Feature Files** | `systest -s mock foo_bar_initialization/foo_bar_initialize.feature foo_bar_setup/foo_bar_config_steps.feature`      | Runs all scenarios within all specified feature files.                                                                |
| **Specific Scenario**      | `systest -s mock foo_bar_initialization/foo_bar_initialize.feature:12`                                              | Runs only the scenario starting on line 12 of the feature file.                                                       |
| **Specific Scenarios**     | `systest -s mock foo_bar_initialization/foo_bar_initialize.feature:12 foo_bar_setup/foo_bar_config_steps.feature:8` | Runs only the specific scenarios identified by the file path and line number combinations.                            |

**Example of Execution Output**

```shell
user@hostname:~$ systest -s mock foo_bar_initialization/foo_bar_initialize.feature:12
USING RUNNER: systest.systest_behave.runner:SystestRunner
@SIR-17 @bar @context
Feature: Bar Context Initialization # mock_suite/features/foo_bar_initialization/foo_bar_initialize.feature:2
  As a developer
  I want the Bar context to be initialized
  So that I can verify its availability
  @SIR-17 @bar @context
  Feature: Bar Context Initialization  # mock_suite/features/foo_bar_initialization/foo_bar_initialize.feature:2

  @SIR-T13
  Scenario: Successful Initialization and Object Availability  # mock_suite/features/foo_bar_initialization/foo_bar_initialize.feature:12
    Given initialized the foo_bar_initialization background    # mock_suite/features/foo_bar_initialization/steps/foo_bar_initialize_steps.py:8 0.501s
    Given the Bar context has not been initialized             # mock_suite/features/foo_bar_initialization/steps/foo_bar_initialize_steps.py:13 0.000s
    When the Bar context is initialized                        # mock_suite/features/foo_bar_initialization/steps/foo_bar_initialize_steps.py:24 0.000s
    Then the Bar object has a valid, unique identifier         # mock_suite/features/foo_bar_initialization/steps/foo_bar_initialize_steps.py:42 0.000s

  @SIR-T25
  Scenario Outline: Verify the Bar object has the expected methods -- @1.1 Methods  # mock_suite/features/foo_bar_initialization/foo_bar_initialize.feature:25
    Given initialized the foo_bar_initialization background                         # None
    Given the Bar context has not been initialized                                  # None
    When the Bar context is initialized                                             # None
    Then the Bar object exposes the 'set_dry_run' method                            # None

  @SIR-T25
  Scenario Outline: Verify the Bar object has the expected methods -- @1.2 Methods  # mock_suite/features/foo_bar_initialization/foo_bar_initialize.feature:26
    Given initialized the foo_bar_initialization background                         # None
    Given the Bar context has not been initialized                                  # None
    When the Bar context is initialized                                             # None
    Then the Bar object exposes the 'get_dry_run' method                            # None

[...]

1 feature passed, 0 failed, 0 skipped
1 scenario passed, 0 failed, 6 skipped
4 steps passed, 0 failed, 24 skipped
Took 0min 0.501s
```

## Advanced Test Execution

The execution of test suites can be precisely controlled by combining **path filtering** with **options**.

| Example Command                                   | Purpose                                                                                                                                                                                                     |
| :------------------------------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `systest -s mock -t @smoke`                       | Runs only **scenarios tagged** with `@smoke` within the `mock` suite.                                                                                                                                       |
| `systest -s mock foo_bar_setup/foo_bar_*.feature` | Runs all feature files within the `foo_bar_setup` directory whose filename matches the pattern `foo_bar_*.feature`.                                                                                         |
| `systest -s mock foo_bar_initialization --stop`   | Runs all feature files in the `foo_bar_initialization` directory for the `mock` suite and **stops on the first failure** encountered during execution.                                                      |
| `systest -s mock @smoke_features.txt`             | Runs the test specified in the **AT file** (`smoke_features.txt`). The file contains execution targets defined by **DIRECTORY**, **FILE**, or **FILE:LINE** entries.<br>See the section [AT File](#at-file) |

## Command Arguments

The `systest` command supports a wide array of options for granular control over execution, logging, and reporting.

**paths**

Feature directories, files, scenarios (FILE:LINE), or @files. Defaults to all features if unspecified.

(environment variable: `SYSTEST_PATHS`)

**-s SUITE, --suite SUITE**

The test suite to execute (e.g., 'mock', 'r2d2-3.2.1').

(environment variable: None)

**--suites-dir SUITES_DIRECTORY**

The directory containing all test suites folders.

(environment variable: `SYSTEST_SUITES_DIRECTORY`)

**--create-suite CREATE_SUITE_NAME**

Creates a new test suite directory structure, named by the argument.

(environment variable: None)

**--config CONFIG**

Specify the path to a configuration file.

(environment variable: None)

**-C, --no-color**

Disable colored mode.

(environment variable: `SYSTEST_COLOR`)

**--color \[auto,on,off,always,never\]**

Use colored mode or not (default: auto).

(environment variable: `SYSTEST_COLOR`)

**-d, --dry-run**

Invokes formatters without executing the steps.

(environment variable: `SYSTEST_DRY_RUN`)

**-D NAME=VALUE, --define NAME=VALUE**

Define user-specific data for the config.userdata dictionary. Example: -D foo=bar to store it in
config.userdata\["foo"\]. Can be specified multiple times.

(environment variable: `SYSTEST_USERDATA_DEFINES`)

**-e PATTERN, --exclude PATTERN**

Don't run feature files matching regular expression PATTERN.

(environment variable: `SYSTEST_EXCLUDE_RE`)

**-i PATTERN, --include PATTERN**

Only run feature files matching regular expression PATTERN.

(environment variable: `SYSTEST_INCLUDE_RE`)

**--no-junit**

Don't output JUnit-compatible reports.

(environment variable: `SYSTEST_JUNIT`)

**--junit**

Output JUnit-compatible reports. When junit is enabled, all stdout and stderr will be redirected and dumped to the junit
report, regardless of the "--capture" and "--no-capture" options.

(environment variable: `SYSTEST_JUNIT`)

**--junit-directory PATH**

Directory in which to store JUnit reports.

(environment variable: `SYSTEST_JUNIT_DIRECTORY`)

**-j NUMBER, --jobs NUMBER, --parallel NUMBER**

Number of concurrent jobs to use (default: 1). Only supported by test runners that support parallel execution.

(environment variable: `SYSTEST_JOBS`)

**-f FORMATTER, --format FORMATTER**

Specify a formatter. If none is specified the default formatter is used. Pass "--format help" to get a list of available
formatters. Can be specified multiple times.

(environment variable: `SYSTEST_FORMAT`)

**--steps-catalog**

Show a catalog of all available step definitions. SAME AS: "--format=steps.catalog --dry-run --no-summary -q".

(environment variable: `SYSTEST_STEPS_CATALOG`)

**--no-skipped**

Don't print skipped steps (due to tags).

(environment variable: `SYSTEST_SHOW_SKIPPED`)

**--show-skipped**

Print skipped steps. This is the default behaviour. This switch is used to override a configuration file setting.

(environment variable: `SYSTEST_SHOW_SKIPPED`)

**--no-snippets**

Don't print snippets for unimplemented steps.

(environment variable: `SYSTEST_SHOW_SNIPPETS`)

**--snippets**

Print snippets for unimplemented steps. This is the default behaviour. This switch is used to override a configuration
file setting.

(environment variable: `SYSTEST_SHOW_SNIPPETS`)

**--no-multiline**

Don't print multiline strings and tables under steps.

(environment variable: `SYSTEST_SHOW_MULTILINE`)

**--multiline**

Print multiline strings and tables under steps. This is the default behaviour. This switch is used to override a
configuration file setting.

(environment variable: `SYSTEST_SHOW_MULTILINE`)

**-n NAME_PATTERN, --name NAME_PATTERN**

Select feature elements (scenarios, ...) to run which match part of the given name (regex pattern). If this option is
given more than once, it will match against all the given names. Can be specified multiple times.

(environment variable: `SYSTEST_NAME`)

**--capture**

Enable capture mode (stdout/stderr/log-output). Any capture output will be printed on a failure/error.

(environment variable: `SYSTEST_CAPTURE`)

**--no-capture**

Disable capture mode (stdout/stderr/log-output).

(environment variable: `SYSTEST_CAPTURE`)

**--capture-stdout**

Enable capture of stdout.

(environment variable: `SYSTEST_CAPTURE_STDOUT`)

**--no-capture-stdout**

Disable capture of stdout.

(environment variable: `SYSTEST_CAPTURE_STDOUT`)

**--capture-stderr**

Enable capture of stderr.

(environment variable: `SYSTEST_CAPTURE_STDERR`)

**--no-capture-stderr**

Disable capture of stderr.

(environment variable: `SYSTEST_CAPTURE_STDERR`)

**--capture-log, --logcapture**

Enable capture of logging output.

(environment variable: `SYSTEST_CAPTURE_LOG`)

**--no-capture-log, --no-logcapture**

Disable capture of logging output.

(environment variable: `SYSTEST_CAPTURE_LOG`)

**--capture-hooks**

Enable capture of hooks (except: before_all).

(environment variable: `SYSTEST_CAPTURE_HOOKS`)

**--no-capture-hooks**

Disable capture of hooks.

(environment variable: `SYSTEST_CAPTURE_HOOKS`)

**--logging-level LOG_LEVEL**

Specify a level to capture logging at. The default is INFO - capturing everything.

(environment variable: `SYSTEST_LOGGING_LEVEL`)

**--logging-format LOG_FORMAT**

Specify custom format to print statements. Uses the same format as used by standard logging handlers. The default is
"%(levelname)s:%(name)s:%(message)s".

(environment variable: `SYSTEST_LOGGING_FORMAT`)

**--logging-datefmt LOG_DATE_FORMAT**

Specify custom date/time format to print statements. Uses the same format as used by standard logging handlers.

(environment variable: `SYSTEST_LOGGING_DATEFMT`)

**--logging-filter LOG_FILTER**

Specify which statements to filter in/out. By default, everything is captured. If the output is too verbose, use this
option to filter out needless output. Example: --logging-filter=foo will capture statements issued ONLY to foo or
foo.what.ever.sub but not foobar or other logger. Specify multiple loggers with comma: filter=foo,bar,baz. If any logger
name is prefixed with a minus, eg filter=-foo, it will be excluded rather than included.

(environment variable: `SYSTEST_LOGGING_FILTER`)

**--logging-clear-handlers**

Clear existing logging handlers (during capture-log).

(environment variable: `SYSTEST_LOGGING_CLEAR_HANDLERS`)

**--no-logging-clear-handlers**

Keep existing logging handlers (during capture-log).

(environment variable: `SYSTEST_LOGGING_CLEAR_HANDLERS`)

**--no-summary**

Don't display the summary at the end of the run.

(environment variable: `SYSTEST_SUMMARY`)

**--summary**

Display the summary at the end of the run.

(environment variable: `SYSTEST_SUMMARY`)

**-o FILENAME, --outfile FILENAME**

Write formatter output to output-file (default: stdout). Can be specified multiple times.

(environment variable: `SYSTEST_OUTFILES`)

**-q, --quiet**

Alias for --no-snippets --no-source.

(environment variable: `SYSTEST_QUIET`)

**-r RUNNER_CLASS, --runner RUNNER_CLASS**

Use own runner class, like: "behave.runner:Runner"

(environment variable: `SYSTEST_RUNNER`)

**--no-source**

Don't print the file and line of the step definition with the steps.

(environment variable: `SYSTEST_SHOW_SOURCE`)

**--show-source**

Print the file and line of the step definition with the steps. This is the default behaviour. This switch is used to
override a configuration file setting.

(environment variable: `SYSTEST_SHOW_SOURCE`)

**--stage STAGE**

Defines the current test stage. The test stage name is used as name prefix for the environment file and the steps
directory (instead of default path names).

(environment variable: `SYSTEST_STAGE`)

**--stop**

Stop running tests at the first failure.

(environment variable: `SYSTEST_STOP`)

**-t TAG_EXPRESSION, --tags TAG_EXPRESSION**

Only execute features or scenarios with tags matching TAG_EXPRESSION. Use :option:`--tags-help` option for more
information. Can be specified multiple times.

(environment variable: `SYSTEST_TAGS`)

**-T, --no-timings**

Don't print the time taken for each step.

(environment variable: `SYSTEST_SHOW_TIMINGS`)

**--show-timings**

Print the time taken, in seconds, of each step after the step has completed. This is the default behaviour. This switch
is used to override a configuration file setting.

(environment variable: `SYSTEST_SHOW_TIMINGS`)

**-v, --verbose**

Show the files and features loaded.

(environment variable: None)

**-w, --wip**

Only run scenarios tagged with "wip". Additionally: use the "plain" formatter, do not capture stdout or logging output
and stop at the first failure.

(environment variable: `SYSTEST_WIP`)

**--lang LANG**

Use keywords for a language other than English.

(environment variable: `SYSTEST_LANG`)

**--lang-list**

List the languages available for --lang.

(environment variable: None)

**--lang-help LANG**

List the translations accepted for one language.

(environment variable: None)

**--tags-help**

Show help for tag expressions.

(environment variable: None)

**--version**

Show version.

(environment variable: None)

## Configuration

The `systest` configuration combines settings from five distinct sources. Values from a higher-priority source will
generally **override** values from a lower-priority source, except for specific multi-valued options that use **Additive
Merge**.

For local development, a file named `.env` may be placed in the project root. This file is **not included by default**
but will be loaded if present when the code is executed from source code.

**Configuration Source and Priority Order**

|    Priority     | Method                    | Description                                                                     |
| :-------------: | :------------------------ | :------------------------------------------------------------------------------ |
| **5 (Highest)** | **CLI Arguments**         | Values passed directly **always** take precedence.                              |
|      **4**      | **Specified Config File** | Loaded from a configuration file specified using the `--config` flag.           |
|      **3**      | **Project `.env` File**   | Loaded from the project-specific `.env` file in the framework's root directory. |
|      **2**      | **User Home Config**      | Loaded from `~/.systest` in the user's home directory.                          |
| **1 (Lowest)**  | **Environment Variables** | Values inherited from the operating system (e.g., `export SYSTEST_JOBS=4`).     |

**Defining multi-values**

When providing multiple values for a setting (like tags or arguments), the system treats the input like a command line
string.

Syntax Rules:

1. **Multiple Items:** Separate items with a space.
1. **Values with Spaces:** If a single item contains spaces, wrap it in double (`"`) or single (`'`) quotes.

**Examples:**

```bash
# Simple list of tags
SYSTEST_TAGS="@smoke @regression @wip"

# List containing items with spaces (quoted)
SYSTEST_ARGS='"--browser chrome" "--profile Tablet Mode"'
```

**Additive Merge**

For multi-valued options, the CLI Arguments (Level 5) are **appended to** the final value determined by the
lower-priority sources (Levels 1-4), which follow the normal order.

| Priority Level           | Example Value         | Action                                     | Effective Value       |
| :----------------------- | :-------------------- | :----------------------------------------- | :-------------------- |
| 1. Environment Variables | `SYSTEST_TAGS=@slow`  | Sets initial value.                        | `[@slow]`             |
| 2. User Home Config      | `SYSTEST_TAGS=@bar`   | **Overrides** Environment Variables value. | `[@bar]`              |
| 3. Project `.env` File   | `SYSTEST_TAGS=@foo`   | **Overrides** User Home Config value.      | `[@foo]`              |
| 4. Specified Config File | `SYSTEST_TAGS=@smoke` | **Overrides** Project `.env` File value.   | `[@smoke]`            |
| 5. CLI Arguments         | `-t @critical`        | **Appends** to the Level 4 value.          | `[@smoke, @critical]` |

### Environment Variable Examples

```properties
# ----------------------------------------------------------------------
# SYSTEST FRAMEWORK VARIABLES
# ----------------------------------------------------------------------

# The primary directory where the framework looks for test suites.
# If left empty, the framework uses its default location.
SYSTEST_SUITES_DIRECTORY=./suites

# ----------------------------------------------------------------------
# BEHAVE GENERAL CONFIGURATION
# ----------------------------------------------------------------------

# Specify default feature paths (used when no paths are provided on CLI)
SYSTEST_PATHS="feature_area_a/component_a.feature feature_area_b/component_b.feature"

# Use colored output (auto, on, off, always, or never)
SYSTEST_COLOR=auto

# Stop running tests at the first failure.
SYSTEST_STOP=true

# Defines the current test stage (e.g., development, production)
SYSTEST_STAGE=integration

# Alias for --no-snippets --no-source.
SYSTEST_QUIET=false

# Only run scenarios tagged with "wip".
SYSTEST_WIP=false

# Use keywords for a language other than English (e.g., 'no' for Norwegian)
SYSTEST_LANG=en

# Default tags to use when none are provided (e.g., @smoke)
SYSTEST_DEFAULT_TAGS=

# Select features/scenarios based on a tag expression (e.g., @p1 and not @slow)
SYSTEST_TAGS='@critical "@burn and not @slow"'

# Specify the tag-expression protocol to use (v2 is default/only supported)
SYSTEST_TAG_EXPRESSION_PROTOCOL=v2

# Define user-specific data
SYSTEST_USERDATA_DEFINES="key=value1 key2=value2"

# ----------------------------------------------------------------------
# RUN EXECUTION OPTIONS
# ----------------------------------------------------------------------

# Number of concurrent jobs to use (default: 1)
SYSTEST_JOBS=4

# Select feature elements to run which match part of the given name (regex pattern)
SYSTEST_NAME='"^Scenario: Login" "^Scenario: Test$"'

# Invokes formatters without executing the steps.
SYSTEST_DRY_RUN=false

# Only run feature files matching regular expression PATTERN.
SYSTEST_INCLUDE_RE=".*service_test.*"

# Don't run feature files matching regular expression PATTERN.
SYSTEST_EXCLUDE_RE="^temp_.*"

# ----------------------------------------------------------------------
# STEP DEFINITION/SOURCE OPTIONS
# ----------------------------------------------------------------------

# Print the file and line of the step definition with the steps.
SYSTEST_SHOW_SOURCE=true

# Show a catalog of all available step definitions.
SYSTEST_STEPS_CATALOG=false

# ----------------------------------------------------------------------
# OUTPUT AND REPORTING OPTIONS
# ----------------------------------------------------------------------

# Write formatter output to output-file (e.g., report.txt)
SYSTEST_OUTFILES='file "path/with space/file"'

# Display the summary at the end of the run.
SYSTEST_SUMMARY=true

# Print skipped steps.
SYSTEST_SHOW_SKIPPED=false

# Print snippets for unimplemented steps.
SYSTEST_SHOW_SNIPPETS=true

# Print multiline strings and tables under steps.
SYSTEST_SHOW_MULTILINE=true

# Print the time taken, in seconds, of each step.
SYSTEST_SHOW_TIMINGS=false

# ----------------------------------------------------------------------
# CAPTURE AND LOGGING
# ----------------------------------------------------------------------

# Enable capture mode (stdout/stderr/log-output).
SYSTEST_CAPTURE=true

# Enable capture of stdout.
SYSTEST_CAPTURE_STDOUT=true

# Enable capture of stderr.
SYSTEST_CAPTURE_STDERR=true

# Enable capture of logging output.
SYSTEST_CAPTURE_LOG=true

# Enable capture of hooks (except: before_all).
SYSTEST_CAPTURE_HOOKS=true

# Specify a level to capture logging at. (CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET)
SYSTEST_LOGGING_LEVEL=DEBUG

# Specify which statements to filter in/out (e.g., 'mylogger,-requests')
SYSTEST_LOGGING_FILTER=

# Clear existing logging handlers (during capture-log).
SYSTEST_LOGGING_CLEAR_HANDLERS=true
```

## AT File

The **AT file** (prefixed by `@` on the command line) allows for detailed, file-based control over which tests are
executed and helps to overcome command-line character limits when processing long lists of paths.

**Example Contents**

The file can contain a mix of feature area directories, specific feature files, and line-specific scenarios:

```text
# Targets a specific scenario at line 12
foo_bar_initialization/foo_bar_initialize.feature:12

# Targets all scenarios in a specific feature file
foo_bar_setup/foo_bar_config_steps.feature
```

### Path Resolution

All paths listed within the AT file are resolved as **absolute** paths or as **relative** paths (relative to the
`<test suite>/features` directory).
