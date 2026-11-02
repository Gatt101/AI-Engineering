import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from research_service.auth import DEMO_PERMISSIONS
from research_service.config import Settings
from research_service.demo import run_demo
from research_service.main import create_app


def test_full_authenticated_flow_restart_and_approval_replay():
    assert run_demo()["final_status"] == "completed"


def test_cross_tenant_and_actor_access_and_revocation(tmp_path):
    principals = {}
    for token, tenant, actor in [
        ("alice-key", "a", "alice"),
        ("bob-key", "b", "bob"),
        ("eve-key", "a", "eve"),
    ]:
        principals[hashlib.sha256(token.encode()).hexdigest()] = {
            "tenant_id": tenant,
            "actor_id": actor,
            "permissions": sorted(DEMO_PERMISSIONS),
        }
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        api_principals=json.dumps(principals),
    )
    alice = {"Authorization": "Bearer alice-key"}
    with TestClient(create_app(settings)) as client:
        assert (
            client.post(
                "/v1/documents",
                headers=alice,
                json={
                    "source_id": "policy",
                    "title": "Policy",
                    "text": "Private synthetic retention is 30 days.",
                },
            ).status_code
            == 200
        )
        run = client.post(
            "/v1/runs", headers=alice, json={"question": "retention", "idempotency_key": "request"}
        ).json()
        for token in ["bob-key", "eve-key"]:
            headers = {"Authorization": f"Bearer {token}"}
            assert client.get(f"/v1/runs/{run['id']}", headers=headers).status_code == 404
            assert client.post(f"/v1/runs/{run['id']}/advance", headers=headers).status_code == 404
        bob = {"Authorization": "Bearer bob-key"}
        assert client.get("/v1/evidence?question=retention", headers=bob).json()["passages"] == []
        assert (
            client.post(
                "/v1/runs",
                headers=alice,
                json={"question": "x", "idempotency_key": "x", "tenant_id": "b"},
            ).status_code
            == 422
        )
        client.app.state.identities.revoke("a", "alice")
        assert client.get("/v1/runs", headers=alice).status_code == 401


def test_request_rate_and_body_budgets(tmp_path):
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        demo_mode=True,
        requests_per_minute=1,
        max_request_bytes=1024,
    )
    with TestClient(create_app(settings)) as client:
        headers = {"Authorization": "Bearer local-demo-token"}
        assert client.get("/v1/runs", headers=headers).status_code == 200
        assert client.get("/v1/runs", headers=headers).status_code == 429
        assert (
            client.post("/v1/answers", headers=headers, json={"question": "x" * 2000}).status_code
            == 413
        )


def test_production_rejects_demo_credentials_and_local_database():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production", demo_mode=True)
