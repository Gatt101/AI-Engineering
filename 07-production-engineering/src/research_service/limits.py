"""ASGI admission and body limits hold through the entire streamed response."""

import asyncio

from starlette.responses import JSONResponse


class ResourceLimits:
    def __init__(self, app, *, max_bytes=131072, concurrency=16):
        self.app = app
        self.max_bytes = max_bytes
        self.concurrency = concurrency
        self.active = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if self.active >= self.concurrency:
            return await JSONResponse({"error": {"code": "overloaded"}}, 429)(scope, receive, send)
        self.active += 1
        try:
            chunks = []
            total = 0
            try:
                async with asyncio.timeout(10):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        total += len(message.get("body", b""))
                        if total > self.max_bytes:
                            return await JSONResponse(
                                {"error": {"code": "request_too_large"}}, 413
                            )(scope, receive, send)
                        chunks.append(message)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                return await JSONResponse({"error": {"code": "body_timeout"}}, 408)(
                    scope, receive, send
                )
            cursor = 0

            async def bounded_receive():
                nonlocal cursor
                if cursor < len(chunks):
                    message = chunks[cursor]
                    cursor += 1
                    return message
                return await receive()

            await self.app(scope, bounded_receive, send)
        finally:
            self.active -= 1
