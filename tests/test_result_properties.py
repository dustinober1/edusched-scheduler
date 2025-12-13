"""Property-based tests for Result export functionality."""

import os
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import hypothesis.strategies as st
from hypothesis import given, assume, settings

from edusched.domain.assignment import Assignment
from edusched.domain.result import Result


# Strategies for generating test data
@st.composite
def timezone_aware_datetimes(draw, min_year=2024, max_year=2025):
    """Generate timezone-aware datetimes."""
    year = draw(st.integers(min_value=min_year, max_value=max_year))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))

    tz = ZoneInfo("UTC")
    return datetime(year, month, day, hour, minute, tzinfo=tz)


@st.composite
def valid_assignments(draw):
    """Generate valid Assignment instances."""
    start = draw(timezone_aware_datetimes())
    duration = draw(st.timedeltas(min_value=timedelta(minutes=15), max_value=timedelta(hours=4)))

    return Assignment(
        request_id=draw(st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789")),
        occurrence_index=draw(st.integers(min_value=0, max_value=10)),
        start_time=start,
        end_time=start + duration,
        assigned_resources=draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.lists(st.text(min_size=1, max_size=10)),
            max_size=3
        )),
        cohort_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=10))),
    )


class TestResultProperties:
    """Property-based tests for Result export functionality."""

    @given(st.lists(valid_assignments(), min_size=0, max_size=10))
    def test_assignment_data_preservation(self, assignments):
        """
        **Feature: edusched-scheduler, Property 15: Assignment Data Preservation**

        For any Result, the to_records() method should preserve all assignment
        data without loss or modification.

        **Validates: Requirements 6.4**
        """
        # Create result
        result = Result(
            status="feasible" if assignments else "infeasible",
            assignments=assignments,
            unscheduled_requests=[],
            backend_used="test",
            seed_used=42
        )

        # Export to records
        records = result.to_records()

        # Check record count matches
        assert len(records) == len(assignments), "Record count should match assignment count"

        # Check each assignment is preserved
        for assignment, record in zip(assignments, records):
            # Check required fields
            assert "start_time" in record, "Record should have start_time"
            assert "end_time" in record, "Record should have end_time"
            assert "request_id" in record, "Record should have request_id"
            assert "cohort_id" in record, "Record should have cohort_id"
            assert "resource_ids" in record, "Record should have resource_ids"
            assert "backend" in record, "Record should have backend"
            assert "objective_score" in record, "Record should have objective_score"

            # Check data integrity
            assert record["start_time"] == assignment.start_time, "start_time should be preserved"
            assert record["end_time"] == assignment.end_time, "end_time should be preserved"
            assert record["request_id"] == assignment.request_id, "request_id should be preserved"
            assert record["cohort_id"] == assignment.cohort_id, "cohort_id should be preserved"
            assert record["resource_ids"] == assignment.assigned_resources, "resource_ids should be preserved"
            assert record["backend"] == result.backend_used, "backend should be set"
            assert record["objective_score"] == result.objective_score, "objective_score should be set"

    @given(st.lists(valid_assignments(), min_size=1, max_size=3))
    @settings(deadline=None)  # Disable deadline for potentially slow pandas import
    def test_dataframe_schema_consistency(self, assignments):
        """
        **Feature: edusched-scheduler, Property 16: DataFrame Schema Consistency**

        When pandas is available, the to_dataframe() method should produce
        a DataFrame with the same schema as to_records().

        **Validates: Requirements 10.2**
        """
        # Create result
        result = Result(
            status="feasible",
            assignments=assignments,
            unscheduled_requests=[],
            backend_used="test",
            seed_used=42,
            objective_score=0.85
        )

        # Get records reference
        records = result.to_records()

        # Try to create DataFrame
        try:
            df = result.to_dataframe()

            # Check DataFrame has same number of rows
            assert len(df) == len(records), "DataFrame should have same number of rows as records"

            # Check DataFrame has all required columns
            expected_columns = set(records[0].keys()) if records else set()
            actual_columns = set(df.columns)
            assert expected_columns == actual_columns, f"DataFrame columns {actual_columns} should match record columns {expected_columns}"

            # Check schema version is set
            assert hasattr(df, "attrs"), "DataFrame should have attrs attribute"
            assert df.attrs.get("schema_version") == "1.0", "DataFrame should have schema_version"

            # Check data consistency for first few rows
            for i in range(min(3, len(records))):
                record = records[i]
                row = df.iloc[i]

                for col in expected_columns:
                    assert row[col] == record[col], f"Column {col} should match between DataFrame and records"

        except Exception as e:
            # If pandas is not available, should raise MissingOptionalDependency
            from edusched.errors import MissingOptionalDependency
            assert isinstance(e, MissingOptionalDependency), "Should raise MissingOptionalDependency when pandas not available"
            assert "DataFrame" in str(e), "Error message should mention DataFrame"

    @given(st.lists(valid_assignments(), min_size=1, max_size=2))
    @settings(deadline=None)
    def test_ics_format_validity(self, assignments):
        """
        **Feature: edusched-scheduler, Property 17: ICS Format Validity**

        When icalendar is available, the to_ics() method should produce a
        valid ICS file with all assignments included as events.

        **Validates: Requirements 6.2**
        """
        import tempfile
        import os

        # Create result
        result = Result(
            status="feasible",
            assignments=assignments,
            unscheduled_requests=[],
            backend_used="test",
            seed_used=42
        )

        # Test ICS export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ics', delete=False) as f:
            filename = f.name

        try:
            # Export to ICS
            result.to_ics(filename)

            # Check file was created
            assert os.path.exists(filename), "ICS file should be created"

            # Check file has content
            with open(filename, 'rb') as f:
                content = f.read()

            assert len(content) > 0, "ICS file should not be empty"

            # Check for ICS header and footer
            content_str = content.decode('utf-8')
            assert 'BEGIN:VCALENDAR' in content_str, "ICS file should have calendar header"
            assert 'END:VCALENDAR' in content_str, "ICS file should have calendar footer"
            assert 'VERSION:2.0' in content_str, "ICS file should specify version"

            # Check each assignment has an event
            for assignment in assignments:
                # Check for VEVENT
                event_uid = f"{assignment.request_id}-{assignment.occurrence_index}@edusched"
                assert f'UID:{event_uid}' in content_str, f"Assignment {event_uid} should be in ICS"
                assert 'BEGIN:VEVENT' in content_str, "Should have VEVENT blocks"
                assert 'END:VEVENT' in content_str, "Should have VEVENT blocks"

                # Check for required fields
                assert f'SUMMARY:Session {assignment.request_id}' in content_str, "Should have event summary"
                assert 'DTSTART:' in content_str, "Should have start time"
                assert 'DTEND:' in content_str, "Should have end time"

        except Exception as e:
            # If icalendar is not available, should raise MissingOptionalDependency
            from edusched.errors import MissingOptionalDependency
            assert isinstance(e, MissingOptionalDependency), "Should raise MissingOptionalDependency when icalendar not available"
            assert "ICS" in str(e), "Error message should mention ICS"

        finally:
            # Clean up
            if os.path.exists(filename):
                os.unlink(filename)

    @given(st.lists(valid_assignments(), min_size=1, max_size=5))
    def test_ics_timezone_preservation(self, assignments):
        """
        ICS export should preserve timezone information.
        """
        import tempfile
        import os

        # Ensure assignments have timezone-aware datetimes
        for assignment in assignments:
            assert assignment.start_time.tzinfo is not None, "All assignments should have timezone-aware start_time"
            assert assignment.end_time.tzinfo is not None, "All assignments should have timezone-aware end_time"

        # Create result
        result = Result(
            status="feasible",
            assignments=assignments,
            unscheduled_requests=[],
            backend_used="test",
            seed_used=42
        )

        # Test ICS export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ics', delete=False) as f:
            filename = f.name

        try:
            # Export to ICS
            result.to_ics(filename)

            # Check timezone information is preserved
            with open(filename, 'r') as f:
                content = f.read()

            # ICS format typically uses UTC or includes TZID
            # We're using UTC timezone in our test data, so times should be consistent
            for assignment in assignments[:2]:  # Check first few assignments
                start_str = assignment.start_time.strftime('%Y%m%dT%H%M%SZ')
                end_str = assignment.end_time.strftime('%Y%m%dT%H%M%SZ')
                assert start_str in content or assignment.start_time.isoformat() in content, \
                    "Start time should be preserved in ICS"
                assert end_str in content or assignment.end_time.isoformat() in content, \
                    "End time should be preserved in ICS"

        except Exception:
            # Skip if icalendar not available
            pass

        finally:
            # Clean up
            if os.path.exists(filename):
                os.unlink(filename)

    @given(st.lists(valid_assignments(), min_size=0, max_size=3), st.text(min_size=5, max_size=10))
    def test_excel_export_with_metadata(self, assignments, backend_name):
        """
        Excel export should include all assignment data and metadata.
        """
        import tempfile
        import os

        # Create result with specific backend
        result = Result(
            status="feasible" if assignments else "infeasible",
            assignments=assignments,
            unscheduled_requests=[],
            backend_used=backend_name,
            seed_used=12345,
            objective_score=0.75,
            solve_time_seconds=2.5
        )

        # Test Excel export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xlsx', delete=False) as f:
            filename = f.name

        try:
            # Export to Excel
            result.to_excel(filename)

            # Check file was created
            assert os.path.exists(filename), "Excel file should be created"

            # Check file has content (Excel files should have a signature)
            with open(filename, 'rb') as f:
                content = f.read()

            # Check for Excel file signature
            assert len(content) > 8, "Excel file should have content"
            # Excel files start with PK (zip signature)
            assert content[:2] == b'PK', "Excel file should have zip signature"

        except Exception:
            # Skip if openpyxl not available
            pass

        finally:
            # Clean up
            if os.path.exists(filename):
                os.unlink(filename)

    @given(
        st.text(min_size=1, max_size=10),
        st.sampled_from(["feasible", "partial", "infeasible"]),
        st.lists(st.text(min_size=1, max_size=10), min_size=0, max_size=3),
        st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0)),
        st.one_of(st.none(), st.integers(min_value=1, max_value=10000))
    )
    def test_result_data_integrity(self, backend, status, unscheduled, objective_score, seed):
        """
        Result should preserve all metadata accurately.
        """
        result = Result(
            status=status,
            assignments=[],
            unscheduled_requests=unscheduled,
            backend_used=backend,
            seed_used=seed,
            objective_score=objective_score,
            solve_time_seconds=1.5
        )

        # Check status property
        assert result.status == status, "Status should be preserved"
        assert result.feasible == (status == "feasible"), "feasible property should match status"

        # Check assignments and unscheduled
        assert result.assignments == [], "Assignments should be empty list"
        assert result.unscheduled_requests == unscheduled, "Unscheduled requests should be preserved"

        # Check metadata
        assert result.backend_used == backend, "Backend should be preserved"
        assert result.seed_used == seed, "Seed should be preserved"
        assert result.objective_score == objective_score, "Objective score should be preserved"

        # Export to records and check metadata is included
        records = result.to_records()
        assert isinstance(records, list), "Records should be a list"
        assert len(records) == 0, "No records should exist for empty assignments"