Feature: Guest Job Application
  As a job seeker
  I want the bot to apply to jobs as a guest
  So that I don't need to create accounts

  Scenario: Successfully apply to a guest-enabled job posting
    Given a configured profile with name "Jane" and email "jane@test.com"
    And a job posting for "Acme Corp" titled "Engineer" that allows guest applications
    And debug mode is disabled
    When the bot processes the application
    Then the application status should be "applied"
    And the user receives a confirmation message containing "Acme Corp"
    And the resume was uploaded

  Scenario: Bot fills in all profile fields from config
    Given a configured profile with name "Jane" and email "jane@test.com"
    And the profile has phone "+1234" and address "123 Main St"
    And a job posting for "Beta Inc" titled "Dev" that allows guest applications
    When the bot processes the application
    Then the browser filled "full_name" with "Jane"
    And the browser filled "email" with "jane@test.com"
    And the browser filled "phone" with "+1234"
    And the browser filled "address" with "123 Main St"
