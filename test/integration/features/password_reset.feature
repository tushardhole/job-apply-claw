Feature: Password Reset Flow
  As a job seeker
  I want the bot to handle forgot password scenarios
  So that I can still apply even if I already have an account

  Scenario: Agent handles code-based password reset
    Given a configured profile with name "Jane" and email "jane@test.com"
    And the LLM agent will perform a code-based password reset
    When the agent executes the task
    Then the agent result status is "success"
    And the agent asked the user for "Enter the reset code from your email"
    And the agent filled "reset_code" with "RESET-ABC"
    And the agent filled "new_password" with "NewPass123!"

  Scenario: Agent handles link-based password reset
    Given a configured profile with name "Jane" and email "jane@test.com"
    And the LLM agent will perform a link-based password reset
    When the agent executes the task
    Then the agent result status is "success"
    And the agent visited "https://portal.test/reset?token=xyz"
    And the agent filled "new_password" with "NewPass123!"

  Scenario: Agent lands on login page after reset and logs in
    Given a configured profile with name "Jane" and email "jane@test.com"
    And the LLM agent resets password and lands on login page
    When the agent executes the task
    Then the agent result status is "success"
    And the agent filled "email" with "jane@test.com"
    And the agent filled "password" with "NewPass123!"
    And the agent visited "https://example.test/jobs/1"

  Scenario: Agent lands on dashboard after reset and navigates to job
    Given a configured profile with name "Jane" and email "jane@test.com"
    And the LLM agent resets password and lands on dashboard
    When the agent executes the task
    Then the agent result status is "success"
    And the agent visited "https://example.test/jobs/1"

  Scenario: Agent handles password reset with no confirm field
    Given a configured profile with name "Jane" and email "jane@test.com"
    And the LLM agent resets password without confirm field
    When the agent executes the task
    Then the agent result status is "success"
    And the agent filled "new_password" with "NewPass123!"

  Scenario: Agent retries on invalid reset code
    Given a configured profile with name "Jane" and email "jane@test.com"
    And the LLM agent retries after invalid reset code
    When the agent executes the task
    Then the agent result status is "success"
    And the agent asked the user 2 times

  Scenario: Agent fails when reset times out
    Given a configured profile with name "Jane" and email "jane@test.com"
    And the LLM agent times out during password reset
    When the agent executes the task
    Then the agent result status is "failed"
    And the agent failure reason contains "maximum steps"

  Scenario: Agent skips submit in debug mode after password reset
    Given a configured profile with name "Jane" and email "jane@test.com"
    And the LLM agent resets password in debug mode
    When the agent executes the task
    Then the agent result status is "skipped"
    And the agent failure reason contains "Debug mode"
