Feature: Image Captcha Handling
  As a job seeker
  I want the bot to stop when an image captcha is detected
  So that I know automation cannot continue

  Scenario: Bot fails fast when image captcha is detected
    Given a configured profile with name "Jane" and email "jane@test.com"
    And a job posting for "ImgCaptcha Corp" titled "Dev" with an image captcha
    When the bot processes the application
    Then the application status should be "failed"
    And the failure reason contains "Image-based captcha"
