"""Server-owned identity and revocable permissions for local/staging machine clients."""

import hashlib
import json
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Annotated

from fastapi import Depends, Header, Request
from research_sdk.provider import ResearchError
from research_tools.tools import Actor

from research_service.config import Settings

DEMO_PERMISSIONS = frozenset(
    {
        "evidence:read",
        "evidence:write",
        "company:read",
        "draft:create",
        "run:create",
        "run:read",
        "run:advance",
        "action:approve",
        "deliver",
        "agent:run",
        "research:run",
    }
)


class IdentityRegistry:
    def __init__(self, settings: Settings):
        self.demo_mode = settings.demo_mode
        self.limit = settings.requests_per_minute
        self.lock = Lock()
        self.requests = defaultdict(deque)
        self.principals: dict[str, Actor] = {}
        entries = json.loads(settings.api_principals.get_secret_value())
        if not isinstance(entries, dict):
            raise ValueError("API_PRINCIPALS must be a JSON object.")
        for digest, principal in entries.items():
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("API_PRINCIPALS keys must be SHA-256 token digests.")
            self.principals[digest] = Actor.model_validate_json(json.dumps(principal))
        if self.demo_mode:
            self.principals[hashlib.sha256(b"local-demo-token").hexdigest()] = Actor(
                actor_id="demo-user", tenant_id="demo", permissions=DEMO_PERMISSIONS
            )

    def authenticate(self, authorization: str | None) -> Actor:
        if not authorization or not authorization.startswith("Bearer "):
            raise ResearchError("unauthenticated", "A bearer token is required.", 401)
        digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
        actor = self.principals.get(digest)
        if actor is None:
            raise ResearchError("unauthenticated", "Invalid credentials.", 401)
        key = (actor.tenant_id, actor.actor_id)
        with self.lock:
            window = self.requests[key]
            now = time.monotonic()
            while window and window[0] <= now - 60:
                window.popleft()
            if len(window) >= self.limit:
                raise ResearchError("rate_limited", "Request budget exceeded.", 429)
            window.append(now)
        return actor

    def authorize(self, tenant_id: str, actor_id: str, permission: str) -> bool:
        return any(
            actor.tenant_id == tenant_id
            and actor.actor_id == actor_id
            and permission in actor.permissions
            for actor in self.principals.values()
        )

    def revoke(self, tenant_id: str, actor_id: str) -> None:
        self.principals = {
            key: actor
            for key, actor in self.principals.items()
            if (actor.tenant_id, actor.actor_id) != (tenant_id, actor_id)
        }


def current_actor(request: Request, authorization: Annotated[str | None, Header()] = None) -> Actor:
    return request.app.state.identities.authenticate(authorization)


ActorDep = Annotated[Actor, Depends(current_actor)]


def require(actor: Actor, permission: str) -> None:
    if permission not in actor.permissions:
        raise ResearchError("forbidden", "This action is not permitted.", 403)
