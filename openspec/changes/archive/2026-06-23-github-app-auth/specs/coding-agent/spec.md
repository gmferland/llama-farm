## MODIFIED Requirements

### Requirement: Completion—open pull request
When the agent loop completes successfully and the task executor has made at least one commit, the agent SHALL open a pull request from the working branch to the default branch. All GitHub API calls (posting comments, opening the PR) SHALL use the installation access token obtained for the triggering event's installation ID.

#### Scenario: PR opened on success
- **WHEN** the agent loop completes with commits in the workspace
- **THEN** the agent SHALL push the working branch and open a PR with a title derived from the task description and a body summarizing the changes made, using the installation access token for authentication

#### Scenario: No changes made
- **WHEN** the agent loop completes but no files were modified
- **THEN** the agent SHALL post a comment indicating no changes were made and SHALL NOT open a PR

## ADDED Requirements

### Requirement: Workspace cloning with installation access token
The workspace initialization SHALL clone the target repository using the installation access token obtained from the token provider for the event's `installation_id`, embedded in the HTTPS clone URL as `https://x-access-token:{token}@github.com/{repo}`.

#### Scenario: Clone succeeds with installation token
- **WHEN** `Workspace.init()` is called with an `EventContext` containing a valid `installation_id`
- **THEN** it SHALL fetch an installation access token and use it to clone the repository

#### Scenario: Token fetch fails before clone
- **WHEN** the token provider raises an exception (e.g., invalid installation ID)
- **THEN** `Workspace.init()` SHALL propagate the exception; the agent run SHALL fail and post an error comment

### Requirement: Configuration via GitHub App credentials
The service SHALL read `GITHUB_APP_ID` (integer) and `GITHUB_APP_PRIVATE_KEY` (PEM string, with literal newlines or `\n`-escaped) from environment variables. `GITHUB_TOKEN` and `GITHUB_REPO` SHALL no longer be required.

#### Scenario: Valid App credentials present
- **WHEN** `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` are set with valid values
- **THEN** the service SHALL start successfully and process webhook events

#### Scenario: Missing App credentials
- **WHEN** either `GITHUB_APP_ID` or `GITHUB_APP_PRIVATE_KEY` is absent from the environment
- **THEN** the service SHALL fail to start with a clear error message
