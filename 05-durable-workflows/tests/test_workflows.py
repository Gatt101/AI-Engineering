"""Approval, lease, retry, and crash behavior against an actual transactional store."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from research_state.db import Database, actions, approvals, fake_receipts
from research_state.store import WorkflowStore
from research_workflows.workflows import (
    FakeDelivery,
    RetryableDeliveryError,
    StateError,
    WorkerCrash,
    WorkflowWorker,
)
from sqlalchemy import func, select, update


class Evidence:
    def answer(self, tenant_id, question):
        return {
            "answer": "A cited synthetic answer.",
            "status": "answered",
            "citations": [{"source_id": "test"}],
        }


@pytest.fixture
def context(database):
    clock = [100.0]
    store = WorkflowStore(database.engine, clock=lambda: clock[0])
    allowed = [True]
    worker = WorkflowWorker(store, Evidence(), lambda *_: allowed[0], lease_seconds=10)
    run = store.create_run("tenant", "actor", "question", "key")
    return store, worker, run, clock, allowed


def draft(context):
    store, worker, run, *_ = context
    assert worker.tick()["status"] == "researched"
    result = worker.tick()
    assert result["status"] == "awaiting_approval"
    return result["action"]


def approve(context):
    action = draft(context)
    context[0].approve("tenant", "actor", action["id"], action["version"])
    return action


def test_happy_path_and_replay(context):
    store, worker, run, *_ = context
    action = approve(context)
    with pytest.raises(StateError):
        store.approve("tenant", "actor", action["id"], action["version"])
    completed = worker.tick()
    assert completed["status"] == "completed"
    assert completed["action"]["receipt"].startswith("fake-")
    assert worker.tick() is None
    with pytest.raises(StateError):
        store.approve("tenant", "actor", action["id"], action["version"])
    assert "action.sent" in [event["event"] for event in store.audit("tenant", "actor", run["id"])]


def test_approval_ownership_is_never_model_supplied(context):
    store, *_ = context
    action = draft(context)
    for tenant, actor in [("evil", "actor"), ("tenant", "evil")]:
        with pytest.raises(StateError) as caught:
            store.approve(tenant, actor, action["id"], action["version"])
        assert caught.value.status_code == 404


def test_changed_payload_invalidates_old_approval(context):
    store, worker, *_ = context
    action = approve(context)
    revised = store.revise_action(
        "tenant",
        "actor",
        action["id"],
        action["version"],
        {"destination": "fake://outbox", "text": "Revised draft"},
    )
    assert revised["version"] == 2
    assert worker.tick() is None
    with pytest.raises(StateError):
        store.approve("tenant", "actor", action["id"], action["version"])
    store.approve("tenant", "actor", action["id"], revised["version"])
    assert worker.tick()["status"] == "completed"


def test_tampered_payload_fails_hash_binding(context):
    store, worker, *_ = context
    action = approve(context)
    with store.engine.begin() as connection:
        connection.execute(
            update(actions)
            .where(actions.c.id == action["id"])
            .values(payload={"destination": "fake://outbox", "text": "tampered"})
        )
    result = worker.tick()
    assert result["status"] == "failed"
    assert result["error_code"] == "invalid_approval"
    assert worker.provider.lookup(action["id"]) is None


def test_expired_approval_and_revocation(context):
    store, worker, _, clock, allowed = context
    action = draft(context)
    store.approve("tenant", "actor", action["id"], 1, expires_in_seconds=1)
    clock[0] += 2
    result = worker.tick()
    assert result["error_code"] == "invalid_approval"
    assert worker.provider.lookup(action["id"]) is None
    # A separate run has a valid approval, but current permission is revoked.
    store.create_run("tenant", "actor", "question", "another")
    worker.tick()
    action = worker.tick()["action"]
    store.approve("tenant", "actor", action["id"], 1)
    allowed[0] = False
    assert worker.tick()["error_code"] == "denied"
    assert worker.provider.lookup(action["id"]) is None


def test_rejection_is_terminal(context):
    store, worker, *_ = context
    action = draft(context)
    assert store.reject("tenant", "actor", action["id"], 1)["status"] == "rejected"
    with pytest.raises(StateError):
        store.approve("tenant", "actor", action["id"], 1)
    assert worker.tick() is None


def test_checkpoint_recovery_and_fenced_old_worker(context):
    store, worker, run, clock, _ = context
    claim = store.claim("crashed-worker", lease_seconds=1)
    assert worker.tick() is None
    clock[0] += 2
    assert worker.tick()["status"] == "researched"
    with pytest.raises(StateError, match="lease"):
        store.checkpoint(claim, "failed")
    assert worker.tick()["status"] == "awaiting_approval"


def test_crash_after_side_effect_recovers_receipt_without_second_effect(context):
    store, worker, run, clock, _ = context
    action = approve(context)
    worker.crash_after_send = True
    with pytest.raises(WorkerCrash):
        worker.tick()
    assert store.get_run("tenant", "actor", run["id"])["status"] == "dispatching"
    assert worker.tick() is None  # Lease prevents immediate duplicate dispatch.
    clock[0] += 11
    recovered = WorkflowWorker(store, Evidence(), lambda *_: True).tick()
    assert recovered["status"] == "completed"
    with store.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(fake_receipts)).scalar_one() == 1
        assert connection.execute(
            select(approvals.c.consumed).where(approvals.c.action_id == action["id"])
        ).scalar_one()


def test_indeterminate_non_idempotent_provider_requires_manual_review(context):
    class Ambiguous:
        idempotent = False
        calls = 0

        def deliver(self, *args):
            self.calls += 1
            raise TimeoutError("Ambiguous external response")

        def lookup(self, action_id):
            return None

    _, worker, *_ = context
    approve(context)
    worker.provider = Ambiguous()
    assert worker.tick()["status"] == "reconcile"
    assert worker.tick()["status"] == "manual_review"
    assert worker.tick() is None
    assert worker.provider.calls == 1


def test_retry_budget_stops_known_failures(context):
    class Transient(FakeDelivery):
        def deliver(self, *args):
            raise RetryableDeliveryError()

    store, worker, *_ = context
    approve(context)
    worker.provider = Transient(store.engine)
    assert worker.tick()["status"] == "reconcile"
    assert worker.tick()["status"] == "reconcile"
    result = worker.tick()
    assert result["status"] == "failed"
    assert result["attempts"] == 3
    assert result["error_code"] == "retries_exhausted"


def test_concurrent_workers_claim_once(context):
    store, *_ = context
    with ThreadPoolExecutor(max_workers=6) as pool:
        claims = list(pool.map(lambda index: store.claim(str(index)), range(10)))
    assert sum(claim is not None for claim in claims) == 1


def test_insufficient_evidence_never_generates_action(context):
    class Insufficient:
        def answer(self, *args):
            return {
                "answer": "Insufficient evidence",
                "status": "insufficient_evidence",
                "citations": [],
            }

    _, worker, *_ = context
    worker.evidence = Insufficient()
    result = worker.tick()
    assert result["status"] == "needs_review"
    assert result["action"] is None


def test_fake_provider_hash_conflict(context):
    _, worker, *_ = context
    action = approve(context)
    receipt = worker.provider.deliver(action["id"], action["payload"])
    assert worker.provider.deliver(action["id"], action["payload"]) == receipt
    with pytest.raises(StateError):
        worker.provider.deliver(action["id"], {"destination": "fake://outbox", "text": "other"})


def test_business_state_survives_restart_after_draft(tmp_path):
    url = f"sqlite:///{tmp_path / 'restart.db'}"
    db = Database(url, migrate=True)
    store = WorkflowStore(db.engine)
    worker = WorkflowWorker(store, Evidence(), lambda *_: True)
    run = store.create_run("tenant", "actor", "question", "key")
    worker.tick()
    draft = worker.tick()
    db.close()
    restarted = Database(url)
    recovered = WorkflowStore(restarted.engine).get_run("tenant", "actor", run["id"])
    assert recovered["brief"] == draft["brief"]
    assert recovered["draft"] == draft["draft"]
    assert recovered["action"]["id"] == draft["action"]["id"]
    assert recovered["status"] == "awaiting_approval"
    restarted.close()
