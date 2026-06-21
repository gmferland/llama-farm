## ADDED Requirements

### Requirement: Workspace initialization
The task executor SHALL initialize a fresh workspace for each agent run by performing a shallow git clone of the target repository into a temporary directory, then checking out a new working branch named `agent/<run-id>`.

#### Scenario: Workspace created
- **WHEN** a new agent run begins
- **THEN** the executor SHALL clone the repo with `--depth=1`, create a branch `agent/<run-id>`, and return the workspace path to the agent

#### Scenario: Clone failure
- **WHEN** the git clone fails (e.g., invalid repo URL, auth failure)
- **THEN** the executor SHALL raise an error that the agent reports as a failure comment

### Requirement: Read file tool
The executor SHALL provide a `read_file` tool that returns the contents of a file within the workspace.

#### Scenario: File read succeeds
- **WHEN** the agent calls `read_file` with a path relative to the workspace root
- **THEN** the executor SHALL return the file contents as a string

#### Scenario: File not found
- **WHEN** the agent calls `read_file` with a path that does not exist
- **THEN** the executor SHALL return an error string indicating the file was not found

### Requirement: Write file tool
The executor SHALL provide a `write_file` tool that creates or overwrites a file within the workspace.

#### Scenario: File written successfully
- **WHEN** the agent calls `write_file` with a relative path and content
- **THEN** the executor SHALL write the content to that path, creating parent directories as needed

#### Scenario: Path escapes workspace
- **WHEN** the resolved absolute path would be outside the workspace root (path traversal attempt)
- **THEN** the executor SHALL return an error string and SHALL NOT write any file

### Requirement: List directory tool
The executor SHALL provide a `list_directory` tool that returns the names of files and directories at a given path within the workspace.

#### Scenario: Directory listed
- **WHEN** the agent calls `list_directory` with a relative path
- **THEN** the executor SHALL return a JSON array of entry names with a `type` field (`file` or `dir`) for each

#### Scenario: Path not a directory
- **WHEN** the path does not exist or is not a directory
- **THEN** the executor SHALL return an error string

### Requirement: Run shell command tool
The executor SHALL provide a `run_shell` tool that executes a shell command within the workspace directory and returns stdout, stderr, and exit code.

#### Scenario: Command succeeds
- **WHEN** the agent calls `run_shell` with a command string
- **THEN** the executor SHALL run the command with `cwd` set to the workspace root and return `{"stdout": "...", "stderr": "...", "exit_code": 0}`

#### Scenario: Command times out
- **WHEN** the command does not complete within 60 seconds
- **THEN** the executor SHALL terminate the process and return an error result with `exit_code: -1` and a timeout message in stderr

### Requirement: Commit changes tool
The executor SHALL provide a `commit_changes` tool that stages all modified and new files in the workspace and creates a git commit with a provided message.

#### Scenario: Changes committed
- **WHEN** the agent calls `commit_changes` with a commit message
- **THEN** the executor SHALL run `git add -A && git commit -m "<message>"` in the workspace and return the resulting commit SHA

#### Scenario: Nothing to commit
- **WHEN** there are no staged or unstaged changes
- **THEN** the executor SHALL return a result indicating no changes were committed

### Requirement: Post GitHub comment tool
The executor SHALL provide a `post_comment` tool that posts a comment on the triggering issue or PR via the GitHub API.

#### Scenario: Comment posted
- **WHEN** the agent calls `post_comment` with a message body
- **THEN** the executor SHALL POST to the GitHub API to create a comment on the triggering issue or PR and return the comment URL

### Requirement: Workspace cleanup
After an agent run completes (success or failure), the executor SHALL delete the temporary workspace directory.

#### Scenario: Workspace deleted after run
- **WHEN** the agent run finishes for any reason
- **THEN** the executor SHALL remove the cloned workspace directory from the filesystem

### Requirement: Concurrency limit
The executor SHALL enforce a maximum number of concurrent agent runs (default: 20, configurable via `AGENT_MAX_CONCURRENCY`). Runs beyond the limit SHALL be rejected with an error.

#### Scenario: Concurrency limit reached
- **WHEN** a new agent run is triggered and the number of active runs equals `AGENT_MAX_CONCURRENCY`
- **THEN** the executor SHALL reject the new run and the agent SHALL post a comment indicating the system is busy
