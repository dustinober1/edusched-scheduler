# EduSched End-to-End Test Suite

This directory contains the comprehensive end-to-end test suite for the EduSched application.

## Test Organization

### API Tests (`api/`)
Tests for backend API endpoints:
- `test_schedules.py` - Schedule CRUD operations
- `test_resources.py` - Resource management
- `test_constraints.py` - Constraint validation
- Additional API modules to be added

### Frontend Tests (`frontend/`)
Tests for frontend functionality using Playwright:
- `booking.spec.ts` - Main booking workflow tests
- `playwright.config.ts` - Playwright configuration

### Workflow Tests (`workflows/`)
Complete end-to-end workflow tests:
- `test_complete_workflow.py` - Full scheduling workflow
- `test_multi_user.py` - Multi-user collaboration

### Specialized Tests
- `test_edge_cases.py` - Edge cases and error handling
- `test_performance.py` - Performance and load testing
- `test_security.py` - Security testing (TODO)

## Running Tests

### Prerequisites

1. Install dependencies:
```bash
# Python dependencies
pip install -e .[all,dev]
pip install pytest pytest-asyncio pytest-playwright httpx websockets

# Node.js dependencies (for frontend tests)
cd frontend
npm install
npx playwright install
```

2. Start test services:
```bash
# Start backend API server
python -m edusched.api.main

# Start frontend dev server (in separate terminal)
cd frontend
npm run dev

# Start database (if not already running)
docker-compose up -d postgres redis
```

### Running Tests

#### All E2E Tests
```bash
cd tests/e2e
pytest -v
```

#### API Tests Only
```bash
pytest -v -m api
```

#### Frontend Tests Only
```bash
npx playwright test
```

#### Performance Tests
```bash
pytest -v -m performance
```

#### Specific Test File
```bash
pytest -v test_schedules.py
```

#### With Coverage
```bash
pytest --cov=../src --cov-report=html
```

### Running Tests in Parallel

#### API Tests (pytest-xdist)
```bash
pip install pytest-xdist
pytest -n auto -v
```

#### Frontend Tests (Playwright)
```bash
npx playwright test --shard=1/2  # First shard
npx playwright test --shard=2/2  # Second shard
```

## Test Configuration

### Environment Variables
```bash
# API server URL
export TEST_API_URL=http://localhost:8000

# Frontend URL
export TEST_FRONTEND_URL=http://localhost:3000

# Test database
export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/edusched_test

# Redis for tests
export TEST_REDIS_URL=redis://localhost:6379/1
```

### Test Markers
Use pytest markers to run specific test categories:

- `-m api` - API endpoint tests
- `-m frontend` - Frontend UI tests
- `-m slow` - Tests that take > 10 seconds
- `-m integration` - Integration tests
- `-m performance` - Performance tests
- `-m smoke` - Quick smoke tests

### Test Data

Test data is managed through fixtures and factories:
- `conftest.py` - Common test fixtures
- `factories/` - Test data factories (TODO)
- `test_data/` - Static test data files (TODO)

## Test Reports

### HTML Reports
```bash
# API tests
pytest --html=report.html --self-contained-html

# Frontend tests
npx playwright test --reporter=html
```

### Coverage Reports
```bash
pytest --cov=../src --cov-report=html
open htmlcov/index.html
```

### Performance Reports
Performance tests generate reports in:
- `performance-reports/` - JSON and HTML reports

## CI/CD Integration

### GitHub Actions
The tests are configured to run in CI/CD:
- On every push: API unit and integration tests
- On PR: Full test suite
- Nightly: Performance and load tests

### Test Results
- Test results are stored as artifacts
- Coverage reports uploaded to codecov
- Performance trends tracked

## Debugging Tests

### API Tests
```bash
# Run with verbose output
pytest -v -s test_schedules.py::TestScheduleAPI::test_create_schedule

# Stop on first failure
pytest -x

# Run with debugger
pytest --pdb
```

### Frontend Tests
```bash
# Run in headed mode (show browser)
npx playwright test --headed

# Run with trace
npx playwright test --trace on

# Debug mode
npx playwright test --debug
```

## Best Practices

### Writing New Tests

1. **Follow Naming Conventions**:
   - Test files: `test_*.py` or `*_test.py`
   - Test classes: `Test*`
   - Test methods: `test_*`

2. **Use Descriptive Names**:
   ```python
   def test_create_schedule_with_invalid_data_returns_400(self):
       pass
   ```

3. **Include Test IDs**:
   ```python
   def test_TC_API_SCH_001_create_schedule(self):
       """TC-API-SCH-001: Test creating a new schedule."""
       pass
   ```

4. **Use Fixtures for Setup**:
   ```python
   @pytest.fixture
   async def sample_schedule_data():
       return {"name": "Test Schedule", ...}
   ```

5. **Clean Up Resources**:
   ```python
   @pytest.fixture
   async def cleanup_db():
       yield
       # Clean up code here
   ```

### API Testing Guidelines

1. Test all HTTP methods
2. Verify status codes and response bodies
3. Test error conditions
4. Use proper authentication
5. Test authorization and permissions

### Frontend Testing Guidelines

1. Use data-testid attributes for selectors
2. Test user workflows, not just components
3. Include accessibility tests
4. Test responsive design
5. Verify error handling

## Troubleshooting

### Common Issues

1. **Port Conflicts**:
   - Ensure ports 3000, 8000, 5432, 6379 are available
   - Use `lsof -i :<port>` to check

2. **Database Connection**:
   - Verify PostgreSQL is running
   - Check connection string
   - Ensure test database exists

3. **Authentication Failures**:
   - Verify test users exist
   - Check auth token handling
   - Ensure CORS is configured

4. **Timeout Errors**:
   - Increase timeout values for slow tests
   - Check for hanging operations
   - Verify service health

5. **Browser Issues (Playwright)**:
   - Reinstall browsers: `npx playwright install`
   - Update browser dependencies
   - Check system requirements

## Contributing

When adding new tests:

1. Follow existing patterns
2. Update documentation
3. Add to test plan if needed
4. Verify all tests pass
5. Update fixtures if required

## More Information

- [Main Test Plan](../e2e-test-plan.md) - Detailed test documentation
- [API Documentation](../../docs/api.md) - API reference
- [Developer Guide](../../docs/developer-guide.md) - Development setup