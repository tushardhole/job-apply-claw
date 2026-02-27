Feature: Config Validation
  As a user
  I want the app to validate my config folder on startup
  So that I get clear errors if something is missing

  Scenario: Valid config passes validation
    Given a complete config folder with all required files
    When the config is validated
    Then validation passes with no errors

  Scenario: Missing config.json reports error
    Given a config folder without config.json
    When the config is validated
    Then validation reports an error containing "config.json"

  Scenario: Missing profile.json reports error
    Given a config folder without profile.json
    When the config is validated
    Then validation reports an error containing "profile.json"

  Scenario: Missing resume PDF reports error
    Given a config folder without resume PDF
    When the config is validated
    Then validation reports an error containing "Resume not found"

  Scenario: Invalid JSON reports error
    Given a config folder with invalid JSON in config.json
    When the config is validated
    Then validation reports an error containing "Cannot read"

  Scenario: Missing required keys reports error
    Given a config folder with config.json missing "OPENAI_KEY"
    When the config is validated
    Then validation reports an error containing "missing keys"

  Scenario: Placeholder BOT_TOKEN is detected
    Given a config folder with BOT_TOKEN set to "YOUR_TELEGRAM_BOT_TOKEN"
    When the config is validated
    Then validation reports an error containing "BOT_TOKEN is a placeholder"

  Scenario: Non-numeric chat ID is detected
    Given a config folder with TELEGRAM_CHAT_ID set to "not-a-number"
    When the config is validated
    Then validation reports an error containing "TELEGRAM_CHAT_ID must be numeric"

  Scenario: Placeholder email in profile is detected
    Given a config folder with profile email set to "your@email.com"
    When the config is validated
    Then validation reports an error containing "email is a placeholder"

  Scenario: Successful connectivity check
    Given a valid config with working API keys
    When connectivity is validated with mock success
    Then connectivity passes
    And the bot username is "test_bot"

  Scenario: Failed Telegram connectivity
    Given a valid config with working API keys
    When connectivity is validated with Telegram failure
    Then connectivity reports an error containing "BOT_TOKEN"
