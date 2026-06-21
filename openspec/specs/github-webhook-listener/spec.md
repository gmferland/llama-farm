# Spec: GitHub Webhook Listener

## Purpose

Receives and validates incoming GitHub webhook events, then routes recognized events to the agent dispatcher for processing.

## Requirements

### Requirement: Webhook endpoint accepts GitHub payloads
The service SHALL expose a POST `/github/webhook` HTTP endpoint that accepts GitHub webhook payloads with `Content-Type: application/json`.

#### Scenario: Valid webhook received
- **WHEN** GitHub sends a POST to `/github/webhook` with a valid `X-Hub-Signature-256` header and a JSON body
- **THEN** the service SHALL respond with HTTP 202 and schedule the event for processing

#### Scenario: Missing signature header
- **WHEN** a POST arrives at `/github/webhook` without an `X-Hub-Signature-256` header
- **THEN** the service SHALL respond with HTTP 401 and discard the payload

### Requirement: HMAC signature validation
The service SHALL validate the `X-Hub-Signature-256` header on every incoming webhook using the configured `GITHUB_WEBHOOK_SECRET` environment variable.

#### Scenario: Valid signature
- **WHEN** the computed HMAC-SHA256 of the raw request body matches the value in `X-Hub-Signature-256`
- **THEN** the payload SHALL be accepted and routed to the dispatcher

#### Scenario: Invalid signature
- **WHEN** the computed HMAC-SHA256 does not match `X-Hub-Signature-256`
- **THEN** the service SHALL respond with HTTP 401 and log a warning with the event delivery ID

### Requirement: Event type routing
The service SHALL inspect the `X-GitHub-Event` header and route recognized event types to the dispatcher. Unrecognized event types SHALL be acknowledged (HTTP 202) but not dispatched.

#### Scenario: Recognized event type dispatched
- **WHEN** the event type is `issue_comment`, `pull_request_review_comment`, or `issues` with action `labeled`
- **THEN** the payload SHALL be forwarded to the dispatcher

#### Scenario: Unrecognized event type ignored
- **WHEN** the event type is any other value (e.g., `push`, `star`)
- **THEN** the service SHALL respond with HTTP 202 and take no further action

### Requirement: Immediate response with background processing
The service SHALL return an HTTP response to GitHub within 5 seconds. Agent processing SHALL occur in a background task after the response is sent.

#### Scenario: Agent task deferred
- **WHEN** a valid, recognized event arrives
- **THEN** the service SHALL respond HTTP 202 before agent execution begins, and agent work SHALL proceed asynchronously

### Requirement: Health check endpoint
The service SHALL expose a GET `/health` endpoint that returns HTTP 200 when the service is running.

#### Scenario: Health check succeeds
- **WHEN** a GET request is sent to `/health`
- **THEN** the service SHALL respond with HTTP 200 and a JSON body `{"status": "ok"}`
