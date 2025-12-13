# Requirements Document

## Introduction

EduSched is a constraint-based scheduling package designed for educational institutions to generate optimal schedules for sessions (classes, trainings, assessments, tutoring blocks). The system must handle both hard constraints (must not violate) and soft preferences (optimize) while providing clear explanations when schedules cannot be built and supporting multiple export formats.

## Glossary

- **EduSched_System**: The constraint-based scheduling package and its components
- **SessionRequest**: A request to schedule one or more occurrences of an educational activity
- **Resource**: Any bookable entity such as instructors, rooms, campuses, or online slots
- **Calendar**: A collection of availability windows and blackout rules
- **Assignment**: The placement of a SessionRequest occurrence into a specific timeslot with bound resources
- **Constraint**: A hard rule that must be satisfied in the scheduling process
- **Objective**: A soft preference that is optimized through weighted scoring
- **Backend**: The underlying solver algorithm (heuristic or OR-Tools)
- **Problem**: A complete scheduling scenario including requests, resources, calendars, and constraints

## Requirements

### Requirement 1

**User Story:** As an educational scheduler, I want to define session requests with specific requirements, so that the system can schedule them according to institutional needs.

#### Acceptance Criteria

1. WHEN a user creates a SessionRequest, THE EduSched_System SHALL accept duration, number of occurrences, date constraints, cohort information, modality, and required resources
2. WHEN a SessionRequest specifies earliest and latest dates, THE EduSched_System SHALL only schedule occurrences within that date range
3. WHEN a SessionRequest requires specific resources, THE EduSched_System SHALL only assign those resource types to the session
4. WHEN a SessionRequest specifies a cohort, THE EduSched_System SHALL maintain cohort associations in all assignments
5. WHEN a SessionRequest defines modality requirements, THE EduSched_System SHALL respect online, in-person, or hybrid constraints

### Requirement 2

**User Story:** As a resource manager, I want to define available resources and their constraints, so that the system can properly allocate them during scheduling.

#### Acceptance Criteria

1. WHEN a user defines a Resource, THE EduSched_System SHALL accept resource type, capacity, and availability information
2. WHEN a Resource has concurrency capacity limits, THE EduSched_System SHALL prevent simultaneous assignments beyond those limits
3. WHEN a Resource has availability windows, THE EduSched_System SHALL only schedule assignments within available times
4. WHEN multiple Resource types are defined, THE EduSched_System SHALL distinguish between instructors, rooms, campuses, and online slots
5. WHEN a Resource is unavailable during specific periods, THE EduSched_System SHALL respect those blackout periods

### Requirement 3

**User Story:** As a scheduler, I want to define hard constraints that must never be violated, so that the system produces feasible schedules.

#### Acceptance Criteria

1. WHEN a NoOverlap constraint is applied to a resource, THE EduSched_System SHALL prevent double-booking of that resource
2. WHEN a BlackoutDates constraint is defined, THE EduSched_System SHALL not schedule any sessions during blackout periods
3. WHEN a MaxPerDay constraint is set for a resource, THE EduSched_System SHALL not exceed the daily limit for that resource
4. WHEN a MinGapBetweenOccurrences constraint is specified, THE EduSched_System SHALL maintain minimum spacing between session occurrences
5. WHEN a WithinDateRange constraint is applied, THE EduSched_System SHALL only schedule sessions within the specified date boundaries

### Requirement 4

**User Story:** As a scheduler, I want to define soft preferences that the system optimizes, so that I can get the best possible schedule quality.

#### Acceptance Criteria

1. WHEN SpreadEvenlyAcrossTerm objective is specified, THE EduSched_System SHALL calculate distribution scores and maximize uniformity within backend capabilities
2. WHEN MinimizeEveningSessions objective is applied, THE EduSched_System SHALL assign penalty scores to slots after the configurable evening threshold (default 17:00 local time) and minimize total penalty
3. WHEN BalanceInstructorLoad objective is set, THE EduSched_System SHALL calculate load variance and minimize instructor workload differences
4. WHEN multiple objectives are defined with weights, THE EduSched_System SHALL normalize each objective score to [0, 1] by default and compute total_score = Σ(weight_i * score_i)
5. WHEN objectives conflict with each other, THE EduSched_System SHALL return a feasible schedule that maximizes the total weighted objective score within the capabilities of the selected backend

### Requirement 5

**User Story:** As a user, I want clear explanations when schedules cannot be built, so that I can understand and resolve scheduling conflicts.

#### Acceptance Criteria

1. WHEN a scheduling problem is infeasible, THE EduSched_System SHALL provide a structured infeasibility report including unscheduled_requests, violated_constraints_summary, top_conflicts, and per_request_explanations
2. WHEN constraints conflict, THE EduSched_System SHALL identify the specific conflicting constraints and affected requests in the violated_constraints_summary
3. WHEN a SessionRequest cannot be scheduled, THE EduSched_System SHALL include constraint-specific explanations in the per_request_explanations section
4. WHEN multiple violations exist, THE EduSched_System SHALL prioritize explanations by impact in the top_conflicts section and provide actionable recommendations
5. WHEN constraint violations occur, THE EduSched_System SHALL use human-readable language in all explanation fields

### Requirement 6

**User Story:** As a scheduler, I want to export schedules in multiple formats, so that I can integrate with existing institutional systems and workflows.

#### Acceptance Criteria

1. WHEN a schedule is generated, THE EduSched_System SHALL export results to a list of Assignment objects using core dependencies, and SHALL export as a pandas DataFrame when the optional [pandas] extra is installed
2. WHEN ICS export is requested with optional dependencies installed, THE EduSched_System SHALL generate valid calendar files compatible with standard calendar applications
3. WHEN Excel export is requested with optional dependencies installed, THE EduSched_System SHALL create formatted spreadsheets with schedule data
4. WHEN exporting to any format, THE EduSched_System SHALL preserve all assignment details including resources, times, and session information
5. WHEN optional export dependencies are missing, THE EduSched_System SHALL provide clear installation guidance for the required extras

### Requirement 7

**User Story:** As a developer, I want a clean and intuitive API, so that I can easily integrate the scheduling system into educational applications.

#### Acceptance Criteria

1. WHEN creating a Problem instance, THE EduSched_System SHALL accept requests, resources, calendars, constraints, and objectives through a unified interface
2. WHEN calling the solve function, THE EduSched_System SHALL return a Result object with feasibility status and schedule data
3. WHEN using optional backend solvers, THE EduSched_System SHALL maintain identical result format and API semantics while allowing different schedules and scores between backends
4. WHEN errors occur during API usage, THE EduSched_System SHALL provide clear error messages with specific guidance
5. WHEN the package is installed, THE EduSched_System SHALL support optional dependencies through extras installation (e.g., [ortools], [excel])

### Requirement 8

**User Story:** As a system administrator, I want the package to be lightweight and performant, so that it can be deployed in various educational environments.

#### Acceptance Criteria

1. WHEN installing the base package, THE EduSched_System SHALL require only minimal core dependencies
2. WHEN solving scheduling problems using the heuristic backend, THE EduSched_System SHALL complete the provided 'edu_typical_50' benchmark scenario within 5 seconds on a single CPU core (95th percentile)
3. WHEN optional backends are available, THE EduSched_System SHALL allow users to choose between heuristic and OR-Tools solvers
4. WHEN memory usage is considered, THE EduSched_System SHALL handle typical institutional scheduling loads without excessive resource consumption
5. WHEN the package is distributed, THE EduSched_System SHALL be installable via both PyPI and conda-forge package managers

### Requirement 9

**User Story:** As a scheduler, I want precise time representation and timezone handling, so that schedules work correctly across different institutional contexts.

#### Acceptance Criteria

1. WHEN a Problem specifies timezone and timeslot granularity, THE EduSched_System SHALL generate assignments aligned to that granularity and preserve timezone in exports
2. WHEN timeslot granularity is defined, THE EduSched_System SHALL only create assignments at valid time boundaries (e.g., 15-minute increments)
3. WHEN multi-hour sessions are scheduled, THE EduSched_System SHALL represent them as contiguous timeslot blocks
4. WHEN timezone information is provided, THE EduSched_System SHALL maintain timezone consistency across all scheduling operations
5. WHEN no timezone is specified, THE EduSched_System SHALL default to UTC and document this behavior

### Requirement 10

**User Story:** As a developer, I want robust input validation and consistent output schemas, so that I can reliably integrate the system into applications.

#### Acceptance Criteria

1. WHEN required fields are missing or invalid, THE EduSched_System SHALL raise a ValidationError describing the field and expected format
2. WHEN exporting to DataFrame, THE EduSched_System SHALL produce a consistent documented schema including start_time, end_time, request_id, cohort_id, resource_ids, backend, and objective_score columns
3. WHEN input data types are incorrect, THE EduSched_System SHALL validate types and provide specific correction guidance
4. WHEN constraint parameters are invalid, THE EduSched_System SHALL validate constraint configuration before solving
5. WHEN export formats are requested, THE EduSched_System SHALL validate export parameters and handle I/O errors with actionable messages

### Requirement 11

**User Story:** As a scheduler, I want deterministic and reproducible results, so that I can reliably recreate and debug schedules.

#### Acceptance Criteria

1. WHEN solve is called with a fixed seed parameter, THE EduSched_System SHALL produce deterministic results for the heuristic backend
2. WHEN identical inputs and seed are provided, THE EduSched_System SHALL generate identical schedules and scores for the same backend
3. WHEN no seed is provided, THE EduSched_System SHALL use a random seed and document the seed used in the result
4. WHEN different backends are used with the same seed, THE EduSched_System SHALL maintain determinism within each backend while allowing different results between backends
5. WHEN reproducibility is required, THE EduSched_System SHALL include seed information in all result exports
6. WHEN processing inputs for determinism, THE EduSched_System SHALL canonicalize input ordering through stable sorting by identifier before solving

### Requirement 12

**User Story:** As a resource manager, I want to specify resource attributes and requirements matching, so that sessions are only assigned to qualified resources.

#### Acceptance Criteria

1. WHEN a SessionRequest requires specific attributes, THE EduSched_System SHALL only assign resources whose attributes satisfy all requirements
2. WHEN a Resource has defined attributes, THE EduSched_System SHALL match those attributes against SessionRequest requirements during assignment
3. WHEN attribute matching fails, THE EduSched_System SHALL include attribute mismatches in infeasibility explanations
4. WHEN multiple resources could satisfy requirements, THE EduSched_System SHALL consider all qualified resources during optimization
5. WHEN resource concurrency capacity is defined, THE EduSched_System SHALL interpret it as maximum simultaneous assignments for that resource

### Requirement 13

**User Story:** As a scheduler, I want to lock existing assignments and schedule incrementally, so that confirmed sessions are not moved when adding new requests.

#### Acceptance Criteria

1. WHEN locked assignments are specified, THE EduSched_System SHALL keep locked assignments unchanged during solving
2. WHEN scheduling around locked assignments, THE EduSched_System SHALL treat locked timeslots and resources as unavailable for new assignments
3. WHEN locked assignments create conflicts, THE EduSched_System SHALL include locked assignment conflicts in infeasibility explanations
4. WHEN incremental scheduling is requested, THE EduSched_System SHALL only reschedule unlocked SessionRequests
5. WHEN locked assignments violate current constraints, THE EduSched_System SHALL report which locked assignments cause constraint violations