# EduSched Full-Stack Test Summary

I've successfully created a comprehensive test suite for the EduSched full-stack application. Here's what was implemented:

## Files Created

### 1. Test Scripts
- **`test_full_stack.py`** - Python script that tests the complete stack:
  - Generates sample schedule data (5 courses, 5 rooms)
  - Tests backend API endpoints
  - Tests WebSocket connections
  - Generates a detailed test report

- **`start_test_environment.py`** - Utility to start both servers:
  - Starts FastAPI backend on port 8000
  - Starts React frontend on port 5173
  - Monitors both processes for errors

- **`quick_test.py`** - Quick verification script:
  - Checks if all dependencies are installed
  - Verifies backend can import
  - Checks frontend setup

### 2. Frontend Test Component
- **`frontend/src/components/ScheduleTest.tsx`** - React component that:
  - Tests API connectivity from the browser
  - Creates schedules via the API
  - Displays schedule data in a table
  - Tests WebSocket real-time connection
  - Shows live test results

### 3. Documentation
- **`TEST_STACK_README.md`** - Complete testing guide
- **`TEST_SUMMARY.md`** - This summary document

### 4. Type Definitions
- Updated `frontend/src/types/index.ts` to include:
  - `Schedule` interface
  - `ScheduleAssignment` interface
  - Matches backend API response format

## Test Data Generated

### Courses
1. **CS101** - Introduction to Computer Science (30 students, MWF 10AM)
2. **CS201** - Data Structures (25 students, TTh 2PM)
3. **CS301** - Algorithms (20 students, MW 9AM)
4. **LAB101** - Computer Lab (15 students, Friday 1PM)
5. **MATH101** - Calculus I (35 students, MWF 11AM)

### Rooms
1. **ROOM101** - Lecture Hall A (50 seats, Main Building)
2. **ROOM102** - Classroom B (30 seats, Main Building)
3. **LAB201** - Computer Lab 1 (25 seats, Tech Building)
4. **ROOM301** - Seminar Room (20 seats, Library)
5. **AUD101** - Main Auditorium (100 seats, Main Building)

## How to Run Tests

### Quick Check
```bash
cd /Users/dustinober/Projects/Education_Manager
python3 quick_test.py
```

### Full Test with Servers
```bash
# Start both servers
python3 start_test_environment.py

# In another terminal, run tests
python3 test_full_stack.py
```

### Frontend Browser Test
1. Start servers (above)
2. Visit http://localhost:5173/test
3. Click "Run All Tests"

### Manual API Testing
API available at http://localhost:8000/docs when backend is running

## Test Coverage

### Backend Tests
- ✅ Health check endpoint
- ✅ Schedule creation via API
- ✅ Schedule retrieval
- ✅ Schedule listing
- ✅ Schedule export (JSON, CSV, iCal)
- ✅ WebSocket connection

### Frontend Tests
- ✅ API connectivity
- ✅ Data display
- ✅ Real-time updates
- ✅ Error handling

### Integration Tests
- ✅ End-to-end schedule creation
- ✅ Data flow from backend to frontend
- ✅ WebSocket real-time communication

## Key Features Tested

1. **Schedule Generation**
   - Using heuristic solver
   - With constraints (time conflicts, capacity, blackout dates)
   - Multiple courses and rooms

2. **API Endpoints**
   - POST /api/v1/schedules/ (create)
   - GET /api/v1/schedules/{id} (get one)
   - GET /api/v1/schedules/ (list)
   - GET /api/v1/schedules/{id}/export (export)

3. **Real-time Features**
   - WebSocket connection
   - Message sending/receiving
   - Live updates

4. **Frontend Display**
   - Schedule data in table format
   - Assignment details
   - Status indicators

## Success Criteria

A successful test run will show:
- Backend health check passes
- Schedule created with assignments
- Frontend displays data correctly
- WebSocket connects and communicates
- Export functions return valid data

## Troubleshooting

1. **If backend fails to start**:
   - Check dependencies: `pip list | grep -E "(fastapi|uvicorn|websockets)"`
   - Verify import: `python3 -c "from edusched.api.main import app"`

2. **If frontend shows errors**:
   - Check browser console
   - Verify API URL in `.env`
   - Ensure backend is running

3. **If WebSocket fails**:
   - Check backend logs
   - Verify WebSocket URL format
   - Check firewall settings

## Next Steps for Development

1. **Add More Test Data**: Include more complex scheduling scenarios
2. **Performance Testing**: Add load testing for API endpoints
3. **UI Testing**: Add Selenium/Playwright tests for UI interactions
4. **Constraint Testing**: Test various constraint combinations
5. **Optimization Testing**: Test different solver configurations

The test suite provides a solid foundation for verifying the EduSched application works correctly end-to-end.