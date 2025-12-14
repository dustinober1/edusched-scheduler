# EduSched End-to-End Test Plan

## Table of Contents
1. [Test Environment Setup](#test-environment-setup)
2. [Backend API Testing](#backend-api-testing)
3. [Frontend Integration Testing](#frontend-integration-testing)
4. [Full Workflow Testing](#full-workflow-testing)
5. [Edge Cases and Error Handling](#edge-cases-and-error-handling)
6. [Performance Testing](#performance-testing)
7. [Security Testing](#security-testing)
8. [Test Data Management](#test-data-management)

## Test Environment Setup

### Prerequisites
- Python 3.8+ with pip
- Node.js 18+ and npm
- Docker and Docker Compose
- PostgreSQL database
- Redis (for caching and real-time features)

### Environment Configuration
```bash
# Backend setup
cd /Users/dustinober/Projects/Education_Manager
pip install -e .[all,dev]
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/edusched_test
export REDIS_URL=redis://localhost:6379/1

# Frontend setup
cd frontend
npm install
export VITE_API_URL=http://localhost:8000/api
```

### Test Utilities Installation
```bash
# Install E2E testing framework
npm install -g playwright
npx playwright install

# Install additional test tools
pip install pytest-playwright pytest-asyncio httpx websockets
```

## Backend API Testing

### 1. Health Check Endpoints

#### TC-API-HC-001: Basic Health Check
**Objective**: Verify the API responds to basic health checks
**Steps**:
1. Send GET request to `/health`
2. Verify response status is 200
3. Verify response contains `status: "healthy"`
4. Verify response contains version information

**Expected Result**:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### TC-API-HC-002: Root Endpoint
**Objective**: Verify root endpoint provides API information
**Steps**:
1. Send GET request to `/`
2. Verify response status is 200
3. Verify response contains API name, version, and documentation links

### 2. Schedule CRUD Operations

#### TC-API-SCH-001: Create Schedule
**Objective**: Successfully create a new schedule
**Steps**:
1. Authenticate as test user
2. Send POST request to `/api/v1/schedules` with schedule data
3. Verify response status is 201
4. Verify schedule ID is returned
5. Verify schedule data is persisted

**Request Body**:
```json
{
  "name": "Test Schedule 2024",
  "solver": "heuristic",
  "optimize": true,
  "seed": 12345
}
```

#### TC-API-SCH-002: Get Schedule by ID
**Objective**: Retrieve a specific schedule
**Steps**:
1. Use schedule ID from TC-API-SCH-001
2. Send GET request to `/api/v1/schedules/{schedule_id}`
3. Verify response status is 200
4. Verify schedule details match created data
5. Verify assignments array is present

#### TC-API-SCH-003: List Schedules
**Objective**: Retrieve paginated list of schedules
**Steps**:
1. Send GET request to `/api/v1/schedules`
2. Verify response status is 200
3. Verify pagination parameters work (limit, skip)
4. Verify search functionality works

**Test Cases**:
- List without filters
- List with limit=10
- List with search term
- List with pagination (skip=10, limit=10)

#### TC-API-SCH-004: Update Schedule
**Objective**: Update existing schedule properties
**Steps**:
1. Use schedule ID from TC-API-SCH-001
2. Send PUT request to `/api/v1/schedules/{schedule_id}`
3. Verify response status is 200
4. Verify updated fields reflect changes
5. Verify original unchanged fields persist

#### TC-API-SCH-005: Delete Schedule
**Objective**: Soft delete a schedule
**Steps**:
1. Create a test schedule
2. Send DELETE request to `/api/v1/schedules/{schedule_id}`
3. Verify response status is 200
4. Verify schedule is marked as deleted
5. Verify it doesn't appear in list responses

#### TC-API-SCH-006: Duplicate Schedule
**Objective**: Create a copy of an existing schedule
**Steps**:
1. Use existing schedule ID
2. Send POST request to `/api/v1/schedules/{schedule_id}/duplicate`
3. Verify response status is 201
4. Verify new schedule has different ID
5. Verify assignments are copied

#### TC-API-SCH-007: Export Schedule
**Objective**: Export schedule in different formats
**Steps**:
1. Use existing schedule ID
2. Send GET request to `/api/v1/schedules/{schedule_id}/export`
3. Test all supported formats: json, csv, ical, excel
4. Verify response headers include correct content-type
5. Verify exported file is valid

### 3. Resource Management

#### TC-API-RES-001: Create Resource
**Objective**: Add new schedulable resource
**Steps**:
1. Send POST request to `/api/v1/resources`
2. Verify response status is 201
3. Verify resource ID is generated
4. Verify all properties are saved

**Request Body**:
```json
{
  "name": "Room 101",
  "type": "classroom",
  "capacity": 30,
  "building_id": "building-a",
  "attributes": {
    "has_projector": true,
    "has_whiteboard": true
  },
  "availability": {
    "monday": [["09:00", "17:00"]],
    "tuesday": [["09:00", "17:00"]],
    "wednesday": [["09:00", "17:00"]],
    "thursday": [["09:00", "17:00"]],
    "friday": [["09:00", "17:00"]]
  }
}
```

#### TC-API-RES-002: Bulk Import Resources
**Objective**: Import multiple resources from file
**Steps**:
1. Prepare CSV/Excel file with resource data
2. Send POST request with file to `/api/v1/resources/bulk-import`
3. Verify response status is 200
4. Verify import summary is returned
5. Verify resources are created in database

### 4. Constraint Management

#### TC-API-CON-001: Create Constraint
**Objective**: Add scheduling constraint
**Steps**:
1. Send POST request to `/api/v1/constraints`
2. Verify response status is 201
3. Verify constraint is properly configured
4. Test constraint types: time, resource, capacity

#### TC-API-CON-002: Validate Constraints
**Objective**: Check constraint validity
**Steps**:
1. Send POST request to `/api/v1/constraints/validate`
2. Include valid and invalid constraints
3. Verify response identifies errors
4. Verify suggestions for fixing issues

### 5. Optimization Engine

#### TC-API-OPT-001: Run Optimization
**Objective**: Execute schedule optimization
**Steps**:
1. Send POST request to `/api/v1/optimization/run`
2. Include problem definition and constraints
3. Verify job ID is returned
4. Verify optimization starts asynchronously

#### TC-API-OPT-002: Get Optimization Status
**Objective**: Check optimization progress
**Steps**:
1. Use job ID from TC-API-OPT-001
2. Send GET request to `/api/v1/optimization/status/{job_id}`
3. Verify status: queued, running, completed, failed
4. Verify progress percentage updates

#### TC-API-OPT-003: Get Optimization Results
**Objective**: Retrieve optimization output
**Steps**:
1. Use completed job ID
2. Send GET request to `/api/v1/optimization/results/{job_id}`
3. Verify complete schedule is returned
4. Verify metrics and statistics are included

### 6. Conflict Detection

#### TC-API-CONF-001: Detect Conflicts
**Objective**: Identify scheduling conflicts
**Steps**:
1. Send POST request to `/api/v1/conflicts/detect`
2. Include schedule data
3. Verify all conflict types are detected:
   - Resource overlaps
   - Teacher conflicts
   - Room capacity violations
   - Time conflicts

#### TC-API-CONF-002: Resolve Conflicts
**Objective**: Get conflict resolution suggestions
**Steps**:
1. Send POST request to `/api/v1/conflicts/resolve`
2. Include conflict list
3. Verify resolution strategies are suggested
4. Verify suggested alternatives are valid

### 7. WebSocket Functionality

#### TC-API-WS-001: Connection Management
**Objective**: Test WebSocket connection lifecycle
**Steps**:
1. Connect to WebSocket endpoint `/ws?user_id=test&schedule_id=schedule123`
2. Verify connection is established
3. Verify connection receives heartbeat
4. Disconnect gracefully
5. Verify connection is closed

#### TC-API-WS-002: Real-time Updates
**Objective**: Receive live updates
**Steps**:
1. Connect to WebSocket with schedule ID
2. Trigger schedule change via REST API
3. Verify WebSocket receives update message
4. Verify message contains changed data
5. Verify message timestamp is current

## Frontend Integration Testing

### 1. Page Loading and Navigation

#### TC-FE-NAV-001: Application Initialization
**Objective**: Verify app loads without errors
**Steps**:
1. Navigate to `http://localhost:3000`
2. Verify main application shell loads
3. Verify no JavaScript errors in console
4. Verify all required assets load successfully
5. Verify loading states display properly

#### TC-FE-NAV-002: Route Navigation
**Objective**: Test all application routes
**Steps**:
1. Test navigation to each route:
   - `/dashboard`
   - `/schedules`
   - `/schedules/new`
   - `/schedules/:id`
   - `/resources`
   - `/constraints`
   - `/optimization`
   - `/analytics`
   - `/settings`
2. Verify each page renders correctly
3. Verify 404 page for invalid routes
4. Verify browser history navigation

#### TC-FE-NAV-003: Protected Routes
**Objective**: Verify authentication requirements
**Steps**:
1. Clear authentication tokens
2. Attempt to access protected routes
3. Verify redirect to login page
4. Verify proper error messaging
5. Verify successful login redirects to intended page

### 2. Data Fetching and Display

#### TC-FE-DATA-001: Dashboard Data Loading
**Objective**: Verify dashboard displays correct information
**Steps**:
1. Navigate to dashboard
2. Verify loading spinner appears
3. Verify metrics display after data loads:
   - Total schedules
   - Active schedules
   - Resource utilization
   - Recent activities
4. Verify error handling if API fails

#### TC-FE-DATA-002: Schedule List
**Objective**: Verify schedule listing functionality
**Steps**:
1. Navigate to schedules page
2. Verify list loads with pagination
3. Test filtering:
   - By status
   - By date range
   - By search term
4. Verify sorting options
5. Verify empty state displays

#### TC-FE-DATA-003: Schedule Details
**Objective**: Verify schedule detail view
**Steps**:
1. Click on a schedule in list
2. Verify all schedule details display
3. Verify assignments render in calendar
4. Verify statistics panel shows correct data
5. Verify export options are available

#### TC-FE-DATA-004: Real-time Updates
**Objective**: Verify WebSocket integration
**Steps**:
1. Open schedule detail view
2. Make changes via another browser/API
3. Verify updates appear automatically
4. Verify change notifications display
5. Verify no page refresh needed

### 3. User Interactions

#### TC-FE-INT-001: Create New Schedule
**Objective**: Test schedule creation flow
**Steps**:
1. Click "New Schedule" button
2. Fill in schedule details form
3. Add constraints via constraint builder
4. Select optimization options
5. Submit form
6. Verify success notification
7. Verify redirect to new schedule

#### TC-FE-INT-002: Edit Schedule
**Objective**: Test schedule editing
**Steps**:
1. Open existing schedule
2. Click edit button
3. Modify schedule properties
4. Add/remove assignments
5. Save changes
6. Verify updates persist
7. Verify validation errors display

#### TC-FE-INT-003: Drag and Drop
**Objective**: Test assignment manipulation
**Steps**:
1. Open schedule in calendar view
2. Drag assignment to new time slot
3. Verify update request is sent
4. Drop on different resource
5. Verify conflict detection
6. Verify visual feedback

#### TC-FE-INT-004: Constraint Builder
**Objective**: Test constraint configuration UI
**Steps**:
1. Open constraint builder
2. Select constraint type
3. Configure constraint parameters
4. Preview constraint effect
5. Save constraint
6. Verify constraint appears in list

### 4. Form Validation and Error Handling

#### TC-FE-VAL-001: Required Fields
**Objective**: Test form validation
**Steps**:
1. Submit forms with empty required fields
2. Verify error messages display
3. Verify submit is blocked
4. Fix validation errors
5. Verify form submits successfully

#### TC-FE-VAL-002: Invalid Data
**Objective**: Test input validation
**Steps**:
1. Enter invalid data types
2. Enter values outside allowed ranges
3. Enter invalid dates/times
4. Verify client-side validation
5. Verify server-side validation

#### TC-FE-VAL-003: Network Errors
**Objective**: Test error handling
**Steps**:
1. Disable network connection
2. Attempt API operations
3. Verify error messages display
4. Verify retry options
5. Reconnect and retry operations

### 5. Responsive Design

#### TC-FE-RES-001: Desktop View
**Objective**: Verify desktop layout
**Steps**:
1. Open app at 1920x1080 resolution
2. Verify all elements display properly
3. Verify sidebar navigation
4. Verify content area usage
5. Verify modals and overlays

#### TC-FE-RES-002: Tablet View
**Objective**: Verify tablet layout
**Steps**:
1. Open app at 768x1024 resolution
2. Verify layout adapts correctly
3. Verify navigation changes
4. Verify touch interactions work
5. Verify readability

#### TC-FE-RES-003: Mobile View
**Objective**: Verify mobile layout
**Steps**:
1. Open app at 375x667 resolution
2. Verify mobile menu
3. Verify stacked layouts
4. Verify swipe gestures
5. Verify readable text sizes

## Full Workflow Testing

### 1. Complete Scheduling Workflow

#### TC-WF-001: New Institution Setup
**Objective**: Test full system initial setup
**Steps**:
1. Register new admin account
2. Configure institution settings
3. Import initial resources:
   - Buildings
   - Rooms
   - Equipment
4. Create academic calendar
5. Set up departments
6. Verify all data imported correctly

#### TC-WF-002: Semester Scheduling
**Objective**: Test complete semester scheduling
**Steps**:
1. Create new semester schedule
2. Import course catalog
3. Assign course requirements
4. Add faculty availability
5. Define constraints:
   - Room capacities
   - Teaching loads
   - Blackout dates
6. Run optimization
7. Review generated schedule
8. Make manual adjustments
9. Finalize schedule
10. Publish schedule

#### TC-WF-003: Schedule Modification
**Objective**: Test in-semester changes
**Steps**:
1. Load active schedule
2. Handle room change request
3. Accommodate new course section
4. Resolve teacher unavailability
5. Add special event
6. Update affected assignments
7. Notify stakeholders
8. Verify no conflicts created

### 2. Multi-user Collaboration

#### TC-WF-MU-001: Concurrent Editing
**Objective**: Test simultaneous schedule modifications
**Steps**:
1. User A opens schedule for editing
2. User B opens same schedule
3. User A makes changes
4. User B attempts conflicting changes
5. Verify conflict resolution
6. Verify proper notification
7. Verify final state consistency

#### TC-WF-MU-002: Permission Management
**Objective**: Test role-based access
**Steps**:
1. Create users with different roles:
   - Administrator
   - Scheduler
   - Department Head
   - Teacher
   - Student
2. Test each role's permissions
3. Verify restricted access
4. Verify audit trail

### 3. Integration Workflows

#### TC-WF-INT-001: SIS Integration
**Objective**: Test Student Information System sync
**Steps**:
1. Configure SIS connection
2. Test authentication
3. Sync student enrollment data
4. Sync course offerings
5. Sync faculty assignments
6. Verify data consistency
7. Handle sync errors

#### TC-WF-INT-002: Calendar Export
**Objective**: Test external calendar integration
**Steps**:
1. Generate schedule
2. Export to iCal format
3. Import into Google Calendar
4. Verify all events appear
5. Verify recurring events
6. Verify updates propagate

## Edge Cases and Error Handling

### 1. Network Failures

#### TC-EC-NET-001: Intermittent Connection
**Objective**: Test unstable network conditions
**Steps**:
1. Start API operation
2. Simulate network drop
3. Verify error handling
4. Resume connection
5. Verify operation recovery
6. Verify data integrity

#### TC-EC-NET-002: Timeout Scenarios
**Objective**: Test timeout handling
**Steps**:
1. Trigger long-running optimization
2. Verify timeout occurs
3. Verify partial results saved
4. Verify user notified
5. Verify can resume operation

### 2. Data Edge Cases

#### TC-EC-DATA-001: Large Data Sets
**Objective**: Test performance with large schedules
**Steps**:
1. Create schedule with 1000+ assignments
2. Test list pagination
3. Test filtering performance
4. Test export functionality
5. Verify memory usage

#### TC-EC-DATA-002: Invalid Data States
**Objective**: Test corrupted data handling
**Steps**:
1. Create schedule with invalid dates
2. Add impossible constraints
3. Create circular dependencies
4. Verify validation catches issues
5. Verify recovery options

#### TC-EC-DATA-003: Resource Exhaustion
**Objective**: Test system limits
**Steps**:
1. Max out room capacity
2. Exceed teacher load limits
3. Fill all time slots
4. Verify graceful handling
5. Verify clear error messages

### 3. Concurrent Operations

#### TC-EC-CON-001: Simultaneous Optimizations
**Objective**: Test concurrent solver runs
**Steps**:
1. Start optimization job A
2. Start optimization job B
3. Verify queue management
4. Verify resource allocation
5. Verify results isolation

#### TC-EC-CON-002: Database Locks
**Objective**: Test concurrent database access
**Steps**:
1. Multiple users update same schedule
2. Verify transaction isolation
3. Verify deadlock handling
4. Verify data consistency

### 4. Browser Limitations

#### TC-EC-BR-001: Memory Constraints
**Objective**: Test with limited browser memory
**Steps**:
1. Simulate low memory environment
2. Load large schedules
3. Verify garbage collection
4. Verify performance degradation

#### TC-EC-BR-002: Browser Compatibility
**Objective**: Test across browsers
**Steps**:
1. Test on Chrome
2. Test on Firefox
3. Test on Safari
4. Test on Edge
5. Verify consistent behavior

## Performance Testing

### 1. API Performance

#### TC-PERF-API-001: Response Times
**Objective**: Measure API response times
**Steps**:
1. Test all endpoints with varying loads
2. Measure response times:
   - Empty database: < 100ms
   - Normal load: < 500ms
   - Heavy load: < 2000ms
3. Verify SLA compliance

#### TC-PERF-API-002: Throughput
**Objective**: Measure concurrent request handling
**Steps**:
1. Generate concurrent requests
2. Measure requests per second
3. Target: 100+ RPS for read operations
4. Target: 50+ RPS for write operations

#### TC-PERF-API-003: Load Testing
**Objective**: Test under sustained load
**Steps**:
1. Simulate 100 concurrent users
2. Run for 1 hour
3. Monitor memory usage
4. Monitor database connections
5. Verify no degradation

### 2. Frontend Performance

#### TC-PERF-FE-001: Page Load Times
**Objective**: Optimize page rendering
**Steps**:
1. Measure initial load time
2. Target: < 3 seconds first load
3. Target: < 1 second subsequent loads
4. Optimize bundle sizes

#### TC-PERF-FE-002: Rendering Performance
**Objective**: Test with large datasets
**Steps**:
1. Render 1000+ assignments
2. Test scrolling performance
3. Test filter performance
4. Verify 60 FPS animations

### 3. Database Performance

#### TC-PERF-DB-001: Query Optimization
**Objective**: Optimize database queries
**Steps**:
1. Analyze slow queries
2. Add necessary indexes
3. Verify query plans
4. Monitor query times

#### TC-PERF-DB-002: Connection Pooling
**Objective**: Test connection management
**Steps**:
1. Simulate high concurrent usage
2. Monitor connection pool
3. Verify no connection leaks
4. Tune pool settings

## Security Testing

### 1. Authentication

#### TC-SEC-AUTH-001: Login Security
**Objective**: Test authentication mechanisms
**Steps**:
1. Test valid credentials
2. Test invalid credentials
3. Test account lockout after failures
4. Test password requirements
5. Test session management

#### TC-SEC-AUTH-002: Token Security
**Objective**: Test JWT implementation
**Steps**:
1. Verify token structure
2. Test token expiration
3. Test token refresh
4. Test token revocation
5. Test token theft scenarios

### 2. Authorization

#### TC-SEC-AUTHZ-001: Role-Based Access
**Objective**: Test permission system
**Steps**:
1. Test each role's permissions
2. Test permission inheritance
3. Test permission escalation attempts
4. Verify audit logging

#### TC-SEC-AUTHZ-002: Resource Access
**Objective**: Test data access controls
**Steps**:
1. User A tries to access User B's schedule
2. Test cross-tenant data access
3. Verify data isolation
4. Test API key permissions

### 3. Input Validation

#### TC-SEC-VAL-001: Injection Prevention
**Objective**: Test for injection vulnerabilities
**Steps**:
1. Test SQL injection in inputs
2. Test XSS in text fields
3. Test command injection
4. Verify input sanitization

#### TC-SEC-VAL-002: Data Validation
**Objective**: Test data integrity checks
**Steps**:
1. Test file upload restrictions
2. Test data type validation
3. Test size limits
4. Test malformed requests

### 4. API Security

#### TC-SEC-API-001: Rate Limiting
**Objective**: Test rate limiting implementation
**Steps**:
1. Exceed rate limits
2. Verify throttling
3. Verify rate limit headers
4. Test rate limit bypass attempts

#### TC-SEC-API-002: CORS Configuration
**Objective**: Test cross-origin policies
**Steps**:
1. Test allowed origins
2. Test forbidden origins
3. Test credential handling
4. Test preflight requests

## Test Data Management

### 1. Test Data Generation

#### TC-DATA-GEN-001: Sample Data
**Objective**: Generate realistic test data
**Steps**:
1. Create test data generators
2. Generate:
   - 10 buildings
   - 100 rooms
   - 50 teachers
   - 200 courses
   - 1000 students
3. Verify data relationships

#### TC-DATA-GEN-002: Edge Cases
**Objective**: Generate special test cases
**Steps**:
1. Create conflicting schedules
2. Create maximum capacity scenarios
3. Create complex constraint networks
4. Create invalid data states

### 2. Test Environment Reset

#### TC-DATA-RESET-001: Database Cleanup
**Objective**: Ensure clean test runs
**Steps**:
1. Truncate all test tables
2. Reset sequences
3. Clear caches
4. Verify clean state

#### TC-DATA-RESET-002: Isolation
**Objective**: Prevent test interference
**Steps**:
1. Use separate test database
2. Use unique identifiers
3. Parallel test execution
4. Verify data isolation

## Test Execution Plan

### 1. Daily Smoke Tests
- Health checks
- Basic CRUD operations
- Critical path workflows

### 2. Weekly Regression Tests
- Full API test suite
- Full frontend test suite
- Performance benchmarks

### 3. Release Testing
- End-to-end workflow tests
- Security scans
- Performance testing
- Browser compatibility

### 4. Continuous Integration
- Unit tests on every commit
- Integration tests on PR
- E2E tests on merge

## Test Automation Implementation

### 1. API Test Framework
```python
# tests/e2e/api_test_framework.py
import pytest
import httpx
from typing import Dict, Any

class APITestFramework:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url)
        self.auth_token = None

    def login(self, username: str, password: str):
        response = self.client.post("/auth/login", json={
            "username": username,
            "password": password
        })
        self.auth_token = response.json()["token"]
        self.client.headers["Authorization"] = f"Bearer {self.auth_token}"
        return response

    def create_schedule(self, data: Dict[str, Any]):
        return self.client.post("/api/v1/schedules", json=data)

    # ... other API methods
```

### 2. Frontend Test Framework
```typescript
// tests/e2e/frontend.spec.ts
import { test, expect } from '@playwright/test';

test.describe('EduSched E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
  });

  test('complete scheduling workflow', async ({ page }) => {
    // Create new schedule
    await page.click('[data-testid="new-schedule-btn"]');
    await page.fill('[data-testid="schedule-name"]', 'Test Schedule');
    // ... complete workflow
  });
});
```

### 3. Test Data Factory
```python
# tests/factories/schedule_factory.py
import factory
from datetime import datetime, timedelta

class ScheduleFactory(factory.Factory):
    class Meta:
        model = dict

    name = factory.Sequence(lambda n: f"Schedule {n}")
    solver = "heuristic"
    optimize = True
    seed = factory.Faker('random_int')
```

## Test Reporting

### 1. Metrics to Track
- Test pass rate
- Test execution time
- Defect density
- Code coverage
- Performance benchmarks
- Security scan results

### 2. Notification System
- Test failure alerts
- Performance degradation alerts
- Security vulnerability alerts
- Daily test summary reports

### 3. Test Documentation
- Automated test report generation
- Test case documentation
- Bug tracking integration
- Release notes generation

## Conclusion

This comprehensive end-to-end test plan covers all aspects of the EduSched application, ensuring:
- Reliability through thorough testing
- Performance through benchmarking
- Security through vulnerability testing
- Usability through workflow testing
- Maintainability through test automation

The test plan should be regularly updated as new features are added and existing functionality evolves.