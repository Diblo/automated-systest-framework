@SIR-11 @foo @bar @setup @dry_run
Feature: Foo Bar config
  As the Foo configuration parameters is set
  I want the Bar class to be using Foo configuration
  So that the Bar is correctly initialized

  @SIR-T11
  Scenario Outline: Verify config for Bar
    Given the Bar dry run is '<State>'
    When Foo dry run is '<Negation_State>'
    Then the Bar dry run should be '<Negation_State>'

    Examples: Execution Matrix
      | State | Negation_State |
      | False | True           |
      | True  | False          |
