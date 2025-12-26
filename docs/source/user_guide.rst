User Guide
==========

This guide provides detailed information on how to use EduSched for various scheduling scenarios.

Advanced Scheduling
-------------------

Defining Constraints
~~~~~~~~~~~~~~~~~~~~

EduSched supports various types of constraints:

Hard Constraints
^^^^^^^^^^^^^^^^
* **NoOverlap**: Prevents double-booking of resources
* **BlackoutDates**: Respects calendar blackout periods
* **MaxPerDay**: Limits daily resource usage
* **MinGapBetweenOccurrences**: Enforces spacing between session occurrences
* **WithinDateRange**: Enforces session date boundaries
* **AttributeMatch**: Ensures resource attributes satisfy requirements

.. code-block:: python

   from edusched.constraints import NoOverlap, BlackoutDates, MaxPerDay

   # Example constraints
   no_overlap_constraint = NoOverlap(resource_id="room-101")
   blackout_constraint = BlackoutDates(calendar_id="fall-2024")
   max_per_day_constraint = MaxPerDay(resource_id="room-101", max_per_day=3)

Soft Constraints (Objectives)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* **SpreadEvenlyAcrossTerm**: Distribute sessions evenly
* **MinimizeEveningSessions**: Prefer daytime scheduling
* **BalanceInstructorLoad**: Equalize instructor workloads

.. code-block:: python

   from edusched.objectives import SpreadEvenlyAcrossTerm, MinimizeEveningSessions

   # Example objectives
   spread_objective = SpreadEvenlyAcrossTerm(request_id="CS101", weight=1.0)
   evening_objective = MinimizeEveningSessions(weight=0.5)

Scheduling Patterns
~~~~~~~~~~~~~~~~~~~

You can define complex scheduling patterns by combining requests, resources, and constraints:

.. code-block:: python

   from edusched.domain import SessionRequest, Resource
   from edusched.constraints import NoOverlap, WithinDateRange

   # Define a course that needs to happen twice a week
   advanced_cs = SessionRequest(
       id="CS201",
       duration=timedelta(hours=1, minutes=30),
       number_of_occurrences=26,  # 2x/week for 13 weeks
       earliest_date=datetime(2024, 9, 1, tzinfo=ZoneInfo("America/New_York")),
       latest_date=datetime(2024, 12, 15, tzinfo=ZoneInfo("America/New_York")),
       enrollment_count=20,
       required_attributes={"computer_lab": True}  # Needs computer lab
   )

   # Define specialized resources
   computer_lab = Resource(
       id="lab-001",
       resource_type="computer_lab",
       capacity=25,
       attributes={"computer_lab": True, "projector": True}
   )

Solver Selection
~~~~~~~~~~~~~~~~

EduSched provides multiple solver backends:

* **Heuristic Solver** (default): Fast greedy algorithm suitable for most use cases
* **OR-Tools Solver**: Optimal constraint programming solver (requires optional dependency)

.. code-block:: python

   # Use heuristic solver (default)
   result = solve(problem, backend="heuristic")

   # Use OR-Tools solver
   result = solve(problem, backend="ortools")

   # Auto-select best available solver
   result = solve(problem, backend="auto")