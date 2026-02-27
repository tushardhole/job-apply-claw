Feature: Multi-Step Form Handling
  As a job seeker
  I want the bot to navigate multi-step application forms
  So that it clicks Next/Continue for intermediate steps and Submit only at the end

  Scenario: Agent navigates a three-step form and submits
    Given a profile for multi-step with name "Jane" and email "jane@test.com"
    And the LLM agent will navigate a 3-step form
    When the multi-step agent runs
    Then the multi-step result is "success"
    And the agent clicked "Next" 2 times
    And the agent clicked "Submit Application" 1 times

  Scenario: Agent skips final submit in debug mode on multi-step form
    Given a profile for multi-step with name "Jane" and email "jane@test.com"
    And the LLM agent will navigate a 3-step form in debug mode
    When the multi-step agent runs
    Then the multi-step result is "skipped"
    And the agent clicked "Next" 2 times
    And the agent did not click "Submit Application"

  Scenario: Agent handles Save and Continue buttons
    Given a profile for multi-step with name "Jane" and email "jane@test.com"
    And the LLM agent will use Save and Continue buttons
    When the multi-step agent runs
    Then the multi-step result is "success"
    And the agent clicked "Save & Continue" 2 times

  Scenario: Agent navigates review page before final submit
    Given a profile for multi-step with name "Jane" and email "jane@test.com"
    And the LLM agent encounters a review page before submit
    When the multi-step agent runs
    Then the multi-step result is "success"
    And the agent clicked "Submit Application" 1 times
