## MODIFIED Requirements

### Requirement: Event type routing
The service SHALL inspect the `X-GitHub-Event` header and route recognized event types to the dispatcher. Unrecognized event types SHALL be acknowledged (HTTP 202) but not dispatched. For recognized events, the service SHALL extract the `installation.id` field from the payload and include it in the event context passed to the dispatcher. If `installation.id` is absent, the event SHALL be treated as unrecognized and not dispatched.

#### Scenario: Recognized event type dispatched
- **WHEN** the event type is `issue_comment`, `pull_request_review_comment`, or `issues` with action `labeled`, and the payload contains `installation.id`
- **THEN** the payload SHALL be forwarded to the dispatcher with the installation ID included in the event context

#### Scenario: Unrecognized event type ignored
- **WHEN** the event type is any other value (e.g., `push`, `star`)
- **THEN** the service SHALL respond with HTTP 202 and take no further action

#### Scenario: Missing installation ID
- **WHEN** a recognized event type arrives but the payload does not contain `installation.id`
- **THEN** the service SHALL respond with HTTP 202 and not dispatch the event
