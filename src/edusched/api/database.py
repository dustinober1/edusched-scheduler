"""In-memory database for schedule persistence.

For Phase 2, we use an in-memory database.
In later phases, this would be replaced with a proper database
like PostgreSQL or MongoDB.
"""

import json
import os
import logging
import sqlite3
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
        db_path = os.getenv("EDUSCHED_DB_PATH", os.path.join("data", "edusched.sqlite3"))
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                assignments_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                solver_config_json TEXT NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_schedules_user_id ON schedules(user_id)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_schedules_updated_at ON schedules(updated_at)"
        )
        self._conn.commit()

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

        assignment_dicts = [asdict(a) for a in assignments]

        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO schedules (
                id, name, user_id, status, created_at, updated_at,
                assignments_json, metadata_json, solver_config_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                schedule_id,
                name,
                user_id,
                "active",
                now.isoformat(),
                now.isoformat(),
                json.dumps(assignment_dicts),
                json.dumps(metadata or {}),
                json.dumps(solver_config or {}),
            ),
        )
        self._conn.commit()
        return schedule_id

    def get_schedule(self, schedule_id: str) -> Optional[ScheduleRecord]:
        """Get a schedule by ID.

        Args:
            schedule_id: Schedule ID

        Returns:
            Schedule record or None if not found
        """
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
        row = cur.fetchone()
        if not row:
            return None

        return ScheduleRecord(
            id=str(row["id"]),
            name=str(row["name"]),
            user_id=str(row["user_id"]),
            status=str(row["status"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            assignments=json.loads(str(row["assignments_json"]) or "[]"),
            metadata=json.loads(str(row["metadata_json"]) or "{}"),
            solver_config=json.loads(str(row["solver_config_json"]) or "{}"),
        )

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
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return False

        new_name = name if name is not None else schedule.name
        new_assignments = (
            [asdict(a) for a in assignments] if assignments is not None else schedule.assignments
        )
        new_metadata = schedule.metadata
        if metadata is not None:
            new_metadata = {**(schedule.metadata or {}), **metadata}

        new_status = schedule.status
        if metadata is not None and "status" in metadata and metadata["status"] is not None:
            new_status = str(metadata["status"])

        now = datetime.now()

        cur = self._conn.cursor()
        cur.execute(
            """
            UPDATE schedules
            SET name = ?, status = ?, updated_at = ?, assignments_json = ?, metadata_json = ?
            WHERE id = ?
            """,
            (
                new_name,
                new_status,
                now.isoformat(),
                json.dumps(new_assignments),
                json.dumps(new_metadata or {}),
                schedule_id,
            ),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            True if deleted, False if not found
        """
        cur = self._conn.cursor()
        cur.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        self._conn.commit()
        return cur.rowcount > 0

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
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT * FROM schedules
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, int(limit), int(skip)),
        )
        rows = cur.fetchall()

        schedules: List[ScheduleRecord] = []
        for row in rows:
            schedules.append(
                ScheduleRecord(
                    id=str(row["id"]),
                    name=str(row["name"]),
                    user_id=str(row["user_id"]),
                    status=str(row["status"]),
                    created_at=datetime.fromisoformat(str(row["created_at"])),
                    updated_at=datetime.fromisoformat(str(row["updated_at"])),
                    assignments=json.loads(str(row["assignments_json"]) or "[]"),
                    metadata=json.loads(str(row["metadata_json"]) or "{}"),
                    solver_config=json.loads(str(row["solver_config_json"]) or "{}"),
                )
            )

        return schedules

    def count_user_schedules(self, user_id: str) -> int:
        """Count schedules for a user.

        Args:
            user_id: User ID

        Returns:
            Number of schedules
        """
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(1) AS c FROM schedules WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return int(row["c"]) if row else 0

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
        query = "SELECT id FROM schedules WHERE 1=1"
        params: List[Any] = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if name_filter:
            query += " AND LOWER(name) LIKE ?"
            params.append(f"%{name_filter.lower()}%")
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(int(limit))

        cur = self._conn.cursor()
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        schedules: List[ScheduleRecord] = []
        for row in rows:
            schedule = self.get_schedule(str(row["id"]))
            if schedule is not None:
                schedules.append(schedule)
        return schedules

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Statistics dictionary
        """
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(1) AS c FROM schedules")
        total_schedules_row = cur.fetchone()
        total_schedules = int(total_schedules_row["c"]) if total_schedules_row else 0

        cur.execute("SELECT COUNT(DISTINCT user_id) AS c FROM schedules")
        total_users_row = cur.fetchone()
        total_users = int(total_users_row["c"]) if total_users_row else 0

        cur.execute("SELECT status, COUNT(1) AS c FROM schedules GROUP BY status")
        status_counts: Dict[str, int] = {str(r["status"]): int(r["c"]) for r in cur.fetchall()}

        cur.execute("SELECT user_id, COUNT(1) AS c FROM schedules GROUP BY user_id")
        user_schedule_counts = [int(r["c"]) for r in cur.fetchall()]

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
        cur = self._conn.cursor()
        cur.execute("SELECT id FROM schedules")
        rows = cur.fetchall()
        schedules: Dict[str, Any] = {}
        for row in rows:
            schedule_id = str(row["id"])
            schedule = self.get_schedule(schedule_id)
            if schedule is not None:
                schedules[schedule_id] = asdict(schedule)

        return {
            "schedules": schedules,
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
            cur = self._conn.cursor()
            cur.execute("DELETE FROM schedules")

            for schedule_id, schedule_data in data.get("schedules", {}).items():
                created_at = schedule_data.get("created_at")
                updated_at = schedule_data.get("updated_at")

                if isinstance(created_at, datetime):
                    created_at_str = created_at.isoformat()
                else:
                    created_at_str = str(created_at)

                if isinstance(updated_at, datetime):
                    updated_at_str = updated_at.isoformat()
                else:
                    updated_at_str = str(updated_at)

                cur.execute(
                    """
                    INSERT INTO schedules (
                        id, name, user_id, status, created_at, updated_at,
                        assignments_json, metadata_json, solver_config_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(schedule_id),
                        str(schedule_data.get("name", "")),
                        str(schedule_data.get("user_id", "")),
                        str(schedule_data.get("status", "active")),
                        created_at_str,
                        updated_at_str,
                        json.dumps(schedule_data.get("assignments", [])),
                        json.dumps(schedule_data.get("metadata", {})),
                        json.dumps(schedule_data.get("solver_config", {})),
                    ),
                )

            self._conn.commit()
            return True
        except Exception as e:
            logging.getLogger(__name__).exception("Import error")
            return False


# Global database instance
db = InMemoryDatabase()
