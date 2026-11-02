"""Request budgets, error normalization, structured logs, and streaming semantics."""

import asyncio
import json
import logging
import time
from contextlib import contextmanager

from openai import APIConnectionError, APIResponseValidationError, APIStatusError, APITimeoutError

from research_sdk.provider import OpenAIProvider, ResearchError, read_result

logger = logging.getLogger("researchops")


@contextmanager
def safe_errors():
    # Never return str(exc): provider errors can contain prompts or credentials.
    try:
        yield
    except (TimeoutError, APITimeoutError) as exc:
        raise ResearchError("timeout", "The request exceeded its time budget.", 504) from exc
    except APIConnectionError as exc:
        raise ResearchError("connection_error", "Could not reach the model provider.", 502) from exc
    except APIResponseValidationError as exc:
        raise ResearchError(
            "malformed_output", "The provider returned an invalid response."
        ) from exc
    except APIStatusError as exc:
        code = "rate_limited" if exc.status_code == 429 else "provider_error"
        status = 503 if exc.status_code in (401, 403, 429) else 502
        raise ResearchError(
            code, "The model provider could not fulfill this request.", status
        ) from exc
    except (ValueError, AttributeError, TypeError, KeyError) as exc:
        raise ResearchError(
            "malformed_output", "The provider returned an invalid response."
        ) from exc


class ResearchService:
    def __init__(self, provider: OpenAIProvider):
        self.provider = provider

    def record(self, request_id, started, outcome, result=None):
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    "outcome": outcome,
                    "model": self.provider.settings.openai_model,
                    "usage": result.usage.model_dump() if result and result.usage else None,
                }
            )
        )

    async def answer(self, question: str, request_id: str):
        started = time.monotonic()
        try:
            # SDK timeout applies per attempt; this outer deadline includes retries/backoff.
            with safe_errors():
                async with asyncio.timeout(self.provider.settings.request_timeout_seconds):
                    result = await self.provider.answer(question, request_id)
            self.record(request_id, started, result.status, result)
            return result
        except ResearchError as exc:
            self.record(request_id, started, exc.code)
            raise
        except asyncio.CancelledError:
            self.record(request_id, started, "cancelled")
            raise

    async def events(self, question: str, request_id: str):
        started = time.monotonic()
        terminal = False
        try:
            yield {"event": "start", "data": {"request_id": request_id}}
            with safe_errors():
                async with asyncio.timeout(self.provider.settings.request_timeout_seconds):
                    async with self.provider.stream(question) as stream:
                        async for event in stream:
                            if event.type == "response.output_text.delta":
                                yield {"event": "delta", "data": {"text": event.delta}}
                            elif event.type in ("response.completed", "response.incomplete"):
                                result = read_result(event.response, request_id)
                                self.record(request_id, started, result.status, result)
                                terminal = True
                                yield {"event": "done", "data": result.model_dump()}
                                return
                            elif event.type in ("error", "response.failed"):
                                raise ResearchError(
                                    "provider_failed", "The provider stream failed."
                                )
                        raise ResearchError(
                            "interrupted_stream", "The stream ended before completion."
                        )
        except ResearchError as exc:
            self.record(request_id, started, exc.code)
            terminal = True
            # HTTP headers have already been sent. An SSE error, not HTTP 200 alone,
            # tells the client this request failed. Never replay a partially emitted stream.
            yield {
                "event": "error",
                "data": {
                    "request_id": request_id,
                    "error": {"code": exc.code, "message": exc.message},
                },
            }
        finally:
            if not terminal:
                self.record(request_id, started, "cancelled")
