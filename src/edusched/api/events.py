"""Event system for schedule changes and notifications.

Provides event-driven architecture for schedule updates,
conflict detection, and real-time notifications.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from edusched.api.websocket import manager

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events in the system."""

    SCHEDULE_CREATED = "schedule_created"
    SCHEDULE_UPDATED = "schedule_updated"
    SCHEDULE_DELETED = "schedule_deleted"
    ASSIGNMENT_ADDED = "assignment_added"
    ASSIGNMENT_UPDATED = "assignment_updated"
    ASSIGNMENT_REMOVED = "assignment_removed"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    SOLVER_STARTED = "solver_started"
    SOLVER_PROGRESS = "solver_progress"
    SOLVER_COMPLETED = "solver_completed"
    SOLVER_FAILED = "solver_failed"
    DATA_IMPORTED = "data_imported"
    DATA_EXPORTED = "data_exported"
    USER_CONNECTED = "user_connected"
    USER_DISCONNECTED = "user_disconnected"


class Event:
    """Represents a system event."""

    def __init__(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        schedule_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Initialize an event.

        Args:
            event_type: Type of event
            data: Event data payload
            user_id: User who triggered the event
            schedule_id: Related schedule ID
            timestamp: Event timestamp
        """
        self.event_type = event_type
        self.data = data
        self.user_id = user_id
        self.schedule_id = schedule_id
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary.

        Returns:
            Event as dictionary
        """
        return {
            "type": self.event_type.value,
            "data": self.data,
            "user_id": self.user_id,
            "schedule_id": self.schedule_id,
            "timestamp": self.timestamp.isoformat(),
        }


class EventListener:
    """Base class for event listeners."""

    async def handle_event(self, event: Event):
        """Handle an event.

        Args:
            event: Event to handle
        """
        raise NotImplementedError


class WebSocketListener(EventListener):
    """WebSocket event listener for real-time updates."""

    async def handle_event(self, event: Event):
        """Handle event by broadcasting to WebSocket clients.

        Args:
            event: Event to handle
        """
        if event.schedule_id:
            # Send to schedule subscribers
            await manager.send_schedule_update(
                event.schedule_id,
                event.event_type.value.replace("_", " "),
                event.data,
            )
        elif event.user_id:
            # Send to specific user
            await manager.send_to_user(event.to_dict(), event.user_id)


class LoggingListener(EventListener):
    """Event listener for logging important events."""

    def __init__(self, log_level: int = logging.INFO):
        """Initialize logging listener.

        Args:
            log_level: Logging level
        """
        self.log_level = log_level

    async def handle_event(self, event: Event):
        """Log the event.

        Args:
            event: Event to log
        """
        message = f"Event: {event.event_type.value}"
        if event.user_id:
            message += f" (User: {event.user_id})"
        if event.schedule_id:
            message += f" (Schedule: {event.schedule_id})"

        logger.log(self.log_level, message)


class EventManager:
    """Manages event system with listeners and dispatch."""

    def __init__(self):
        """Initialize event manager."""
        self.listeners: Dict[EventType, List[EventListener]] = {}
        self.global_listeners: List[EventListener] = []
        self.event_history: List[Event] = []
        self.max_history = 1000  # Keep last 1000 events

    def add_listener(self, event_type: EventType, listener: EventListener):
        """Add a listener for specific event type.

        Args:
            event_type: Event type to listen for
            listener: Event listener
        """
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)

    def add_global_listener(self, listener: EventListener):
        """Add a global listener for all events.

        Args:
            listener: Event listener
        """
        self.global_listeners.append(listener)

    def remove_listener(self, event_type: EventType, listener: EventListener):
        """Remove a listener for specific event type.

        Args:
            event_type: Event type
            listener: Event listener to remove
        """
        if event_type in self.listeners:
            self.listeners[event_type] = [l for l in self.listeners[event_type] if l != listener]

    async def emit(self, event: Event):
        """Emit an event to all listeners.

        Args:
            event: Event to emit
        """
        # Store in history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history :]

        # Notify global listeners first
        for listener in self.global_listeners:
            try:
                await listener.handle_event(event)
            except Exception as e:
                logger.error(f"Global listener error: {e}")

        # Notify specific listeners
        if event.event_type in self.listeners:
            for listener in self.listeners[event.event_type]:
                try:
                    await listener.handle_event(event)
                except Exception as e:
                    logger.error(f"Event listener error: {e}")

    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        user_id: Optional[str] = None,
        schedule_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get filtered event history.

        Args:
            event_type: Filter by event type
            user_id: Filter by user
            schedule_id: Filter by schedule
            limit: Maximum number of events to return

        Returns:
            List of events as dictionaries
        """
        events = self.event_history

        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if schedule_id:
            events = [e for e in events if e.schedule_id == schedule_id]

        # Return latest events
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in events[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        """Get event system statistics.

        Returns:
            Statistics dictionary
        """
        event_counts = {}
        for event in self.event_history:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        return {
            "total_events": len(self.event_history),
            "event_types": len(event_counts),
            "event_counts": event_counts,
            "active_listeners": {
                event_type.value: len(listeners) for event_type, listeners in self.listeners.items()
            },
            "global_listeners": len(self.global_listeners),
        }


# Global event manager instance
event_manager = EventManager()


# Initialize default listeners
event_manager.add_global_listener(WebSocketListener())
event_manager.add_global_listener(LoggingListener())


# Convenience functions
async def emit_schedule_created(schedule_id: str, user_id: str, data: Dict[str, Any]):
    """Emit schedule created event.

    Args:
        schedule_id: Schedule ID
        user_id: User ID
        data: Schedule data
    """
    event = Event(
        EventType.SCHEDULE_CREATED,
        data,
        user_id=user_id,
        schedule_id=schedule_id,
    )
    await event_manager.emit(event)


async def emit_schedule_updated(schedule_id: str, user_id: str, changes: Dict[str, Any]):
    """Emit schedule updated event.

    Args:
        schedule_id: Schedule ID
        user_id: User ID
        changes: What changed
    """
    event = Event(
        EventType.SCHEDULE_UPDATED,
        changes,
        user_id=user_id,
        schedule_id=schedule_id,
    )
    await event_manager.emit(event)


async def emit_conflict_detected(schedule_id: str, conflicts: List[Dict[str, Any]]):
    """Emit conflict detected event.

    Args:
        schedule_id: Schedule ID
        conflicts: List of conflicts
    """
    event = Event(
        EventType.CONFLICT_DETECTED,
        {"conflicts": conflicts, "count": len(conflicts)},
        schedule_id=schedule_id,
    )
    await event_manager.emit(event)


async def emit_conflict_resolved(schedule_id: str, conflict_id: str, resolution: Dict[str, Any]):
    """Emit conflict resolved event.

    Args:
        schedule_id: Schedule ID
        conflict_id: ID of resolved conflict
        resolution: Resolution details
    """
    event = Event(
        EventType.CONFLICT_RESOLVED,
        {"conflict_id": conflict_id, "resolution": resolution},
        schedule_id=schedule_id,
    )
    await event_manager.emit(event)


async def emit_solver_started(schedule_id: str, user_id: str, solver_config: Dict[str, Any]):
    """Emit solver started event.

    Args:
        schedule_id: Schedule ID
        user_id: User ID
        solver_config: Solver configuration
    """
    event = Event(
        EventType.SOLVER_STARTED,
        {"config": solver_config, "status": "running"},
        user_id=user_id,
        schedule_id=schedule_id,
    )
    await event_manager.emit(event)


async def emit_solver_progress(schedule_id: str, user_id: str, progress: Dict[str, Any]):
    """Emit solver progress event.

    Args:
        schedule_id: Schedule ID
        user_id: User ID
        progress: Progress information
    """
    event = Event(
        EventType.SOLVER_PROGRESS,
        progress,
        user_id=user_id,
        schedule_id=schedule_id,
    )
    await event_manager.emit(event)


async def emit_solver_completed(schedule_id: str, user_id: str, result: Dict[str, Any]):
    """Emit solver completed event.

    Args:
        schedule_id: Schedule ID
        user_id: User ID
        result: Solver result
    """
    event = Event(
        EventType.SOLVER_COMPLETED,
        result,
        user_id=user_id,
        schedule_id=schedule_id,
    )
    await event_manager.emit(event)


async def emit_solver_failed(
    schedule_id: str, user_id: str, error: str, details: Dict[str, Any] = None
):
    """Emit solver failed event.

    Args:
        schedule_id: Schedule ID
        user_id: User ID
        error: Error message
        details: Additional error details
    """
    event = Event(
        EventType.SOLVER_FAILED,
        {"error": error, "details": details or {}},
        user_id=user_id,
        schedule_id=schedule_id,
    )
    await event_manager.emit(event)


async def emit_data_imported(
    user_id: str, data_type: str, count: int, details: Dict[str, Any] = None
):
    """Emit data imported event.

    Args:
        user_id: User ID who imported data
        data_type: Type of data imported
        count: Number of records imported
        details: Additional import details
    """
    event = Event(
        EventType.DATA_IMPORTED,
        {"data_type": data_type, "count": count, "details": details or {}},
        user_id=user_id,
    )
    await event_manager.emit(event)


async def emit_data_exported(
    user_id: str, data_type: str, format: str, details: Dict[str, Any] = None
):
    """Emit data exported event.

    Args:
        user_id: User ID who exported data
        data_type: Type of data exported
        format: Export format
        details: Additional export details
    """
    event = Event(
        EventType.DATA_EXPORTED,
        {"data_type": data_type, "format": format, "details": details or {}},
        user_id=user_id,
    )
    await event_manager.emit(event)
