# Framework Development Guide

The **Automated System Test Framework** is specifically designed to facilitate the **development, execution, and
analysis** of system tests. It fully incorporates **Behave** testing practices to provide a structured environment for
writing clear, executable **behavioral specifications**.

## Contents

1. [Structure and Components](#structure-and-components)
1. [Backward Compatibility](#backward-compatibility)
1. [Defining Command Line Options](#defining-command-line-options)
1. [Running Internal Tests](#running-internal-tests)
1. [Build Debian/Ubuntu Package](#build-debianubuntu-package)
1. [Creating a Formatter](#creating-a-formatter)
1. [Creating a Reporter](#creating-a-reporter)

## Structure and Components

The framework's internal source code (`src`) and its own dedicated tests (`tests`) are organized to be completely
separate from product-specific test suites, promoting a clean, reusable architecture.

**Key Directory Layout**

```text
+-- automated-systest-framework/
│   +-- debian/
│   +-- docs/
│   +-- mock_suite/                   # Example/Placeholder for a Test Suite.
│   +-- src/
│   │   +-- bin/
│   │   │   +-- systest               # The framework's Main Entry Point (executable script).
│   │   +-- systest/                  # Internal framework logic.
│   │   │   +-- systest_behave/       # Behavior Testing execution and reporting logic.
│   │   │   │   +-- formatter/
│   │   │   │   │   +-- *.py
│   │   │   │   +-- reporter/
│   │   │   │   │   +-- zephyr.py     # Reporter implementation for integrating results with the Zephyr app for Jira.
│   │   │   │   │   +-- *.py
│   │   │   │   +-- configuration.py  # Parses and manages framework settings from CLI arguments and config files.
│   │   │   │   +-- runner.py         # The systest runner module, which supports running tests using a feature area folder structure.
│   │   │   │   +-- wrapper.py
│   │   │   +-- __main__.py
│   │   │   +-- constants.py          # Defines Core Configuration and CLI Options.
│   │   │   +-- exceptions.py
│   │   │   +-- suite_manager.py
│   │   │   +-- types.py              # Defines data types and structures used across the framework.
│   │   │   +-- utils.py
│   │   +-- __builtins__.pyi
│   +-- tests/                        # The framework's Internal Unit and Integration Tests.
│   │   +-- integration/
│   │   │   +-- *.py
│   │   +-- unit/
│   │   │   +-- *.py
│   │   +-- conftest.py
│   │   +-- support.py
│   +-- build-deb.sh
│   +-- create-venv.sh
│   +-- example.env                   # Example Configuration/Environment Variables.
│   +-- setup.py
```

**Component Overview**

| Directory/File   | Purpose                  | Key Details                                                                                                                           |
| :--------------- | :----------------------- | :------------------------------------------------------------------------------------------------------------------------------------ |
| `src`            | **Framework Source**     | Contains all core logic for the **System Test Framework**.                                                                            |
| `bin/systest`    | **Entry Point**          | The **main module** used to invoke and configure the framework's execution.                                                           |
| `tests`          | **Framework Tests**      | **Unit and integration tests** for the code in `src`, ensuring the framework's reliability.                                           |
| `mock_suite`     | **Example Suite**        | A complete, functional placeholder suite for **development, testing, and demonstration** purposes. See [Test Suite](./test_suite.md). |
| `create-venv.sh` | **Environment Setup**    | A **mandatory** helper script used for production and development environments to ensure compliance with target product constraints.  |
| `example.env`    | **Environment Template** | An example file showing available configuration options. This file can be copied to `.env` to configure the local environment.        |

## Backward Compatibility

The framework incorporates a compatibility mechanism designed to ensure continued support for existing test suites. By
exposing current version information, the system enables the implementation of version-specific logic, ensuring that
test suites remain functional across different framework updates.

The framework version can be accessed via:

- **Configuration Object:** The framework version is available through the `.run_version` attribute of the configuration
  instance.
- **Utility Function:** The version can be retrieved by calling the `run_version()` function from the `utils` module.
- **As an Environment Variable:** The framework exposes its version via the `SYSTEST_RUN_VERSION` environment variable.

## Defining Command Line Options

Defining new command-line options for the `systest` command requires propagating changes through `constants.py`,
`configuration.py`, and the initialization logic.

### 1. Define Option in Constants

Modification of the `OPTIONS` constant located in `src/systest/constants.py` is required. This ensures the option is
integrated into the `argparse` logic.

*Example: Adding a string option with flags `-t` and `--test`.*

```python
OPTIONS: Options = [
    (
        # ... existing ...

        ("-t", "--test"),
        dict(
            dest="test",
            action="store",
            type=str,
            help="Specify a test argument."
        )
    ),
]
```

### 2. Set Default Value

The `systest_defaults` dictionary in `src/systest/systest_behave/configuration.py` must be updated to provide a default
value when the argument is not provided.

```python
class Configuration(BehaveConfiguration):
    # ... existing ...

    systest_defaults: DefaultValues = {
        # ... existing ...

        "test": None # Map CLI argument destination ('dest') to a default value
    }

    # ... existing ...
```

### 3. Initialize Attribute

The `init()` method in `Configuration` must be updated to explicitly define the new attribute.

```python
class Configuration(BehaveConfiguration):
    # ... existing ...

    def init(self, verbose: Optional[bool] = None, **kwargs: DefaultValues):
        # ... existing ...

        # Add the new attribute.
        self.test: Optional[str] = None

    # ... existing ...
```

### 4. Implement Validation (Optional)

If the argument requires validation or transformation, add a private method following the `setup_<dest>` convention and
call it in `__init__`.

```python
class Configuration(BehaveConfiguration):
    # ... existing ...

    def __init__(self, command_args: Optional[CommandArgs] = None, load_config: bool = True,
                 verbose: Optional[bool] = None, **kwargs: DefaultValues):
        # ... existing ...

        self.setup_test() # <--- Call the setup method

    # ... existing ...

    def setup_test(self):
        """Processes the value of the 'test' argument."""
        if self.test is not None:
            # Example: Convert the string pattern into a compiled regex
            try:
                self._test_regex = re.compile(self.test)
            except re.error as e:
                raise ConfigError(f"Invalid test pattern '{self.test}': {e}")
```

## Running Internal Tests

The following steps ensure the framework's internal functionality is validated using `pytest` against the code in the
`src` directory.

1. **Install Test Dependencies** This step is only necessary the first time or whenever dependencies change.

```shell
.venv/bin/pip install -e .[test]
```

1. **Execute Tests** Run pytest specifying the target directories or files.

*Unit Tests (Validate individual functions in isolation):*

```shell
.venv/bin/pytest tests/unit/*
```

*Integration Tests (Validate system interactions):*

```shell
.venv/bin/pytest tests/integration/*
```

## Build Debian/Ubuntu Package

The framework can be packaged into a Debian (`.deb`) file for easy installation on Debian or Ubuntu systems.

### Build Command

Execute the dedicated build script from the project root directory:

```shell
sudo sh ./build-deb.sh --version 1.2.3
```

### Maintenance Note

It is crucial to maintain synchronization between the project's main `.gitignore` file and the Debian source
configuration file, `debian/source/options`. This ensures that unnecessary files and build artifacts are correctly
excluded from the final `.deb` package.

## Creating a Formatter

A formatter is utilized to output the test process (e.g., to the console or a file).

### Formatter File Creation

Create the file at: `src/systest/systest_behave/formatter/test.py`. *Ensure the directory exists and contains an
`__init__.py`.*

The class must derive from `behave.formatter.base.Formatter`:

```python
from behave.formatter.base import Formatter

# Using a descriptive name like TestFormatter is recommended
class TestFormatter(Formatter):

    # Required attributes for registration and documentation
    name = "test"
    description = "A formatter for the test suite."

    # The attributes 'config' and 'stream' (providing the `stream.write` method)
    # are instantiated by the Formatter class.

    # Implement methods from the table below.
```

### Methods for Implementation

The following table outlines the methods available for implementation, their responsibilities, and when they are invoked
during the test run.

| Method Signature         | Responsibility                                    | Hierarchy / Timing                                                                         |
| :----------------------- | :------------------------------------------------ | :----------------------------------------------------------------------------------------- |
| `uri(uri: str)`          | Sets up file-level context or logs the file path. | Invoked first.                                                                             |
| `feature(feature)`       | Invoked with the current Feature object.          | Invoked immediately after URI.                                                             |
| `background(background)` | Invoked with the current Background object.       | Invoked during discovery when encountered.                                                 |
| `rule(rule)`             | Invoked with the current Rule object.             | Invoked during discovery when encountered.                                                 |
| `scenario(scenario)`     | Invoked with the current Scenario object.         | Invoked during discovery when encountered.                                                 |
| `step(step)`             | Invoked with the current Step object.             | Invoked during discovery when encountered.                                                 |
| `match(match)`           | Provides step-to-code mapping info.               | Invoked during execution (immediately after all steps in a scenario have been discovered). |
| `result(step)`           | Invoked after step execution.                     | Invoked during execution (immediately after the step function completes).                  |
| `eof()`                  | Invoked after processing a feature file.          | Invoked after discovery and execution are complete.                                        |

### Formatter Registration

Register the formatter in `src/systest/constants.py` by appending to `SYSTEST_FORMATS`:

```python
SYSTEST_FORMATS = [
    # ... existing ...

    ("test", "systest.systest_behave.formatter.test:TestFormatter")
]
```

**Usage:** `systest --suite mock --format test`

## Creating a Reporter

A reporter is utilized for **aggregating and summarizing results** after the entire suite has finished.

### Reporter File Creation

Create the file at: `src/systest/systest_behave/reporter/test.py`. *Ensure the directory exists and contains an
`__init__.py`.*

The class must derive from `behave.reporter.base.Reporter`:

```python
from behave.reporter.base import Reporter

# Using a descriptive name like TestReporter is recommended
class TestReporter(Reporter):
    # The attribute `config` (the configuration object) is instantiated by the Reporter class.

    # Implement methods (see below)
```

### Methods for Implementation

| Method Signature   | Responsibility                                                                |
| :----------------- | :---------------------------------------------------------------------------- |
| `feature(feature)` | Invoked with the Feature object immediately after it has been fully executed. |
| `end()`            | Invoked once, after **all** feature files in the suite have been processed.   |

### Reporter Implementation

Instantiate and append the reporter in `src/systest/systest_behave/configuration.py` inside `setup_systest_reporters`:

```python
# ... existing ...
from .reporter.test import TestReporter

class Configuration(BehaveConfiguration):
    # ... existing ...

  def setup_systest_reporters(self):
      # ... existing ...

      # Assuming the 'enable_test_reporter' is available for use as user data
      if self.config.userdata.get('enable_test_reporter') == 'true':
          # Instantiation requires passing the configuration object (self)
          self.reporters.append(TestReporter(self))
```

**Usage:** `systest --suite mock --define enable_test_reporter`
