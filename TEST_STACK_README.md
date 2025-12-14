# EduSched Full-Stack Testing Guide

This guide explains how to test the complete EduSched stack, including the backend API and frontend integration.

## Prerequisites

1. Python 3.8+ installed
2. Node.js 16+ and npm installed
3. All Python dependencies installed:
   ```bash
   cd /Users/dustinober/Projects/Education_Manager
   pip install -e .[dev]
   ```

## Quick Start

### Option 1: Using the Test Environment Script

The easiest way to start both backend and frontend for testing:

```bash
# Start both servers
python start_test_environment.py
```

This will start:
- Backend API server on http://localhost:8000
- Frontend dev server on http://localhost:5173
- Monitor output from both servers

### Option 2: Manual Startup

Start backend (in terminal 1):
```bash
cd /Users/dustinober/Projects/Education_Manager
uvicorn edusched.api.main:app --reload --host 0.0.0.0 --port 8000
```

Start frontend (in terminal 2):
```bash
cd /Users/dustinober/Projects/Education_Manager/frontend
npm run dev
```

## Running the Tests

### 1. Backend-Only Tests

Test the backend API directly:

```bash
# Run the Python test script
python test_full_stack.py
```

This will:
- Generate sample schedule data (5 courses, 5 rooms, constraints)
- Test API connectivity
- Create a schedule via the API
- Test schedule retrieval
- Test WebSocket connection
- Generate a test report

### 2. Frontend Integration Tests

Once both servers are running:

1. Open your browser to http://localhost:5173
2. Navigate to http://localhost:5173/test
3. Click "Run All Tests" to test:
   - API connectivity
   - Schedule creation
   - Data retrieval and display
   - WebSocket connection

### 3. Manual API Testing

You can also test the API directly using curl or any API client:

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Create a Schedule
```bash
curl -X POST http://localhost:8000/api/v1/schedules/ \
  -H "Content-Type: application/json" \
  -d '{
    "solver": "heuristic",
    "seed": 42,
    "optimize": true
  }'
```

#### Get Schedule
```bash
# Replace SCHEDULE_ID with the ID from the create response
curl http://localhost:8000/api/v1/schedules/SCHEDULE_ID
```

#### List Schedules
```bash
curl http://localhost:8000/api/v1/schedules/
```

## Test Data

The test generates the following sample data:

### Courses
1. **CS101** - Introduction to Computer Science
   - 30 students, MWF 10:00 AM, 90 minutes
   - Requires computer classroom

2. **CS201** - Data Structures
   - 25 students, TTh 2:00 PM, 90 minutes
   - Requires computer classroom

3. **CS301** - Algorithms
   - 20 students, MW 9:00 AM, 90 minutes
   - Requires computer classroom

4. **LAB101** - Computer Lab
   - 15 students, Friday 1:00 PM, 120 minutes
   - Requires lab room

5. **MATH101** - Calculus I
   - 35 students, MWF 11:00 AM, 90 minutes
   - Regular classroom

### Rooms
1. **ROOM101** - Lecture Hall A (Main Building, 50 seats)
2. **ROOM102** - Classroom B (Main Building, 30 seats)
3. **LAB201** - Computer Lab 1 (Tech Building, 25 seats)
4. **ROOM301** - Seminar Room (Library, 20 seats)
5. **AUD101** - Main Auditorium (Main Building, 100 seats)

## Expected Behavior

### Successful Test Results
- Backend health check returns status: "healthy"
- Schedule creation succeeds with assignments
- Frontend displays schedule data correctly
- WebSocket connection established
- Export functions work (JSON, CSV, iCal)

### Common Issues

1. **Backend not running**
   - Ensure FastAPI and uvicorn are installed
   - Check if port 8000 is available

2. **Frontend not connecting to API**
   - Verify backend is running on http://localhost:8000
   - Check CORS settings in backend
   - Verify frontend .env configuration

3. **WebSocket connection fails**
   - Ensure backend is running with WebSocket support
   - Check firewall settings

4. **Schedule creation fails**
   - Check backend logs for errors
   - Verify all constraints are properly configured

## Troubleshooting

### Backend Issues
- Check backend output for error messages
- Verify all dependencies are installed
- Check database connection if applicable

### Frontend Issues
- Clear browser cache
- Check browser console for errors
- Verify API URL in .env file

### General Issues
- Ensure both backend and frontend are running
- Check network connectivity
- Verify ports are not blocked

## Next Steps

Once the full-stack test passes:

1. **Explore the UI**: Navigate to http://localhost:5173 and explore the full interface
2. **Test Optimization**: Use the optimization page to test different solvers
3. **Export Schedules**: Test different export formats
4. **Add Real Data**: Import your own schedule data using the API

## API Documentation

When the backend is running, you can access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

These provide interactive API documentation for testing all endpoints.