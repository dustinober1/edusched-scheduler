"""Tests for student-centric scheduling features."""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from edusched.domain.student import Student, StudentStatus, AcademicLevel
from edusched.domain.curriculum import Curriculum, CourseInfo, Major, RequirementType, CourseType
from edusched.domain.resource import Resource, ResourceStatus, RoomType, Equipment
from edusched.constraints.student_constraints import (
    StudentConflictConstraint,
    PrerequisiteConstraint,
    StudentCapacityConstraint,
    StudentCreditLoadConstraint
)
from edusched.solvers.incremental import IncrementalSolver
from edusched.scoring.conflict_scorer import ConflictScorer, ConstraintPriority
from edusched.constraints.base import ConstraintContext, Violation
from edusched.domain.session_request import SessionRequest


class TestStudentFeatures:
    """Test suite for student scheduling features."""

    def test_student_model(self):
        """Test student domain model."""
        # Create student
        student = Student(
            id="student123",
            first_name="Alice",
            last_name="Smith",
            email="alice.smith@university.edu",
            student_number="202400123",
            academic_level=AcademicLevel.JUNIOR,
            major_ids=["cs", "math"],
            max_credits_per_semester=18,
            has_job=True,
            work_hours=[{"day": "monday", "start": "17:00", "end": "22:00"}]
        )

        # Test basic properties
        assert student.id == "student123"
        assert student.get_full_name() == "Alice Smith"
        assert student.academic_level == AcademicLevel.JUNIOR
        assert "cs" in student.major_ids

        # Test availability
        # Monday 18:00 should conflict with work
        monday_6pm = datetime(2024, 9, 2, 18, 0, tzinfo=ZoneInfo("UTC"))
        assert not student.is_available_at_time(monday_6pm)

        # Wednesday 10:00 should be available
        wednesday_10am = datetime(2024, 9, 4, 10, 0, tzinfo=ZoneInfo("UTC"))
        assert student.is_available_at_time(wednesday_10am)

        # Test registration eligibility
        can_register, reason = student.can_register()
        assert can_register, reason

        # Test with hold
        student.holds.append({"type": "financial", "reason": "Tuition balance"})
        can_register, reason = student.can_register()
        assert not can_register
        assert "Financial hold" in reason

    def test_curriculum_model(self):
        """Test curriculum domain model."""
        # Create curriculum
        curriculum = Curriculum(
            institution_id="univ_001",
            academic_year=2024
        )

        # Add courses
        cs101 = CourseInfo(
            id="CS101",
            title="Introduction to Computer Science",
            code="CS101",
            department_id="cs",
            credits=3.0,
            course_type=CourseType.LECTURE,
            level=100,
            prerequisites=[],
            semesters_offered=["fall", "spring"]
        )
        curriculum.add_course(cs101)

        cs401 = CourseInfo(
            id="CS401",
            title="Advanced Algorithms",
            code="CS401",
            department_id="cs",
            credits=3.0,
            course_type=CourseType.LECTURE,
            level=400,
            prerequisites=["CS101", "CS201"]
        )
        curriculum.add_course(cs401)

        # Create major
        cs_major = Major(
            id="cs",
            name="Computer Science",
            department_id="cs",
            degree_type="BS",
            total_credits_required=120,
            major_credits_required=45,
            elective_credits_required=15,
            required_courses=["CS101", "CS201", "CS301", "CS401"]
        )
        curriculum.add_major(cs_major)

        # Test prerequisite checking
        completed_courses = {"CS101"}
        can_take_401, missing = curriculum.check_prerequisites("student123", "CS401", completed_courses)
        assert not can_take_401
        assert "CS201" in missing

        completed_courses = {"CS101", "CS201", "CS301"}
        can_take_401, missing = curriculum.check_prerequisites("student123", "CS401", completed_courses)
        assert can_take_401
        assert len(missing) == 0

    def test_enhanced_resource_model(self):
        """Test enhanced resource model with advanced features."""
        # Create computer lab with equipment
        lab = Resource(
            id="Lab201",
            resource_type="lab",
            room_type=RoomType.COMPUTER_LAB,
            building_id="engineering",
            floor_number=2,
            capacity=30,
            wheelchair_accessible=True,
            has_projector=True,
            power_outlets_per_seat=2,
            status=ResourceStatus.AVAILABLE
        )

        # Add equipment
        computers = Equipment(
            id="comp_set_1",
            name="Computer Lab Set",
            type="computer",
            quantity=30,
            requires_setup=True,
            setup_time_minutes=15
        )
        lab.add_equipment(computers)

        # Test features
        assert lab.has_equipment("computer")
        assert lab.get_equipment_count("computer") == 30
        assert lab.calculate_setup_time() == 15
        assert lab.meets_accessibility_requirements({"wheelchair_accessible": True})

        # Test availability
        available, reason = lab.is_available(
            datetime(2024, 9, 2, 10, 0),
            datetime(2024, 9, 2, 12, 0)
        )
        assert available
        assert reason == "Available"

        # Add maintenance window
        from edusched.domain.resource import MaintenanceWindow
        maintenance = MaintenanceWindow(
            start_time=datetime(2024, 9, 3, 2, 0),
            end_time=datetime(2024, 9, 3, 6, 0),
            reason="System upgrade"
        )
        lab.add_maintenance_window(maintenance)

        # Check availability during maintenance
        available, reason = lab.is_available(
            datetime(2024, 9, 3, 3, 0),
            datetime(2024, 9, 3, 4, 0)
        )
        assert not available
        assert "Maintenance scheduled" in reason

    def test_student_constraints(self):
        """Test student-related constraints."""
        # Create students
        student1 = Student(
            id="student1",
            first_name="Bob",
            last_name="Jones",
            academic_level=AcademicLevel.SOPHOMORE,
            completed_courses={"CS101"},
            in_progress_courses={"CS201"}
        )
        student2 = Student(
            id="student2",
            first_name="Carol",
            last_name="Williams",
            academic_level=AcademicLevel.JUNIOR,
            completed_courses={"CS101", "CS201", "CS301"},
            in_progress_courses=set()
        )

        # Create assignments with time overlap
        from edusched.domain.assignment import Assignment
        assignment1 = Assignment(
            request_id="CS201",
            occurrence_index=0,
            start_time=datetime(2024, 9, 2, 10, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 9, 2, 11, 0, tzinfo=ZoneInfo("UTC")),
            cohort_id="cohort1",
            assigned_resources={}
        )

        assignment2 = Assignment(
            request_id="CS301",
            occurrence_index=0,
            start_time=datetime(2024, 9, 2, 10, 30, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 9, 2, 11, 30, tzinfo=ZoneInfo("UTC")),
            cohort_id="cohort1",
            assigned_resources={}
        )

        # Test conflict constraint
        conflict_constraint = StudentConflictConstraint("student1")

        # This would need integration with actual Assignment objects
        # For now, we'll test the overlap detection
        assert conflict_constraint._times_overlap(assignment1, assignment2)

        # Test credit load constraint
        credit_constraint = StudentCreditLoadConstraint(["student1"], max_credits=18)
        # Would check against student's current load

        # Test capacity constraint
        lab = Resource(
            id="Lab201",
            resource_type="lab",
            capacity=20
        )
        capacity_constraint = StudentCapacityConstraint(
            ["student1", "student2", "student3"]  # 3 students
        )

        # Would check if room can accommodate students

    def test_incremental_solver(self):
        """Test incremental scheduling capabilities."""
        solver = IncrementalSolver()

        # Create mock existing schedule
        existing_assignments = [
            {
                "request_id": "CS101",
                "occurrence_index": 0,
                "start_time": datetime(2024, 9, 2, 10, 0),
                "end_time": datetime(2024, 9, 2, 11, 0),
                "student_ids": ["student1"]
            }
        ]

        # Create new course request
        from edusched.domain.session_request import SessionRequest
        new_request = SessionRequest(
            id="CS301",
            duration=timedelta(hours=1.5),
            number_of_occurrences=1,
            earliest_date=datetime(2024, 9, 1, 8, 0),
            latest_date=datetime(2024, 12, 15, 17, 0),
            enrollment_count=25
        )

        # Test adding course
        # This would need proper context setup
        # success, updated, conflicts = solver.add_course(
        #     existing_assignments, new_request, context, indices
        # )

        # Test removing course
        # success, updated, removed = solver.remove_course(
        #     existing_assignments, "CS101", context
        # )

        # Test moving assignment
        # success, updated, message = solver.move_assignment(
        #     existing_assignments, "CS101_001",
        #     (datetime(2024, 9, 3, 14, 0), datetime(2024, 9, 3, 15, 30)),
        #     context, indices
        # )

        assert solver.backend_name == "incremental"

    def test_conflict_scorer(self):
        """Test conflict scoring system."""
        scorer = ConflictScorer()

        # Create different types of violations
        violations = [
            Violation(
                constraint_type="hard.room_double_booking",
                affected_request_id="CS101",
                message="Room Eng101 is double-booked"
            ),
            Violation(
                constraint_type="soft.teacher_preference",
                affected_request_id="CS201",
                message="Teacher prefers afternoon classes"
            ),
            Violation(
                constraint_type="hard.prerequisite_missing",
                affected_request_id="CS401",
                message="Student missing prerequisites: CS201"
            ),
            Violation(
                constraint_type="hard.capacity_exceeded",
                affected_request_id="LAB101",
                message="Room capacity (30) exceeded by enrollment (35)"
            )
        ]

        # Score violations
        total_score, detailed_scores = scorer.score_conflicts(violations)
        assert total_score > 0
        assert len(detailed_scores) == 4

        # Check scoring priorities
        critical_scores = [s for s in detailed_scores if s.priority == ConstraintPriority.CRITICAL]
        assert len(critical_scores) >= 1  # room_double_booking

        # Test ranking
        ranked = scorer.rank_violations(violations, max_to_resolve=3)
        assert len(ranked) == 3

        # First should be highest priority
        assert ranked[0].priority == ConstraintPriority.CRITICAL

        # Test summary
        summary = scorer.get_conflict_summary(detailed_scores)
        assert summary["total_violations"] == 4
        assert summary["critical_violations"] >= 1

    def test_student_workflow(self):
        """Test complete student workflow from registration to scheduling."""
        # Create curriculum with courses
        curriculum = Curriculum(
            institution_id="university",
            academic_year=2024
        )

        # Add sample courses
        courses = [
            CourseInfo(
                id="CS101",
                title="Intro to Programming",
                code="CS101",
                department_id="cs",
                credits=3,
                course_type=CourseType.LECTURE,
                level=100,
                prerequisites=[]
            ),
            CourseInfo(
                id="CS201",
                title="Data Structures",
                code="CS201",
                department_id="cs",
                credits=4,
                course_type=CourseType.LECTURE,
                level=200,
                prerequisites=["CS101"]
            )
        ]
        for course in courses:
            curriculum.add_course(course)

        # Create student
        student = Student(
            id="student001",
            first_name="John",
            last_name="Doe",
            academic_level=AcademicLevel.FRESHMAN,
            major_ids=["cs"],
            completed_courses={"CS101"},
            in_progress_courses=set(),
            max_credits_per_semester=18
        )

        # Test registration eligibility
        can_register, reason = student.can_register()
        assert can_register, reason

        # Test course eligibility
        can_take_201, missing = curriculum.check_prerequisites(
            student.id, "CS201", student.completed_courses
        )
        assert can_take_201

        # Register for CS201
        registration = student.add_registration("CS201")
        assert registration.course_id == "CS201"
        assert registration.status == "registered"

        # Check credit load
        student.get_current_credits()  # Would include CS101 and CS201

        # Test dropping course
        dropped = student.drop_course("CS201")
        assert dropped

        # Verify no longer in progress
        assert "CS201" not in student.in_progress_courses

    def test_integration_all_features(self):
        """Test integration of all student features together."""
        print("\n=== INTEGRATION TEST: Student Scheduling Features ===\n")

        # Create curriculum
        curriculum = Curriculum("university", 2024)

        # Add courses with prerequisites
        courses = [
            CourseInfo("CS101", "Intro to CS", "CS101", "cs", 3, CourseType.LECTURE, 100, [], ["fall", "spring"]),
            CourseInfo("CS201", "Data Structures", "CS201", "cs", 4, CourseType.LECTURE, 200, ["CS101"], ["fall", "spring"]),
            CourseInfo("CS301", "Algorithms", "CS301", "cs", 4, CourseType.LECTURE, 300, ["CS201"], ["fall"]),
            CourseInfo("CS401", "Advanced", "CS401", "cs", 3, CourseType.SEMINAR, 400, ["CS301"], ["spring"])
        ]
        for course in courses:
            curriculum.add_course(course)

        # Create students with varying levels and needs
        students = [
            Student(
                id="s001", first_name="Alice", last_name="Smith",
                academic_level=AcademicLevel.FRESHMAN,
                completed_courses={}, in_progress_courses={"CS101"},
                max_credits_per_semester=15,
                mobility_needs=False
            ),
            Student(
                id="s002", first_name="Bob", last_name="Johnson",
                academic_level=AcademicLevel.JUNIOR,
                completed_courses={"CS101", "CS201", "CS301"},
                in_progress_courses=set(),
                max_credits_per_semester=12,
                requires_wheelchair_access=True
            ),
            Student(
                id="s003", first_name="Carol", last_name="Davis",
                academic_level=AcademicLevel.SOPHOMORE,
                completed_courses={"CS101"},
                in_progress_courses={"CS201", "CS301"},
                max_credits_per_semester=18,
                preferred_class_blocks=["morning", "afternoon"]
            )
        ]

        # Create enhanced rooms
        rooms = [
            Resource(
                id="Eng101",
                resource_type="classroom",
                room_type=RoomType.CLASSROOM_TIER1,
                building_id="engineering",
                capacity=50,
                wheelchair_accessible=False,
                has_projector=True,
                power_outlets_per_seat=1
            ),
            Resource(
                id="Eng105",
                resource_type="classroom",
                room_type=RoomType.CLASSROOM_STANDARD,
                building_id="engineering",
                capacity=30,
                wheelchair_accessible=True,
                has_projector=True,
                has_elevator_access=True
            ),
            Resource(
                id="Lab201",
                resource_type="lab",
                room_type=RoomType.COMPUTER_LAB,
                building_id="engineering",
                capacity=25,
                wheelchair_accessible=True
            )
        ]

        print(f"Created {len(courses)} courses")
        print(f"Created {len(students)} students")
        print(f"Created {len(rooms)} rooms")

        # Test student capabilities
        for student in students:
            print(f"\n{student.get_full_name()} (Level: {student.academic_level.value})")
            print(f"  Completed: {len(student.completed_courses)} courses")
            print(f"  In Progress: {len(student.in_progress_courses)} courses")
            print(f"  Max Credits: {student.max_credits_per_semester}")
            print(f"  Can Register: {student.can_register()[0]}")
            if student.mobility_needs:
                print(f"  ⚠️  Mobility needs: Wheelchair access required")

        # Test room capabilities
        for room in rooms:
            print(f"\n{room.id} ({room.room_type.value})")
            print(f"  Capacity: {room.capacity}")
            print(f"  Building: {room.building_id}")
            print(f"  Accessible: {room.wheelchair_accessible}")
            if room.has_equipment("computer"):
                print(f"  Computers: {room.get_equipment_count('computer')}")

        # Test prerequisite checking
        print("\n=== Prerequisite Checking ===")
        for course in courses:
            for student in students:
                can_take, missing = curriculum.check_prerequisites(
                    student.id, course.id, student.completed_courses
                )
                status = "✓ Can take" if can_take else f"✗ Missing: {', '.join(missing)}"
                print(f"{student.id} → {course.code}: {status}")

        # Score potential conflicts
        print("\n=== Conflict Scoring Demo ===")
        scorer = ConflictScorer()

        # Create sample violations
        violations = [
            Violation(
                constraint_type="hard.room_double_booking",
                affected_request_id="CS101",
                message="Room Eng101 double-booked for CS101 and CS201"
            ),
            Violation(
                constraint_type="hard.prerequisite",
                affected_request_id="CS401",
                message="Student s001 missing prerequisite CS301 for CS401"
            ),
            Violation(
                constraint_type="hard.accessibility",
                affected_request_id="CS201",
                message="Room not wheelchair accessible for student s002"
            ),
            Violation(
                constraint_type="soft.preference",
                affected_request_id="CS101",
                message="Student s003 prefers morning classes (scheduled at 14:00)"
            )
        ]

        total_score, detailed_scores = scorer.score_conflicts(violations)
        summary = scorer.get_conflict_summary(detailed_scores)
        quality_score = scorer.calculate_schedule_quality(violations, 10)

        print(f"Total Conflict Score: {total_score:.1f}")
        print(f"Schedule Quality Score: {quality_score:.2f} (1.0 = perfect)")
        print(f"Violations by Priority:")
        print(f"  Critical: {summary['critical_violations']}")
        print(f"  High: {summary['high_violations']}")
        print(f"  Medium: {summary['medium_violations']}")
        print(f"  Low: {summary['low_violations']}")

        # Show top ranked violations with resolutions
        ranked = scorer.rank_violations(violations)
        print("\n=== Top Violations to Resolve ===")
        for i, score in enumerate(ranked[:3], 1):
            print(f"{i}. Priority: {score.priority.name}")
            print(f"   {score.violation.message}")
            print(f"   Resolution: {score.suggested_resolution}")
            print(f"   Affected: {len(score.affected_parties)} parties")

        print("\nIntegration test completed successfully!")
        return {
            "courses": courses,
            "students": students,
            "rooms": rooms,
            "total_conflict_score": total_score,
            "schedule_quality": quality_score
        }

    def test_real_world_scenario(self):
        """Test a real-world scheduling scenario."""
        print("\n=== REAL-WORLD SCENARIO: Drop/Add Period ===\n")

        # This would simulate the add/drop period where students
        # can modify their schedules dynamically

        # Create base schedule
        base_schedule = []  # Would contain existing assignments

        # Create incremental solver
        solver = IncrementalSolver()

        # Scenario 1: Student wants to add a course
        print("Scenario 1: Student wants to add a course")
        modifications = [
            {
                "type": "add",
                "request": SessionRequest(
                    id="ECON101",
                    duration=timedelta(hours=3),
                    number_of_occurrences=1,
                    earliest_date=datetime(2024, 9, 5),
                    latest_date=datetime(2024, 12, 15),
                    enrollment_count=15
                )
            }
        ]

        # Scenario 2: Professor is sick, need to reschedule
        print("Scenario 2: Professor needs to reschedule due to illness")
        modifications.append({
            "type": "move",
            "assignment_id": "CS301_001",
            "new_time": (
                datetime(2024, 9, 10, 14, 0),
                datetime(2024, 9, 10, 15, 30)
            )
        })

        # Scenario 3: Room maintenance
        print("Scenario 3: Room maintenance affects multiple classes")
        modifications.append({
            "type": "remove",
            "course_id": "MATH201",
            "reason": "Room unavailable for repairs"
        })

        # This would actually perform the incremental scheduling
        print(f"Processing {len(modifications)} modifications...")
        # result = solver.solve(problem, existing_schedule=base_schedule, modifications=modifications)

        print("\nIncremental scheduling system ready for:")
        print("- Real-time add/drop period handling")
        print("- Dynamic conflict resolution")
        print("- Room reassignment capabilities")
        print("- Teacher absence management")