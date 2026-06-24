## ADDED Requirements

### Requirement: Load secret from Docker secret file with env var fallback
The secret loader SHALL attempt to read a named secret from the file at `/run/secrets/<name>`, stripping leading and trailing whitespace from the file contents. If the file does not exist, it SHALL fall back to reading the value from the environment variable with the same name. If neither source provides a non-empty value, the caller is responsible for raising an error.

#### Scenario: Docker secret file present and readable
- **WHEN** `/run/secrets/<name>` exists and is readable
- **THEN** `load_secret(name)` SHALL return the file contents stripped of leading/trailing whitespace

#### Scenario: Docker secret file absent — env var set
- **WHEN** `/run/secrets/<name>` does not exist and the environment variable `<name>` is set to a non-empty value
- **THEN** `load_secret(name)` SHALL return the environment variable value

#### Scenario: Neither file nor env var present
- **WHEN** `/run/secrets/<name>` does not exist and the environment variable `<name>` is unset or empty
- **THEN** `load_secret(name)` SHALL return `None`

#### Scenario: Docker secret file exists but is not readable
- **WHEN** `/run/secrets/<name>` exists but the process lacks read permission
- **THEN** `load_secret(name)` SHALL raise a `PermissionError`, propagating it to the caller without falling back to the environment variable
