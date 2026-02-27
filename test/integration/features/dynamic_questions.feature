Feature: Dynamic Questions
  As a job seeker
  I want the bot to ask me dynamic questions at apply time
  So that my answers are always accurate for each specific application

  Scenario: Agent asks for work authorization
    Given a profile with name "Jane" and email "jane@test.com"
    And the LLM agent encounters a work authorization question
    When the agent runs the task
    Then the agent outcome is "success"
    And the agent asked "Are you authorized to work in the US?"
    And the agent filled "work_auth" with "Yes, US Citizen"

  Scenario: Agent asks for salary expectation
    Given a profile with name "Jane" and email "jane@test.com"
    And the LLM agent encounters a salary expectation question
    When the agent runs the task
    Then the agent outcome is "success"
    And the agent asked "What is your expected salary for this role?"
    And the agent filled "salary" with "120000"

  Scenario: Agent asks for essay question
    Given a profile with name "Jane" and email "jane@test.com"
    And the LLM agent encounters an essay question
    When the agent runs the task
    Then the agent outcome is "success"
    And the agent asked "Why do you want to work at Acme Corp?"
    And the agent filled "essay_why" with "I admire the engineering culture"

  Scenario: Agent asks for notice period
    Given a profile with name "Jane" and email "jane@test.com"
    And the LLM agent encounters a notice period question
    When the agent runs the task
    Then the agent outcome is "success"
    And the agent asked "What is your notice period?"
    And the agent filled "notice_period" with "2 weeks"

  Scenario: Agent fills static fields without asking user
    Given a profile with name "Jane" and email "jane@test.com"
    And the LLM agent fills only static fields
    When the agent runs the task
    Then the agent outcome is "success"
    And the agent filled "full_name" with "Jane"
    And the agent filled "email" with "jane@test.com"
    And the agent did not ask the user anything
