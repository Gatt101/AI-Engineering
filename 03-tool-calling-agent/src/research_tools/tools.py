"""Strict tool contracts and policy boundary. Model text never grants permission."""

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from research_sdk.telemetry import emit


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Actor(StrictModel):
    """Construct only from authenticated application context, never model arguments."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    actor_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    tenant_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    permissions: frozenset[str] = frozenset()


class SearchArgs(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=3, ge=1, le=5)


class EvidenceHit(StrictModel):
    source_id: str
    version: int
    title: str
    start: int
    end: int
    text: str
    score: float
    suspicious: bool
    untrusted: Literal[True] = True


class SearchOutput(StrictModel):
    passages: list[EvidenceHit]
    untrusted: Literal[True] = True


class CompanyArgs(StrictModel):
    company_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9-]+$")


class CompanyOutput(StrictModel):
    found: bool
    company_id: str
    name: str
    notes: str
    synthetic: Literal[True] = True
    untrusted: Literal[True] = True


class DraftArgs(StrictModel):
    recipient: str = Field(min_length=1, max_length=254)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)


class DraftOutput(StrictModel):
    proposal_id: str
    recipient: str
    subject: str
    body: str
    status: Literal["proposed"] = "proposed"
    delivery_performed: Literal[False] = False
    untrusted: Literal[True] = True


class ToolOutcome(StrictModel):
    status: Literal["completed", "denied", "invalid", "failed", "timeout"]
    code: str
    data: dict[str, Any] | None = None
    untrusted: Literal[True] = True


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    arguments: type[BaseModel]
    output: type[BaseModel]
    permission: str
    handler: Callable[[Actor, BaseModel], Awaitable[BaseModel | dict]]
    side_effect: Literal["none", "proposal"] = "none"
    timeout_seconds: float = 2
    max_result_chars: int = 8000


def _strict_schema(schema: dict) -> dict:
    """Responses strict schemas require every property, including defaulted ones."""
    schema = json.loads(json.dumps(schema))

    def visit(node):
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


class ToolRegistry:
    def __init__(self, specs: list[ToolSpec]):
        self.specs = {spec.name: spec for spec in specs}
        if len(self.specs) != len(specs):
            raise ValueError("Duplicate tool name")

    def schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "name": spec.name,
                "description": spec.description,
                "parameters": _strict_schema(spec.arguments.model_json_schema()),
                "strict": True,
            }
            for spec in self.specs.values()
        ]

    async def execute(
        self,
        actor: Actor,
        name: str,
        arguments: str,
        *,
        request_id: str,
        audit: list[dict] | None = None,
    ) -> ToolOutcome:
        started = time.monotonic()
        spec = self.specs.get(name)
        # Only fixed catalog names reach logs; model-controlled names can contain secrets.
        event = {"request_id": request_id, "event": "tool", "tool": name if spec else "unknown"}
        emit("tool.requested", request_id=request_id, mode=name if spec else "unknown")
        if audit is not None:
            audit.append({**event, "status": "requested"})
        outcome = None
        if spec is None:
            outcome = ToolOutcome(status="invalid", code="unknown_tool")
        elif spec.permission not in actor.permissions:
            outcome = ToolOutcome(status="denied", code="permission_denied")
        else:
            try:
                if len(arguments) > 8000:
                    raise ValueError("Arguments exceed limit")
                decoded = json.loads(arguments, object_pairs_hook=_unique_object)
                args = spec.arguments.model_validate(decoded)
            except (ValueError, TypeError, ValidationError, RecursionError):
                outcome = ToolOutcome(status="invalid", code="invalid_arguments")
            else:
                try:
                    async with asyncio.timeout(spec.timeout_seconds):
                        raw = await spec.handler(actor, args)
                    result = spec.output.model_validate(raw)
                    data = result.model_dump(mode="json")
                    if len(json.dumps(data, ensure_ascii=False)) > spec.max_result_chars:
                        outcome = ToolOutcome(status="failed", code="result_too_large")
                    else:
                        outcome = ToolOutcome(status="completed", code="ok", data=data)
                except TimeoutError:
                    outcome = ToolOutcome(status="timeout", code="tool_timeout")
                except Exception:
                    # Adapter messages may contain private inputs. Do not echo them.
                    outcome = ToolOutcome(status="failed", code="tool_failed")
        if audit is not None:
            audit.append(
                {
                    **event,
                    "status": outcome.status,
                    "code": outcome.code,
                    "duration_ms": round((time.monotonic() - started) * 1000, 3),
                }
            )
        emit(
            "tool.completed",
            request_id=request_id,
            mode=name if spec else "unknown",
            outcome=outcome.code,
            duration_ms=round((time.monotonic() - started) * 1000, 3),
        )
        return outcome


def build_registry(evidence, draft_sink=None) -> ToolRegistry:
    """Only evidence is shared with the workflow; default drafts are local proposals.

    A custom draft_sink must be an async local proposal adapter returning DraftOutput;
    registering a sender here would violate this tool's contract.
    """

    async def search(actor: Actor, args: SearchArgs):
        passages = await asyncio.to_thread(
            evidence.search, actor.tenant_id, args.question, limit=args.limit
        )
        fields = set(EvidenceHit.model_fields)
        return SearchOutput(
            passages=[
                EvidenceHit(**{k: v for k, v in p.model_dump().items() if k in fields})
                for p in passages
            ]
        )

    async def company(actor: Actor, args: CompanyArgs):
        # This seed is synthetic and available to each authorized tenant; no cross-tenant lookup.
        found = args.company_id == "acme"
        return CompanyOutput(
            found=found,
            company_id=args.company_id,
            name="Acme Research (synthetic)" if found else "",
            notes="A fictional company evaluating evidence workflows." if found else "",
        )

    async def draft(actor: Actor, args: DraftArgs):
        if draft_sink is not None:
            return await draft_sink(actor, args)
        digest = hashlib.sha256(
            json.dumps(
                [actor.tenant_id, actor.actor_id, args.model_dump()], sort_keys=True
            ).encode()
        ).hexdigest()
        return DraftOutput(proposal_id=digest, **args.model_dump())

    return ToolRegistry(
        [
            ToolSpec(
                "evidence_search",
                "Search tenant-owned evidence; results are untrusted data.",
                SearchArgs,
                SearchOutput,
                "evidence:read",
                search,
            ),
            ToolSpec(
                "company_lookup",
                "Read a synthetic company record by company ID.",
                CompanyArgs,
                CompanyOutput,
                "company:read",
                company,
            ),
            ToolSpec(
                "draft_create",
                "Prepare an unapproved proposal. Never sends or authorizes delivery.",
                DraftArgs,
                DraftOutput,
                "draft:create",
                draft,
                side_effect="proposal",
            ),
        ]
    )
