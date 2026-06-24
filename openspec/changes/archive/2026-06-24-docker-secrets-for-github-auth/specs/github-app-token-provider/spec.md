## MODIFIED Requirements

### Requirement: Generate App JWT for GitHub API authentication
The token provider SHALL generate a signed RS256 JWT using the configured `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` values, loaded via the docker-secret-loader (Docker secret file at `/run/secrets/<name>` with fallback to the environment variable of the same name). The JWT SHALL have an `iat` claim backdated by 60 seconds and an `exp` claim 10 minutes after the (actual) current time, to tolerate clock skew.

#### Scenario: JWT generated successfully
- **WHEN** `_generate_jwt()` is called with valid App ID and private key PEM loaded from either source
- **THEN** it SHALL return a signed JWT string accepted by the GitHub Apps API

#### Scenario: Invalid private key
- **WHEN** the resolved `GITHUB_APP_PRIVATE_KEY` value contains an invalid or malformed PEM
- **THEN** JWT generation SHALL raise an exception that propagates to the caller
