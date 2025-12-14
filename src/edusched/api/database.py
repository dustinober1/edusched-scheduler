"""In-memory database for schedule persistence.

For Phase 2, we use an in-memory database.
In later phases, this would be replaced with a proper database
like PostgreSQL or MongoDB.
"""

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from edusched.api.models import AssignmentModel


@dataclass
class ScheduleRecord:
    """Represents a stored schedule record."""

    id: str
    name: str
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    assignments: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    solver_config: Dict[str, Any]


class InMemoryDatabase:
    """In-memory database implementation for Phase 2."""

    def __init__(self):
        """Initialize the in-memory database."""
        self.schedules: Dict[str, ScheduleRecord] = {}
        self.user_schedules: Dict[str, List[str]] = {}  # user_id -> list of schedule_ids

    def create_schedule(
        self,
        name: str,
        user_id: str,
        assignments: List[AssignmentModel],
        metadata: Dict[str, Any],
        solver_config: Dict[str, Any],
    ) -> str:
        """Create a new schedule record.

        Args:
            name: Schedule name
            user_id: User ID
            assignments: List of assignments
            metadata: Schedule metadata
            solver_config: Solver configuration

        Returns:
            Created schedule ID
        """
        schedule_id = str(uuid.uuid4())
        now = datetime.now()

        # Convert assignments to dict
        assignment_dicts = [asdict(a) for a in assignments]

        schedule = ScheduleRecord(
            id=schedule_id,
            name=name,
            user_id=user_id,
            status="active",
            created_at=now,
            updated_at=now,
            assignments=assignment_dicts,
            metadata=metadata,
            solver_config=solver_config,
        )

        # Store schedule
        self.schedules[schedule_id] = schedule

        # Update user index
        if user_id not in self.user_schedules:
            self.user_schedules[user_id] = []
        self.user_schedules[user_id].append(schedule_id)

        return schedule_id

    def get_schedule(self, schedule_id: str) -> Optional[ScheduleRecord]:
        """Get a schedule by ID.

        Args:
            schedule_id: Schedule ID

        Returns:
            Schedule record or None if not found
        """
        return self.schedules.get(schedule_id)

    def update_schedule(
        self,
        schedule_id: str,
        name: Optional[str] = None,
        assignments: Optional[List[AssignmentModel]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update an existing schedule.

        Args:
            schedule_id: Schedule ID
            name: New name (optional)
            assignments: New assignments (optional)
            metadata: New metadata (optional)

        Returns:
            True if updated, False if not found
        """
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return False

        # Update fields
        if name is not None:
            schedule.name = name
        if assignments is not None:
            schedule.assignments = [asdict(a) for a in assignments]
        if metadata is not None:
            schedule.metadata.update(metadata)

        schedule.updated_at = datetime.now()
        return True

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            True if deleted, False if not found
        """
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return False

        # Remove from schedules
        del self.schedules[schedule_id]

        # Remove from user index
        if schedule.user_id in self.user_schedules:
            self.user_schedules[schedule.user_id].remove(schedule_id)
            if not self.user_schedules[schedule.user_id]:
                del self.user_schedules[schedule.user_id]

        return True

    def get_user_schedules(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> List[ScheduleRecord]:
        """Get all schedules for a user.

        Args:
            user_id: User ID
            skip: Number of schedules to skip
            limit: Maximum schedules to return

        Returns:
            List of schedule records
        """
        schedule_ids = self.user_schedules.get(user_id, [])
        schedules = [self.schedules[sid] for sid in schedule_ids if sid in self.schedules]

        # Sort by updated_at descending
        schedules.sort(key=lambda s: s.updated_at, reverse=True)

        # Apply pagination
        return schedules[skip : skip + limit]

    def count_user_schedules(self, user_id: str) -> int:
        """Count schedules for a user.

        Args:
            user_id: User ID

        Returns:
            Number of schedules
        """
        return len(self.user_schedules.get(user_id, []))

    def search_schedules(
        self,
        user_id: Optional[str] = None,
        name_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[ScheduleRecord]:
        """Search schedules with filters.

        Args:
            user_id: Filter by user ID
            name_filter: Filter by name (contains)
            status_filter: Filter by status
            limit: Maximum results

        Returns:
            List of matching schedules
        """
        schedules = list(self.schedules.values())

        # Apply filters
        if user_id:
            schedules = [s for s in schedules if s.user_id == user_id]
        if name_filter:
            schedules = [s for s in schedules if name_filter.lower() in s.name.lower()]
        if status_filter:
            schedules = [s for s in schedules if s.status == status_filter]

        # Sort by updated_at descending
        schedules.sort(key=lambda s: s.updated_at, reverse=True)

        return schedules[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Statistics dictionary
        """
        total_schedules = len(self.schedules)
        total_users = len(self.user_schedules)

        # Status distribution
        status_counts = {}
        for schedule in self.schedules.values():
            status = schedule.status
            status_counts[status] = status_counts.get(status, 0) + 1

        # User distribution
        user_schedule_counts = [len(schedule_ids) for schedule_ids in self.user_schedules.values()]

        return {
            "total_schedules": total_schedules,
            "total_users": total_users,
            "status_distribution": status_counts,
            "average_schedules_per_user": sum(user_schedule_counts) / max(total_users, 1),
            "max_schedules_per_user": max(user_schedule_counts) if user_schedule_counts else 0,
        }

    def export_to_dict(self) -> Dict[str, Any]:
        """Export all data to dictionary.

        Returns:
            All data as dictionary
        """
        return {
            "schedules": {sid: asdict(schedule) for sid, schedule in self.schedules.items()},
            "user_schedules": self.user_schedules,
            "exported_at": datetime.now().isoformat(),
        }

    def import_from_dict(self, data: Dict[str, Any]) -> bool:
        """Import data from dictionary.

        Args:
            data: Dictionary with schedule data

        Returns:
            True if successful
        """
        try:
            # Clear existing data
            self.schedules.clear()
            self.user_schedules.clear()

            # Import schedules
            for schedule_id, schedule_data in data.get("schedules", {}).items():
                # Convert datetime strings back to datetime objects
                schedule_data["created_at"] = datetime.fromisoformat(schedule_data["created_at"])
                schedule_data["updated_at"] = datetime.fromisoformat(schedule_data["updated_at"])

                schedule = ScheduleRecord(**schedule_data)
                self.schedules[schedule_id] = schedule

            # Import user indexes
            self.user_schedules = data.get("user_schedules", {})

            return True
        except Exception as e:
            print(f"Import error: {e}")
            return False


# Global database instance
db = InMemoryDatabase()
