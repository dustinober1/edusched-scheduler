Examples
========

This section contains practical examples of how to use EduSched for different scheduling scenarios.

University Course Scheduling
----------------------------

Here's a comprehensive example of scheduling university courses:

.. code-block:: python

   from datetime import datetime, timedelta
   from zoneinfo import ZoneInfo

   from edusched import solve
   from edusched.domain import Problem, SessionRequest, Resource, Calendar
   from edusched.constraints import NoOverlap, MaxPerDay, BlackoutDates
   from edusched.objectives import BalanceInstructorLoad, SpreadEvenlyAcrossTerm

   # Create academic calendar
   academic_calendar = Calendar(
       id="fall-2024",
       timezone=ZoneInfo("America/New_York")
   )

   # Define classroom resources
   classrooms = [
       Resource(id="CS-101", resource_type="classroom", capacity=30),
       Resource(id="CS-201", resource_type="classroom", capacity=40),
       Resource(id="CS-LAB", resource_type="lab", capacity=20, attributes={"computer_lab": True}),
   ]

   # Define course requests
   courses = [
       SessionRequest(
           id="CS101-Intro",
           duration=timedelta(hours=1, minutes=30),
           number_of_occurrences=28,
           earliest_date=datetime(2024, 9, 1, tzinfo=ZoneInfo("America/New_York")),
           latest_date=datetime(2024, 12, 15, tzinfo=ZoneInfo("America/New_York")),
           enrollment_count=25
       ),
       SessionRequest(
           id="CS201-Advanced",
           duration=timedelta(hours=1, minutes=30),
           number_of_occurrences=26,
           earliest_date=datetime(2024, 9, 1, tzinfo=ZoneInfo("America/New_York")),
           latest_date=datetime(2024, 12, 15, tzinfo=ZoneInfo("America/New_York")),
           enrollment_count=18,
           required_attributes={"computer_lab": True}
       )
   ]

   # Define constraints
   constraints = [
       # Prevent double-booking of classrooms
       NoOverlap(resource_id="CS-101"),
       NoOverlap(resource_id="CS-201"),
       NoOverlap(resource_id="CS-LAB"),
       # Limit lab usage to 2 sessions per day
       MaxPerDay(resource_id="CS-LAB", max_per_day=2)
   ]

   # Define objectives
   objectives = [
       SpreadEvenlyAcrossTerm(request_id="CS101-Intro", weight=1.0),
       BalanceInstructorLoad(weight=0.5)
   ]

   # Create the problem
   problem = Problem(
       requests=courses,
       resources=classrooms,
       calendars=[academic_calendar],
       constraints=constraints,
       objectives=objectives
   )

   # Solve the problem
   result = solve(problem)

   # Print results
   for assignment in result.assignments:
       print(f"{assignment.request_id}: {assignment.start_time.strftime('%Y-%m-%d %H:%M')} - {assignment.end_time.strftime('%H:%M')} in {assignment.assigned_resources}")

Meeting Room Scheduling
-----------------------

For scheduling meeting rooms in a corporate environment:

.. code-block:: python

   from datetime import datetime, timedelta
   from zoneinfo import ZoneInfo

   from edusched import solve
   from edusched.domain import Problem, SessionRequest, Resource, Calendar
   from edusched.constraints import NoOverlap, AttributeMatch

   # Create a weekly calendar
   weekly_calendar = Calendar(
       id="weekly",
       timezone=ZoneInfo("America/New_York")
   )

   # Define meeting rooms with different capacities and features
   meeting_rooms = [
       Resource(id="small-meeting", resource_type="meeting_room", capacity=6, attributes={"projector": False}),
       Resource(id="large-meeting", resource_type="meeting_room", capacity=15, attributes={"projector": True, "video_conf": True}),
       Resource(id="conference", resource_type="conference_room", capacity=30, attributes={"projector": True, "video_conf": True, "whiteboard": True}),
   ]

   # Define meeting requests
   meetings = [
       SessionRequest(
           id="team-sync",
           duration=timedelta(hours=1),
           number_of_occurrences=5,  # Weekly for a month
           earliest_date=datetime(2024, 10, 1, tzinfo=ZoneInfo("America/New_York")),
           latest_date=datetime(2024, 10, 31, tzinfo=ZoneInfo("America/New_York")),
           enrollment_count=8,
           required_attributes={"projector": True}  # Needs projector
       ),
       SessionRequest(
           id="exec-meeting",
           duration=timedelta(hours=2),
           number_of_occurrences=4,  # Monthly
           earliest_date=datetime(2024, 10, 1, tzinfo=ZoneInfo("America/New_York")),
           latest_date=datetime(2024, 12, 31, tzinfo=ZoneInfo("America/New_York")),
           enrollment_count=12,
           required_attributes={"video_conf": True, "whiteboard": True}
       )
   ]

   # Create the problem with appropriate constraints
   problem = Problem(
       requests=meetings,
       resources=meeting_rooms,
       calendars=[weekly_calendar],
       constraints=[
           NoOverlap(resource_id="small-meeting"),
           NoOverlap(resource_id="large-meeting"),
           NoOverlap(resource_id="conference"),
           AttributeMatch(request_id="team-sync"),  # Ensure projector requirement is met
           AttributeMatch(request_id="exec-meeting"),  # Ensure all requirements are met
       ]
   )

   # Solve
   result = solve(problem)

   # Process results
   for assignment in result.assignments:
       print(f"{assignment.request_id}: {assignment.start_time} in {list(assignment.assigned_resources.values())[0][0]}")