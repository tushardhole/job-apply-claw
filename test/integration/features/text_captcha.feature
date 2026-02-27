Feature: Text Captcha Handling
  As a job seeker
  I want the bot to send me a captcha screenshot and use my answer
  So that I can help solve text-based captchas

  Scenario: Bot asks user to solve text captcha via Telegram
    Given a configured profile with name "Jane" and email "jane@test.com"
    And a job posting for "Captcha Corp" titled "Dev" with a text captcha
    And the user will solve the captcha with "ABC123"
    When the bot processes the application
    Then the application status should be "applied"
    And the browser filled "captcha" with "ABC123"
