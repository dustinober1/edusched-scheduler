A constraint-based scheduler package is a really strong fit for education, because it naturally demonstrates:

* applied optimization (constraints + objectives),
* clean API design,
* explainability (why a schedule can’t be built),
* robust I/O (Excel/CSV/ICS),
* optional “fast solver” backends (OR-Tools), without making the base install heavy.

Here’s a concrete package concept you can build and publish to both PyPI and conda-forge.

Package concept: edusched (working name)

Goal
Generate a schedule of sessions (classes, trainings, assessments, tutoring blocks) given:

* hard constraints (must not violate): blackout dates, room capacity, instructor availability, non-overlap, max sessions/day, required modality/room type
* soft preferences (optimize): evenly spread across term, minimize instructor overload, prefer certain days/times, reduce travel between campuses, minimize gaps for cohorts

Core design (the “portfolio” part)

1. Domain model

* SessionRequest: “what needs to be scheduled”

  * duration, number_of_occurrences, earliest/latest dates, cohort, modality, required resources
* Resource: things that can be booked

  * Instructor, Room, Campus, OnlineSlot, Proctor, etc.
* Calendar: availability windows + blackout rules
* Assignment: placing a SessionRequest occurrence into a timeslot and binding resources

2. Constraints as composable objects
   Each constraint is a class with:

* check(assignment, partial_solution) -> violation or ok
* explain(violation) -> human-readable reason + culprit fields

Examples:

* NoOverlap(resource)
* WithinDateRange()
* BlackoutDates(calendar)
* MinGapBetweenOccurrences(days=7)
* MaxPerDay(resource, n=3)
* Capacity(room >= enrollment)
* SpacingEvenness(target_distribution="uniform", weight=...)

3. Solver interface with pluggable backends

* Base backend (pure Python): greedy + backtracking + local search
* Optional backend: OR-Tools CP-SAT (extra dependency)

This is great for conda/PyPI because you can do:

* pip install edusched
* pip install edusched[ortools]

4. Diagnostics / explainability
   Make the library return not only a schedule, but also:

* infeasibility report (top conflicting constraints, which requests are impossible)
* “what changed” diff between two runs (useful in real scheduling workflows)
* per-request trace (why it got placed where it did)

Suggested public API (clean and demo-friendly)

from edusched import (
Problem, SessionRequest, Resource, Calendar,
constraints as C, objectives as O,
solve
)

problem = Problem(
requests=[...],
resources=[...],
calendars=[...],
constraints=[
C.NoOverlap("room"),
C.NoOverlap("instructor"),
C.BlackoutDates("academic_calendar"),
C.MinGapBetweenOccurrences("course_id", days=7),
C.MaxPerDay("instructor", n=3),
],
objectives=[
O.SpreadEvenlyAcrossTerm(weight=2.0),
O.MinimizeEveningSessions(weight=1.0),
O.BalanceInstructorLoad(weight=1.5),
],
)

result = solve(problem, backend="heuristic", seed=42)

if result.feasible:
df = result.to_dataframe()
result.to_ics("schedule.ics")
result.to_excel("schedule.xlsx")
else:
print(result.diagnostics.summary())
print(result.diagnostics.recommendations())

What to ship as an MVP (2–4 weeks)

MVP features

* session requests with duration + count (e.g., 8 sessions over a semester)
* resources: rooms + instructors
* availability windows + blackout dates
* constraints: no overlap, date range, blackout, max per day, min gap
* heuristic solver that finds something reasonable
* exports: pandas dataframe + ICS

MVP docs/demo

* one “education” example notebook: schedule a bootcamp across a term with holidays and instructor constraints
* one “corporate training” example: multi-cohort sessions with room capacity

High-impact stretch features (that scream “senior”)

* Optional OR-Tools backend with identical API
* Soft constraints with scoring (objective function) and a “tradeoff report”
* Incremental scheduling:

  * lock existing assignments, reschedule only the changed requests
* Import adapters:

  * Excel template (openpyxl) for non-technical stakeholders
  * output “exceptions” sheet listing unscheduled items + reasons
* Property-based tests for constraints using Hypothesis
* Benchmark suite comparing heuristic vs OR-Tools on synthetic instances

Repository structure (what hiring managers like seeing)

edusched/
src/edusched/
**init**.py
model.py
calendars.py
constraints/
base.py
overlap.py
dates.py
capacity.py
objectives/
base.py
balance.py
spacing.py
backends/
heuristic.py
ortools_cp.py   # optional
io/
excel.py
ics.py
diagnostics.py
tests/
docs/
pyproject.toml
LICENSE
README.md

Packaging notes for PyPI + conda-forge

* Keep base deps minimal: pydantic (or attrs/dataclasses), pandas optional, python-dateutil, icalendar optional
* Use optional extras:

  * [ortools] for CP-SAT
  * [excel] for openpyxl
  * [viz] for plotting
* For conda-forge, start with the base package; then add variants or keep extras available via pip inside conda envs. (Conda-forge can package optional deps too, but simplest is “base works everywhere”.)

A polished “portfolio README” outline

* 30-second pitch + gif (even a static screenshot is fine)
* Quickstart code snippet (like above)
* Education-focused example: “Schedule 12 sections across 3 campuses with spring break blackout”
* Explainability section: show an infeasible case and the diagnostics output
* Backend comparison: heuristic vs OR-Tools (table of runtime + score)

If you want, I can draft:

* the exact pyproject.toml (with extras, ruff/mypy/pytest config),
* a minimal heuristic backend (greedy + repair),
* and one education-themed example dataset + notebook that produces a schedule and an ICS file.

And to keep it aligned with your existing work: your FY26 course scheduling project maps almost 1:1 into this as the first flagship example.
