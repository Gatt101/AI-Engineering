import json
import logging

from research_service.demo import run_demo


def test_failure_trace_links_api_model_tools_and_workflow_without_prompts(caplog):
    with caplog.at_level(logging.INFO, logger="researchops.trace"):
        run_demo()
    records = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "researchops.trace"
    ]
    failed_tool = next(
        record
        for record in records
        if record["event"] == "tool.completed" and record.get("outcome") == "unknown_tool"
    )
    chain = [record["event"] for record in records if record["trace_id"] == failed_tool["trace_id"]]
    assert {"api.started", "model.started", "tool.completed", "api.completed"} <= set(chain)
    assert any(record["event"] == "workflow.claimed" for record in records)
    serialized = json.dumps(records)
    assert "Research Acme and send" not in serialized
    assert "local-demo-token" not in serialized
