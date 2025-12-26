Quick Start
===========

This guide will help you get started with EduSched by showing you how to create and solve a simple scheduling problem.

Basic Example
-------------

Here's a simple example that demonstrates how to create a scheduling problem and solve it:

.. code-block:: python

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

Understanding the Components
----------------------------

* **Problem**: Represents a complete scheduling scenario with requests, resources, calendars, and constraints
* **SessionRequest**: Represents a request for scheduling (like a class or meeting)
* **Resource**: Represents a resource that can be scheduled (like a room or equipment)
* **Calendar**: Defines available time slots and time zones
* **Assignment**: Represents a scheduled session with specific time and resources
* **Constraint**: Defines rules that must be followed in the schedule