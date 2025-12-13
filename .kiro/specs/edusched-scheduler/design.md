# EduSched Design Document

## Overview

EduSched is a constraint-based scheduling package designed for educational institutions. The system uses a modular architecture with pluggable constraint systems, multiple solver backends, and comprehensive export capabilities. The design emphasizes explainability, determinism, and clean API design while maintaining lightweight core dependencies.

## Architecture

The system follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Public API Layer                         │
│  Problem, solve(), Result, SessionRequest, Resource         │
├─────────────────────────────────────────────────────────────┤
│                  Constraint System                          │
│     Hard Constraints + Soft Objectives + Validation        │
├─────────────────────────────────────────────────────────────┤
│                   Solver Backends                           │
│        Heuristic (core) + OR-Tools (optional)              │
├─────────────────────────────────────────────────────────────┤
│                   Domain Model                              │
│   SessionRequest, Resource, Calendar, Assignment            │
├─────────────────────────────────────────────────────────────┤
│                 I/O & Diagnostics                           │
│    Export (DataFrame/ICS/Excel) + Infeasibility Reports    │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Composable Constraints**: Each constraint is an independent object with check() and explain() methods
2. **Backend Abstraction**: Identical API across heuristic and OR-Tools solvers
3. **Explainability First**: Rich diagnostics for infeasible problems
4. **Deterministic by Default**: Reproducible results with seed control
5. **Lightweight Core**: Minimal dependencies with optional extras

## Components and Interfaces

### Core Domain Model

#### SessionRequest
Represents a request to schedule one or more session occurrences.

```python
@dataclass
class SessionRequest:
    id: str
    duration: timedelta
    number_of_occurrences: int
    earliest_date: datetime  # timezone-aware datetime required
    latest_date: datetime    # timezone-aware datetime required
    cohort_id: Optional[str] = None
    modality: Literal["online", "in_person", "hybrid"] = "in_person"
    required_attributes: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[ValidationError]:
        """Validate request parameters including timezone-aware datetime requirement"""
```

#### Resource
Base class for all bookable resources with attributes and capacity.

```python
@dataclass
class Resource:
    id: str
    resource_type: str
    concurrency_capacity: int = 1
    attributes: Dict[str, Any] = field(default_factory=dict)
    availability_calendar_id: Optional[str] = None  # References Calendar.id
    
    def can_satisfy(self, requirements: Dict[str, Any]) -> bool:
        """Check if resource attributes satisfy requirements"""
```

#### Calendar
Manages availability windows and blackout periods with timezone support.

```python
@dataclass
class Calendar:
    id: str
    timezone: ZoneInfo = ZoneInfo("UTC")  # Using zoneinfo.ZoneInfo
    timeslot_granularity: timedelta = timedelta(minutes=15)
    availability_windows: List[TimeWindow] = field(default_factory=list)
    blackout_periods: List[TimeWindow] = field(default_factory=list)
    
    def is_available(self, start: datetime, end: datetime) -> bool:
        """Check if time period is available (all datetimes must be timezone-aware)"""
```

#### Assignment
Represents the placement of a SessionRequest occurrence into a specific timeslot.

```python
@dataclass
class Assignment:
    request_id: str
    occurrence_index: int
    start_time: datetime  # timezone-aware datetime
    end_time: datetime    # timezone-aware datetime
    assigned_resources: Dict[str, List[str]]  # resource_type -> list of resource_ids
    cohort_id: Optional[str] = None
```

### Constraint System

#### Base Constraint Interface

```python
@dataclass
class ConstraintContext:
    """Context object providing access to problem data during constraint checking"""
    problem: 'Problem'
    resource_lookup: Dict[str, Resource]
    calendar_lookup: Dict[str, Calendar]
    request_lookup: Dict[str, SessionRequest]

class Constraint(ABC):
    @abstractmethod
    def check(self, assignment: Assignment, solution: List[Assignment], context: ConstraintContext) -> Optional[Violation]:
        """Check if assignment violates this constraint"""
    
    @abstractmethod
    def explain(self, violation: Violation) -> str:
        """Provide human-readable explanation of violation"""
    
    @property
    @abstractmethod
    def constraint_type(self) -> str:
        """Unique identifier for constraint type (e.g., 'hard.no_overlap')"""
```

#### Hard Constraints

- **NoOverlap**: Prevents resource double-booking
- **WithinDateRange**: Enforces session date boundaries  
- **BlackoutDates**: Respects calendar blackout periods
- **MaxPerDay**: Limits daily resource usage
- **MinGapBetweenOccurrences**: Enforces spacing between sessions
- **AttributeMatch**: Ensures resource attributes satisfy requirements

#### Objective System

```python
class Objective(ABC):
    def __init__(self, weight: float = 1.0):
        self.weight = weight
    
    @abstractmethod
    def score(self, solution: List[Assignment]) -> float:
        """Calculate normalized score [0,1] using penalty-based normalization
        
        Normalization strategy: penalty-based with fixed bounds
        - Calculate total penalty from objective-specific violations
        - Normalize using: score = max(0, 1 - (total_penalty / max_penalty_bound))
        - max_penalty_bound is objective-specific and configurable
        """
    
    @property
    @abstractmethod
    def objective_type(self) -> str:
        """Unique identifier for objective type"""
```

### Solver Interface

```python
class SolverBackend(ABC):
    @abstractmethod
    def solve(self, problem: Problem, seed: Optional[int] = None, fallback: bool = False) -> Result:
        """Solve scheduling problem and return result"""
    
    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Backend identifier for reproducibility"""

### OR-Tools Backend Mapping Strategy

**Decision Variables**:
- `start_time[request_id, occurrence_index]`: Integer variable representing timeslot index for each session occurrence
- `resource_assignment[request_id, occurrence_index, resource_type, resource_id]`: Boolean variable for resource assignments

**Hard Constraints Translation**:
- **NoOverlap**: `NoOverlap2D` constraint on resource timeslots with session durations
- **BlackoutDates**: Domain restriction on start_time variables to exclude blackout timeslots
- **MaxPerDay**: `LinearConstraint` summing daily assignments per resource ≤ limit
- **MinGapBetweenOccurrences**: `LinearConstraint` on start_time differences between occurrences
- **AttributeMatch**: Domain restriction on resource_assignment variables to qualified resources only

**Objective Translation**:
- **Weighted Sum**: `Minimize(Σ(weight_i * penalty_i))` where penalties are linear approximations of objective functions
- **SpreadEvenlyAcrossTerm**: Minimize variance in daily session counts using auxiliary variables
- **MinimizeEveningSessions**: Linear penalty based on evening timeslot assignments
- **BalanceInstructorLoad**: Minimize maximum instructor load using auxiliary max variables
```

## Data Models

### Problem Definition

```python
@dataclass
class Problem:
    requests: List[SessionRequest]
    resources: List[Resource]
    calendars: List[Calendar]
    constraints: List[Constraint]
    objectives: List[Objective] = field(default_factory=list)
    locked_assignments: List[Assignment] = field(default_factory=list)
    institutional_calendar_id: Optional[str] = None  # Primary calendar for timeslot generation
    
    def validate(self) -> List[ValidationError]:
        """Comprehensive problem validation including timezone-aware datetime checks"""
    
    def canonicalize(self) -> 'Problem':
        """Sort inputs by ID for deterministic processing and build lookup indices"""
    
    def _build_indices(self) -> Tuple[Dict[str, Resource], Dict[str, Calendar], Dict[str, SessionRequest]]:
        """Build lookup tables for efficient constraint checking"""
```

### Calendar and Resource Relationship Model

The system supports a two-level calendar hierarchy:

1. **Institutional Calendar**: Referenced by `Problem.institutional_calendar_id`, defines the overall timeslot grid and institutional blackouts (holidays, breaks)
2. **Resource Calendars**: Referenced by `Resource.availability_calendar_id`, defines resource-specific availability and blackouts

**Resolution Order**:
- Timeslot generation uses the institutional calendar's granularity and timezone
- Resource availability is the intersection of institutional calendar and resource-specific calendar
- If no institutional calendar is specified, the system uses the first calendar or creates a default UTC calendar

### Internal Indexing and Caching Strategy

For performance optimization, the system builds several lookup structures during `Problem.canonicalize()`:

```python
@dataclass
class ProblemIndices:
    """Cached lookup structures for efficient constraint checking"""
    resource_lookup: Dict[str, Resource]                    # resource_id -> Resource
    calendar_lookup: Dict[str, Calendar]                    # calendar_id -> Calendar  
    request_lookup: Dict[str, SessionRequest]               # request_id -> SessionRequest
    resources_by_type: Dict[str, List[Resource]]           # resource_type -> [Resources]
    qualified_resources: Dict[str, List[str]]              # request_id -> [qualified_resource_ids]
    time_occupancy_maps: Dict[str, Set[Tuple[datetime, datetime]]]  # resource_id -> occupied_intervals
    locked_intervals: Dict[str, Set[Tuple[datetime, datetime]]]     # resource_id -> locked_intervals
```

These indices enable:
- O(1) resource/calendar/request lookups during constraint checking
- O(1) resource type filtering for assignment generation
- O(log n) interval overlap checking using sorted interval sets
- Efficient qualification pre-filtering to reduce search space

### Result Schema

```python
@dataclass
class Result:
    status: Literal["feasible", "partial", "infeasible"]
    assignments: List[Assignment]
    unscheduled_requests: List[str]  # Always present when not fully feasible
    objective_score: Optional[float]
    backend_used: str
    seed_used: Optional[int]
    solve_time_seconds: float
    diagnostics: Optional[InfeasibilityReport]
    
    @property
    def feasible(self) -> bool:
        """Backward compatibility property"""
        return self.status == "feasible"
    
    def to_records(self) -> List[Dict[str, Any]]:
        """Export as list of dictionaries using core dependencies
        Schema: start_time, end_time, request_id, cohort_id, resource_ids, backend, objective_score"""
    
    def to_dataframe(self) -> 'pd.DataFrame':
        """Export as pandas DataFrame with documented schema
        Raises MissingOptionalDependency if pandas not installed"""
    
    def to_ics(self, filename: str) -> None:
        """Export as ICS calendar file (requires icalendar extra)"""
    
    def to_excel(self, filename: str) -> None:
        """Export as formatted Excel spreadsheet (requires openpyxl extra)"""
```

### Infeasibility Reporting

```python
@dataclass
class InfeasibilityReport:
    unscheduled_requests: List[str]
    violated_constraints_summary: Dict[str, int]
    top_conflicts: List[ConflictDescription]
    per_request_explanations: Dict[str, List[str]]
    
    def summary(self) -> str:
        """Human-readable summary of infeasibility"""
    
    def recommendations(self) -> List[str]:
        """Actionable suggestions for resolving conflicts"""
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Core Scheduling Properties

**Property 1: Date Range Enforcement**
*For any* SessionRequest with earliest and latest dates, all generated assignments should have start and end times within the specified date range.
**Validates: Requirements 1.2**

**Property 2: Resource Type Matching**
*For any* SessionRequest requiring specific resource types, all assignments should only use resources of the required types.
**Validates: Requirements 1.3**

**Property 3: Cohort Preservation**
*For any* SessionRequest with a cohort specification, all generated assignments should maintain the same cohort association.
**Validates: Requirements 1.4**

**Property 4: Modality Constraint Enforcement**
*For any* SessionRequest with modality requirements, all assignments should respect the specified modality constraints (online, in-person, hybrid).
**Validates: Requirements 1.5**

### Resource Management Properties

**Property 5: Concurrency Capacity Limits**
*For any* resource with defined concurrency capacity, the number of simultaneous assignments should never exceed the capacity limit.
**Validates: Requirements 2.2**

**Property 6: Availability Window Enforcement**
*For any* resource with availability windows, all assignments should only occur within the defined available time periods.
**Validates: Requirements 2.3**

**Property 7: Resource Blackout Respect**
*For any* resource with blackout periods, no assignments should be scheduled during those unavailable periods.
**Validates: Requirements 2.5**

### Hard Constraint Properties

**Property 8: No Resource Double-Booking**
*For any* resource with a NoOverlap constraint, no two assignments should overlap in time for that resource.
**Validates: Requirements 3.1**

**Property 9: Blackout Date Enforcement**
*For any* BlackoutDates constraint, no assignments should be scheduled during the specified blackout periods.
**Validates: Requirements 3.2**

**Property 10: Daily Resource Limits**
*For any* resource with a MaxPerDay constraint, the number of assignments per day should not exceed the specified limit.
**Validates: Requirements 3.3**

**Property 11: Minimum Gap Maintenance**
*For any* SessionRequest with MinGapBetweenOccurrences constraint, the time between consecutive occurrences should meet or exceed the minimum gap.
**Validates: Requirements 3.4**

**Property 12: Date Boundary Compliance**
*For any* WithinDateRange constraint, all assignments should fall within the specified date boundaries.
**Validates: Requirements 3.5**

### Objective Scoring Properties

**Property 13: Objective Score Normalization**
*For any* combination of objectives with weights, each objective score should be normalized to [0,1] and the total score should equal Σ(weight_i * score_i).
**Validates: Requirements 4.4**

**Property 14: Evening Penalty Calculation**
*For any* MinimizeEveningSessions objective with configurable evening threshold (default 17:00 local time), assignments after the threshold should receive penalty scores proportional to their evening placement.
**Validates: Requirements 4.2**

### Export and Data Integrity Properties

**Property 15: Assignment Data Preservation**
*For any* schedule export operation, all assignment details (resources, times, session information) should be preserved in the output format.
**Validates: Requirements 6.4**

**Property 16: DataFrame Schema Consistency**
*For any* DataFrame export, the output should contain the documented schema columns: start_time, end_time, request_id, cohort_id, resource_ids, backend, objective_score.
**Validates: Requirements 10.2**

**Property 17: ICS Format Validity**
*For any* ICS export, the generated calendar file should be valid according to RFC 5545 standards.
**Validates: Requirements 6.2**

### Time and Timezone Properties

**Property 18: Timeslot Granularity Alignment**
*For any* problem with defined timeslot granularity, all assignment start and end times should align to the specified time boundaries.
**Validates: Requirements 9.2**

**Property 19: Timezone Consistency**
*For any* problem with specified timezone, all scheduling operations and exports should maintain consistent timezone handling.
**Validates: Requirements 9.4**

**Property 20: Multi-Hour Session Contiguity**
*For any* multi-hour session, the assignment should represent contiguous timeslot blocks without gaps.
**Validates: Requirements 9.3**

### Validation and Error Handling Properties

**Property 21: Validation Error Completeness**
*For any* invalid input, the system should raise ValidationError with specific field identification and expected format description.
**Validates: Requirements 10.1**

**Property 22: Type Validation Accuracy**
*For any* incorrect input data type, the system should validate types and provide specific correction guidance.
**Validates: Requirements 10.3**

### Determinism and Reproducibility Properties

**Property 23: Seed-Based Determinism**
*For any* solve operation with a fixed seed, multiple runs should produce identical results for the same backend.
**Validates: Requirements 11.1, 11.2**

**Property 24: Input Canonicalization**
*For any* input set, the system should canonicalize ordering through stable sorting by identifier before processing.
**Validates: Requirements 11.6**

**Property 25: Seed Documentation**
*For any* solve operation, the result should include the seed used (whether provided or generated).
**Validates: Requirements 11.3, 11.5**

### Attribute Matching Properties

**Property 26: Resource Attribute Satisfaction**
*For any* SessionRequest with attribute requirements, only resources whose attributes satisfy all requirements should be assigned.
**Validates: Requirements 12.1, 12.2**

**Property 27: Qualified Resource Consideration**
*For any* optimization scenario with multiple qualifying resources, all qualified resources should be considered during assignment.
**Validates: Requirements 12.4**

### Incremental Scheduling Properties

**Property 28: Locked Assignment Preservation**
*For any* solve operation with locked assignments, the locked assignments should remain unchanged in the final solution.
**Validates: Requirements 13.1**

**Property 29: Locked Resource Unavailability**
*For any* scheduling operation with locked assignments, locked timeslots and resources should be treated as unavailable for new assignments.
**Validates: Requirements 13.2**

### Infeasibility Reporting Properties

**Property 30: Infeasibility Report Structure**
*For any* infeasible scheduling problem, the report should include unscheduled_requests, violated_constraints_summary, top_conflicts, and per_request_explanations sections.
**Validates: Requirements 5.1**

**Property 31: Constraint Conflict Identification**
*For any* constraint conflicts, the violated_constraints_summary should identify specific conflicting constraints and affected requests.
**Validates: Requirements 5.2**

**Property 32: Request Explanation Completeness**
*For any* unschedulable SessionRequest, the per_request_explanations should include constraint-specific explanations for why it cannot be scheduled.
**Validates: Requirements 5.3**

## Error Handling

### Validation Strategy
- **Input Validation**: Comprehensive validation at Problem creation with specific ValidationError types
- **Timezone Validation**: All datetime objects must be timezone-aware; naive datetimes are rejected with conversion guidance
- **Constraint Validation**: Pre-solve validation of constraint parameters and compatibility
- **Resource Validation**: Attribute matching and capacity validation before assignment
- **Export Validation**: Parameter validation and graceful I/O error handling

### Timezone Handling Requirements
```python
def validate_datetime(dt: datetime, field_name: str) -> datetime:
    """Validate and normalize datetime to be timezone-aware"""
    if dt.tzinfo is None:
        raise ValidationError(
            field=field_name,
            expected_format="timezone-aware datetime (e.g., datetime.now(ZoneInfo('UTC')))",
            actual_value=dt
        )
    return dt
```

### Error Types
```python
class ValidationError(Exception):
    def __init__(self, field: str, expected_format: str, actual_value: Any):
        self.field = field
        self.expected_format = expected_format
        self.actual_value = actual_value

class InfeasibilityError(Exception):
    def __init__(self, report: InfeasibilityReport):
        self.report = report

class BackendError(Exception):
    def __init__(self, backend_name: str, error_details: str):
        self.backend_name = backend_name
        self.error_details = error_details

class MissingOptionalDependency(Exception):
    def __init__(self, feature: str, install_command: str):
        self.feature = feature
        self.install_command = install_command
        super().__init__(f"Feature '{feature}' requires optional dependencies. Install with: {install_command}")
```

### Graceful Degradation
- **Missing optional dependencies**: Raise `MissingOptionalDependency` with clear installation guidance
- **Backend failures**: Raise `BackendError` by default; opt-in fallback with `fallback=True` parameter
- **Partial infeasibility**: Return `Result` with `status="partial"` and populated `unscheduled_requests`
- **Export errors**: Detailed I/O error messages with suggested fixes
- **Timezone validation**: Reject naive datetimes with specific guidance to use timezone-aware datetimes
- **Datetime normalization**: All datetimes normalized to Problem/Calendar timezone during validation

### Backend Failure Handling
```python
def solve(problem: Problem, backend: str = "auto", seed: Optional[int] = None, fallback: bool = False) -> Result:
    try:
        solver = _get_backend(backend)
        return solver.solve(problem, seed, fallback=False)
    except BackendError as e:
        if fallback and backend != "heuristic":
            logger.warning(f"Backend {backend} failed, falling back to heuristic: {e}")
            heuristic_solver = _get_backend("heuristic")
            result = heuristic_solver.solve(problem, seed)
            result.diagnostics.add_note(f"Fallback used due to {backend} failure: {e.error_details}")
            return result
        raise
```

## Testing Strategy

### Dual Testing Approach
The system requires both unit testing and property-based testing to ensure comprehensive correctness validation:

**Unit Testing**:
- Specific examples demonstrating correct behavior
- Edge cases and boundary conditions
- Integration points between components
- Error condition handling
- API interface validation

**Property-Based Testing**:
- Universal properties verified across all valid inputs
- Constraint satisfaction across random problem instances
- Objective scoring consistency across different scenarios
- Export format preservation across various schedules
- Determinism verification across multiple runs

### Property-Based Testing Framework
- **Library**: Hypothesis for Python property-based testing
- **Test Configuration**: 
  - CI/fast: 25 iterations per property test
  - Local/comprehensive: 100 iterations per property test  
  - Nightly/thorough: 200+ iterations per property test
- **Property Tagging**: Each test tagged with format: `**Feature: edusched-scheduler, Property {number}: {property_text}**`
- **Generator Strategy**: Smart generators that constrain inputs to valid problem spaces with timezone-aware datetimes

### Test Organization
```
tests/
├── unit/
│   ├── test_domain_model.py
│   ├── test_constraints.py
│   ├── test_objectives.py
│   ├── test_backends.py
│   └── test_exports.py
├── property/
│   ├── test_scheduling_properties.py
│   ├── test_constraint_properties.py
│   ├── test_export_properties.py
│   └── test_determinism_properties.py
├── integration/
│   ├── test_end_to_end.py
│   └── test_backend_compatibility.py
└── fixtures/
    ├── sample_problems.py
    └── benchmark_scenarios.py
```

### Performance Testing
- **Benchmark Suite**: 'edu_typical_50' scenario for performance validation
- **Target**: 95th percentile completion within 5 seconds on single CPU core
- **Memory Profiling**: Validation of memory usage for typical institutional loads
- **Backend Comparison**: Performance benchmarking between heuristic and OR-Tools backends

## Implementation Notes

### Dependency Management
```toml
[project]
dependencies = [
    "python-dateutil>=2.8.0",
    "typing-extensions>=4.0.0",
]

[project.optional-dependencies]
pandas = ["pandas>=1.5.0"]
ortools = ["ortools>=9.0.0"]
excel = ["openpyxl>=3.0.0"]
ics = ["icalendar>=4.0.0"]
viz = ["matplotlib>=3.5.0"]  # Removed seaborn for simplicity
all = ["edusched[pandas,ortools,excel,ics,viz]"]
```

### Core vs Optional Export Strategy
- **Core exports**: `Result.to_records()` returns `List[Dict[str, Any]]` with documented schema using only core dependencies
- **Optional exports**: `Result.to_dataframe()`, `Result.to_ics()`, `Result.to_excel()` require respective extras
- **Fallback behavior**: Optional export methods raise `MissingOptionalDependency` with installation guidance when dependencies are missing
- **Schema consistency**: Both `to_records()` and `to_dataframe()` use identical column schema for compatibility

### Backend Selection Strategy
```python
def solve(problem: Problem, backend: str = "auto", seed: Optional[int] = None) -> Result:
    if backend == "auto":
        backend = "ortools" if _ortools_available() else "heuristic"
    
    solver = _get_backend(backend)
    return solver.solve(problem, seed)
```

### Extensibility Points
- **Custom Constraints**: Inherit from Constraint base class
- **Custom Objectives**: Inherit from Objective base class  
- **Custom Backends**: Implement SolverBackend interface
- **Custom Resources**: Extend Resource with additional attributes
- **Custom Exports**: Add new export methods to Result class

### Performance Optimizations
- **Lazy Evaluation**: Constraint checking only when necessary
- **Caching**: Memoization of expensive constraint evaluations
- **Incremental Updates**: Efficient handling of locked assignments
- **Memory Management**: Streaming exports for large schedules
- **Parallel Processing**: Multi-threaded constraint checking where applicable

### Future Extensions (Portfolio Considerations)

**CLI Interface** (Future v2):
```bash
edusched solve input.xlsx --backend ortools --out schedule.xlsx --format excel
edusched validate problem.json --constraints-only
edusched benchmark --scenario edu_typical_50 --backends heuristic,ortools
```

**Schema Versioning**:
- DataFrame exports include `schema_version` metadata for backward compatibility
- Result objects include `api_version` for client compatibility checking

**Advanced Features Roadmap**:
- Multi-objective Pareto optimization
- Constraint relaxation suggestions for infeasible problems  
- Real-time schedule updates with conflict resolution
- Integration adapters for common LMS systems (Canvas, Blackboard)
- Advanced visualization of schedule conflicts and optimization trade-offs