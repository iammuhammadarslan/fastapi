# Requirements Document

## Introduction

The Time-Off Microservice is a NestJS + SQLite service that manages employee time-off requests for ExampleHR. It maintains local time-off balances per employee per location, synchronizes with an external HCM (Human Capital Management) system as the Source of Truth for employment data, and handles the full lifecycle of time-off requests from submission through approval or rejection.

The service must remain defensively correct: HCM may update balances independently (e.g., work anniversaries, year-start refreshes), may not always return errors for invalid operations, and may be temporarily unavailable. The service must detect and resolve conflicts, prevent over-draws, and provide employees and managers with accurate, real-time balance information.

---

## Glossary

- **TimeOffService**: The NestJS microservice being specified in this document.
- **HCM**: The Human Capital Management system (e.g., Workday, SAP) that is the Source of Truth for employment data and time-off balances.
- **Employee**: A user persona who submits time-off requests and views their balances.
- **Manager**: A user persona who approves or rejects time-off requests.
- **Balance**: The number of available time-off days for a specific Employee at a specific Location.
- **Location**: An organizational dimension (e.g., country or office) that scopes a Balance.
- **TimeOffRequest**: A record representing an Employee's request to use time off for a date range.
- **HCM_RealTimeAPI**: The HCM endpoint that gets or sets a single Balance for a given employeeId and locationId.
- **HCM_BatchEndpoint**: The HCM endpoint that sends the full corpus of all Balances to the TimeOffService.
- **MockHCM**: A deployable mock server that simulates HCM behavior for use in the test suite.
- **SyncJob**: A scheduled or triggered process that reconciles local Balances with HCM.
- **ConflictResolver**: The component responsible for detecting and resolving discrepancies between local and HCM Balances.
- **Dimension**: The combination of employeeId and locationId that uniquely identifies a Balance.

---

## Requirements

### Requirement 1: Time-Off Balance Storage

**User Story:** As an Employee, I want my time-off balance to be stored per location, so that I can see how many days I have available at each of my work locations.

#### Acceptance Criteria

1. THE TimeOffService SHALL store a Balance record for each unique combination of employeeId and locationId.
2. THE TimeOffService SHALL persist Balance records in a SQLite database.
3. WHEN a Balance record is created, THE TimeOffService SHALL record the timestamp of creation.
4. WHEN a Balance record is updated, THE TimeOffService SHALL record the timestamp of the last update and the source of the update (Employee request, HCM real-time sync, or HCM batch sync).
5. THE TimeOffService SHALL enforce that a Balance value is a non-negative number with up to two decimal places.
6. IF a request is made to set a Balance to a negative value, THEN THE TimeOffService SHALL reject the request with a 422 Unprocessable Entity response and an error message identifying the invalid value.

---

### Requirement 2: Time-Off Request Lifecycle

**User Story:** As an Employee, I want to submit, view, and cancel time-off requests, so that I can manage my planned absences.

#### Acceptance Criteria

1. WHEN an Employee submits a time-off request with a valid employeeId, locationId, start date, end date, and number of days, THE TimeOffService SHALL create a TimeOffRequest record with status `PENDING`.
2. THE TimeOffService SHALL assign each TimeOffRequest a unique identifier upon creation.
3. WHEN a TimeOffRequest is created, THE TimeOffService SHALL record the submission timestamp.
4. WHEN an Employee requests a list of their TimeOffRequests, THE TimeOffService SHALL return all TimeOffRequests associated with that employeeId, ordered by submission timestamp descending.
5. WHEN an Employee submits a cancellation for a TimeOffRequest with status `PENDING`, THE TimeOffService SHALL update the status to `CANCELLED` and restore the reserved Balance.
6. IF an Employee submits a cancellation for a TimeOffRequest with status `APPROVED` or `REJECTED`, THEN THE TimeOffService SHALL reject the cancellation with a 409 Conflict response.
7. THE TimeOffService SHALL support the following TimeOffRequest statuses: `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`.

---

### Requirement 3: Balance Validation Before Request Submission

**User Story:** As an Employee, I want instant feedback when I submit a time-off request, so that I know immediately if I have insufficient balance.

#### Acceptance Criteria

1. WHEN an Employee submits a time-off request, THE TimeOffService SHALL check the local Balance for the given employeeId and locationId before creating the TimeOffRequest.
2. IF the requested number of days exceeds the available local Balance, THEN THE TimeOffService SHALL reject the request with a 422 Unprocessable Entity response containing the current available balance and the requested amount.
3. WHEN a TimeOffRequest is created with status `PENDING`, THE TimeOffService SHALL reserve the requested days by reducing the local Balance by the requested amount.
4. WHEN a TimeOffRequest transitions to `APPROVED`, THE TimeOffService SHALL confirm the deduction is already applied and SHALL NOT deduct the balance a second time.
5. WHEN a TimeOffRequest transitions to `REJECTED`, THE TimeOffService SHALL restore the reserved Balance by adding the requested days back to the local Balance.

---

### Requirement 4: Manager Approval Workflow

**User Story:** As a Manager, I want to approve or reject pending time-off requests, so that I can manage team availability with confidence in the data's validity.

#### Acceptance Criteria

1. WHEN a Manager approves a TimeOffRequest with status `PENDING`, THE TimeOffService SHALL update the status to `APPROVED` and submit the balance deduction to the HCM_RealTimeAPI.
2. WHEN a Manager rejects a TimeOffRequest with status `PENDING`, THE TimeOffService SHALL update the status to `REJECTED` and restore the reserved Balance.
3. IF the HCM_RealTimeAPI returns an error when the Manager approves a request, THEN THE TimeOffService SHALL update the TimeOffRequest status to `REJECTED`, restore the reserved Balance, and return a 502 Bad Gateway response with the HCM error detail.
4. IF the HCM_RealTimeAPI is unavailable when the Manager approves a request, THEN THE TimeOffService SHALL update the TimeOffRequest status to `REJECTED`, restore the reserved Balance, and return a 503 Service Unavailable response.
5. IF a Manager attempts to approve or reject a TimeOffRequest that is not in `PENDING` status, THEN THE TimeOffService SHALL reject the action with a 409 Conflict response indicating the current status.

---

### Requirement 5: Real-Time HCM Sync (Per Employee/Location)

**User Story:** As a Manager, I want the system to verify balances against HCM before approving requests, so that approvals are based on accurate data.

#### Acceptance Criteria

1. WHEN a Manager initiates approval of a TimeOffRequest, THE TimeOffService SHALL query the HCM_RealTimeAPI for the current Balance for the given employeeId and locationId before finalizing the approval.
2. WHEN the HCM_RealTimeAPI returns a Balance that differs from the local Balance by more than 0.01 days, THE TimeOffService SHALL update the local Balance to match the HCM value and record the update source as `HCM_REALTIME`.
3. WHEN a real-time sync updates the local Balance, THE TimeOffService SHALL re-evaluate whether the pending TimeOffRequest can still be fulfilled with the updated Balance.
4. IF the updated Balance is insufficient to fulfill the TimeOffRequest after a real-time sync, THEN THE TimeOffService SHALL reject the TimeOffRequest with a 422 Unprocessable Entity response, restore the reserved Balance, and return the updated HCM balance in the response body.
5. WHEN a GET request is made to `/balances/{employeeId}/{locationId}`, THE TimeOffService SHALL return the locally stored Balance without triggering a real-time HCM sync.
6. WHEN a POST request is made to `/balances/{employeeId}/{locationId}/sync`, THE TimeOffService SHALL trigger a real-time HCM sync for that Dimension and return the updated Balance.

---

### Requirement 6: Batch HCM Sync

**User Story:** As a system operator, I want the TimeOffService to accept and process batch balance updates from HCM, so that all employee balances stay current after bulk HCM operations like year-start refreshes.

#### Acceptance Criteria

1. WHEN the HCM_BatchEndpoint sends a POST request to `/hcm/batch-sync` with a payload containing an array of Balance records, THE TimeOffService SHALL process each record and update the corresponding local Balance.
2. WHEN processing a batch sync, THE TimeOffService SHALL update the local Balance for each record where the HCM value differs from the local value by more than 0.01 days.
3. WHEN processing a batch sync, THE TimeOffService SHALL record the update source as `HCM_BATCH` for each updated Balance.
4. WHEN a batch sync updates a Balance for an employeeId/locationId that has one or more `PENDING` TimeOffRequests, THE TimeOffService SHALL re-evaluate each affected `PENDING` request against the new Balance.
5. IF a batch sync causes a `PENDING` TimeOffRequest to exceed the updated Balance, THEN THE TimeOffService SHALL update the TimeOffRequest status to `CANCELLED`, restore the reserved Balance, and record a cancellation reason of `BALANCE_UPDATED_BY_HCM`.
6. WHEN a batch sync completes, THE TimeOffService SHALL return a summary response containing the total number of records received, the number of Balances updated, and the number of TimeOffRequests cancelled due to insufficient balance.
7. IF a batch sync payload contains a record with an invalid Dimension (unrecognized employeeId or locationId), THEN THE TimeOffService SHALL skip that record, log a warning, and include the skipped record count in the summary response.
8. IF a batch sync payload contains a record with a negative Balance value, THEN THE TimeOffService SHALL skip that record, log a warning, and include it in the skipped record count.

---

### Requirement 7: Defensive Balance Validation

**User Story:** As a system operator, I want the TimeOffService to validate balances independently of HCM error responses, so that the system remains correct even when HCM silently accepts invalid operations.

#### Acceptance Criteria

1. BEFORE submitting any balance deduction to the HCM_RealTimeAPI, THE TimeOffService SHALL verify that the local Balance is sufficient to cover the deduction.
2. AFTER receiving a success response from the HCM_RealTimeAPI for a balance deduction, THE TimeOffService SHALL query the HCM_RealTimeAPI again to confirm the new Balance matches the expected post-deduction value.
3. IF the post-deduction HCM Balance does not match the expected value within a tolerance of 0.01 days, THEN THE TimeOffService SHALL log a warning with the employeeId, locationId, expected value, and actual HCM value, and SHALL update the local Balance to match the confirmed HCM value.
4. THE TimeOffService SHALL treat any HCM success response as potentially unreliable and SHALL always perform a post-write read to confirm the committed Balance.
5. WHEN the TimeOffService detects a discrepancy between the local Balance and the HCM Balance during any sync operation, THE TimeOffService SHALL record a BalanceDiscrepancy event with the timestamp, employeeId, locationId, local value, HCM value, and resolution action taken.

---

### Requirement 8: Conflict Resolution for Independent HCM Balance Changes

**User Story:** As an Employee, I want my balance to reflect the latest HCM data even when HCM updates it independently, so that I always see an accurate balance.

#### Acceptance Criteria

1. WHEN a SyncJob runs, THE TimeOffService SHALL query the HCM_RealTimeAPI for each Dimension that has had a local Balance update within the past 24 hours and reconcile any differences.
2. WHEN the ConflictResolver detects that the HCM Balance for a Dimension is higher than the local Balance, THE TimeOffService SHALL update the local Balance to the HCM value and record the source as `HCM_CONFLICT_RESOLUTION`.
3. WHEN the ConflictResolver detects that the HCM Balance for a Dimension is lower than the local Balance, THE TimeOffService SHALL update the local Balance to the HCM value and record the source as `HCM_CONFLICT_RESOLUTION`.
4. WHEN a conflict resolution updates a Balance that has one or more `PENDING` TimeOffRequests, THE TimeOffService SHALL re-evaluate each affected `PENDING` request against the resolved Balance.
5. IF a conflict resolution causes a `PENDING` TimeOffRequest to exceed the resolved Balance, THEN THE TimeOffService SHALL update the TimeOffRequest status to `CANCELLED` and record a cancellation reason of `BALANCE_UPDATED_BY_HCM`.
6. THE TimeOffService SHALL expose a GET endpoint at `/balances/discrepancies` that returns all recorded BalanceDiscrepancy events, filterable by employeeId, locationId, and date range.

---

### Requirement 9: HCM API Client

**User Story:** As a developer, I want a well-defined HCM API client, so that all HCM interactions are consistent, retryable, and observable.

#### Acceptance Criteria

1. THE TimeOffService SHALL communicate with the HCM_RealTimeAPI using an HTTP client module that is configurable via environment variables for base URL and timeout.
2. WHEN an HCM_RealTimeAPI request fails with a 5xx status or a network timeout, THE TimeOffService SHALL retry the request up to 3 times with exponential backoff starting at 200ms.
3. WHEN all retry attempts are exhausted, THE TimeOffService SHALL log the failure with the employeeId, locationId, HTTP status code, and number of attempts, and SHALL propagate a structured error to the calling service layer.
4. THE TimeOffService SHALL log every outbound HCM request and inbound HCM response at the DEBUG level, including the HTTP method, URL, request body, response status, and response body.
5. WHEN the HCM_RealTimeAPI returns a 4xx error, THE TimeOffService SHALL NOT retry the request and SHALL propagate the error immediately to the calling service layer.

---

### Requirement 10: Mock HCM Server

**User Story:** As a developer, I want a deployable mock HCM server, so that I can run the full test suite without depending on a real HCM system.

#### Acceptance Criteria

1. THE MockHCM SHALL expose a GET endpoint at `/hcm/balances/{employeeId}/{locationId}` that returns the current Balance for the given Dimension.
2. THE MockHCM SHALL expose a PUT endpoint at `/hcm/balances/{employeeId}/{locationId}` that accepts a new Balance value and updates the stored Balance.
3. THE MockHCM SHALL expose a POST endpoint at `/hcm/simulate/balance-change` that allows tests to directly set a Balance for a Dimension, simulating an independent HCM update (e.g., work anniversary, year-start refresh).
4. THE MockHCM SHALL expose a POST endpoint at `/hcm/simulate/error` that configures the MockHCM to return a specified HTTP error code for the next N requests to a given Dimension, enabling error-path testing.
5. THE MockHCM SHALL validate that a PUT request to reduce a Balance does not result in a negative Balance, and SHALL return a 422 error if it would, simulating HCM's validation behavior.
6. WHERE the MockHCM is configured to simulate insufficient balance errors, THE MockHCM SHALL return a 422 error with a body containing `{"error": "INSUFFICIENT_BALANCE", "available": <current_balance>}`.
7. THE MockHCM SHALL maintain in-memory state that is reset between test runs via a DELETE request to `/hcm/reset`.
8. THE MockHCM SHALL be startable as a standalone NestJS application on a configurable port for use in integration and end-to-end tests.

---

### Requirement 11: REST API Surface

**User Story:** As a developer integrating with the TimeOffService, I want a consistent and well-documented REST API, so that I can build reliable integrations.

#### Acceptance Criteria

1. THE TimeOffService SHALL expose the following endpoints:
   - `POST /time-off-requests` — submit a new time-off request
   - `GET /time-off-requests?employeeId={id}` — list requests for an employee
   - `GET /time-off-requests/{id}` — get a single request by ID
   - `PATCH /time-off-requests/{id}/approve` — approve a pending request
   - `PATCH /time-off-requests/{id}/reject` — reject a pending request
   - `PATCH /time-off-requests/{id}/cancel` — cancel a pending request
   - `GET /balances/{employeeId}/{locationId}` — get local balance
   - `POST /balances/{employeeId}/{locationId}/sync` — trigger real-time HCM sync
   - `GET /balances/discrepancies` — list balance discrepancy events
   - `POST /hcm/batch-sync` — receive batch balance update from HCM
2. WHEN a request is made with a missing required field, THE TimeOffService SHALL return a 400 Bad Request response with a body listing each missing field and its expected type.
3. WHEN a request is made with a valid structure but semantically invalid data (e.g., end date before start date), THE TimeOffService SHALL return a 422 Unprocessable Entity response with a descriptive error message.
4. THE TimeOffService SHALL return all responses in JSON format with a `Content-Type: application/json` header.
5. WHEN a resource is not found (e.g., unknown employeeId, locationId, or request ID), THE TimeOffService SHALL return a 404 Not Found response with a body containing the resource type and the identifier that was not found.

---

### Requirement 12: Property-Based and Regression Test Suite

**User Story:** As a developer, I want a rigorous test suite with property-based tests, so that balance integrity is guaranteed across a wide range of inputs and sequences of operations.

#### Acceptance Criteria

1. THE TimeOffService test suite SHALL include property-based tests that verify: for any sequence of valid time-off request submissions and approvals, the sum of all approved request days plus the current Balance equals the initial Balance for that Dimension.
2. THE TimeOffService test suite SHALL include a round-trip property test that verifies: for any valid Balance value written to the HCM_RealTimeAPI via the MockHCM, reading the Balance back returns the same value within a tolerance of 0.01 days.
3. THE TimeOffService test suite SHALL include property-based tests that verify: after any batch sync operation, no local Balance is negative.
4. THE TimeOffService test suite SHALL include property-based tests that verify: submitting a time-off request for more days than the available Balance always results in a 422 response, regardless of the specific balance and request values.
5. THE TimeOffService test suite SHALL include integration tests using the MockHCM that cover: successful approval flow, HCM error on approval, HCM independent balance change followed by re-sync, and batch sync with cancelled pending requests.
6. THE TimeOffService test suite SHALL include a regression test for each bug fix, named with the issue identifier, to prevent reintroduction of fixed defects.
