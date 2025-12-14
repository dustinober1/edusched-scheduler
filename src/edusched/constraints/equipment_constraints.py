"""Equipment-related constraints for scheduling.

Ensures equipment availability, tracks reservations,
prevents double bookings, and manages maintenance schedules.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, List, Optional

from edusched.constraints.base import Constraint, ConstraintContext, Violation

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment
    from edusched.domain.equipment import EquipmentInventory


class EquipmentAvailabilityConstraint(Constraint):
    """Ensures required equipment is available for sessions."""

    def __init__(
        self,
        equipment_inventory: "EquipmentInventory",
        violation_penalty: float = 1000.0,
    ):
        """
        Initialize equipment availability constraint.

        Args:
            equipment_inventory: Equipment inventory manager
            violation_penalty: Penalty for equipment conflicts
        """
        super().__init__("equipment_availability", violation_penalty)
        self.equipment_inventory = equipment_inventory

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if required equipment is available."""
        # Get session request
        request = context.request_lookup.get(assignment.request_id)
        if not request or not request.equipment_requirements:
            return None

        # Get session time window
        session_start = assignment.start_time
        session_end = session_start + timedelta(minutes=float(request.duration))
        session_id = str(assignment.id)

        # Check each equipment requirement
        for requirement in request.equipment_requirements:
            available_ids = self.equipment_inventory.get_available_equipment(
                equipment_type_id=requirement.equipment_type_id,
                start_time=session_start,
                end_time=session_end,
                quantity=requirement.quantity,
            )

            if len(available_ids) < requirement.quantity and not requirement.optional:
                return Violation(
                    constraint=self,
                    assignment=assignment,
                    message=(
                        f"Insufficient equipment available: "
                        f"need {requirement.quantity} of type {requirement.equipment_type_id}, "
                        f"only {len(available_ids)} available for session {session_id}"
                    ),
                    details={
                        "equipment_type": requirement.equipment_type_id,
                        "required_quantity": requirement.quantity,
                        "available_quantity": len(available_ids),
                        "session_id": session_id,
                        "session_start": session_start.isoformat(),
                        "session_end": session_end.isoformat(),
                    },
                )

        return None


class EquipmentReservationConstraint(Constraint):
    """Manages equipment reservations and prevents conflicts."""

    def __init__(
        self,
        equipment_inventory: "EquipmentInventory",
        allow_overbooking: bool = False,
        violation_penalty: float = 800.0,
    ):
        """
        Initialize equipment reservation constraint.

        Args:
            equipment_inventory: Equipment inventory manager
            allow_overbooking: Allow double booking for optional equipment
            violation_penalty: Penalty for reservation conflicts
        """
        super().__init__("equipment_reservation", violation_penalty)
        self.equipment_inventory = equipment_inventory
        self.allow_overbooking = allow_overbooking

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check for reservation conflicts with existing assignments."""
        # Get session request
        request = context.request_lookup.get(assignment.request_id)
        if not request or not request.equipment_requirements:
            return None

        # Get session time window
        session_start = assignment.start_time
        session_end = session_start + timedelta(minutes=float(request.duration))
        str(assignment.id)
        room_id = str(assignment.resource.id)

        # Check against other assignments
        for other_assignment in solution:
            if other_assignment.id == assignment.id:
                continue

            other_request = context.request_lookup.get(other_assignment.request_id)
            if not other_request or not other_request.equipment_requirements:
                continue

            # Check time overlap
            other_start = other_assignment.start_time
            other_end = other_start + timedelta(minutes=float(other_request.duration))

            if self._times_overlap(session_start, session_end, other_start, other_end):
                # Check for equipment conflicts
                conflicts = self._check_equipment_conflicts(
                    request.equipment_requirements,
                    other_request.equipment_requirements,
                    room_id,
                    str(other_assignment.resource.id),
                )

                if conflicts:
                    return Violation(
                        constraint=self,
                        assignment=assignment,
                        message=(
                            f"Equipment reservation conflict with session {other_assignment.id}: "
                            f"{', '.join(conflicts)}"
                        ),
                        details={
                            "conflicting_session_id": str(other_assignment.id),
                            "conflicting_equipment": conflicts,
                            "session_overlap": f"{session_start} - {session_end}",
                        },
                    )

        return None

    def _times_overlap(
        self,
        start1: datetime,
        end1: datetime,
        start2: datetime,
        end2: datetime,
    ) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and start2 < end1

    def _check_equipment_conflicts(
        self,
        req1_equipment: List,
        req2_equipment: List,
        room1_id: str,
        room2_id: str,
    ) -> List[str]:
        """Check for equipment conflicts between two requirements."""
        conflicts = []

        # Create equipment type to quantity maps
        req1_map = {}
        for req in req1_equipment:
            if not req.optional:
                req1_map[req.equipment_type_id] = (
                    req1_map.get(req.equipment_type_id, 0) + req.quantity
                )

        req2_map = {}
        for req in req2_equipment:
            if not req.optional:
                req2_map[req.equipment_type_id] = (
                    req2_map.get(req.equipment_type_id, 0) + req.quantity
                )

        # Check for conflicts in same room (can't share)
        if room1_id == room2_id:
            for equipment_type, _quantity in req1_map.items():
                if equipment_type in req2_map:
                    # Equipment in same room can't be shared
                    conflicts.append(f"{equipment_type} (same room conflict)")

        return conflicts


class EquipmentMaintenanceConstraint(Constraint):
    """Prevents scheduling during equipment maintenance windows."""

    def __init__(
        self,
        equipment_inventory: "EquipmentInventory",
        violation_penalty: float = 1500.0,
    ):
        """
        Initialize equipment maintenance constraint.

        Args:
            equipment_inventory: Equipment inventory manager
            violation_penalty: Penalty for maintenance conflicts
        """
        super().__init__("equipment_maintenance", violation_penalty)
        self.equipment_inventory = equipment_inventory

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if any required equipment is under maintenance."""
        # Get session request
        request = context.request_lookup.get(assignment.request_id)
        if not request or not request.equipment_requirements:
            return None

        # Get session time window
        session_start = assignment.start_time
        session_end = session_start + timedelta(minutes=float(request.duration))
        session_id = str(assignment.id)

        # Check maintenance windows for each equipment type
        for requirement in request.equipment_requirements:
            if requirement.optional:
                continue

            maintenance_conflicts = self._check_maintenance_conflicts(
                requirement.equipment_type_id,
                session_start,
                session_end,
            )

            if maintenance_conflicts:
                return Violation(
                    constraint=self,
                    assignment=assignment,
                    message=(
                        f"Equipment maintenance conflict for type {requirement.equipment_type_id}: "
                        f"{', '.join(maintenance_conflicts)}"
                    ),
                    details={
                        "equipment_type": requirement.equipment_type_id,
                        "maintenance_windows": maintenance_conflicts,
                        "session_id": session_id,
                    },
                )

        return None

    def _check_maintenance_conflicts(
        self,
        equipment_type_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[str]:
        """Check for maintenance conflicts."""
        conflicts = []
        upcoming_maintenance = self.equipment_inventory.get_maintenance_schedule(days_ahead=365)

        for maintenance in upcoming_maintenance:
            if maintenance.equipment_id.startswith(equipment_type_id):
                # Check time overlap
                if self._times_overlap(
                    maintenance.start_time, maintenance.end_time, start_time, end_time
                ):
                    conflicts.append(
                        f"{maintenance.equipment_id}: {maintenance.start_time} - {maintenance.end_time} "
                        f"({maintenance.maintenance_type})"
                    )

        return conflicts

    def _times_overlap(
        self,
        start1: datetime,
        end1: datetime,
        start2: datetime,
        end2: datetime,
    ) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and start2 < end1


class EquipmentSetupConstraint(Constraint):
    """Ensures sufficient time for equipment setup and teardown."""

    def __init__(
        self,
        equipment_inventory: "EquipmentInventory",
        violation_penalty: float = 500.0,
    ):
        """
        Initialize equipment setup constraint.

        Args:
            equipment_inventory: Equipment inventory manager
            violation_penalty: Penalty for setup time violations
        """
        super().__init__("equipment_setup", violation_penalty)
        self.equipment_inventory = equipment_inventory

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if there's sufficient setup/teardown time."""
        # Get session request
        request = context.request_lookup.get(assignment.request_id)
        if not request or not request.equipment_requirements:
            return None

        session_id = str(assignment.id)
        room_id = str(assignment.resource.id)

        # Calculate required setup time
        total_setup_time = 0
        for requirement in request.equipment_requirements:
            if requirement.setup_time_minutes > 0:
                total_setup_time = max(total_setup_time, requirement.setup_time_minutes)

        if total_setup_time == 0:
            return None

        # Check if room is available before session for setup
        setup_start = assignment.start_time - timedelta(minutes=total_setup_time)
        if setup_start < datetime.now():
            # Can't setup in the past
            return Violation(
                constraint=self,
                assignment=assignment,
                message=(
                    f"Insufficient setup time for session {session_id}: "
                    f"need {total_setup_time} minutes before {assignment.start_time}"
                ),
                details={
                    "required_setup_minutes": total_setup_time,
                    "session_start": assignment.start_time.isoformat(),
                    "setup_needed_by": setup_start.isoformat(),
                },
            )

        # Check for conflicts with previous assignments
        for other_assignment in solution:
            if other_assignment.id == assignment.id:
                continue

            if str(other_assignment.resource.id) != room_id:
                continue

            other_end = other_assignment.start_time + timedelta(
                minutes=float(context.request_lookup[other_assignment.request_id].duration)
            )

            # Check if setup time conflicts
            if other_end > setup_start and other_end < assignment.start_time:
                return Violation(
                    constraint=self,
                    assignment=assignment,
                    message=(
                        f"Setup time conflict with session {other_assignment.id}: "
                        f"need {total_setup_time} minutes before session {session_id}"
                    ),
                    details={
                        "conflicting_session_id": str(other_assignment.id),
                        "conflicting_session_end": other_end.isoformat(),
                        "required_setup_minutes": total_setup_time,
                        "setup_start": setup_start.isoformat(),
                    },
                )

        return None


class EquipmentCertificationConstraint(Constraint):
    """Ensures users are certified to operate required equipment."""

    def __init__(
        self,
        equipment_inventory: "EquipmentInventory",
        violation_penalty: float = 2000.0,
    ):
        """
        Initialize equipment certification constraint.

        Args:
            equipment_inventory: Equipment inventory manager
            violation_penalty: Penalty for certification violations
        """
        super().__init__("equipment_certification", violation_penalty)
        self.equipment_inventory = equipment_inventory

    def check(
        self,
        assignment: "Assignment",
        solution: list["Assignment"],
        context: ConstraintContext,
    ) -> Optional[Violation]:
        """Check if user is certified for required equipment."""
        # Get session request
        request = context.request_lookup.get(assignment.request_id)
        if not request or not request.equipment_requirements:
            return None

        # Get user info from request or context
        user_id = getattr(request, "user_id", None) or getattr(assignment, "user_id", None)
        if not user_id:
            return None  # Can't check without user ID

        session_id = str(assignment.id)
        uncertified = []

        # Check each equipment requirement
        for requirement in request.equipment_requirements:
            if requirement.optional:
                continue

            # Get equipment type
            equipment_type = self.equipment_inventory.equipment_types.get(
                requirement.equipment_type_id
            )
            if not equipment_type or not equipment_type.requires_certification:
                continue

            # Check if user has any certified equipment of this type
            certified_equipment = self.equipment_inventory.get_equipment_requiring_certification(
                user_id
            )
            has_certification = any(
                eq
                for eq in certified_equipment
                if eq.equipment_type_id == requirement.equipment_type_id
            )

            if not has_certification:
                uncertified.append(requirement.equipment_type_id)

        if uncertified:
            return Violation(
                constraint=self,
                assignment=assignment,
                message=(
                    f"User {user_id} not certified for equipment: {', '.join(uncertified)} "
                    f"in session {session_id}"
                ),
                details={
                    "user_id": user_id,
                    "uncertified_equipment": uncertified,
                    "session_id": session_id,
                },
            )

        return None


@dataclass
class EquipmentUsage:
    """Tracks equipment usage statistics."""

    equipment_type_id: str
    equipment_id: str
    usage_count: int = 0
    total_usage_hours: float = 0.0
    maintenance_count: int = 0
    last_used: Optional[datetime] = None
    utilization_rate: float = 0.0


class EquipmentUsageTracker:
    """Tracks and analyzes equipment usage patterns."""

    def __init__(self, equipment_inventory: "EquipmentInventory"):
        self.equipment_inventory = equipment_inventory
        self.usage_history: Dict[str, List[EquipmentUsage]] = {}

    def record_usage(
        self,
        equipment_id: str,
        session_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        """Record equipment usage for a session."""
        # Get equipment info
        equipment = self.equipment_inventory.equipment.get(equipment_id)
        if not equipment:
            return

        # Create usage record
        usage = EquipmentUsage(
            equipment_type_id=equipment.equipment_type_id,
            equipment_id=equipment_id,
            usage_count=1,
            total_usage_hours=(end_time - start_time).total_seconds() / 3600,
            last_used=end_time,
        )

        # Add to history
        if equipment_id not in self.usage_history:
            self.usage_history[equipment_id] = []
        self.usage_history[equipment_id].append(usage)

    def get_equipment_efficiency(self, equipment_id: str) -> float:
        """Calculate equipment efficiency metric."""
        usage_records = self.usage_history.get(equipment_id, [])
        if not usage_records:
            return 0.0

        # Simple efficiency: usage count / total available time
        equipment = self.equipment_inventory.equipment.get(equipment_id)
        if not equipment:
            return 0.0

        # Calculate utilization
        now = datetime.now()
        days_since_purchase = (now - (equipment.purchase_date or now)).days or 1
        total_hours = days_since_purchase * 24

        used_hours = sum(record.total_usage_hours for record in usage_records)
        return min(100.0, (used_hours / total_hours * 100))

    def get_underutilized_equipment(self, threshold: float = 20.0) -> List[str]:
        """Get equipment with utilization below threshold."""
        underutilized = []
        for equipment_id in self.equipment_inventory.equipment:
            efficiency = self.get_equipment_efficiency(equipment_id)
            if efficiency < threshold:
                underutilized.append(equipment_id)
        return underutilized

    def suggest_maintenance(self, usage_threshold: int = 100) -> List[str]:
        """Suggest maintenance based on usage count."""
        suggestions = []
        for equipment_id, records in self.usage_history.items():
            total_usage = sum(record.usage_count for record in records)
            if total_usage >= usage_threshold:
                suggestions.append(equipment_id)
        return suggestions
