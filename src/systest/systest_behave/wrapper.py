import typing

from behave.formatter.base import Formatter
from behave.reporter.base import Reporter

from ..types import override

__all__ = ["ReporterWrapper", "FormatterWrapper"]

T = typing.TypeVar("T")


class ModelWrapper(typing.Generic[T]):
    """Base class providing delegation via __getattr__ and the manual 'done' hook."""

    wrapped: T

    def __init__(self, wrapped: T):
        self.wrapped = wrapped

    def __getattr__(self, name: str):
        """Delegates all other calls to the wrapped object."""
        return getattr(self.wrapped, name)

    def get_wrapped(self) -> T:
        return self.wrapped

    def done(self):
        """Placeholder for the original wrapped cleanup method."""
        raise NotImplementedError()


class ReporterWrapper(ModelWrapper[Reporter]):
    """
    Wrapper for behave.reporter.base.Reporter.
    Intercepts the Reporter's `end()` method to prevent premature closing
    during iterative feature area runs, exposing the original method via `done()`.
    """

    @override
    def done(self):
        """Calls the original Reporter.end() for cleanup."""
        self.wrapped.end()

    def end(self):
        """
        Patch: Overrides the original end() method and does nothing
        to prevent premature cleanup.
        """


class FormatterWrapper(ModelWrapper[Formatter]):
    """
    Wrapper for behave.formatter.base.Formatter.
    Intercepts the Formatter's `close()` method to prevent premature closing
    during iterative feature area runs, exposing the original method via `done()`.
    """

    @override
    def done(self):
        """Calls the original Formatter.close() for resource closing."""
        self.wrapped.close()

    def close(self):
        """Overrides the original close() method to prevent premature resource closing."""
