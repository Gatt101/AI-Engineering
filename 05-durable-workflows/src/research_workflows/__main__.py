"""Exercise checkpoints, exact approval, interruption, and receipt reconciliation."""

import json
import tempfile
from pathlib import Path

from research_evidence.retrieval import EvidenceService, seed_corpus
from research_state.db import Database
from research_state.store import WorkflowStore

from research_workflows.workflows import WorkerCrash, WorkflowWorker


def run_demo():
    with tempfile.TemporaryDirectory() as directory:
        url = f"sqlite:///{Path(directory) / 'workflow.db'}"
        database = Database(url, migrate=True)
        now = [100.0]
        store = WorkflowStore(database.engine, clock=lambda: now[0])
        evidence = EvidenceService(database.engine, create_schema=False)
        seed_corpus(evidence)
        run = store.create_run("demo", "researcher", "Acme retention deletion", "demo")
        worker = WorkflowWorker(store, evidence, lambda *_: True, lease_seconds=1)
        worker.tick()
        draft = worker.tick()
        assert draft["status"] == "awaiting_approval"
        action = draft["action"]
        store.approve("demo", "researcher", action["id"], action["version"])
        worker.crash_after_send = True
        try:
            worker.tick()
        except WorkerCrash:
            pass
        receipt_before = worker.provider.lookup(action["id"])
        database.close()
        database = Database(url)
        try:
            now[0] += 2
            store = WorkflowStore(database.engine, clock=lambda: now[0])
            evidence = EvidenceService(database.engine, create_schema=False)
            recovered = WorkflowWorker(store, evidence, lambda *_: True).tick()
            assert recovered["status"] == "completed"
            assert recovered["action"]["receipt"] == receipt_before
            return {
                "recovery_success": True,
                "receipt_deduplicated": True,
                "status": recovered["status"],
                "delivery": "fake",
                "audit": store.audit("demo", "researcher", run["id"]),
            }
        finally:
            database.close()


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
