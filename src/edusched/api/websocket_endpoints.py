"""WebSocket endpoints for real-time collaborative scheduling."""

import asyncio
import json
from typing import Dict, List, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from edusched.domain.assignment import Assignment
from edusched.domain.problem import Problem


class CollaborativeSession:
    """Manages a collaborative scheduling session."""
    
    def __init__(self, session_id: str, problem: Problem):
        self.session_id = session_id
        self.problem = problem
        self.active_connections: Set[WebSocket] = set()
        self.current_schedule: List[Assignment] = []
        self.user_presences: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Add a new user to the session."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.user_presences[user_id] = {
            "connected_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "user_id": user_id
        }
        
        # Send current schedule to new user
        await self.send_current_schedule(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a user from the session."""
        self.active_connections.discard(websocket)
        self.user_presences.pop(user_id, None)
    
    async def broadcast(self, message: Dict):
        """Send a message to all connected users."""
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected.add(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.active_connections.discard(connection)
    
    async def send_current_schedule(self, websocket: WebSocket):
        """Send the current schedule to a specific user."""
        message = {
            "type": "schedule_update",
            "data": {
                "assignments": [assignment.__dict__ for assignment in self.current_schedule],
                "users": list(self.user_presences.keys())
            }
        }
        await websocket.send_text(json.dumps(message))
    
    async def handle_assignment_update(self, user_id: str, assignment_data: Dict):
        """Handle an assignment update from a user."""
        # Convert data to Assignment object
        assignment = Assignment(
            request_id=assignment_data["request_id"],
            occurrence_index=assignment_data.get("occurrence_index", 0),
            start_time=datetime.fromisoformat(assignment_data["start_time"]),
            end_time=datetime.fromisoformat(assignment_data["end_time"]),
            cohort_id=assignment_data.get("cohort_id"),
            assigned_resources=assignment_data.get("assigned_resources", {})
        )
        
        # Update our internal schedule
        # This is a simplified approach - in a real implementation, you'd want more sophisticated
        # conflict resolution and change tracking
        self.current_schedule = [a for a in self.current_schedule if a.request_id != assignment.request_id]
        self.current_schedule.append(assignment)
        
        # Broadcast the update to all users
        await self.broadcast({
            "type": "assignment_update",
            "user_id": user_id,
            "assignment": assignment_data
        })
    
    async def handle_schedule_solve(self, user_id: str, solve_params: Dict):
        """Handle a request to solve the schedule."""
        from edusched import solve
        
        try:
            # In a real implementation, you'd want to validate that the problem is complete
            # and handle the solving in a background task
            result = solve(self.problem, **solve_params)
            
            # Update internal schedule
            self.current_schedule = result.assignments
            
            # Broadcast the solved schedule
            await self.broadcast({
                "type": "schedule_solved",
                "user_id": user_id,
                "assignments": [a.__dict__ for a in result.assignments],
                "status": result.status
            })
        except Exception as e:
            await self.broadcast({
                "type": "solve_error",
                "user_id": user_id,
                "error": str(e)
            })


# Global store for collaborative sessions
COLLABORATIVE_SESSIONS: Dict[str, CollaborativeSession] = {}


async def get_collaborative_session(session_id: str, problem: Problem) -> CollaborativeSession:
    """Get or create a collaborative session."""
    if session_id not in COLLABORATIVE_SESSIONS:
        COLLABORATIVE_SESSIONS[session_id] = CollaborativeSession(session_id, problem)
    return COLLABORATIVE_SESSIONS[session_id]


class WebSocketManager:
    """Manages WebSocket connections for collaborative scheduling."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new WebSocket."""
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        """Disconnect a WebSocket."""
        self.active_connections.pop(client_id, None)
    
    async def send_personal_message(self, message: str, client_id: str):
        """Send a message to a specific client."""
        websocket = self.active_connections.get(client_id)
        if websocket:
            await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients."""
        for websocket in list(self.active_connections.values()):
            await websocket.send_text(message)