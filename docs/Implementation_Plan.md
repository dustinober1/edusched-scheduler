# EduSched Implementation Plan

## Project Overview
Building a constraint-based scheduler package (`edusched`) for educational scheduling with clean API design, explainability, and multiple backend support.

## Phase 1: Foundation & MVP (Weeks 1-2)

### 1.1 Project Setup
- [ ] Initialize repository structure
- [ ] Configure `pyproject.toml` with dependencies and optional extras
- [ ] Set up development environment (ruff, mypy, pytest)
- [ ] Create basic package structure with `__init__.py`

### 1.2 Core Domain Model (`model.py`)
- [ ] Implement `SessionRequest` class
  - duration, number_of_occurrences, date constraints
  - cohort, modality, required resources
- [ ] Implement `Resource` base class and subclasses
  - Instructor, Room, Campus, OnlineSlot
- [ ] Implement `Calendar` class
  - availability windows, blackout dates
- [ ] Implement `Assignment` class
  - timeslot binding, resource allocation

### 1.3 Basic Constraints System (`constraints/`)
- [ ] Create `base.py` with constraint interface
  - `check(assignment, partial_solution)` method
  - `explain(violation)` method
- [ ] Implement core constraints:
  - [ ] `NoOverlap` (resource conflicts)
  - [ ] `WithinDateRange` (date boundaries)
  - [ ] `BlackoutDates` (calendar restrictions)
  - [ ] `MaxPerDay` (daily limits)
  - [ ] `MinGapBetweenOccurrences` (spacing requirements)

### 1.4 Heuristic Solver (`backends/heuristic.py`)
- [ ] Implement greedy assignment algorithm
- [ ] Add basic backtracking for conflicts
- [ ] Create solver interface with `solve()` function

## Phase 2: Core Features & API (Weeks 2-3)

### 2.1 Problem Definition & API
- [ ] Implement `Problem` class
  - requests, resources, calendars collections
  - constraints and objectives lists
- [ ] Create main `solve()` function with clean API
- [ ] Implement `Result` class with feasibility checking

### 2.2 Basic I/O Support (`io/`)
- [ ] Pandas DataFrame export (`to_dataframe()`)
- [ ] ICS calendar export (`to_ics()`)
- [ ] Basic Excel export (`to_excel()`)

### 2.3 Diagnostics System (`diagnostics.py`)
- [ ] Infeasibility reporting
- [ ] Constraint violation explanations
- [ ] Human-readable error messages

### 2.4 Testing Foundation
- [ ] Unit tests for all constraint classes
- [ ] Integration tests for heuristic solver
- [ ] Test data fixtures for education scenarios

## Phase 3: Advanced Features (Weeks 3-4)

### 3.1 Objectives System (`objectives/`)
- [ ] Create objective function interface
- [ ] Implement core objectives:
  - [ ] `SpreadEvenlyAcrossTerm`
  - [ ] `MinimizeEveningSessions`
  - [ ] `BalanceInstructorLoad`
- [ ] Add weighted objective scoring

### 3.2 Enhanced Solver Features
- [ ] Local search improvements
- [ ] Solution scoring and comparison
- [ ] Seed-based reproducibility

### 3.3 Calendar Management (`calendars.py`)
- [ ] Academic calendar templates
- [ ] Holiday/break handling
- [ ] Multi-timezone support

## Phase 4: Polish & Documentation (Week 4)

### 4.1 Documentation
- [ ] Comprehensive README with examples
- [ ] API documentation
- [ ] Education-focused example notebook
- [ ] Corporate training example

### 4.2 Example Scenarios
- [ ] Bootcamp scheduling across semester
- [ ] Multi-cohort training sessions
- [ ] FY26 course scheduling (real-world example)

### 4.3 Package Polish
- [ ] Error handling improvements
- [ ] Performance optimizations
- [ ] Code quality review (ruff, mypy)

## Phase 5: Stretch Features (Optional)

### 5.1 OR-Tools Backend (`backends/ortools_cp.py`)
- [ ] CP-SAT solver integration
- [ ] Identical API compatibility
- [ ] Performance benchmarking

### 5.2 Advanced I/O
- [ ] Excel template import
- [ ] Exception reporting sheets
- [ ] Configuration file support

### 5.3 Incremental Scheduling
- [ ] Lock existing assignments
- [ ] Reschedule only changed requests
- [ ] Change impact analysis

### 5.4 Property-Based Testing
- [ ] Hypothesis-based constraint testing
- [ ] Synthetic data generation
- [ ] Benchmark suite

## Deliverables Checklist

### MVP Deliverables
- [ ] Working package installable via pip
- [ ] Core scheduling functionality
- [ ] Basic constraint system
- [ ] DataFrame and ICS export
- [ ] One complete education example

### Stretch Deliverables
- [ ] OR-Tools backend option
- [ ] Excel import/export
- [ ] Comprehensive documentation
- [ ] Multiple example scenarios
- [ ] Performance benchmarks

## Repository Structure
```
edusched/
├── src/edusched/
│   ├── __init__.py
│   ├── model.py
│   ├── calendars.py
│   ├── constraints/
│   │   ├── base.py
│   │   ├── overlap.py
│   │   ├── dates.py
│   │   └── capacity.py
│   ├── objectives/
│   │   ├── base.py
│   │   ├── balance.py
│   │   └── spacing.py
│   ├── backends/
│   │   ├── heuristic.py
│   │   └── ortools_cp.py
│   ├── io/
│   │   ├── excel.py
│   │   └── ics.py
│   └── diagnostics.py
├── tests/
├── docs/
├── examples/
├── pyproject.toml
├── LICENSE
└── README.md
```

## Success Metrics
- [ ] Package successfully installs via `pip install edusched`
- [ ] Can schedule 50+ sessions with 10+ constraints in <5 seconds
- [ ] Clear error messages for infeasible problems
- [ ] Export formats work with common tools (Excel, Google Calendar)
- [ ] Documentation enables new users to get started in <10 minutes

## Next Steps
1. Review and approve this plan
2. Set up development environment
3. Begin Phase 1 implementation
4. Regular progress check-ins at end of each phase