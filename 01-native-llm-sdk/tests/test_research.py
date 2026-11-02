"""Exercise the real OpenAI SDK over fake HTTP: no credentials/network required."""

import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import AsyncOpenAI
from research_sdk.config import Settings
from research_sdk.main import create_app
from research_sdk.provider import OpenAIProvider, ResearchError
from research_sdk.service import ResearchService


def response_body(text="A language model predicts tokens.", status="completed"):
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 1,
        "model": "test-model",
        "status": status,
        "error": None,
        "incomplete_details": {"reason": "max_output_tokens"} if status == "incomplete" else None,
        "instructions": None,
        "metadata": {},
        "parallel_tool_calls": True,
        "temperature": 1,
        "tool_choice": "auto",
        "tools": [],
        "top_p": 1,
        "output": [
            {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
        "usage": {
            "input_tokens": 10,
            "output_tokens": 6,
            "total_tokens": 16,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }


@asynccontextmanager
async def provider_for(handler, **overrides):
    settings = Settings(_env_file=None, openai_api_key="fake-key", **overrides)
    async with AsyncOpenAI(
        api_key="fake-key",
        max_retries=settings.openai_max_retries,
        _strict_response_validation=True,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as client:
        yield OpenAIProvider(settings, client)


async def test_success_and_native_request():
    def handler(request):
        payload = json.loads(request.content)
        assert request.url.path == "/v1/responses"
        assert payload["input"] == "What is an LLM?"
        assert payload["store"] is False
        assert payload["max_output_tokens"] == 1024
        assert "no web search" in payload["instructions"]
        return httpx.Response(200, json=response_body())

    async with provider_for(handler) as provider:
        result = await ResearchService(provider).answer("What is an LLM?", "id1")
    assert result.status == "completed"
    assert result.usage.total_tokens == 16
    assert result.request_id == "id1"


@pytest.mark.parametrize(
    "status,expected",
    [
        (400, "provider_error"),
        (401, "provider_error"),
        (403, "provider_error"),
        (429, "rate_limited"),
        (500, "provider_error"),
    ],
)
async def test_retry_policy_and_redacted_errors(status, expected):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            status,
            json={"error": {"message": "secret-prompt fake-key"}},
            headers={"retry-after-ms": "1"},
        )

    async with provider_for(handler) as provider:
        with pytest.raises(ResearchError) as caught:
            await ResearchService(provider).answer("secret-prompt", "id1")
    assert caught.value.code == expected
    assert "fake-key" not in str(caught.value)
    assert "secret-prompt" not in str(caught.value)
    assert calls == (3 if status in (429, 500) else 1)


async def test_retry_then_success():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429, json={"error": {"message": "busy"}}, headers={"retry-after-ms": "1"}
            )
        return httpx.Response(200, json=response_body())

    async with provider_for(handler) as provider:
        assert (await ResearchService(provider).answer("hello", "id")).status == "completed"
    assert calls == 2


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("empty", "empty_output"),
        ("malformed", "malformed_output"),
        ("refusal", "refused"),
        ("failed", "provider_failed"),
    ],
)
async def test_bad_model_output(kind, expected):
    body = response_body("" if kind == "empty" else "answer")
    if kind == "malformed":
        body = {"output": "wrong-type"}
    elif kind == "refusal":
        body["output"][0]["content"] = [{"type": "refusal", "refusal": "private refusal"}]
    elif kind == "failed":
        body["status"] = "failed"
    async with provider_for(lambda r: httpx.Response(200, json=body)) as provider:
        with pytest.raises(ResearchError) as caught:
            await ResearchService(provider).answer("hello", "id")
    assert caught.value.code == expected


async def test_incomplete_is_not_reported_as_complete():
    async with provider_for(
        lambda r: httpx.Response(200, json=response_body("Partial", "incomplete"))
    ) as provider:
        result = await ResearchService(provider).answer("hello", "id")
    assert result.status == "incomplete"


async def test_total_deadline():
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=response_body())

    async with provider_for(handler, request_timeout_seconds=0.01) as provider:
        with pytest.raises(ResearchError) as caught:
            await ResearchService(provider).answer("hello", "id")
    assert caught.value.code == "timeout"


@pytest.mark.parametrize(
    "exception,expected", [(httpx.ConnectError, "connection_error"), (httpx.ReadTimeout, "timeout")]
)
async def test_transport_errors(exception, expected):
    def handler(request):
        raise exception("private detail", request=request)

    async with provider_for(handler, openai_max_retries=0) as provider:
        with pytest.raises(ResearchError) as caught:
            await ResearchService(provider).answer("hello", "id")
    assert caught.value.code == expected


def test_http_validation_health_missing_key():
    with TestClient(create_app(Settings(_env_file=None, openai_api_key=""))) as client:
        assert client.get("/health").json() == {"status": "ok", "provider_configured": False}
        for body in (
            {},
            {"question": "  "},
            {"question": "x" * 8001},
            {"question": "hi", "extra": "secret"},
        ):
            result = client.post("/research", json=body)
            assert result.status_code == 422
            assert result.json()["error"]["code"] == "invalid_request"
            assert result.headers["x-request-id"] == result.json()["request_id"]
        for path in ("/research", "/research/stream"):
            assert client.post(path, json={"question": "hello"}).status_code == 503


@pytest.mark.parametrize("ending", ["completed", "incomplete", "interrupted", "failed"])
async def test_real_sdk_stream(ending):
    events = [
        {
            "type": "response.output_text.delta",
            "delta": "Hello",
            "sequence_number": 0,
            "item_id": "msg_test",
            "output_index": 0,
            "content_index": 0,
            "logprobs": [],
        }
    ]
    if ending in ("completed", "incomplete"):
        events.append(
            {
                "type": f"response.{ending}",
                "sequence_number": 1,
                "response": response_body("Hello", ending),
            }
        )
    elif ending == "failed":
        events.append(
            {
                "type": "error",
                "sequence_number": 1,
                "code": "server_error",
                "message": "secret",
                "param": None,
            }
        )
    wire = "".join(f"data: {json.dumps(e)}\n\n" for e in events)
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(200, text=wire, headers={"content-type": "text/event-stream"})

    async with provider_for(handler) as provider:
        results = [event async for event in ResearchService(provider).events("hi", "id")]
    assert results[1] == {"event": "delta", "data": {"text": "Hello"}}
    assert results[-1]["event"] == ("done" if ending in ("completed", "incomplete") else "error")
    assert calls == 1  # Never replay a partial stream.


async def test_cancellation_closes_stream(caplog):
    closed = False

    class Provider:
        settings = Settings(_env_file=None)

        @asynccontextmanager
        async def stream(self, question):
            nonlocal closed

            async def events():
                yield SimpleNamespace(type="response.output_text.delta", delta="Hello")
                await asyncio.sleep(10)

            try:
                yield events()
            finally:
                closed = True

    async def consume():
        async for event in ResearchService(Provider()).events("private", "id"):
            if event["event"] == "delta":
                asyncio.current_task().cancel()

    task = asyncio.create_task(consume())
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed


async def test_structured_logs_do_not_contain_prompt(caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="researchops"):
        async with provider_for(lambda r: httpx.Response(200, json=response_body())) as provider:
            await ResearchService(provider).answer("private-question", "id")
    record = json.loads(next(r.message for r in caplog.records if r.name == "researchops"))
    assert record["usage"]["total_tokens"] == 16
    assert record["outcome"] == "completed"
    assert "private-question" not in caplog.text


async def test_http_success_and_sse_serialization():
    def handler(request):
        if json.loads(request.content).get("stream"):
            events = [
                {
                    "type": "response.output_text.delta",
                    "delta": "Hello",
                    "sequence_number": 0,
                    "item_id": "msg_test",
                    "output_index": 0,
                    "content_index": 0,
                    "logprobs": [],
                },
                {
                    "type": "response.completed",
                    "sequence_number": 1,
                    "response": response_body("Hello"),
                },
            ]
            return httpx.Response(
                200,
                text="".join(f"data: {json.dumps(event)}\n\n" for event in events),
                headers={"content-type": "text/event-stream"},
            )
        return httpx.Response(200, json=response_body())

    async with provider_for(handler) as provider:
        with TestClient(create_app(provider=provider)) as client:
            result = client.post("/research", json={"question": "hello"})
            assert result.status_code == 200
            assert result.json()["request_id"] == result.headers["x-request-id"]
            assert result.json()["usage"]["total_tokens"] == 16
            streamed = client.post("/research/stream", json={"question": "hello"})
            assert streamed.status_code == 200
            assert streamed.headers["content-type"].startswith("text/event-stream")
            assert "event: delta" in streamed.text
            assert "event: done" in streamed.text
            assert '"text":"Hello"' in streamed.text.replace(" ", "")


async def test_stream_timeout_error_and_cleanup():
    closed = False

    class Provider:
        settings = Settings(_env_file=None, request_timeout_seconds=0.01)

        @asynccontextmanager
        async def stream(self, question):
            nonlocal closed

            async def events():
                yield SimpleNamespace(type="response.output_text.delta", delta="Partial")
                await asyncio.sleep(10)

            try:
                yield events()
            finally:
                closed = True

    events = [event async for event in ResearchService(Provider()).events("hi", "id")]
    assert events[-1]["event"] == "error"
    assert events[-1]["data"]["error"]["code"] == "timeout"
    assert closed


async def test_http_stream_error_redacted():
    async with provider_for(
        lambda r: httpx.Response(
            200, text="data: {bad-json}\n\n", headers={"content-type": "text/event-stream"}
        )
    ) as provider:
        with TestClient(create_app(provider=provider)) as client:
            result = client.post("/research/stream", json={"question": "private"})
            assert result.status_code == 200
            assert "event: error" in result.text
            assert "malformed_output" in result.text
            assert "bad-json" not in result.text


async def test_deadline_includes_retry_delay():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            429, json={"error": {"message": "busy"}}, headers={"retry-after": "1"}
        )

    async with provider_for(handler, request_timeout_seconds=0.02) as provider:
        with pytest.raises(ResearchError, match="time budget"):
            await ResearchService(provider).answer("hello", "id")
    assert calls == 1
