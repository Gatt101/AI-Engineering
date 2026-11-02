"""Authenticated API scenario using synthetic data and a temporary database."""

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from research_tools.agent import AgentService, AgentTurn, ScriptedAgentProvider, ToolCall
from research_tools.tools import build_registry

from research_service.config import Settings
from research_service.main import create_app


def run_demo():
    with tempfile.TemporaryDirectory() as directory:
        settings = Settings(
            _env_file=None,
            openai_api_key=None,
            demo_mode=True,
            database_url=f"sqlite:///{Path(directory) / 'demo.db'}",
        )
        headers = {"Authorization": "Bearer local-demo-token"}
        with TestClient(create_app(settings)) as client:
            assert client.get("/ready").status_code == 200
            assert client.get("/v1/runs").status_code == 401
            answer = client.post(
                "/v1/answers", headers=headers, json={"question": "Acme retention deletion"}
            ).json()
            assert answer["status"] == "answered" and answer["citations"]
            client.app.state.agent = AgentService(
                ScriptedAgentProvider(
                    [
                        AgentTurn(
                            calls=[
                                ToolCall(
                                    "search",
                                    "evidence_search",
                                    '{"question":"Acme retention deletion","limit":3}',
                                )
                            ]
                        ),
                        AgentTurn(calls=[ToolCall("send", "send_email", "{}")]),
                        AgentTurn(text="Delivery tool unavailable; approval is required."),
                    ]
                ),
                build_registry(client.app.state.evidence),
            )
            trajectory = client.post(
                "/v1/agent",
                headers=headers,
                json={"question": "Research Acme and send a follow-up"},
            )
            assert trajectory.status_code == 200, trajectory.text
            audit = trajectory.json()["audit"]
            assert any(item.get("status") == "invalid" for item in audit)
            body = {"question": "Acme retention deletion", "idempotency_key": "demo"}
            created = client.post("/v1/runs", headers=headers, json=body)
            assert created.status_code == 201, created.text
            run = created.json()
            duplicate = client.post("/v1/runs", headers=headers, json=body).json()
            assert duplicate["id"] == run["id"]
            path = f"/v1/runs/{run['id']}"
            for _ in range(2):
                step = client.post(path + "/advance", headers=headers)
                assert step.status_code == 200, step.text
            draft = client.get(path, headers=headers).json()
            assert draft["status"] == "awaiting_approval"
            action = draft["action"]
            approved = client.post(
                f"/v1/actions/{action['id']}/approve",
                headers=headers,
                json={"expected_version": action["version"]},
            )
            assert approved.status_code == 200, approved.text
        # Recreate the entire application: persisted approved work survives restart.
        with TestClient(create_app(settings)) as client:
            completed = client.post(path + "/advance", headers=headers).json()["run"]
            assert completed["status"] == "completed", completed
            replay = client.post(
                f"/v1/actions/{action['id']}/approve",
                headers=headers,
                json={"expected_version": action["version"]},
            )
            assert replay.status_code == 409
            return {
                "api_flow": "passed",
                "answer_mode": answer["mode"],
                "citations": len(answer["citations"]),
                "restart": "passed",
                "idempotency": "passed",
                "approval_replay": "denied",
                "unauthenticated_access": "denied",
                "delivery": "fake",
                "final_status": completed["status"],
            }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
