# Backend Improvement Tasks by Priority

## Priority 1: Critical Security & Production Fixes
**Timeline: Week 1 (Immediate)**

### 1.1 Replace Wildcard Imports
- **File**: `src/edusched/io/import_export.py:16-17`
- **Issue**: `from edusched.constraints.hard_constraints import *`
- **Risk**: Namespace pollution, security vulnerabilities
- **Action**: Replace with explicit imports
- **Effort**: 2 hours

### 1.2 Improve Exception Handling
- **Files**: Multiple files with bare `except:` clauses
- **Risk**: Silent failures, poor error visibility
- **Action**: Use specific exception types with logging
- **Effort**: 4 hours

### 1.3 Replace Print Statements
- **Files**: `main.py`, `database.py`, `calendar.py`, `data_import.py`
- **Risk**: Poor production logging
- **Action**: Replace with structured logging
- **Effort**: 3 hours

## Priority 2: Performance & Scalability
**Timeline: Week 2**

### 2.1 Database Optimization
- **Current**: SQLite with JSON columns
- **Issues**: No connection pooling, inefficient queries
- **Action**: PostgreSQL support, connection pooling, proper schema
- **Effort**: 8 hours

### 2.2 Async Database Operations
- **Issue**: Synchronous DB operations in async endpoints
- **Impact**: Blocking operations, poor performance
- **Action**: Implement asyncpg for PostgreSQL
- **Effort**: 4 hours

### 2.3 Caching Strategy
- **Missing**: Redis integration, query caching
- **Action**: Implement Redis-based caching
- **Effort**: 6 hours

## Priority 3: Code Quality & Testing
**Timeline: Week 3**

### 3.1 Comprehensive Test Suite
- **Current**: Limited test coverage
- **Missing**: Integration tests, API tests, auth tests
- **Action**: Implement full test coverage
- **Effort**: 16 hours

### 3.2 Input Validation Enhancement
- **Current**: Basic validation only
- **Action**: Expand Pydantic models, custom validators
- **Effort**: 6 hours

### 3.3 API Documentation
- **Current**: Basic FastAPI docs
- **Action**: Enhanced OpenAPI with examples
- **Effort**: 4 hours

## Priority 4: Monitoring & Architecture
**Timeline: Week 4**

### 4.1 Structured Logging
- **Current**: Basic logging
- **Action**: JSON logging, correlation IDs, metrics
- **Effort**: 6 hours

### 4.2 Background Job Processing
- **Missing**: Celery/RQ for async tasks
- **Action**: Implement background job queue
- **Effort**: 12 hours

### 4.3 Metrics Collection
- **Missing**: Prometheus metrics
- **Action**: Add metrics endpoint
- **Effort**: 5 hours

## Quick Wins (Under 4 hours)
1. Fix wildcard imports (2h)
2. Replace print statements (3h)
3. Add request correlation IDs (2h)
4. Enhance health checks (3h)

## Medium Effort (4-8 hours)
1. Improve exception handling (4h)
2. Async database operations (4h)
3. Input validation enhancement (6h)
4. Structured logging (6h)
5. API documentation (4h)

## Large Effort (8+ hours)
1. Database optimization (8h)
2. Comprehensive testing (16h)
3. Background job processing (12h)
4. Dependency injection enhancement (8h)

## Total Effort: 91 hours
- Week 1: 9 hours (Critical fixes)
- Week 2: 18 hours (Performance)
- Week 3: 26 hours (Quality)
- Week 4: 38 hours (Architecture/Monitoring)
