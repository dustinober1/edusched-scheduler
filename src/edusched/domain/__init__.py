"""Domain model classes for EduSched."""

from edusched.domain.assignment import Assignment
from edusched.domain.calendar import Calendar
from edusched.domain.problem import Problem
from edusched.domain.resource import Resource
from edusched.domain.result import Result
from edusched.domain.session_request import SessionRequest

__all__ = [
    "SessionRequest",
    "Resource",
    "Calendar",
    "Assignment",
    "Problem",
    "Result",
]
