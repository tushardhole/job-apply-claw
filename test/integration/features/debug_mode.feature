Feature: Debug Mode
  As a developer
  I want the bot to skip the final submit in debug mode
  So that I can verify the flow without actually applying

  Scenario: Bot skips submit and captures screenshots in debug mode
    Given a configured profile with name "Jane" and email "jane@test.com"
    And a job posting for "Debug Corp" titled "Engineer" that allows guest applications
    And debug mode is enabled
    When the bot processes the application
    Then the application status should be "skipped"
    And the user receives a message containing "DEBUG"
    And debug screenshots are saved
    And debug metadata is saved with outcome "skipped"
    And the "Apply" button was not clicked

  Scenario: Bot applies normally when debug mode is off
    Given a configured profile with name "Jane" and email "jane@test.com"
    And a job posting for "Normal Corp" titled "Engineer" that allows guest applications
    And debug mode is disabled
    When the bot processes the application
    Then the application status should be "applied"
    And the "Apply" button was clicked
