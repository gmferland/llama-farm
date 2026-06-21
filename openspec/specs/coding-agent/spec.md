# Spec: Coding Agent

## Purpose

Drives autonomous coding tasks against a self-hosted LLM using the OpenAI tool-calling protocol, responding to GitHub events and producing pull requests with the resulting changes.

## Requirements

### Requirement: Agent activation via slash command
The agent SHALL activate when an issue comment or PR review comment begins with `/agent` (case-insensitive, leading whitespace ignored). The text following `/agent` is treated as the task description.

#### Scenario: Issue comment with slash command
- **WHEN** an `issue_comment` event arrives with a body starting with `/agent <task>`
- **THEN** the agent SHALL be invoked with the task description and the issue's repository context

#### Scenario: No slash command present
- **WHEN** an `issue_comment` event arrives with a body that does not start with `/agent`
- **THEN** the agent SHALL not activate

### Requirement: Agent activation via label
The agent SHALL activate when an issue receives the label `agent-task`. The issue body is used as the task description.

#### Scenario: Issue labeled with agent-task
- **WHEN** an `issues` event with action `labeled` arrives and the label name is `agent-task`
- **THEN** the agent SHALL be invoked with the issue body as the task description

### Requirement: Initial acknowledgement comment
When activated, the agent SHALL post a comment on the triggering issue or PR indicating it has started work, before beginning the agent loop.

#### Scenario: Start comment posted
- **WHEN** the agent is activated by a valid trigger
- **THEN** the agent SHALL post a comment of the form "Agent started: <brief task summary>" within 10 seconds of activation

### Requirement: Agent loop with tool calling
The agent SHALL drive a multi-turn conversation with the local LLM endpoint using the OpenAI tool-calling protocol. Each turn, the agent sends the current conversation history plus the tool schema, receives a response, executes any tool calls, appends results, and continues.

#### Scenario: Tool call in response
- **WHEN** the LLM response contains one or more `tool_calls`
- **THEN** the agent SHALL execute each tool call in order, append a `tool` role message with the result, and send the next turn

#### Scenario: No tool call in response
- **WHEN** the LLM response contains no `tool_calls` and the finish reason is `stop`
- **THEN** the agent SHALL treat the run as complete and proceed to the completion step

### Requirement: Maximum iteration limit
The agent loop SHALL terminate after a configurable maximum number of LLM turns (default: 20, configurable via `AGENT_MAX_ITERATIONS` environment variable) to prevent runaway loops.

#### Scenario: Max iterations reached
- **WHEN** the agent has completed `AGENT_MAX_ITERATIONS` turns without reaching a stop condition
- **THEN** the agent SHALL halt, post a comment indicating it reached the iteration limit, and not open a PR

### Requirement: Completion—open pull request
When the agent loop completes successfully and the task executor has made at least one commit, the agent SHALL open a pull request from the working branch to the default branch.

#### Scenario: PR opened on success
- **WHEN** the agent loop completes with commits in the workspace
- **THEN** the agent SHALL push the working branch and open a PR with a title derived from the task description and a body summarizing the changes made

#### Scenario: No changes made
- **WHEN** the agent loop completes but no files were modified
- **THEN** the agent SHALL post a comment indicating no changes were made and SHALL NOT open a PR

### Requirement: Error reporting via comment
If the agent encounters an unrecoverable error during execution, it SHALL post a comment on the triggering issue or PR with a brief error description.

#### Scenario: Unrecoverable error
- **WHEN** the agent catches an exception that prevents further progress (e.g., LLM endpoint unreachable, git push failure)
- **THEN** the agent SHALL post a comment of the form "Agent failed: <error summary>" and terminate

### Requirement: System prompt with context
The agent SHALL construct a system prompt that includes the repository name, the triggering event context (issue title, PR title, or label), and instructions for the available tools.

#### Scenario: System prompt constructed
- **WHEN** the agent loop is started
- **THEN** the first message in the conversation SHALL be a `system` role message containing repository context and tool usage instructions
