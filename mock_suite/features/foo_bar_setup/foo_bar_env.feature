@SIR-15 @SIR-T12 @foo @bar @setup @context @mode
Feature: Foo Bar Context Environment
  As the Foo environment configuration parameters is set
  I want the Bar class to be using Foo environment configuration parameters
  So that the Bar execution environment is correctly initialized

  Scenario Outline: Verify environment for Bar
    Given Foo environment parameters is CONTEXT_ID '<Context_ID>' and EXECUTION_MODE '<Execution_Mode>'
    When the Bar context id is '<Context_ID>' and execution mode is '<Execution_Mode>' is set to Foo environment parameters
    Then the Foo and Bar context ID should be '<Context_ID>'
    And the Foo and Bar execution mode should be '<Execution_Mode>'

    Examples: Execution Matrix
      | Context_ID | Execution_Mode | Description                 |
      | robot_a    | mock           | Default testing environment |
      | robot_b    | hardware       | Real device execution mode  |
      | test_case  | integration    | Integration level test run  |
