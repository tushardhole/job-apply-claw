Feature: Login with OTP Verification
  As a job seeker
  I want the bot to handle OTP verification during account creation
  So that I can verify my account via Telegram

  Scenario: Bot asks user for OTP and completes application
    Given a configured profile with name "Jane" and email "jane@test.com"
    And a job posting for "OTP Corp" titled "Engineer" that requires login with OTP
    And the user will provide OTP "123456"
    When the bot processes the application
    Then the application status should be "applied"
    And the browser filled "otp" with "123456"
    And an account credential is stored for "OTP Corp"
