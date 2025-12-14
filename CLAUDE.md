# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EduSched is a constraint-based scheduling package for educational institutions. It's a Python library (not a web application) that enables scheduling of courses, rooms, teachers, and resources subject to various constraints and optimization objectives.

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_domain_properties.py

# Run with verbose output
pytest -v --tb=short

# Run property-based tests
pytest -m hypothesis
```

### Code Quality
```bash
# Lint code
ruff check src/ tests/

# Format code (if formatter is added)
ruff format src/ tests/

# Type checking
mypy src/
```

### Package Development
```bash
# Install with development dependencies
pip install -e .[dev]

# Install with all optional dependencies
pip install -e .[all]

# Build package
python -m build

# Generate sample data
python scripts/generate_sample_data.py

# Create Excel templates
python scripts/create_excel_templates.py
```

## Architecture

### Core Components

1. **Domain Model** (`src/edusched/domain/`)
   - `Problem`: Central container for all scheduling data, constraints, and objectives
   - `SessionRequest`: Course/class to be scheduled (duration, occurrences, date range, requirements)
   - `Resource`: Schedulable entities (rooms, labs, equipment) with attributes and availability
   - `Calendar`: Timezone-aware availability patterns for resources
   - `Assignment`: Solution mapping of requests to specific time slots and resources
   - `Result`: Contains assignments, diagnostics, and solver statistics

2. **Constraint System** (`src/edusched/constraints/`)
   - `Constraint` base class with `check()` method returning `Violation` or None
   - `HardConstraints`: Must be satisfied (no overlaps, blackout dates, capacity limits)
   - Constraints operate on individual assignments and can access full solution context
   - Implementation pattern: each constraint type in separate file (e.g., `teacher_constraints.py`)

3. **Solver Backend** (`src/edusched/solvers/`)
   - `HeuristicSolver`: Greedy algorithm with efficiency scoring and constraint checking
   - `SolverBackend`: Abstract interface for future optimization solvers (OR-Tools integration planned)
   - Main entry point: `api.solve(problem, backend="heuristic", seed=None)`

4. **Data Import** (`src/edusched/utils/data_import.py`)
   - Supports CSV, JSON, Excel (with pandas) formats
   - Bulk operations via `api/bulk_import.py` (FastAPI endpoints - development scaffolding)

### Key Design Patterns

- **Immutable domain objects**: Dataclasses with validation
- **Type hints throughout**: With optional mypy checking
- **Constraint composition**: Add constraints to `Problem.constraints` list
- **Objective functions**: Optimize for spread, load balance, etc.
- **Incremental solving**: Add requests/constraints and re-solve
- **Property-based testing**: Extensive Hypothesis tests for invariants

### Problem Structure
The `Problem` class is the central data structure containing:
- Lists of domain objects (requests, resources, calendars, constraints, objectives)
- `ProblemIndices` for efficient O(1) lookups during solving
- Validation via `problem.validate()` before solving
- `canonicalize()` method for deterministic sorting

### Constraint Implementation
Constraints receive:
- Current assignment being evaluated
- Partial solution (list of existing assignments)
- Context with lookups to all problem data

Return `Violation` object if constraint violated, None if satisfied.

### Solver Flow
1. Problem validation and canonicalization
2. Sort requests by priority/duration
3. For each request: find earliest valid slot
4. Check all constraints, backtrack if violated
5. Apply efficiency scoring for resource selection
6. Return Result with assignments and diagnostics

## Testing Strategy

- **Property-based tests**: Hypothesis-generated test cases verifying invariants
- **Unit tests**: Individual component testing
- **Integration tests**: Full problem-solving scenarios
- Test files follow pattern: `test_*_properties.py` for property-based tests

## Dependencies

- Core: `python-dateutil`, `typing-extensions`
- Optional: `pandas`, `openpyxl` for Excel support
- Development: `pytest`, `hypothesis`, `mypy`, `ruff`

## Notes

- This is a library package, not a deployed application
- No authentication or web server components in core library
- FastAPI code in `api/bulk_import.py` appears to be scaffolding/unfinished
- Timezone handling throughout using Python's zoneinfo
- Extensive validation and error handling with custom exception types