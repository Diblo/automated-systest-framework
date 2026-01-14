# Automated System Test Framework (`systest`)

The **Automated System Test Framework** (`systest`) is a CLI for running behavioral system tests that help verify the
quality, functionality, and reliability of products under test. It is built on **Behave** and **Gherkin** and provides a
clean, consistent way to organize and execute test suites.

This document provides guidance for both framework users and developers.

## Contents

1. [Install DEB](#install-deb)
1. [Install from Source](#install-from-source)
1. [Setup for Development](#setup-for-development)
1. [Set Fixed Test Suites Location (Optional)](#set-fixed-test-suites-location-optional)
1. [More Documentation](#more-documentation)

## Install DEB

If the package is available in your package repository, this is the recommended installation method.

```shell
sudo apt update
sudo apt install systest
```

## Install from Source

Use this method to install the framework manually if you cannot use the `.deb` package. This will set up the environment
in `/usr/share` and make the `systest` command globally available.

### 1. Install Dependencies

Running `systest` requires Python 3.8 and the Python virtual environment module.

```shell
sudo apt update
sudo apt install python3.8 python3.8-venv
```

### 2. Clone the Repository to a Temporary Location

```shell
cd ~
bor clone automated-systest-framework
cd automated-systest-framework

# Ensure the correct branch is checked out
git checkout main
```

### 3. Create the Production Virtual Environment

```shell
sudo sh ./create-venv.sh --create-production "/usr/share/systest/venv"
```

### 4. Create a Global `systest` Command

```shell
sudo ln -sf /usr/share/systest/venv/bin/systest /usr/local/bin/systest
```

### 5. Enable Shell Completion (bash)

```shell
grep -qxF 'eval "$(/usr/share/systest/venv/bin/register-python-argcomplete --shell bash systest)"' ~/.bashrc || echo 'eval "$(/usr/share/systest/venv/bin/register-python-argcomplete --shell bash systest)"' >> ~/.bashrc
source ~/.bashrc
```

### 6. Verify the Installation

```shell
systest --version
```

### 7. Clean Up (Optional)

Once the production virtual environment is created, the source directory is no longer required.

```shell
cd ~
rm -rf ~/automated-systest-framework
```

## Setup for Development

Follow these steps to set up the **Automated System Test Framework** for local development.

### 1. Install Dependencies

Running `systest` requires Python 3.8 and the Python virtual environment module.

```shell
sudo apt update
sudo apt install python3.8 python3.8-venv
```

### 2. Clone the Repository

It is recommended to set up the project in a dedicated directory within your home folder.

```shell
# Navigate to the preferred directory (home folder in this example)
cd ~

# Clone the repository
bor clone automated-systest-framework
cd automated-systest-framework
```

### 3. Create the Development Virtual Environment

Install the required Python packages using the provided `create-venv.sh` script.

```shell
sh ./create-venv.sh
```

### 4. Make the `systest` Script Executable

```shell
chmod +x ~/automated-systest-framework/src/bin/systest
```

You can now run system tests using the full path:

```shell
~/automated-systest-framework/src/bin/systest
```

### 5. Enable Shell Completion (Recommended)

```shell
grep -qxF 'eval "$(~/automated-systest-framework/.venv/bin/register-python-argcomplete --shell bash ~/automated-systest-framework/src/bin/systest)"' ~/.bashrc || echo 'eval "$(~/automated-systest-framework/.venv/bin/register-python-argcomplete --shell bash ~/automated-systest-framework/src/bin/systest)"' >> ~/.bashrc
source ~/.bashrc
```

**NOTE**: It will only work when invoked as `~/automated-systest-framework/src/bin/systest`.

### 6. Add `systest` to `PATH` (Recommended)

To run `systest` from any directory without specifying the full path, add the script directory to your `PATH`.

```shell
echo 'export PATH="$HOME/automated-systest-framework/src/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

You can now run system tests using:

```shell
systest
```

## Set Fixed Test Suites Location (Optional)

By default, `systest` searches for test suites in the **current working directory**.

To run tests from any location without changing directories, you can configure a fixed test suites path. The following
methods are supported, listed by precedence:

1. **Command Line:** `--suites-dir <path>`
1. **Project Config File:** `.env` (recommended for development)
1. **User Config File:** `.systest` (recommended for users)
1. **Environment Variable:** `SYSTEST_SUITES_DIRECTORY` (recommended for CI/CD pipelines)

### User Config File Example

Create a file named `.systest` in your home directory and define the absolute path to your test suites:

```properties
# ~/.systest
SYSTEST_SUITES_DIRECTORY="/home/<user>/my-test-suites"
```

## More Documentation

- [Usage](./docs/usage.md)
- [Test Suite](./docs/test_suite.md)
- [Development](./docs/development.md)
