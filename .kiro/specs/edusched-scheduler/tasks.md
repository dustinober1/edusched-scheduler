# Implementation Plan

## Overview

Convert the EduSched design into a series of incremental implementation tasks that build a constraint-based scheduling package with clean API design, explainability, and multiple backend support.

## Tasks

- [ ] 1. Set up project structure and core dependencies
  - Create package directory structure with src/edusched layout
  - Configure pyproject.toml with core dependencies (python-dateutil, typing-extensions) and optional extras
  - Set up development environment with ruff, mypy, pytest, and hypothesis
  - Create __init__.py files and basic package imports
  - _Requirements: 7.5, 8.1, 8.5_

- [ ] 2. Implement core domain model with timezone validation
  - [ ] 2.1 Create SessionRequest class with timezone-aware datetime validation
    - Implement SessionRequest dataclass with all required fields
    - Add validate() method with timezone-aware datetime checking
    - Include modality and attribute requirements support
    - _Requirements: 1.1, 1.4, 1.5, 9.5, 10.1_

  - [ ] 2.2 Write property test for SessionRequest validation
    - **Property 1: Date Range Enforcement**
    - **Validates: Requirements 1.2**

  - [ ] 2.3 Create Resource class with attribute matching
    - Implement Resource dataclass with concurrency capacity and attributes
    - Add can_satisfy() method for attribute requirement matching
    - Include availability_calendar_id reference
    - _Requirements: 2.1, 2.4, 12.1, 12.2_

  - [ ] 2.4 Write property test for resource attribute matching
    - **Property 26: Resource Attribute Satisfaction**
    - **Validates: Requirements 12.1, 12.2**

  - [ ] 2.5 Create Calendar class with timezone support
    - Implement Calendar dataclass with ZoneInfo timezone handling
    - Add timeslot granularity and availability window support
    - Include is_available() method for time period checking
    - _Requirements: 9.1, 9.4, 9.5_

  - [ ] 2.6 Write property test for timezone consistency
    - **Property 19: Timezone Consistency**
    - **Validates: Requirements 9.4**

  - [ ] 2.7 Create Assignment class with multi-resource support
    - Implement Assignment dataclass with timezone-aware datetimes
    - Use Dict[str, List[str]] for assigned_resources to support multiple resources per type
    - Include cohort_id preservation
    - _Requirements: 1.4, 9.1_

  - [ ] 2.8 Write property test for cohort preservation
    - **Property 3: Cohort Preservation**
    - **Validates: Requirements 1.4**

- [ ] 3. Implement constraint system with context-aware checking
  - [ ] 3.1 Create base constraint interface with ConstraintContext
    - Implement Constraint ABC with check() method using ConstraintContext
    - Create ConstraintContext dataclass with problem indices
    - Add explain() method interface for human-readable violations
    - _Requirements: 3.1, 5.2, 5.5_

  - [ ] 3.2 Implement NoOverlap constraint
    - Create NoOverlap constraint class with resource overlap checking
    - Use interval-based overlap detection with time occupancy maps
    - Include clear violation explanations
    - _Requirements: 3.1_

  - [ ] 3.3 Write property test for no resource double-booking
    - **Property 8: No Resource Double-Booking**
    - **Validates: Requirements 3.1**

  - [ ] 3.4 Implement BlackoutDates constraint
    - Create BlackoutDates constraint with calendar integration
    - Support both institutional and resource-specific blackouts
    - _Requirements: 3.2_

  - [ ] 3.5 Write property test for blackout date enforcement
    - **Property 9: Blackout Date Enforcement**
    - **Validates: Requirements 3.2**

  - [ ] 3.6 Implement MaxPerDay and MinGapBetweenOccurrences constraints
    - Create MaxPerDay constraint with daily limit tracking
    - Create MinGapBetweenOccurrences constraint with occurrence spacing
    - _Requirements: 3.3, 3.4_

  - [ ] 3.7 Write property tests for daily limits and spacing
    - **Property 10: Daily Resource Limits**
    - **Property 11: Minimum Gap Maintenance**
    - **Validates: Requirements 3.3, 3.4**

  - [ ] 3.8 Implement WithinDateRange and AttributeMatch constraints
    - Create WithinDateRange constraint for date boundary enforcement
    - Create AttributeMatch constraint using Resource.can_satisfy()
    - _Requirements: 3.5, 12.1_

  - [ ] 3.9 Write property tests for date boundaries and attribute matching
    - **Property 12: Date Boundary Compliance**
    - **Property 26: Resource Attribute Satisfaction**
    - **Validates: Requirements 3.5, 12.1**

- [ ] 4. Implement objective system with penalty-based scoring
  - [ ] 4.1 Create base objective interface with normalization
    - Implement Objective ABC with penalty-based score() method
    - Define normalization strategy using fixed penalty bounds
    - Include weight handling and objective_type property
    - _Requirements: 4.4_

  - [ ] 4.2 Write property test for objective score normalization
    - **Property 13: Objective Score Normalization**
    - **Validates: Requirements 4.4**

  - [ ] 4.3 Implement SpreadEvenlyAcrossTerm objective
    - Create objective that minimizes variance in daily session distribution
    - Use penalty-based scoring with configurable bounds
    - _Requirements: 4.1_

  - [ ] 4.4 Implement MinimizeEveningSessions objective
    - Create objective with configurable evening threshold (default 17:00)
    - Apply penalties proportional to evening placement
    - _Requirements: 4.2_

  - [ ] 4.5 Write property test for evening penalty calculation
    - **Property 14: Evening Penalty Calculation**
    - **Validates: Requirements 4.2**

  - [ ] 4.6 Implement BalanceInstructorLoad objective
    - Create objective that minimizes instructor workload variance
    - Calculate load distribution across instructors
    - _Requirements: 4.3_

- [ ] 5. Create Problem class with indexing and validation
  - [ ] 5.1 Implement Problem dataclass with comprehensive validation
    - Create Problem class with all required collections
    - Add validate() method with timezone-aware datetime checking
    - Include institutional_calendar_id for timeslot generation
    - _Requirements: 7.1, 10.1, 10.4_

  - [ ] 5.2 Write property test for validation error completeness
    - **Property 21: Validation Error Completeness**
    - **Validates: Requirements 10.1**

  - [ ] 5.3 Implement canonicalize() method with deterministic ordering
    - Add stable sorting by identifier for all input collections
    - Build ProblemIndices with lookup tables and occupancy maps
    - Support locked assignments in index building
    - _Requirements: 11.6, 13.1, 13.2_

  - [ ] 5.4 Write property test for input canonicalization
    - **Property 24: Input Canonicalization**
    - **Validates: Requirements 11.6**

  - [ ] 5.5 Implement calendar and resource relationship resolution
    - Add logic for institutional vs resource-specific calendar handling
    - Build qualified_resources index using attribute matching
    - Create time_occupancy_maps for efficient overlap checking
    - _Requirements: 2.3, 2.5, 12.4_

- [ ] 6. Implement Result class with multi-format export support
  - [ ] 6.1 Create Result dataclass with status tracking
    - Implement Result with feasible/partial/infeasible status
    - Include unscheduled_requests for partial solutions
    - Add seed tracking and backend identification
    - _Requirements: 7.2, 11.3, 11.5_

  - [ ] 6.2 Implement core export method (to_records)
    - Create to_records() method returning List[Dict] with documented schema
    - Use only core dependencies for this export method
    - Include all assignment details and metadata
    - _Requirements: 6.1, 6.4_

  - [ ] 6.3 Write property test for assignment data preservation
    - **Property 15: Assignment Data Preservation**
    - **Validates: Requirements 6.4**

  - [ ] 6.4 Implement optional pandas DataFrame export
    - Create to_dataframe() method with MissingOptionalDependency handling
    - Use identical schema as to_records() for consistency
    - Include schema_version metadata for future compatibility
    - _Requirements: 6.1, 10.2_

  - [ ] 6.5 Write property test for DataFrame schema consistency
    - **Property 16: DataFrame Schema Consistency**
    - **Validates: Requirements 10.2**

  - [ ] 6.6 Implement ICS and Excel export methods
    - Create to_ics() method with icalendar dependency checking
    - Create to_excel() method with openpyxl dependency checking
    - Include timezone preservation in calendar exports
    - _Requirements: 6.2, 6.3, 9.1_

  - [ ] 6.7 Write property test for ICS format validity
    - **Property 17: ICS Format Validity**
    - **Validates: Requirements 6.2**

- [ ] 7. Implement heuristic solver backend
  - [ ] 7.1 Create SolverBackend interface
    - Implement SolverBackend ABC with solve() method signature
    - Include seed parameter and fallback option support
    - Add backend_name property for reproducibility tracking
    - _Requirements: 7.3, 11.1, 11.4_

  - [ ] 7.2 Implement greedy assignment algorithm
    - Create heuristic solver with greedy assignment strategy
    - Use ProblemIndices for efficient constraint checking
    - Include timeslot granularity alignment
    - _Requirements: 8.2, 9.2_

  - [ ] 7.3 Write property test for timeslot granularity alignment
    - **Property 18: Timeslot Granularity Alignment**
    - **Validates: Requirements 9.2**

  - [ ] 7.4 Add backtracking and local search improvements
    - Implement backtracking for conflict resolution
    - Add local search for objective optimization
    - Include seed-based determinism
    - _Requirements: 11.1, 11.2_

  - [ ] 7.5 Write property test for seed-based determinism
    - **Property 23: Seed-Based Determinism**
    - **Validates: Requirements 11.1, 11.2**

  - [ ] 7.6 Implement multi-hour session handling
    - Add logic for contiguous timeslot block creation
    - Ensure proper duration handling across timeslot boundaries
    - _Requirements: 9.3_

  - [ ] 7.7 Write property test for multi-hour session contiguity
    - **Property 20: Multi-Hour Session Contiguity**
    - **Validates: Requirements 9.3**

- [ ] 8. Implement infeasibility reporting and diagnostics
  - [ ] 8.1 Create InfeasibilityReport dataclass
    - Implement structured report with unscheduled_requests and violated_constraints_summary
    - Add top_conflicts and per_request_explanations sections
    - Include summary() and recommendations() methods
    - _Requirements: 5.1, 5.4_

  - [ ] 8.2 Write property test for infeasibility report structure
    - **Property 30: Infeasibility Report Structure**
    - **Validates: Requirements 5.1**

  - [ ] 8.3 Implement constraint conflict identification
    - Add logic to identify specific conflicting constraints
    - Include affected requests in violation summaries
    - Generate human-readable explanations using constraint.explain()
    - _Requirements: 5.2, 5.3_

  - [ ] 8.4 Write property tests for conflict identification and explanations
    - **Property 31: Constraint Conflict Identification**
    - **Property 32: Request Explanation Completeness**
    - **Validates: Requirements 5.2, 5.3**

  - [ ] 8.5 Implement locked assignment conflict reporting
    - Add special handling for locked assignment violations
    - Include locked assignment conflicts in infeasibility explanations
    - _Requirements: 13.3, 13.5_

  - [ ] 8.6 Write property tests for locked assignment handling
    - **Property 28: Locked Assignment Preservation**
    - **Property 29: Locked Resource Unavailability**
    - **Validates: Requirements 13.1, 13.2**

- [ ] 9. Create main solve() function and API integration
  - [ ] 9.1 Implement main solve() function
    - Create solve() function with backend selection and fallback handling
    - Include automatic backend detection (ortools -> heuristic)
    - Add seed parameter with random seed generation when not provided
    - _Requirements: 7.1, 7.2, 11.3_

  - [ ] 9.2 Write property test for API behavior consistency
    - **Property 23: Seed-Based Determinism**
    - **Validates: Requirements 7.3, 11.4**

  - [ ] 9.3 Implement error handling and validation integration
    - Add comprehensive ValidationError handling with specific guidance
    - Include MissingOptionalDependency errors for export methods
    - Implement BackendError handling with optional fallback
    - _Requirements: 7.4, 10.3, 10.5_

  - [ ] 9.4 Write property test for type validation accuracy
    - **Property 22: Type Validation Accuracy**
    - **Validates: Requirements 10.3**

  - [ ] 9.5 Add incremental scheduling support
    - Implement locked assignment handling in solver
    - Add logic to treat locked resources as unavailable
    - Include incremental scheduling mode for unlocked requests only
    - _Requirements: 13.1, 13.2, 13.4_

  - [ ] 9.6 Write property test for incremental scheduling
    - **Property 28: Locked Assignment Preservation**
    - **Validates: Requirements 13.1, 13.4**

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Create comprehensive test suite and benchmarks
  - [ ] 11.1 Create benchmark scenario (edu_typical_50)
    - Implement edu_typical_50 benchmark with 50+ sessions and 10+ constraints
    - Include realistic educational scheduling data (instructors, rooms, courses)
    - Add performance validation for 5-second completion target
    - _Requirements: 8.2_

  - [ ] 11.2 Implement property-based test generators
    - Create Hypothesis generators for SessionRequest, Resource, Calendar
    - Ensure generators produce timezone-aware datetimes
    - Include smart constraint generation for valid problem spaces
    - _Requirements: 9.4, 10.1_

  - [ ] 11.3 Write remaining property tests for resource management
    - **Property 5: Concurrency Capacity Limits**
    - **Property 6: Availability Window Enforcement**
    - **Property 7: Resource Blackout Respect**
    - **Validates: Requirements 2.2, 2.3, 2.5**

  - [ ] 11.4 Write property tests for qualified resource consideration
    - **Property 27: Qualified Resource Consideration**
    - **Validates: Requirements 12.4**

  - [ ] 11.5 Write property tests for seed documentation
    - **Property 25: Seed Documentation**
    - **Validates: Requirements 11.3, 11.5**

  - [ ] 11.6 Create integration tests for end-to-end scenarios
    - Test complete scheduling workflows from Problem to Result
    - Include both feasible and infeasible problem scenarios
    - Validate export format compatibility across methods
    - _Requirements: 6.4, 7.2_

- [ ] 12. Implement OR-Tools backend
  - [ ] 12.1 Create OR-Tools solver implementation
    - Implement CP-SAT backend with decision variable mapping
    - Translate hard constraints to CP-SAT constraint types
    - Include objective function translation with weighted sums
    - _Requirements: 7.3, 8.3_

  - [ ] 12.2 Add backend compatibility testing
    - Ensure identical API behavior between heuristic and OR-Tools
    - Validate determinism within each backend
    - Include performance benchmarking comparison
    - _Requirements: 7.3, 11.4_

- [ ] 13. Create documentation and examples
  - [ ] 13.1 Write comprehensive README with quickstart
    - Include 30-second pitch and installation instructions
    - Add quickstart code example with education scenario
    - Document API usage patterns and export formats
    - _Requirements: 7.1, 8.5_

  - [ ] 13.2 Create education-focused example notebook
    - Implement bootcamp scheduling example across semester
    - Include holiday blackouts and instructor constraints
    - Demonstrate infeasibility reporting and conflict resolution
    - _Requirements: 5.1, 5.4_

  - [ ] 13.3 Add API documentation and schema reference
    - Document all public classes and methods
    - Include DataFrame schema specification
    - Add constraint and objective reference guide
    - _Requirements: 10.2_

- [ ] 14. Final checkpoint and package polish
  - Ensure all tests pass, ask the user if questions arise.
  - Validate package installation via pip
  - Run performance benchmarks and validate 5-second target
  - Review code quality with ruff and mypy
  - _Requirements: 8.1, 8.2, 8.5_