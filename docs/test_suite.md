# Test Suite Guide

System tests are organized into **Test Suites**. The framework locates suites within a primary directory.

## Contents

1. [Suite Structure](#suite-structure)
1. [Test Suite Naming Paradigm](#test-suite-naming-paradigm)
1. [Test Implementation Paradigm](#test-implementation-paradigm)
1. [Mandatory Requirements](#mandatory-requirements)
1. [Gherkin Feature File](#gherkin-feature-file)
1. [Configuration](#configuration)
1. [Additional Behavior Test Documentation](#additional-behavior-test-documentation)

## Suite Structure

A test suite is a top-level directory containing all feature area folders, Gherkin feature files, step definitions, and
necessary helper code, adhering to the following structure:

```text
+-- <name>[-<version>][-<context>][-<state>]_suite/
|   +-- features/
|   │   +-- <feature_area>/
|   │   │   +-- environment.py
|   │   │   +-- steps/
|   │   │   │   +-- <sub_feature_topic>_steps.py
|   │   │   +-- <sub_feature_topic>.feature
|   +-- support/
|   │   +-- __init__.py
|   │   +-- <module>.py
|   +-- suite.conf
|   +-- requirements.txt
```

| Item                           | Description                                                                                         |
| :----------------------------- | :-------------------------------------------------------------------------------------------------- |
| `<name>..._suite`              | The **directory** for a specific test suite.                                                        |
| `<feature_area>`               | A directory focused on a **functional area**.                                                       |
| `environment.py`               | Contains **hooks** specific to the feature area.                                                    |
| `steps`                        | Contains **Python Step Definition modules** (`*_steps.py`) which implement the Gherkin scenarios.   |
| `<sub_feature_topic>_steps.py` | A specific step definition file corresponding to a feature topic.                                   |
| `<sub_feature_topic>.feature`  | The **Gherkin feature file** describing system scenarios.                                           |
| `__init__.py`                  | Required to treat the directory as a Python package.                                                |
| `support`                      | **Helper modules** (`<module>.py`) that encapsulate interaction logic with the software under test. |
| `suite.conf`                   | Suite-specific configuration file.                                                                  |
| `requirements.txt`             | Defines suite-specific **Python dependencies**.                                                     |

## Test Suite Naming Paradigm

The following naming paradigm applies to all new test suites: `<name>[-<version>][-<context>][-<state>]_suite`. This
strategy ensures clarity, version compatibility, and categorization for different environments.

**Example**

| Pattern Segment              | Example             | Description                                                                                                       |
| :--------------------------- | :------------------ | :---------------------------------------------------------------------------------------------------------------- |
| `<name>-<state>`             | `r2d2-dev`          | Tests for **r2d2 development software** (latest unreleased changes).                                              |
| `<name>-<state>`             | `cloud-dev`         | Tests for **cloud development software** (latest unreleased changes).                                             |
| `<name>-<version>`           | `r2d2-2.2.11`       | Tests targeting a **specific stable r2d2 software version**.                                                      |
| `<name>-<version>-<state>`   | `r2d2-2.2.12-dev`   | Tests for an **in-development r2d2 version** (e.g., v2.2.12).                                                     |
| `<name>-<version>-<context>` | `r2d2-3.2.1-sanity` | **Sanity tests** designed to run on **physical hardware** for rapid health checks on a specific **r2d2** version. |

## Test Implementation Paradigm

The framework enforces a strict **separation of concerns** using the **Gherkin structure** for organized **behavioral
testing**.

| Component                                         | Role                          | Core Responsibility                                                                                    | The **Core Rule** for Interaction                                                                     |
| :------------------------------------------------ | :---------------------------- | :----------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------- |
| **Gherkin Feature Files** (`.feature`)            | **Behavioral Specifications** | Describe the desired **system behavior** in plain language using the **Given/When/Then** format.       | No code interaction.                                                                                  |
| **Step Definition Modules** (`*_steps.py`)        | **Test Logic/Assertions**     | Contain the **executable system tests**, including the test logic and assertions.                      | **MUST NOT** directly interact with the **software under test**.                                      |
| **Support Modules** (`<module>.py` in `support/`) | **Interaction Layer**         | Contain the direct implementation of **all software interaction logic** and reusable helper functions. | Must be used **exclusively** by Step Definition Modules to interact with the **software under test**. |

**Key Takeaway for Maintenance:** Changes to the software's interface typically require modification only within the
centralized **Support Modules**, simplifying test suite maintenance.

## Mandatory Requirements

To ensure the `systest` runner locates and executes a test suite without errors, adherence to the following rules and
components is **mandatory**:

1. **Naming Convention:**

   - The test suite's top-level directory **must** use the suffix `_suite`.

1. **Folders:**

   - The `features` folder must exist to contain the feature area folders.
   - The `support` folder must exist to house the helper modules that encapsulate interaction logic with the software
     under test.

1. **Feature Structure:**

   - At least one **feature area folder** must exist inside the `features` directory.
   - Each feature area folder **must contain at least one** Gherkin feature file (`*.feature`).
   - Each feature area folder **must contain** a `steps` folder with the Python step definition files (`*_steps.py`).

1. **Reserved Naming Constraint:**

   - The term `environment` is a **reserved keyword** solely for identifying the hooks file (`environment.py`).
   - Usage of this word in the filename of any feature file, step file, or support module is **prohibited** to prevent
     conflicts in the test runner.

## Gherkin Feature File

Feature files serve as the "source of truth" for system behavior. These are written in **Gherkin (v6)**, a
domain-specific language describing software behavior regardless of implementation details.

Location requirement: Directly within the specific `<feature_area>` folder (e.g.,
`features/navigation/avoidance.feature`).

### Structure and Keywords

A feature file relies on specific keywords to structure the test scenarios.

| Keyword              | Category      | Description                                                                                                          | Occurrence & Constraints                                                                                                             |
| :------------------- | :------------ | :------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------- |
| **Feature**          | **Structure** | Defines the test group (e.g., "Battery Charging"). It is the root element of the file.                               | **Single** entry per file.                                                                                                           |
| **Background**       | **Setup**     | A set of steps executed *before* every scenario in its scope. Defines the baseline state.                            | **Single** entry per Feature or Rule.                                                                                                |
| **Rule**             | **Structure** | Represents a business rule grouping related scenarios. Used to organize complex features into smaller logical units. | **Multiple** allowed within a Feature.                                                                                               |
| **Scenario**         | **Structure** | Represents a specific test case or user story containing executable steps.                                           | **Multiple** allowed within a Feature or Rule.                                                                                       |
| **Scenario Outline** | **Structure** | A template for a Scenario that runs multiple times with different data sets.                                         | **Multiple** allowed within a Feature or Rule.                                                                                       |
| **Examples**         | **Data**      | Contains the tabular data injected into a Scenario Outline.                                                          | **Multiple** tables allowed per Scenario Outline.                                                                                    |
| **Given**            | **Step**      | Describes the **initial context**. The system state *before* action.                                                 | **Multiple** allowed per Scenario, Scenario Outline, or Background.                                                                  |
| **When**             | **Step**      | Describes the **event or action**. The catalyst for the test.                                                        | **Multiple** allowed per Scenario, Scenario Outline, or Background.                                                                  |
| **Then**             | **Step**      | Describes the **expected outcome** or assertion.                                                                     | **Multiple** allowed per Scenario, Scenario Outline, or Background.                                                                  |
| **And / But**        | **Step**      | Logical conjunctions. They **inherit** the type (`Given`, `When`, `Then`) of the strictly preceding step.            | **Multiple** allowed per Scenario, Scenario Outline, or Background.<br>**Constraint:** **Must** follow a `Given`, `When`, or `Then`. |
| **Tags (`@`)**       | **Metadata**  | Markers used to filter execution or link to external tools.                                                          | **Multiple** allowed per Feature, Rule, Scenario, Scenario Outline, or Examples.                                                     |

### Syntax Example

The following example, `navigation.feature`, illustrates the standard structure of a Gherkin file and the combination of
keywords to define executable tests.

```gherkin
@navigation @release_2.0 @system_level
Feature: Autonomous Robot Navigation
  As a warehouse manager, I want the robot to navigate between stations autonomously,
  so that packages are delivered efficiently without human intervention.

  # Global Background: Executes before EVERY scenario in the file
  Background:
    Given the robot is powered on
    And the LIDAR sensor is active
    And the battery level is above 20%

  @path
  Scenario: Navigate to a designated waypoint
    Given the robot is currently at "Docking Station A"
    When the system receives a command to go to "Shelf 5"
    Then the robot should calculate a valid path
    And the robot should begin moving towards "Shelf 5"

  # Rule groups scenarios related to safety
  @safety @critical
  Rule: The robot must stop or reroute when obstacles are detected

    # Rule Background: Executes ONLY for scenarios inside this Rule
    # This sets specific safety flags not needed for general navigation
    Background:
      Given the "Collision Avoidance System" is enabled
      And possible collision is not detected
      And the audible warning module is ready

    @edge_case @cliff_sensor
    Scenario: Stop immediately when a drop-off is detected
      Given the robot is approaching a downward staircase
      When the ground sensors detect a drop greater than 10cm
      Then the robot should perform the action "Emergency Brake"
      And the admin should receive a "Stuck" alert

    @compliance @dynamic_objects
    Scenario Outline: Reacting to different obstacle types
      Given the robot is moving at <speed>
      When an obstacle of type "<obstacle_type>" is detected at <distance> meters
      Then the robot should perform the action "<expected_action>"
      But the robot should not trigger a collision alarm

      # Examples tagged to allow running specific data sets (e.g., only high priority)
      @high_priority_objects
      Examples:
        | speed | obstacle_type | distance | expected_action  |
        | Fast  | Human         | 5.0      | Slow Down        |
        | Slow  | Box           | 0.5      | Stop Immediately |

      # Additional examples for non-critical objects
      @low_priority_objects
      Examples:
        | speed | obstacle_type | distance | expected_action  |
        | Fast  | Wall          | 2.0      | Reroute Path     |
```

> **Note:** The steps defined above (lines starting with Given, When, Then) require exact string matches in the
> corresponding `steps/navigation_steps.py` file for successful execution.

## Configuration

Suite-specific configurations are managed by the optional `suite.conf` file located in the suite's root directory. This
file allows customization of internal suite paths and framework compatibility settings.

```properties
# Specifies the framework version the test suite is guaranteed to support.
# The framework uses this to ensure compatibility before execution.
framework_version=0.0.1

# Defines the name of the directory that contains all feature area directories for the test suite.
# The default is usually 'features'.
features_folder=features

# Defines the name of the directory containing the shared utility modules and helper functions.
# The default is usually 'support'.
support_folder=support
```

## The Context Object

In the `systest` framework (powered by Behave), the **Context** object is the essential mechanism for sharing state
between steps and lifecycle hooks.

Since step definitions are isolated Python functions, variables defined inside them do not persist. The `context` object
acts as a shared container that travels through your test execution, allowing you to store data in one step (e.g., an ID
returned by an API) and retrieve it in a subsequent step (e.g., verifying that ID in a database).

However, `context` is more than just a dictionary. It acts as a **Variable Stack** that manages namespaces automatically
as the test runner moves through the lifecycle (Test Run → Feature → Rule → Scenario).

### The Context Stack (Lifecycle)

The context operates as a stack of layers. When a new scope begins (e.g., a Feature starts), a new layer is pushed onto
the stack. When that scope ends, the layer is popped, and all data stored in that layer is discarded.

| Scope               | Layer Lifetime                                                            | Accessibility                                                                    |
| ------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Root (Test Run)** | Created in `before_all`. Persists for the entire run.                     | Visible everywhere. Ideal for global clients (e.g., `context.client`).           |
| **Feature**         | Created in `before_feature`. Persists for all scenarios in that feature.  | Visible to all scenarios within the feature. Good for feature-specific config.   |
| **Scenario**        | Created in `before_scenario`. Persists **only** for the current scenario. | Visible only in the current scenario steps. Used for passing data between steps. |

**How Lookup Works:** When you access `context.my_var`, the system looks from the **Top (Scenario)** down to the
**Bottom (Root)**. It returns the first value it finds.

### Context Rules

Understanding the limitations of the Context object is crucial to avoid "flaky" tests or confusing errors.

**Variable Masking (Assignment)**

When you set a variable (`context.user = "Han"`), it is **always** stored in the **current active layer** (e.g.,
Scenario).

**Warning:** If a variable with the same name exists in a higher layer (e.g., Root), you are "masking" (hiding) the
global value for the duration of this scenario. Behave may emit a warning if you accidentally mask framework internals.

**Deletion Constraints**

You can only delete attributes that exist in the **current** layer.

**Example:** If you defined `context.db` in `before_all` (Root layer), you **cannot** delete it from a Scenario step
(`del context.db` will raise an error). You can only delete variables you created inside the current scenario.

**Reserved Attributes**

Behave reserves specific attribute names for its internal state. **Do not overwrite these**, as it will break the test
runner or reporting.

| Attribute          | Description                                                          |
| ------------------ | -------------------------------------------------------------------- |
| `context.feature`  | The current Feature model (only present during feature execution).   |
| `context.scenario` | The current Scenario model (only present during scenario execution). |
| `context.tags`     | The active tags for the current scope.                               |
| `context.failed`   | Boolean (`True`/`False`) indicating if a step has failed.            |
| `context.aborted`  | Boolean indicating if the user aborted the run (KeyboardInterrupt).  |
| `context.table`    | The Gherkin table associated with the current step (if any).         |
| `context.text`     | The DocString text associated with the current step (if any).        |
| `context.config`   | The Behave configuration object.                                     |

### Advanced Features

**Registering Cleanups (`add_cleanup`)**

Instead of relying solely on `after_scenario`, you can register cleanup functions dynamically within a step.

```python
@given('a temporary database is created')
def step_create_temp_db(context):
    db = create_database()
    context.db = db

    # Register a cleanup function immediately
    # This will run automatically when the current layer (Scenario) ends.
    context.add_cleanup(db.close)
    context.add_cleanup(delete_database, db_name=db.name)
```

**Executing Dynamic Steps (`execute_steps`)**

You can call other Gherkin steps from within a Python step.

```python
@when('the user performs the full login sequence')
def step_full_login(context):
    # Runs these steps as if they were in the feature file
    context.execute_steps(u'''
        Given the user navigates to the login page
        When the user enters valid credentials
        Then the dashboard should be visible
    ''')
```

**Embedding Data (`attach`)**

To attach screenshots, logs, or other binary data to the test report (e.g., for JSON output):

```python
# Attach a PNG screenshot to the report
context.attach("image/png", screenshot_bytes)
```

## Additional Behavior Test Documentation

For detailed information on writing tests, defining executable steps, and utilizing lifecycle hooks, consult the
official **Behave for Python documentation**.

[Behave for Python documentation](https://behave.readthedocs.io/en/stable/)
