"""API endpoints for EduSched."""

from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

from edusched.domain.problem import Problem
from edusched.domain.result import Result
from edusched import solve
from .websocket_endpoints import get_collaborative_session, CollaborativeSession

app = FastAPI(title="EduSched API", version="0.1.0")

# Add CORS middleware to allow communication with frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for active collaborative sessions
COLLABORATIVE_SESSIONS: Dict[str, CollaborativeSession] = {}


@app.get("/")
async def root():
    """Root endpoint for the API."""
    return {"message": "EduSched API", "version": "0.1.0"}


@app.post("/solve", response_model=Result)
async def solve_schedule(problem: Problem) -> Result:
    """Solve a scheduling problem."""
    try:
        result = solve(problem)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.websocket("/ws/collaborative/{session_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, user_id: str):
    """WebSocket endpoint for collaborative scheduling."""
    problem = Problem(requests=[], resources=[], calendars=[], constraints=[])  # Placeholder
    session = await get_collaborative_session(session_id, problem)
    
    await session.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "assignment_update":
                await session.handle_assignment_update(user_id, message.get("data", {}))
            elif message_type == "solve_request":
                await session.handle_schedule_solve(user_id, message.get("params", {}))
            elif message_type == "ping":
                # Respond to keep-alive ping
                await websocket.send_text(json.dumps({"type": "pong"}))
            else:
                # Unknown message type
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }))
    
    except WebSocketDisconnect:
        session.disconnect(websocket, user_id)
        await session.broadcast({
            "type": "user_disconnected",
            "user_id": user_id
        })


@app.post("/collaborative_session")
async def create_collaborative_session(problem: Problem) -> Dict:
    """Create a new collaborative scheduling session."""
    import uuid
    
    session_id = str(uuid.uuid4())
    session = await get_collaborative_session(session_id, problem)
    
    return {
        "session_id": session_id,
        "message": "Collaborative session created successfully"
    }


@app.get("/collaborative_session/{session_id}")
async def get_collaborative_session_info(session_id: str) -> Dict:
    """Get information about a collaborative session."""
    if session_id not in COLLABORATIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = COLLABORATIVE_SESSIONS[session_id]
    return {
        "session_id": session.session_id,
        "user_count": len(session.user_presences),
        "users": list(session.user_presences.keys())
    }