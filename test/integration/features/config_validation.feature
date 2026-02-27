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
