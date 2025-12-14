# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-12-14

### Added
- Initial release of EduSched
- Core scheduling engine with constraint-based optimization
- Domain models for resources, sessions, calendars, and assignments
- Hard constraints: NoOverlap, BlackoutDates, MaxPerDay, AttributeMatch, WithinDateRange
- Soft objectives: SpreadEvenlyAcrossTerm, MinimizeEveningSessions, BalanceInstructorLoad
- Heuristic solver for fast scheduling
- OR-Tools solver for optimal solutions (optional dependency)
- Student conflict detection and resolution
- Teacher constraint support (max hours, preferred times, breaks)
- Room capacity and equipment matching
- Building and campus support with walking distance calculations
- Incremental scheduling for add/drop operations
- Export to iCal format
- FastAPI backend scaffolding for web integration
- Comprehensive test suite with 168 passing tests
- Type hints throughout (PEP 561 compliant)
- Python 3.9 - 3.13 support

### Known Limitations
- Some integration modules (SIS, calendar sync) are scaffolding only
- E2E tests require running servers

## [Unreleased]

### Planned
- Full SIS integration (Canvas, Blackboard, Banner)
- Calendar sync (Google, Outlook)
- Web UI dashboard
- Conflict visualization
- Bulk import/export improvements
