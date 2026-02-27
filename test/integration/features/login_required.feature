Feature: Login Required Job Application
  As a job seeker
  I want the bot to create an account when login is required
  So that I can apply to jobs that need authentication

  Scenario: Bot creates account and applies when login is required
    Given a configured profile with name "Jane" and email "jane@test.com"
    And a job posting for "Gamma Corp" titled "Dev" that requires login
    And debug mode is disabled
    When the bot processes the application
    Then the application status should be "applied"
    And an account credential is stored for "Gamma Corp"

  Scenario: Bot detects OAuth-only login and fails fast
    Given a configured profile with name "Jane" and email "jane@test.com"
    And a job posting for "OAuth Corp" titled "Dev" with OAuth-only login
    When the bot processes the application
    Then the application status should be "failed"
    And the failure reason contains "OAuth"
