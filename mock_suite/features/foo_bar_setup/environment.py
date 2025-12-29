"""
Hooks defined in this module execute before and after specific events
during the systest run. This functionality is part of the Behave framework,
extended for system testing.

Official Behave documentation: https://behave.readthedocs.io/en/latest/api/#environment-file-functions
"""

from behave.model import Feature, Rule, Scenario, Step, Tag
from behave.runner import Context
from support.foo_bar_support import BarContextFactory


def before_all(context: Context):
    """
    Setup executed once before any test execution begins.
    """
    # Initializes a shared context object (BarContextFactory) and attaches it
    # to the context for use across all features and scenarios.
    context.bar_handler = BarContextFactory()


def before_feature(context: Context, feature: Feature):
    """
    Executed before each feature.
    """


def before_rule(context: Context, rule: Rule):
    """
    Executed before each rule (if using Gherkin Rules).
    """


def before_scenario(context: Context, scenario: Scenario):
    """
    Executed before each scenario.
    """


def before_step(context: Context, step: Step):
    """
    Executed before every step within a scenario.
    """


def after_step(context: Context, step: Step):
    """
    Executed after every step within a scenario.
    """


def after_scenario(context: Context, scenario: Scenario):
    """
    Executed after each scenario.
    """


def after_rule(context: Context, rule: Rule):
    """
    Executed after each rule (if using Gherkin Rules).
    """


def after_feature(context: Context, feature: Feature):
    """
    Executed after each feature.
    """


def after_all(context: Context):
    """
    Teardown executed once after all test execution has finished.
    """


# --- Tag Hooks ---


def before_tag(context: Context, tag: Tag):
    """
    Executed before each tag.
    """


def after_tag(context: Context, tag: Tag):
    """
    Executed after each tag.
    """
