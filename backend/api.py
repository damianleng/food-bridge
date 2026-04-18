"""
FoodBridge FastAPI backend.

Endpoints:
  POST /chat          — send a message, get Claude's response
  POST /reset         — clear conversation history for a session
  GET  /health        — liveness check
"""

import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import run_agent_sync

app = FastAPI(title="FoodBridge API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store: session_id → conversation history
# Replace with Redis / DB for production
_sessions: dict[str, list[dict]] = {}


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None   # omit to start a new session


class ChatResponse(BaseModel):
    session_id: str
    response: str


class ResetRequest(BaseModel):
    session_id: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    if session_id not in _sessions:
        _sessions[session_id] = []

    history = _sessions[session_id]

    try:
        response_text, updated_history = run_agent_sync(req.message, history)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    _sessions[session_id] = updated_history
    return ChatResponse(session_id=session_id, response=response_text)


@app.post("/reset")
def reset(req: ResetRequest):
    _sessions.pop(req.session_id, None)
    return {"session_id": req.session_id, "status": "cleared"}