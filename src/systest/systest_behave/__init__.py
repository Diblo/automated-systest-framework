from behave.formatter import _registry as _behave_registry

from ..constants import SYSTEST_FORMATS

__all__ = []

_behave_registry.register_formats(SYSTEST_FORMATS)
