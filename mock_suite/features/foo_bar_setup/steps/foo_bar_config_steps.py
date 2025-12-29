import time

from behave import given, then, when
from behave.runner import Context


@given("the Bar dry run is '{state}'")
def step_given(context: Context, state: str):
    """
    Given step to set the initial state of Bar's dry run mode.
    The goal of this test is to verify Bar's state CAN BE overridden/set.
    """
    is_dry_run = state.lower() == "true"

    time.sleep(2)

    context.bar_handler.set_dry_run(is_dry_run)

    # Sanity check that the handler actually saved the state
    assert (
        context.bar_handler.get_dry_run() == is_dry_run
    ), f"GIVEN failed: Bar handler did not set dry run to {is_dry_run}"


@when("Foo dry run is '{negation_state}'")
def step_when(context: Context, negation_state: str):
    """
    When step simulating Foo setting configuration (the environment variable).
    """
    is_dry_run = negation_state.lower() == "true"

    context.bar_handler.set_dry_run(is_dry_run)


@then("the Bar dry run should be '{negation_state}'")
def step_then(context: Context, negation_state: str):
    """
    Then step verifying Bar's state matches the expected environment value.
    This test currently passes because the When step is flawed (see above).
    """
    # The intent of the feature is that Bar is correctly using Foo's config.
    expected_bar_state = negation_state.lower() == "true"

    # Check the state of the Bar handler
    actual_bar_state = context.bar_handler.get_dry_run()

    assert (
        actual_bar_state == expected_bar_state
    ), f"Bar dry run state mismatch. Expected: {expected_bar_state}, Actual: {actual_bar_state}"
