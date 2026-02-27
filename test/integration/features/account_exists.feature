Feature: Account Already Exists
  As a job seeker
  I want the bot to handle "account already exists" by doing forgot password
  So that I can still apply even if I already have an account

  Scenario: Bot does forgot password flow when account exists
    Given a configured profile with name "Jane" and email "jane@test.com"
    And a job posting for "Existing Corp" titled "Dev" where account already exists
    And the user will provide password reset code "RESET-XYZ"
    When the bot processes the application
    Then the application status should be "applied"
    And the browser filled "password_reset_code" with "RESET-XYZ"
