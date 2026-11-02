"""Checkpoint execution and fake delivery recovery."""

from uuid import uuid4

from research_sdk.telemetry import emit
from research_state.db import fake_receipts
from research_state.store import StateError, digest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError


class RetryableDeliveryError(Exception):
    pass


class UncertainDeliveryError(Exception):
    pass


class WorkerCrash(BaseException):
    pass


class FakeDelivery:
    """A local receipt ledger, not an email service. Stable keys deduplicate retries."""

    idempotent = True

    def __init__(self, engine):
        self.engine = engine

    def lookup(self, action_id):
        with self.engine.connect() as connection:
            return connection.execute(
                select(fake_receipts.c.receipt).where(fake_receipts.c.action_id == action_id)
            ).scalar_one_or_none()

    def deliver(self, action_id, payload):
        if payload.get("destination") != "fake://outbox":
            raise ValueError("Only the fake outbox is supported")
        receipt = "fake-" + str(uuid4())
        try:
            with self.engine.begin() as connection:
                connection.execute(
                    insert(fake_receipts).values(
                        action_id=action_id, payload_hash=digest(payload), receipt=receipt
                    )
                )
        except IntegrityError:
            with self.engine.connect() as connection:
                prior = (
                    connection.execute(
                        select(fake_receipts).where(fake_receipts.c.action_id == action_id)
                    )
                    .mappings()
                    .one()
                )
            if prior["payload_hash"] != digest(payload):
                raise StateError(
                    "delivery_conflict", "Delivery key already used for a different payload"
                )
            return prior["receipt"]
        return receipt


class WorkflowWorker:
    def __init__(
        self,
        store,
        evidence,
        authorize=None,
        provider=None,
        *,
        lease_seconds=30,
        max_attempts=3,
        crash_after_send=False,
    ):
        self.store, self.evidence = store, evidence
        self.authorize = authorize or (lambda tenant, actor, permission: False)
        self.provider = provider or FakeDelivery(store.engine)
        self.worker_id = str(uuid4())
        self.lease_seconds, self.max_attempts = lease_seconds, max_attempts
        self.crash_after_send = crash_after_send
        if not 1 <= max_attempts <= 10 or not 1 <= lease_seconds <= 300:
            raise ValueError("Worker lease/retry budget outside supported bounds")

    def tick(self, tenant_id=None, actor_id=None, run_id=None):
        run = self.store.claim(self.worker_id, self.lease_seconds, tenant_id, actor_id, run_id)
        if run is None:
            return None
        emit("workflow.claimed", run_id=run["id"], stage=run["status"])
        if run["status"] == "queued":
            try:
                result = self.evidence.answer(run["tenant_id"], run["question"])
                brief = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
                if brief.get("status") != "answered" or not brief.get("citations"):
                    return self.store.checkpoint(
                        run, "needs_review", brief=brief, error_code="insufficient_evidence"
                    )
                return self.store.checkpoint(run, "researched", brief=brief)
            except StateError:
                raise
            except Exception:
                return self.store.checkpoint(run, "failed", error_code="evidence_failed")
        if run["status"] == "researched":
            draft = {"destination": "fake://outbox", "text": run["brief"]["answer"][:20000]}
            return self.store.checkpoint(run, "awaiting_approval", draft=draft)
        current = self.store.get_run(run["tenant_id"], run["actor_id"], run["id"])
        action = current["action"]
        if run["status"] == "ready":
            if not self.authorize(run["tenant_id"], run["actor_id"], "deliver"):
                return self.store.delivery_result(run, action, "denied")
            try:
                action, run = self.store.begin_dispatch(run)
            except StateError as exc:
                if exc.code == "invalid_approval":
                    return self.store.checkpoint(run, "failed", error_code=exc.code)
                raise
        else:
            try:
                receipt = self.provider.lookup(action["id"])
            except Exception:
                return self.store.delivery_result(run, action, "unknown")
            if receipt is not None:
                return self.store.delivery_result(run, action, "sent", receipt)
            if not self.authorize(run["tenant_id"], run["actor_id"], "deliver"):
                return self.store.delivery_result(run, action, "denied")
            if not self.provider.idempotent:
                return self.store.delivery_result(run, action, "unknown")
            if run["attempts"] >= self.max_attempts:
                return self.store.delivery_result(
                    run, action, "retry", max_attempts=self.max_attempts
                )
            run = self.store.retry_dispatch(run)
        # Revocation can occur after approval. This check is intentionally outside prompts.
        if not self.authorize(run["tenant_id"], run["actor_id"], "deliver"):
            return self.store.delivery_result(run, action, "denied")
        try:
            receipt = self.provider.deliver(action["id"], action["payload"])
            if self.crash_after_send:
                raise WorkerCrash()
            return self.store.delivery_result(run, action, "sent", receipt)
        except RetryableDeliveryError:
            return self.store.delivery_result(run, action, "retry", max_attempts=self.max_attempts)
        except StateError:
            raise
        except Exception:
            return self.store.delivery_result(run, action, "uncertain")
