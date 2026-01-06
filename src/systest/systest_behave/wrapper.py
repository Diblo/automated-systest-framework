"""Wrapper types that adapt behave reporters and formatters."""

import typing

from behave.formatter.base import Formatter
from behave.reporter.base import Reporter

from ..types import override

__all__ = ["ReporterWrapper", "FormatterWrapper"]

T = typing.TypeVar("T")


class ModelWrapper(typing.Generic[T]):
    """Base class providing delegation via __getattr__ and the manual 'done' hook."""

    wrapped: T
    """Wrapped instance delegated to by this wrapper."""

    def __init__(self, wrapped: T):
        """Initialize the wrapper with a target instance.

        Args:
            wrapped (T): Wrapped instance to delegate to.
        """
        self.wrapped = wrapped

    def __getattr__(self, name: str):
        """Delegate attribute access to the wrapped object.

        Args:
            name (str): Attribute name to resolve.

        Returns:
            Any: Resolved attribute from the wrapped object.
        """
        return getattr(self.wrapped, name)

    def get_wrapped(self) -> T:
        """Return the wrapped instance.

        Returns:
            T: Wrapped instance.
        """
        return self.wrapped

    def done(self):
        """Run the wrapped cleanup method."""
        raise NotImplementedError()


class ReporterWrapper(ModelWrapper[Reporter]):
    """
    Wrapper for behave.reporter.base.Reporter.
    Intercepts the Reporter's `end()` method to prevent premature closing
    during iterative feature area runs, exposing the original method via `done()`.
    """

    @override
    def done(self):
        """Call the original Reporter.end() for cleanup."""
        self.wrapped.end()

    def end(self):
        """Override end() to prevent premature cleanup."""


class FormatterWrapper(ModelWrapper[Formatter]):
    """
    Wrapper for behave.formatter.base.Formatter.
    Intercepts the Formatter's `close()` method to prevent premature closing
    during iterative feature area runs, exposing the original method via `done()`.
    """

    @override
    def done(self):
        """Call the original Formatter.close() for resource closing."""
        self.wrapped.close()

    def close(self):
        """Overrides the original close() method to prevent premature resource closing."""
