"""Objective implementations."""

from datetime import datetime, time
from typing import TYPE_CHECKING, List

from edusched.objectives.base import Objective

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class SpreadEvenlyAcrossTerm(Objective):
    """Minimizes variance in daily session distribution."""

    def score(self, solution: List["Assignment"]) -> float:
        """Calculate score based on distribution uniformity."""
        if not solution:
            return 1.0

        # Count sessions per day
        from collections import defaultdict
        from datetime import date

        daily_counts = defaultdict(int)
        for assignment in solution:
            day = assignment.start_time.date()
            daily_counts[day] += 1

        if not daily_counts:
            return 1.0

        # Calculate variance
        counts = list(daily_counts.values())
        mean = sum(counts) / len(counts)
        variance = sum((c - mean) ** 2 for c in counts) / len(counts)

        # Normalize: lower variance = higher score
        # Assume max variance is when all sessions are on one day
        max_variance = (len(solution) ** 2) / len(daily_counts)
        if max_variance == 0:
            return 1.0

        score = max(0, 1 - (variance / max_variance))
        return score

    @property
    def objective_type(self) -> str:
        """Return objective type identifier."""
        return "soft.spread_evenly_across_term"


class MinimizeEveningSessions(Objective):
    """Minimizes sessions after configurable evening threshold."""

    def __init__(self, weight: float = 1.0, evening_threshold: time = time(17, 0)) -> None:
        super().__init__(weight)
        self.evening_threshold = evening_threshold

    def score(self, solution: List["Assignment"]) -> float:
        """Calculate score based on evening session penalties."""
        if not solution:
            return 1.0

        # Count evening sessions
        evening_count = 0
        for assignment in solution:
            if assignment.start_time.time() >= self.evening_threshold:
                evening_count += 1

        # Normalize: more evening sessions = lower score
        max_evening_penalty = len(solution)
        if max_evening_penalty == 0:
            return 1.0

        score = max(0, 1 - (evening_count / max_evening_penalty))
        return score

    @property
    def objective_type(self) -> str:
        """Return objective type identifier."""
        return "soft.minimize_evening_sessions"


class BalanceInstructorLoad(Objective):
    """Minimizes instructor workload variance."""

    def score(self, solution: List["Assignment"]) -> float:
        """Calculate score based on instructor load balance."""
        if not solution:
            return 1.0

        # Count sessions per instructor
        from collections import defaultdict

        instructor_loads = defaultdict(int)
        for assignment in solution:
            # Assume instructor is in resource type "instructor"
            if "instructor" in assignment.assigned_resources:
                for instructor_id in assignment.assigned_resources["instructor"]:
                    instructor_loads[instructor_id] += 1

        if not instructor_loads:
            return 1.0

        # Calculate variance
        loads = list(instructor_loads.values())
        mean = sum(loads) / len(loads)
        variance = sum((l - mean) ** 2 for l in loads) / len(loads)

        # Normalize: lower variance = higher score
        max_variance = (len(solution) ** 2) / len(instructor_loads)
        if max_variance == 0:
            return 1.0

        score = max(0, 1 - (variance / max_variance))
        return score

    @property
    def objective_type(self) -> str:
        """Return objective type identifier."""
        return "soft.balance_instructor_load"
