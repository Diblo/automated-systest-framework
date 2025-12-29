import os

from behave import given, then, when
from behave.runner import Context


@given("Foo environment parameters is CONTEXT_ID '{context_id}' and EXECUTION_MODE '{execution_mode}'")
def step_given(context: Context, context_id: str, execution_mode: str):
    """
    Given step: Sets the environment variables (Foo's configuration).
    This step definition now matches the feature file.
    """
    os.environ["CONTEXT_ID"] = context_id
    os.environ["EXECUTION_MODE"] = execution_mode


@when(
    "the Bar context id is '{context_id}' and execution mode is '{execution_mode}' is set to Foo environment parameters"
)
def step_when(context: Context, context_id: str, execution_mode: str):
    """
    When step: Simulates Bar reading and applying the environment variables set by Foo.
    This step definition was missing and is now implemented.
    """
    bar_context_id = os.environ.get("CONTEXT_ID", context_id)
    bar_execution_mode = os.environ.get("EXECUTION_MODE", execution_mode)

    context.bar_handler.set_context_id(bar_context_id)
    context.bar_handler.set_execution_mode(bar_execution_mode)


@then("the Foo and Bar context ID should be '{expected_id}'")
def step_then(context: Context, expected_id: str):
    """
    Then step: Verifies Bar's context ID matches the ID read from the environment (Foo's config).
    """
    foo_actual = os.environ.get("CONTEXT_ID", "UNKNOWN")
    bar_actual = context.bar_handler.get_context_id()

    # 1. Verify that Bar's state matches the environment variable (propagation check)
    assert bar_actual == foo_actual, f"Context ID propagation failed. Foo (Env): '{foo_actual}', Bar: '{bar_actual}'."

    # 2. Verify that Bar's state matches the expected value from the Scenario Outline
    assert (
        bar_actual == expected_id
    ), f"Bar Context ID value mismatch. Expected: '{expected_id}', Actual: '{bar_actual}'."


@then("the Foo and Bar execution mode should be '{expected_mode}'")
def step_then(context: Context, expected_mode: str):  # noqa: F811
    """
    Then step: Verifies Bar's execution mode matches the mode read from the environment (Foo's config).
    """
    foo_actual = os.environ.get("EXECUTION_MODE", "UNKNOWN")
    bar_actual = context.bar_handler.get_execution_mode()

    # 1. Verify that Bar's state matches the environment variable (propagation check)
    assert (
        bar_actual == foo_actual
    ), f"Execution Mode propagation failed. Foo (Env): '{foo_actual}', Bar: '{bar_actual}'."

    # 2. Verify that Bar's state matches the expected value from the Scenario Outline
    assert (
        bar_actual == expected_mode
    ), f"Bar Execution Mode value mismatch. Expected: '{expected_mode}', Actual: '{bar_actual}'."
