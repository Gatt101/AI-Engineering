"""HTTP boundary. Run with: uv run fastapi dev (localhost only)."""

import logging
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from openai import AsyncOpenAI

from research_sdk.config import Settings
from research_sdk.provider import OpenAIProvider, ResearchError
from research_sdk.schemas import ErrorDetail, ErrorResponse, ResearchRequest, ResearchResult
from research_sdk.service import ResearchService


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
        try:
            yield
        finally:
            if client:
                await client.close()

    application = FastAPI(title="ResearchOps Assistant", version="0.2.0", lifespan=lifespan)

    @application.middleware("http")
    async def request_id(request: Request, call_next):
        # Generate IDs ourselves rather than trusting arbitrary log content from a header.
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

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

    @application.post("/research")
    async def research(
        body: ResearchRequest, request: Request, service: ServiceDep
    ) -> ResearchResult:
        return await service.answer(body.question, request.state.request_id)

    @application.post("/research/stream", response_class=EventSourceResponse)
    async def research_stream(body: ResearchRequest, request: Request, service: StreamServiceDep):
        async for item in service.events(body.question, request.state.request_id):
            yield ServerSentEvent(event=item["event"], data=item["data"])

    return application


logging.basicConfig(level=logging.INFO, format="%(message)s")
# Suppress third-party request logs; our own logs never contain prompt bodies.
logging.getLogger("httpx").setLevel(logging.WARNING)
app = create_app()
