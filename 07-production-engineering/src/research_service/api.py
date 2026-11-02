"""Authenticated contracts for evidence, agents, and durable research workflows."""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from research_sdk.telemetry import emit

from research_service.auth import ActorDep, require

router = APIRouter(prefix="/v1", tags=["ResearchOps"])


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Question(StrictInput):
    question: str = Field(min_length=1, max_length=8000)


class DocumentInput(StrictInput):
    source_id: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=50000)
    source_uri: str = Field(default="synthetic://local", max_length=500)
    expires_at: str | None = Field(default=None, max_length=40)
    claims: dict[str, str] | None = None


class RunInput(Question):
    idempotency_key: str = Field(min_length=1, max_length=120)


class VersionInput(StrictInput):
    expected_version: int = Field(ge=1)


class ApprovalInput(VersionInput):
    expires_in_seconds: int = Field(default=300, ge=1, le=3600)


@router.post("/documents")
def ingest(body: DocumentInput, request: Request, actor: ActorDep) -> dict:
    require(actor, "evidence:write")
    result = request.app.state.evidence.ingest(actor.tenant_id, **body.model_dump())
    emit("evidence.ingested", outcome="stored")
    return result.model_dump()


@router.get("/evidence")
def search(
    request: Request,
    actor: ActorDep,
    question: Annotated[str, Query(min_length=1, max_length=8000)],
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> dict:
    require(actor, "evidence:read")
    passages = request.app.state.evidence.search(actor.tenant_id, question, limit=limit)
    emit("retrieval.completed", count=len(passages))
    return {"passages": [passage.model_dump() for passage in passages]}


@router.post("/answers")
def answer(body: Question, request: Request, actor: ActorDep) -> dict:
    require(actor, "evidence:read")
    result = request.app.state.evidence.answer(actor.tenant_id, body.question)
    emit("retrieval.completed", count=len(result.citations))
    emit("answer.completed", outcome=result.status, mode=result.mode)
    return result.model_dump()


@router.post("/agent")
async def agent(body: Question, request: Request, actor: ActorDep) -> dict:
    require(actor, "agent:run")
    result = await request.app.state.agent.run(actor, body.question, request.state.request_id)
    emit(
        "agent.completed",
        outcome=result.status,
        rounds=result.rounds,
        tool_calls=result.tool_calls,
        usage_tokens=result.usage_tokens,
    )
    return result.model_dump()


@router.post("/runs", status_code=201)
def create_run(body: RunInput, request: Request, actor: ActorDep) -> dict:
    require(actor, "run:create")
    result = request.app.state.store.create_run(
        actor.tenant_id,
        actor.actor_id,
        body.question,
        body.idempotency_key,
        max_pending=request.app.state.settings.max_pending_runs,
    )
    emit("workflow.accepted", run_id=result["id"], outcome=result["status"])
    return result


@router.get("/runs")
def list_runs(
    request: Request, actor: ActorDep, limit: Annotated[int, Query(ge=1, le=100)] = 50
) -> dict:
    require(actor, "run:read")
    return {"runs": request.app.state.store.list_runs(actor.tenant_id, actor.actor_id, limit=limit)}


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request, actor: ActorDep) -> dict:
    require(actor, "run:read")
    return request.app.state.store.get_run(actor.tenant_id, actor.actor_id, run_id)


@router.post("/runs/{run_id}/advance")
def advance(run_id: str, request: Request, actor: ActorDep) -> dict:
    require(actor, "run:advance")
    # Verify ownership before worker selection, even for a non-runnable record.
    request.app.state.store.get_run(actor.tenant_id, actor.actor_id, run_id)
    result = request.app.state.worker.tick(actor.tenant_id, actor.actor_id, run_id)
    current = request.app.state.store.get_run(actor.tenant_id, actor.actor_id, run_id)
    emit("workflow.checkpoint", run_id=run_id, outcome=current["status"])
    return {"progressed": result is not None, "run": current}


@router.post("/runs/{run_id}/cancel")
def cancel(run_id: str, body: VersionInput, request: Request, actor: ActorDep) -> dict:
    require(actor, "run:create")
    return request.app.state.store.cancel(
        actor.tenant_id, actor.actor_id, run_id, body.expected_version
    )


@router.get("/actions/{action_id}")
def get_action(action_id: str, request: Request, actor: ActorDep) -> dict:
    require(actor, "run:read")
    return request.app.state.store.get_action(actor.tenant_id, actor.actor_id, action_id)


@router.post("/actions/{action_id}/approve")
def approve(action_id: str, body: ApprovalInput, request: Request, actor: ActorDep) -> dict:
    require(actor, "action:approve")
    require(actor, "deliver")
    result = request.app.state.store.approve(
        actor.tenant_id, actor.actor_id, action_id, body.expected_version, body.expires_in_seconds
    )
    emit("action.approved", action_id=action_id)
    return result


@router.post("/actions/{action_id}/reject")
def reject(action_id: str, body: VersionInput, request: Request, actor: ActorDep) -> dict:
    require(actor, "action:approve")
    return request.app.state.store.reject(
        actor.tenant_id, actor.actor_id, action_id, body.expected_version
    )
