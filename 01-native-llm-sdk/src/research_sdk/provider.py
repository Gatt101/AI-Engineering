"""Native SDK boundary: Responses API inputs, events, and safe output validation."""

from contextlib import asynccontextmanager

from openai import AsyncOpenAI
from openai.types.responses import Response

from research_sdk.config import Settings
from research_sdk.schemas import ResearchResult, Usage

PROMPT_VERSION = "stage01-v1"
INSTRUCTIONS = """You are a research-question assistant. Explain clearly and concisely.
You have no web search, retrieval, or external tools. Do not claim you searched,
verified current facts, or accessed private data. State uncertainty and ask for
clarification when necessary. Do not invent citations or private information."""


class ResearchError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 502):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def read_result(response: Response, request_id: str) -> ResearchResult:
    # A refusal is a distinct outcome, not a successful empty answer.
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "refusal":
                    raise ResearchError("refused", "The model declined this request.", 422)
    if response.status not in ("completed", "incomplete"):
        raise ResearchError("provider_failed", "The provider did not complete the request.")
    if not response.output_text.strip():
        raise ResearchError("empty_output", "The provider returned no answer text.")
    usage = None
    if response.usage:
        usage = Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.total_tokens,
        )
    return ResearchResult(
        request_id=request_id,
        answer=response.output_text,
        status=response.status,
        model=response.model,
        usage=usage,
    )


class OpenAIProvider:
    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None):
        self.settings = settings
        self.client = client

    def require_client(self) -> AsyncOpenAI:
        if self.client is None:
            raise ResearchError("not_configured", "Set OPENAI_API_KEY in your local .env.", 503)
        return self.client

    def parameters(self, question: str) -> dict:
        return {
            "model": self.settings.openai_model,
            "instructions": INSTRUCTIONS,
            "input": question,
            "max_output_tokens": self.settings.max_output_tokens,
            # Avoid creating stored Responses for this stateless learning project.
            "store": False,
        }

    async def answer(self, question: str, request_id: str) -> ResearchResult:
        response = await self.require_client().responses.create(**self.parameters(question))
        return read_result(response, request_id)

    @asynccontextmanager
    async def stream(self, question: str):
        # The context manager closes the upstream connection on failure/cancellation.
        stream = await self.require_client().responses.create(
            **self.parameters(question), stream=True
        )
        async with stream:
            yield stream
