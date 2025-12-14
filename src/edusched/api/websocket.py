"""WebSocket connection manager for real-time schedule updates.

Manages WebSocket connections for live schedule updates,
conflict notifications, and collaborative editing.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        """Initialize connection manager."""
        # Active connections by user
        self.active_connections: Dict[str, Set["WebSocket"]] = {}
        # Connections by schedule (for schedule-specific updates)
        self.schedule_subscribers: Dict[str, Set[str]] = {}  # schedule_id -> set of user_ids
        # User session info
        self.user_sessions: Dict[str, Dict] = {}

    async def connect(self, websocket: "WebSocket", user_id: str, schedule_id: str = None):
        """Connect a new WebSocket client.

        Args:
            websocket: WebSocket connection
            user_id: User identifier
            schedule_id: Optional schedule to subscribe to
        """
        await websocket.accept()

        # Add to user connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

        # Store user session
        self.user_sessions[user_id] = {
            "connected_at": datetime.now(),
            "schedule_id": schedule_id,
            "last_ping": datetime.now(),
        }

        # Subscribe to schedule if provided
        if schedule_id:
            if schedule_id not in self.schedule_subscribers:
                self.schedule_subscribers[schedule_id] = set()
            self.schedule_subscribers[schedule_id].add(user_id)

        logger.info(f"WebSocket connected for user {user_id}, schedule {schedule_id}")

        # Send welcome message
        await self.send_personal_message({
            "type": "connected",
            "message": "Successfully connected to EduSched real-time updates",
            "timestamp": datetime.now().isoformat(),
        }, websocket)

    async def disconnect(self, websocket: "WebSocket", user_id: str):
        """Disconnect a WebSocket client.

        Args:
            websocket: WebSocket connection
            user_id: User identifier
        """
        # Remove from user connections
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # Remove from schedule subscriptions
        if user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            if session.get("schedule_id"):
                schedule_id = session["schedule_id"]
                if schedule_id in self.schedule_subscribers:
                    self.schedule_subscribers[schedule_id].discard(user_id)
                    if not self.schedule_subscribers[schedule_id]:
                        del self.schedule_subscribers[schedule_id]

            del self.user_sessions[user_id]

        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: dict, websocket: "WebSocket"):
        """Send a message to a specific WebSocket connection.

        Args:
            message: Message to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")

    async def send_to_user(self, message: dict, user_id: str):
        """Send a message to all connections for a specific user.

        Args:
            message: Message to send
            user_id: Target user identifier
        """
        if user_id not in self.active_connections:
            return

        # Send to all user's connections
        disconnected = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                disconnected.append(connection)

        # Clean up dead connections
        for conn in disconnected:
            self.active_connections[user_id].discard(conn)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected users.

        Args:
            message: Message to broadcast
        """
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(message, user_id)

    async def broadcast_to_schedule(self, message: dict, schedule_id: str):
        """Broadcast a message to all users subscribed to a schedule.

        Args:
            message: Message to broadcast
            schedule_id: Schedule identifier
        """
        if schedule_id not in self.schedule_subscribers:
            return

        for user_id in self.schedule_subscribers[schedule_id]:
            await self.send_to_user(message, user_id)

    async def send_schedule_update(self, schedule_id: str, update_type: str, data: dict):
        """Send a schedule-specific update.

        Args:
            schedule_id: Schedule identifier
            update_type: Type of update (created, updated, deleted, conflict)
            data: Update data
        """
        message = {
            "type": "schedule_update",
            "schedule_id": schedule_id,
            "update_type": update_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        await self.broadcast_to_schedule(message, schedule_id)

    async def send_conflict_alert(self, schedule_id: str, conflicts: List[dict]):
        """Send conflict alerts to schedule subscribers.

        Args:
            schedule_id: Schedule identifier
            conflicts: List of conflict details
        """
        message = {
            "type": "conflict_alert",
            "schedule_id": schedule_id,
            "conflicts": conflicts,
            "timestamp": datetime.now().isoformat(),
        }

        await self.broadcast_to_schedule(message, schedule_id)

    async def send_solver_progress(self, user_id: str, progress: dict):
        """Send solver progress updates to a user.

        Args:
            user_id: User identifier
            progress: Progress information
        """
        message = {
            "type": "solver_progress",
            "progress": progress,
            "timestamp": datetime.now().isoformat(),
        }

        await self.send_to_user(message, user_id)

    async def ping_all(self):
        """Send ping to all connections to check if they're alive."""
        message = {
            "type": "ping",
            "timestamp": datetime.now().isoformat(),
        }

        await self.broadcast(message)

    def get_connection_stats(self) -> dict:
        """Get connection statistics.

        Returns:
            Dictionary with connection statistics
        """
        return {
            "total_users": len(self.active_connections),
            "total_connections": sum(len(conns) for conns in self.active_connections.values()),
            "schedule_subscribers": {
                schedule_id: len(subscribers)
                for schedule_id, subscribers in self.schedule_subscribers.items()
            },
            "active_schedules": len(self.schedule_subscribers),
        }

    def get_user_info(self, user_id: str) -> dict:
        """Get information about a user's connections.

        Args:
            user_id: User identifier

        Returns:
            User connection information
        """
        if user_id not in self.user_sessions:
            return None

        session = self.user_sessions[user_id]
        return {
            "user_id": user_id,
            "connected_at": session["connected_at"].isoformat(),
            "schedule_id": session.get("schedule_id"),
            "active_connections": len(self.active_connections.get(user_id, set())),
            "last_ping": session.get("last_ping").isoformat(),
        }


# Global connection manager instance
manager = ConnectionManager()


# WebSocket endpoint handler
async def websocket_endpoint(websocket: "WebSocket", user_id: str, schedule_id: str = None):
    """Handle WebSocket connections.

    Args:
        websocket: WebSocket connection
        user_id: User identifier from query params
        schedule_id: Optional schedule ID from query params
    """
    await manager.connect(websocket, user_id, schedule_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get("type") == "pong":
                # Update last ping time
                if user_id in manager.user_sessions:
                    manager.user_sessions[user_id]["last_ping"] = datetime.now()

            elif message.get("type") == "subscribe_schedule":
                # Subscribe to a different schedule
                new_schedule_id = message.get("schedule_id")
                if new_schedule_id:
                    # Unsubscribe from current schedule
                    current_session = manager.user_sessions.get(user_id, {})
                    current_schedule_id = current_session.get("schedule_id")
                    if current_schedule_id:
                        if current_schedule_id in manager.schedule_subscribers:
                            manager.schedule_subscribers[current_schedule_id].discard(user_id)

                    # Subscribe to new schedule
                    if new_schedule_id not in manager.schedule_subscribers:
                        manager.schedule_subscribers[new_schedule_id] = set()
                    manager.schedule_subscribers[new_schedule_id].add(user_id)

                    # Update session
                    manager.user_sessions[user_id]["schedule_id"] = new_schedule_id

                    # Send confirmation
                    await manager.send_personal_message({
                        "type": "subscription_updated",
                        "schedule_id": new_schedule_id,
                        "timestamp": datetime.now().isoformat(),
                    }, websocket)

    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await manager.disconnect(websocket, user_id)