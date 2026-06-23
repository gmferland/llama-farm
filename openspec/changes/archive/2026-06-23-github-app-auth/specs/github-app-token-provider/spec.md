## ADDED Requirements

### Requirement: Generate App JWT for GitHub API authentication
The token provider SHALL generate a signed RS256 JWT using the configured `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` environment variables. The JWT SHALL have an `iat` claim backdated by 60 seconds and an `exp` claim 10 minutes after the (actual) current time, to tolerate clock skew.

#### Scenario: JWT generated successfully
- **WHEN** `_generate_jwt()` is called with valid App ID and private key PEM
- **THEN** it SHALL return a signed JWT string accepted by the GitHub Apps API

#### Scenario: Invalid private key
- **WHEN** `GITHUB_APP_PRIVATE_KEY` contains an invalid or malformed PEM
- **THEN** JWT generation SHALL raise an exception that propagates to the caller

### Requirement: Exchange JWT for installation access token
The token provider SHALL call `POST /app/installations/{installation_id}/access_tokens` with the App JWT to obtain a short-lived installation access token scoped to the given installation.

#### Scenario: Token exchange succeeds
- **WHEN** `get_installation_token(installation_id)` is called with a valid installation ID and a valid App JWT
- **THEN** it SHALL return the `token` string from the GitHub API response

#### Scenario: Token exchange fails
- **WHEN** the GitHub API returns a non-2xx response (e.g., invalid installation ID or revoked App)
- **THEN** the function SHALL raise an exception that propagates to the caller

### Requirement: Cache installation tokens with expiry
The token provider SHALL cache installation access tokens in memory, keyed by `installation_id`. On each call, it SHALL return the cached token if it exists and expires more than 5 minutes in the future. Otherwise it SHALL fetch a fresh token, cache it, and return it.

#### Scenario: Cache hit — token still valid
- **WHEN** `get_installation_token(installation_id)` is called and a cached token exists with more than 5 minutes remaining
- **THEN** it SHALL return the cached token without making any HTTP request

#### Scenario: Cache miss — no prior token
- **WHEN** `get_installation_token(installation_id)` is called for an installation ID not in the cache
- **THEN** it SHALL fetch a new token from the GitHub API, store it in the cache, and return it

#### Scenario: Cache expired — token near expiry
- **WHEN** `get_installation_token(installation_id)` is called and the cached token expires within 5 minutes
- **THEN** it SHALL evict the cached entry, fetch a fresh token, cache it, and return it
