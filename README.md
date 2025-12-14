# EduSched

[![PyPI version](https://badge.fury.io/py/edusched.svg)](https://badge.fury.io/py/edusched)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**EduSched** is a powerful constraint-based scheduling library for educational institutions. It provides a flexible framework for creating optimal class schedules while respecting complex constraints like room availability, instructor preferences, student conflicts, and more.

## Features

- 🎯 **Constraint-Based Scheduling** - Define hard and soft constraints for your scheduling needs
- 🏫 **Educational Focus** - Built specifically for schools, universities, and training centers
- 🔧 **Flexible Solvers** - Choose between fast heuristic solving or optimal OR-Tools optimization
- 📊 **Rich Domain Model** - Comprehensive support for rooms, instructors, students, courses, and more
- 🔄 **Incremental Updates** - Add, remove, or modify courses without full re-scheduling
- 📅 **Calendar Integration** - Export schedules to iCal format
- 🌐 **API Ready** - Optional FastAPI backend for web integration

## Installation

### Basic Installation

```bash
pip install edusched
```

### With Optional Dependencies

```bash
# With OR-Tools for optimal solving
pip install edusched[ortools]

# With pandas for data analysis
pip install edusched[pandas]

# With Excel export support
pip install edusched[excel]

# With FastAPI backend
pip install edusched[api]

# All optional dependencies
pip install edusched[all]
```

## Quick Start

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from edusched import solve
from edusched.domain import Problem, SessionRequest, Resource, Calendar

# Create a calendar
calendar = Calendar(
    id="fall-2024",
    timezone=ZoneInfo("America/New_York")
)

# Define resources (rooms)
room_101 = Resource(id="room-101", resource_type="room", capacity=30)
room_102 = Resource(id="room-102", resource_type="room", capacity=50)

# Create course requests
cs101 = SessionRequest(
    id="CS101",
    duration=timedelta(hours=1, minutes=30),
    number_of_occurrences=28,  # 2x/week for 14 weeks
    earliest_date=datetime(2024, 9, 1, tzinfo=ZoneInfo("America/New_York")),
    latest_date=datetime(2024, 12, 15, tzinfo=ZoneInfo("America/New_York")),
    enrollment_count=25
)

# Build the problem
problem = Problem(
    requests=[cs101],
    resources=[room_101, room_102],
    calendars=[calendar],
    constraints=[]  # Add your constraints here
)

# Solve
result = solve(problem)

# Access the schedule
for assignment in result.assignments:
    print(f"{assignment.request_id}: {assignment.start_time} in {assignment.assigned_resources}")
```

## Constraints

EduSched supports a variety of constraints:

### Hard Constraints
- **NoOverlap** - Prevent double-booking of resources
- **BlackoutDates** - Block specific dates/times
- **MaxPerDay** - Limit sessions per day for a resource
- **AttributeMatch** - Ensure resources meet requirements
- **WithinDateRange** - Keep assignments within valid dates

### Soft Constraints / Objectives
- **SpreadEvenlyAcrossTerm** - Distribute sessions evenly
- **MinimizeEveningSessions** - Prefer daytime scheduling
- **BalanceInstructorLoad** - Equalize instructor workloads

## Solvers

### Heuristic Solver (Default)
Fast greedy algorithm suitable for most use cases:
```python
result = solve(problem, backend="heuristic")
```

### OR-Tools Solver
Optimal constraint programming solver (requires `ortools`):
```python
result = solve(problem, backend="ortools")
```

### Auto Selection
Automatically selects the best available solver:
```python
result = solve(problem, backend="auto")
```

## Documentation

- [User Guide](https://github.com/dustinober1/edusched-scheduler/blob/main/USER_GUIDE.md)
- [API Reference](https://github.com/dustinober1/edusched-scheduler/blob/main/docs/)
- [Examples](https://github.com/dustinober1/edusched-scheduler/tree/main/examples)

## Requirements

- Python 3.9 or higher
- `python-dateutil` >= 2.8.0
- `typing-extensions` >= 4.0.0

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with ❤️ for educational institutions
- Inspired by real-world scheduling challenges in academia
