import time

from behave import given, then, when
from behave.runner import Context
from support.foo_bar_support import BarContextFactory


@given("initialized the foo_bar_initialization background")
def step_given(context: Context):
    time.sleep(0.5)


@given("the Bar context has not been initialized")
def step_given(context: Context):  # noqa: F811
    """
    Ensures that the Bar context handler does not exist before the test run.
    """
    # Use hasattr to safely check if the attribute exists on the context object.
    assert not hasattr(context, "bar_handler"), (
        "Failed to establish the precondition: 'bar_handler' attribute still exists in the context "
        "after attempted cleanup. The test state is not clean."
    )


@when("the Bar context is initialized")
def step_when(context: Context):
    """
    Instantiates the BarContextFactory object and attaches it to the Behave context.
    """
    # Initialize the Bar context object
    context.bar_handler = BarContextFactory()

    # Check for successful instantiation
    assert hasattr(context, "bar_handler"), "Failed to set 'bar_handler' attribute on the Behave context."
    assert context.bar_handler is not None, "The Bar handler object was set to None after initialization."
    assert isinstance(context.bar_handler, BarContextFactory), (
        f"Bar handler is the wrong type. Expected {BarContextFactory.__name__}, "
        f"but got {type(context.bar_handler).__name__}."
    )


@then("the Bar object has a valid, unique identifier")
def step_then(context: Context):
    """
    Verifies that the newly created Bar context object has a unique identifier,
    confirming a proper instance was created.
    """
    # Check that the handler exists (was created in the When step)
    assert hasattr(
        context, "bar_handler"
    ), "Prerequisite failure: The Bar context handler ('bar_handler') was not found in the context."

    try:
        # Check that the object ID property is accessible and returns a value
        object_id = context.bar_handler.get_object_id()
    except AttributeError as e:
        raise AssertionError(f"Method 'get_object_id()' not callable on Bar handler. Error: {e}")

    assert isinstance(object_id, int), f"Object ID is not an integer. Found type: {type(object_id).__name__}."
    assert object_id > 0, f"Object ID must be a positive non-zero value. Found: {object_id}."


@then("the Bar object exposes the '{method_name}' method")
def step_then(context: Context, method_name: str):  # noqa: F811
    """
    Verifies that the Bar instance contains the specified method name.

    Args:
        context: The Behave context object containing the Bar instance.
        method_name: The name of the method to check for existence.
    """
    # Check that the handler exists (was created in the When step)
    assert hasattr(
        context, "bar_handler"
    ), "Prerequisite failure: The Bar context handler ('bar_handler') was not found in the context."

    assert hasattr(context.bar_handler, method_name), (
        f"The Bar object (instance of {type(context.bar_handler).__name__}) "
        f"does NOT expose the method: {method_name!r}"
    )

    method_is_callable = callable(getattr(context.bar_handler, method_name))
    assert method_is_callable, f"The attribute {method_name!r} exists, but it is not a callable method."
