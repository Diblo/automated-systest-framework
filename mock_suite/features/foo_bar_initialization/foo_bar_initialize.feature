@SIR-17 @bar @context
Feature: Bar Context Initialization
  As a developer
  I want the Bar context to be initialized
  So that I can verify its availability

  Background: AAA
    Given initialized the foo_bar_initialization background

  @SIR-T13
  Scenario: Successful Initialization and Object Availability
    Given the Bar context has not been initialized
    When the Bar context is initialized
    Then the Bar object has a valid, unique identifier

  @SIR-T25
  Scenario Outline: Verify the Bar object has the expected methods
    Given the Bar context has not been initialized
    When the Bar context is initialized
    Then the Bar object exposes the '<Method_Name>' method

    Examples: Methods
      | Method_Name        |
      | set_dry_run        |
      | get_dry_run        |
      | set_context_id     |
      | get_context_id     |
      | set_execution_mode |
      | get_execution_mode |
