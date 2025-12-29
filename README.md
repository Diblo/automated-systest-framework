# Automated System Test Framework (systest)

The **Automated System Test Framework**, also known as **systest**, is a robust system designed to automatically run
**behavioral system tests**. It ensures the quality, functionality, and reliability of Products Under Test (PuT).

This framework is not a single program, but a collection of tools, libraries, and guidelines that standardize, organize,
and simplify the process of developing, running, and analyzing system-level software tests.

This document provides guidance for both framework users and developers.

## Contents

1. [Install DEB](#install-deb)
1. [Install from Source](#install-from-source)
1. [Setup for Development](#setup-for-development)
1. [Set Fixed Test Suites Location (Optional)](#set-fixed-test-suites-location-optional)
1. [More Documentation](#more-documentation)

## Install DEB

If the package is available in your repository, this is the recommended installation method.

```shell
sudo apt update
sudo apt install systest
```

## Install from Source

Use this method to install the framework manually if you cannot use the `.deb` package. This will set up the environment
in `/usr/share` and make the `systest` command globally available.

```shell
# 1. Clone the repository to a temporary location
cd ~
bor clone automated-systest-framework
cd automated-systest-framework

# 2. Ensure you are on the correct branch
git checkout main

# 3. Create the production virtual environment
# Note: We install to /usr/share/systest/venv (requires sudo)
sudo sh ./create-venv.sh --create-production "/usr/share/systest/venv"

# 4. Create a symlink to make 'systest' accessible globally
sudo ln -sf /usr/share/systest/venv/bin/systest /usr/local/bin/systest

# 5. Verify the installation
systest --version
```

### Clean Up (Optional)

Once the virtual environment is created, the source code folder is no longer needed for the program to run.

```shell
cd ~
rm -rf ~/automated-systest-framework
```

## Setup for Development

Follow these steps to set up the **Automated System Test Framework** for local development and make the `systest`
command globally accessible.

### 1. Install Dependencies

Running `systest` requires Python 3.8 and the virtual environment module.

```shell
sudo apt update
sudo apt install python3.8 python3.8-venv
```

### 2. Clone the Repository

Setting up the project in a dedicated directory within the user's home folder is recommended.

```shell
# Navigate to the preferred directory (The user's home folder in this case)
cd ~

# Clone the repository
bor clone automated-systest-framework
```

### 3. Run Setup

Install the necessary Python packages using the project's `create-venv.sh` script.

```shell
cd ~/automated-systest-framework
sh ./create-venv.sh
```

**The system is now ready to run:** `sh ~/automated-systest-framework/src/bin/systest`.

### 4. Optional Step (Recommended)

To run the `systest` command from any directory **without explicitly specifying the full script path**, add the script's
directory to the system's `PATH` environment variable.

1. **Open the shell configuration file** (e.g., `~/.bashrc`):

```shell
# Use nano or vi/vim
nano ~/.bashrc
```

2. **Add the following line** to the end of the file:

```shell
export PATH="$HOME/automated-systest-framework/src/bin:$PATH"
```

3. **Make `systest` executable**:

```shell
chmod +x ~/automated-systest-framework/src/bin/systest
```

4. **Apply** the changes to the current terminal session:

```shell
source ~/.bashrc
```

Tests can now be run using the short command: `systest`.

## Set Fixed Test Suites Location (Optional)

By default, `systest` searches for test suites in the **current working directory**.

To run tests from any location without having to navigate to the test suites folder first, you can configure a fixed
path. You can define this location in four ways (listed by precedence):

1. **Command Line:** `--suites-dir <path>`
1. **Project Config File:** `.env` (Recommended for Development)
1. **User Config File:** `.systest` (Recommended for Users)
1. **Environment Variable:** `SYSTEST_SUITES_DIRECTORY` (Recommended for Pipelines)

**Setting up the User Config File:**

Create a file named `.systest` in your user home directory (`~/`) and define the absolute path to your suites.

```properties
# ~/.systest
SYSTEST_SUITES_DIRECTORY="/home/<user>/my-test-suites"
```

## More Documentation

- [Usage](./docs/usage.md)
- [Test Suite](./docs/test_suite.md)
- [Development](./docs/development.md)
