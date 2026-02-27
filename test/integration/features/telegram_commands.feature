Feature: Telegram Bot Commands
  As a user
  I want to control the bot via Telegram commands
  So that I can send URLs and trigger job applications

  Scenario: Bot stores URL from message
    Given a running Telegram bot
    When the user sends "https://jobs.example.com/apply/123"
    Then the bot acknowledges with "URL received"
    And the last stored URL is "https://jobs.example.com/apply/123"

  Scenario: Apply without URL warns user
    Given a running Telegram bot
    When the user sends "/apply"
    Then the bot responds with "No URL stored"

  Scenario: Help command shows usage
    Given a running Telegram bot
    When the user sends "/help"
    Then the bot responds with "/apply"

  Scenario: Status with no applications
    Given a running Telegram bot
    When the user sends "/status"
    Then the bot responds with "No applications"

  Scenario: URL clears after apply
    Given a running Telegram bot with a guest-apply browser
    When the user sends "https://example.com/job/1"
    And the user sends "/apply"
    And the user sends "/apply"
    Then the bot responds with "No URL stored"
