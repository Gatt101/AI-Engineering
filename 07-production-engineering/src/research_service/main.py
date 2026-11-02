"""HTTP boundary. Run with: uv run fastapi dev (localhost only)."""

import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from openai import AsyncOpenAI
from research_evidence.retrieval import EvidenceService, seed_corpus
from research_sdk.provider import OpenAIProvider, ResearchError
from research_sdk.schemas import ErrorDetail, ErrorResponse, ResearchRequest, ResearchResult
from research_sdk.service import ResearchService
from research_sdk.telemetry import emit, trace_id
from research_state.db import Database
from research_state.store import StateError, WorkflowStore
from research_tools.agent import AgentService, OpenAIAgentProvider
from research_tools.tools import build_registry
from research_workflows.workflows import WorkflowWorker

from research_service.api import router
from research_service.auth import IdentityRegistry, require
from research_service.config import Settings
from research_service.limits import ResourceLimits


def get_service(request: Request) -> ResearchService:
    return request.app.state.service


ServiceDep = Annotated[ResearchService, Depends(get_service)]


def get_stream_service(request: Request) -> ResearchService:
    service = get_service(request)
    # Dependencies run before streaming headers are sent, unlike the generator body.
    service.provider.require_client()
    return service


StreamServiceDep = Annotated[ResearchService, Depends(get_stream_service)]


def create_app(settings: Settings | None = None, provider: OpenAIProvider | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        client = None
        if provider is None and config.configured:
            client = AsyncOpenAI(
                api_key=config.openai_api_key.get_secret_value(),
                timeout=config.request_timeout_seconds,
                max_retries=config.openai_max_retries,
                _strict_response_validation=True,
            )
        application.state.service = ResearchService(provider or OpenAIProvider(config, client))
        application.state.settings = config
        application.state.identities = IdentityRegistry(config)
        database = Database(config.database_url)
        if config.auto_migrate:
            database.migrate()
        else:
            database.validate_schema()
        application.state.database = database
        application.state.evidence = EvidenceService(database.engine, create_schema=False)
        if config.demo_mode:
            seed_corpus(application.state.evidence, "demo")
        application.state.store = WorkflowStore(database.engine)
        application.state.worker = WorkflowWorker(
            application.state.store,
            application.state.evidence,
            authorize=application.state.identities.authorize,
        )
        application.state.agent = AgentService(
            OpenAIAgentProvider(
                client if provider is None else provider.client,
                config.openai_model,
                config.max_output_tokens,
            ),
            build_registry(application.state.evidence),
        )
        try:
            yield
        finally:
            database.close()
            if client:
                await client.close()

    application = FastAPI(title="ResearchOps Assistant", version="0.2.0", lifespan=lifespan)
    application.add_middleware(
        ResourceLimits,
        max_bytes=config.max_request_bytes,
        concurrency=config.max_concurrent_requests,
    )
    application.include_router(router)

    @application.middleware("http")
    async def request_id(request: Request, call_next):
        # Generate IDs ourselves rather than trusting arbitrary log content from a header.
        request.state.request_id = str(uuid4())
        token = trace_id.set(request.state.request_id)
        started = time.monotonic()
        try:
            emit("api.started")
            response = await call_next(request)
            response.headers["X-Request-ID"] = request.state.request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Cache-Control"] = "no-store"
            emit(
                "api.completed",
                status_code=response.status_code,
                duration_ms=round((time.monotonic() - started) * 1000, 2),
            )
            return response
        finally:
            trace_id.reset(token)

    @application.exception_handler(StateError)
    async def state_error(request: Request, exc: StateError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "request_id": request.state.request_id,
                "error": {"code": exc.code, "message": exc.message},
            },
        )

    @application.exception_handler(ResearchError)
    async def research_error(request: Request, exc: ResearchError):
        body = ErrorResponse(
            request_id=request.state.request_id,
            error=ErrorDetail(code=exc.code, message=exc.message),
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        # FastAPI's default validation body echoes invalid input; keep ours redacted.
        return JSONResponse(
            status_code=422,
            content={
                "request_id": request.state.request_id,
                "error": {
                    "code": "invalid_request",
                    "message": "Request fields do not match the documented contract.",
                },
            },
        )

    @application.get("/health")
    async def health():
        return {
            "status": "ok",
            "provider_configured": application.state.service.provider.client is not None,
        }

    @application.get("/ready")
    def ready():
        try:
            application.state.database.validate_schema()
        except Exception:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        return {"status": "ready", "delivery": "fake"}

    async def legacy_access(request: Request):
        # Preserve stage01's loopback learning client; hosted mode always authenticates.
        if config.environment == "production" or application.state.identities.principals:
            actor = application.state.identities.authenticate(request.headers.get("Authorization"))
            require(actor, "research:run")

    @application.post("/research", dependencies=[Depends(legacy_access)])
    async def research(
        body: ResearchRequest, request: Request, service: ServiceDep
    ) -> ResearchResult:
        return await service.answer(body.question, request.state.request_id)

    @application.post(
        "/research/stream",
        response_class=EventSourceResponse,
        dependencies=[Depends(legacy_access)],
    )
    async def research_stream(body: ResearchRequest, request: Request, service: StreamServiceDep):
        async for item in service.events(body.question, request.state.request_id):
            yield ServerSentEvent(event=item["event"], data=item["data"])

    return application


logging.basicConfig(level=logging.INFO, format="%(message)s")
# Suppress third-party request logs; our own logs never contain prompt bodies.
logging.getLogger("httpx").setLevel(logging.WARNING)
app = create_app()
