from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any
import logging

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from agent_factory.api.checkpoints import CheckpointDecision
from agent_factory.api.ws import ws_manager
from agent_factory.core.factory_graph import build_factory_graph_v3
from agent_factory.core.nodes import (
    cost_estimate_node,
    delivery_node,
    development_node,
    dispatch_phase1_node,
    dispatch_phase2_node,
    discussion_node,
    failure_classifier_node,
    graceful_packager_node,
    human_recovery_node,
    intake_node,
    packaging_node,
    quality_gate_node,
    recovery_strategy_node,
    route_human_recovery,
    route_post_dispatch_phase1,
    route_quality_gate,
    route_recovery_strategy,
    targeted_remediation_node,
    tool_plan_node,
    domain_router_node,
)
from agent_factory.core.state import ExecutionMode, FactoryStateV3, TargetLanguage, create_initial_state


app = FastAPI(title="Agent Factory API", version="0.1.0")
workflow = build_factory_graph_v3()
SESSIONS: dict[str, FactoryStateV3] = {}
TECH_SPEC_CHECKPOINT = "tech_spec_review"
LOGGER = logging.getLogger(__name__)

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


class CreateSessionRequest(BaseModel):
    user_input: str = Field(min_length=3)
    execution_mode: ExecutionMode = ExecutionMode.STANDARD
    target_language: TargetLanguage = TargetLanguage.PYTHON


class CreateSessionResponse(BaseModel):
    session_id: str
    status: str
    execution_mode: ExecutionMode
    target_language: TargetLanguage


class StartRequest(BaseModel):
    input: str = Field(min_length=3)
    language: str = Field(min_length=2)
    execution_mode: ExecutionMode = ExecutionMode.STANDARD


class StartResponse(BaseModel):
    session_id: str
    status: str
    interrupted: bool
    checkpoint: str


class ResumeRequest(BaseModel):
    approved: bool = Field(description="whether the checkpoint review is approved")


@app.get("/health")
async def health() -> dict[str, Any]:
    LOGGER.info("【API日志】health 检查通过")
    return {"status": "ok"}


@app.post("/sessions", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest) -> CreateSessionResponse:
    LOGGER.info(
        "【API日志】创建会话请求 | mode=%s | language=%s | input=%s",
        req.execution_mode.value,
        req.target_language.value,
        req.user_input[:120],
    )
    state = create_initial_state(
        user_input=req.user_input,
        execution_mode=req.execution_mode,
        target_language=req.target_language,
    )
    SESSIONS[state["session_id"]] = state
    LOGGER.info("【API日志】创建会话完成 | session_id=%s | status=%s", state["session_id"], state["status"])
    return CreateSessionResponse(
        session_id=state["session_id"],
        status=state["status"],
        execution_mode=req.execution_mode,
        target_language=req.target_language,
    )


@app.post("/start", response_model=StartResponse)
async def start_session(req: StartRequest) -> StartResponse:
    LOGGER.info(
        "【API日志】start 请求 | mode=%s | language=%s | input=%s",
        req.execution_mode.value,
        req.language,
        req.input[:120],
    )
    language = _parse_target_language(req.language)
    state = create_initial_state(
        user_input=req.input,
        execution_mode=req.execution_mode,
        target_language=language,
    )
    state = await _run_until_tech_spec_checkpoint(state)
    SESSIONS[state["session_id"]] = state
    await ws_manager.publish(
        state["session_id"],
        {
            "type": "session.checkpoint",
            "status": state.get("status"),
            "checkpoint": TECH_SPEC_CHECKPOINT,
        },
    )
    LOGGER.info(
        "【API日志】start 完成 | session_id=%s | status=%s | checkpoint=%s",
        state["session_id"],
        state["status"],
        TECH_SPEC_CHECKPOINT,
    )
    return StartResponse(
        session_id=state["session_id"],
        status=state["status"],
        interrupted=True,
        checkpoint=TECH_SPEC_CHECKPOINT,
    )


@app.get("/status/{session_id}")
async def status_session(session_id: str) -> dict[str, Any]:
    LOGGER.info("【API日志】status 查询 | session_id=%s", session_id)
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    return {
        "session_id": session_id,
        "status": state.get("status", "unknown"),
        "interrupted": bool(state.get("interrupted", False)),
        "checkpoint": state.get("checkpoint"),
    }


@app.get("/result/{session_id}")
async def result_session(session_id: str) -> dict[str, Any]:
    LOGGER.info("【API日志】result 查询 | session_id=%s", session_id)
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    return serialize_state(state)


@app.post("/resume/{session_id}")
async def resume_session(session_id: str, req: ResumeRequest) -> dict[str, Any]:
    LOGGER.info("【API日志】resume 请求 | session_id=%s | approved=%s", session_id, req.approved)
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    if not bool(state.get("interrupted", False)):
        raise HTTPException(status_code=409, detail=f"session is not waiting on checkpoint: {session_id}")

    if not req.approved:
        state["interrupted"] = False
        state["checkpoint"] = ""
        state["status"] = "aborted_by_human"
        SESSIONS[session_id] = state
        await ws_manager.publish(session_id, {"type": "session.completed", "status": state["status"]})
        LOGGER.warning("【API日志】resume 拒绝继续 | session_id=%s | status=%s", session_id, state["status"])
        return serialize_state(state)

    state = await _run_from_checkpoint(state)
    SESSIONS[session_id] = state
    await ws_manager.publish(session_id, {"type": "session.completed", "status": state.get("status")})
    LOGGER.info(
        "【API日志】resume 完成 | session_id=%s | status=%s | delivery=%s",
        session_id,
        state.get("status"),
        bool(state.get("delivery_package")),
    )
    return serialize_state(state)


@app.post("/sessions/{session_id}/run")
async def run_session(session_id: str) -> dict[str, Any]:
    LOGGER.info("【API日志】run 请求 | session_id=%s", session_id)
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    final_state = await workflow.ainvoke(state)
    SESSIONS[session_id] = final_state
    await ws_manager.publish(session_id, {"type": "session.completed", "status": final_state.get("status")})
    LOGGER.info("【API日志】run 完成 | session_id=%s | status=%s", session_id, final_state.get("status"))
    return serialize_state(final_state)


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    LOGGER.info("【API日志】sessions 查询 | session_id=%s", session_id)
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    return serialize_state(state)


@app.post("/sessions/{session_id}/checkpoint")
async def submit_checkpoint_decision(session_id: str, decision: CheckpointDecision) -> dict[str, Any]:
    LOGGER.info(
        "【API日志】checkpoint 决策提交 | session_id=%s | decision=%s",
        session_id,
        decision.decision,
    )
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    state["human_decision"] = decision.decision
    state["status"] = "checkpoint_decision_received"
    return {"session_id": session_id, "decision": decision.decision, "status": state["status"]}


@app.websocket("/ws/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: str) -> None:
    LOGGER.info("【API日志】WebSocket 连接建立 | session_id=%s", session_id)
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)
        LOGGER.info("【API日志】WebSocket 连接关闭 | session_id=%s", session_id)


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


def _parse_target_language(language: str) -> TargetLanguage:
    normalized = language.strip().lower()
    if normalized in {"python", "py"}:
        return TargetLanguage.PYTHON
    if normalized in {"node", "nodejs", "node.js", "ts", "typescript"}:
        return TargetLanguage.NODEJS
    LOGGER.error("【API日志】非法语言参数 | language=%s", language)
    raise HTTPException(status_code=400, detail=f"language 必须为 'python' 或 'nodejs'，收到: {language}")


async def _run_until_tech_spec_checkpoint(state: FactoryStateV3) -> FactoryStateV3:
    LOGGER.info("【API日志】进入首部链路执行 | session_id=%s", state.get("session_id"))
    current = await intake_node(state)
    current = await domain_router_node(current)
    current = await cost_estimate_node(current)
    current = await dispatch_phase1_node(current)

    if route_post_dispatch_phase1(current) == "discussion":
        current = await discussion_node(current)
    current = await tool_plan_node(current)
    current["status"] = "awaiting_tech_spec_review"
    current["interrupted"] = True
    current["checkpoint"] = TECH_SPEC_CHECKPOINT
    LOGGER.info(
        "【API日志】首部链路完成并进入检查点 | session_id=%s | status=%s",
        current.get("session_id"),
        current.get("status"),
    )
    return current


async def _run_from_checkpoint(state: FactoryStateV3) -> FactoryStateV3:
    LOGGER.info("【API日志】从检查点继续执行 | session_id=%s", state.get("session_id"))
    current = state
    current["interrupted"] = False
    current["checkpoint"] = ""
    current = await dispatch_phase2_node(current)
    current = await development_node(current)
    current = await quality_gate_node(current)

    while route_quality_gate(current) == "failure_classifier":
        current = await failure_classifier_node(current)
        current = await recovery_strategy_node(current)
        next_step = route_recovery_strategy(current)
        if next_step == "targeted_remediation":
            current = await targeted_remediation_node(current)
            current = await quality_gate_node(current)
            continue
        if next_step == "graceful_packager":
            current = await graceful_packager_node(current)
            break
        if next_step == "human_recovery":
            # API resume flow defaults to safe degrade when a manual recovery decision is required.
            current["human_decision"] = "degrade"
            current = await human_recovery_node(current)
            human_next = route_human_recovery(current)
            if human_next == "__end__":
                current["status"] = "aborted_by_human"
                return current
            if human_next == "graceful_packager":
                current = await graceful_packager_node(current)
                break
            current = await quality_gate_node(current)
            continue
        current = await quality_gate_node(current)

    if current.get("status") != "graceful_packaged":
        current = await packaging_node(current)
    current = await delivery_node(current)
    LOGGER.info(
        "【API日志】检查点后流程结束 | session_id=%s | final_status=%s",
        current.get("session_id"),
        current.get("status"),
    )
    return current
