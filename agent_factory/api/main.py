from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from agent_factory.api.checkpoints import CheckpointDecision
from agent_factory.api.ws import ws_manager
from agent_factory.core.factory_graph import build_factory_graph_v3
from agent_factory.core.state import ExecutionMode, FactoryStateV3, TargetLanguage, create_initial_state


app = FastAPI(title="Agent Factory API", version="0.1.0")
workflow = build_factory_graph_v3()
SESSIONS: dict[str, FactoryStateV3] = {}


class CreateSessionRequest(BaseModel):
    user_input: str = Field(min_length=3)
    execution_mode: ExecutionMode = ExecutionMode.STANDARD
    target_language: TargetLanguage = TargetLanguage.PYTHON


class CreateSessionResponse(BaseModel):
    session_id: str
    status: str
    execution_mode: ExecutionMode
    target_language: TargetLanguage


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok"}


@app.post("/sessions", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest) -> CreateSessionResponse:
    state = create_initial_state(
        user_input=req.user_input,
        execution_mode=req.execution_mode,
        target_language=req.target_language,
    )
    SESSIONS[state["session_id"]] = state
    return CreateSessionResponse(
        session_id=state["session_id"],
        status=state["status"],
        execution_mode=req.execution_mode,
        target_language=req.target_language,
    )


@app.post("/sessions/{session_id}/run")
async def run_session(session_id: str) -> dict[str, Any]:
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    final_state = await workflow.ainvoke(state)
    SESSIONS[session_id] = final_state
    await ws_manager.publish(session_id, {"type": "session.completed", "status": final_state.get("status")})
    return serialize_state(final_state)


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    return serialize_state(state)


@app.post("/sessions/{session_id}/checkpoint")
async def submit_checkpoint_decision(session_id: str, decision: CheckpointDecision) -> dict[str, Any]:
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    state["human_decision"] = decision.decision
    state["status"] = "checkpoint_decision_received"
    return {"session_id": session_id, "decision": decision.decision, "status": state["status"]}


@app.websocket("/ws/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: str) -> None:
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)


def serialize_state(state: FactoryStateV3) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in state.items():
        if is_dataclass(value):
            serialized[key] = asdict(value)
        elif isinstance(value, list):
            serialized[key] = [asdict(v) if is_dataclass(v) else v for v in value]
        else:
            serialized[key] = value
    return serialized
