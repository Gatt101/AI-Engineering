"""Authoritative state, fenced worker leases, and approval-bound fake delivery.

No chat history or model output can authorize delivery. Adapter execution happens
outside transactions. Ambiguous outcomes are reconciled, never blindly resent.
"""

import hashlib
import json
import time
from collections.abc import Callable
from uuid import uuid4

from research_sdk.telemetry import emit
from sqlalchemy import and_, func, insert, or_, select, text, update
from sqlalchemy.exc import IntegrityError

from research_state.db import actions, approvals, attempts, audit_events, runs


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class StateError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409):
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


def owned(table, tenant_id, actor_id, item_id):
    return and_(table.c.id == item_id, table.c.tenant_id == tenant_id, table.c.actor_id == actor_id)


class WorkflowStore:
    def __init__(self, engine, *, clock: Callable[[], float] = time.time):
        self.engine, self.clock = engine, clock

    def _event(self, connection, run_id, event):
        connection.execute(
            insert(audit_events).values(
                id=str(uuid4()), run_id=run_id, event=event, created_at=self.clock()
            )
        )

    def create_run(self, tenant_id, actor_id, question, idempotency_key, max_pending=100):
        if not (1 <= len(question.strip()) <= 8000 and 1 <= len(idempotency_key) <= 128):
            raise StateError("invalid_request", "Invalid question or idempotency key", 422)
        request_hash = digest({"question": question})
        values = dict(
            id=str(uuid4()),
            tenant_id=tenant_id,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            question=question,
            status="queued",
            version=1,
            brief=None,
            draft=None,
            attempts=0,
            lease_owner=None,
            lease_until=None,
            error_code=None,
            created_at=self.clock(),
            updated_at=self.clock(),
        )
        try:
            with self.engine.begin() as connection:
                # Serialize admission per tenant (all writers for SQLite). Quota and
                # insert share the transaction, so concurrent submissions cannot race it.
                if self.engine.dialect.name == "postgresql":
                    lock_key = int.from_bytes(
                        hashlib.sha256(tenant_id.encode()).digest()[:8], "big", signed=True
                    )
                    connection.execute(
                        text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key}
                    )
                elif self.engine.dialect.name == "sqlite":
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                existing = (
                    connection.execute(
                        select(runs).where(
                            runs.c.tenant_id == tenant_id,
                            runs.c.actor_id == actor_id,
                            runs.c.idempotency_key == idempotency_key,
                        )
                    )
                    .mappings()
                    .first()
                )
                if existing:
                    if existing["request_hash"] != request_hash:
                        raise StateError(
                            "idempotency_conflict", "Key already used for a different request"
                        )
                    return dict(existing)
                pending = connection.execute(
                    select(func.count())
                    .select_from(runs)
                    .where(
                        runs.c.tenant_id == tenant_id,
                        runs.c.status.not_in(["completed", "failed", "cancelled", "rejected"]),
                    )
                ).scalar_one()
                if pending >= max_pending:
                    raise StateError("queue_full", "Tenant pending-run budget reached", 429)
                connection.execute(insert(runs).values(**values))
                self._event(connection, values["id"], "run.created")
            emit("workflow.created", run_id=values["id"], outcome="queued")
            return values
        except IntegrityError:
            with self.engine.connect() as connection:
                existing = (
                    connection.execute(
                        select(runs).where(
                            runs.c.tenant_id == tenant_id,
                            runs.c.actor_id == actor_id,
                            runs.c.idempotency_key == idempotency_key,
                        )
                    )
                    .mappings()
                    .first()
                )
            if existing is None:
                raise
            if existing["request_hash"] != request_hash:
                raise StateError("idempotency_conflict", "Key already used for a different request")
            return dict(existing)

    def get_run(self, tenant_id, actor_id, run_id):
        with self.engine.connect() as connection:
            row = (
                connection.execute(select(runs).where(owned(runs, tenant_id, actor_id, run_id)))
                .mappings()
                .first()
            )
            if row is None:
                raise StateError("not_found", "Run not found", 404)
            result = dict(row)
            action = (
                connection.execute(select(actions).where(actions.c.run_id == run_id))
                .mappings()
                .first()
            )
            result["action"] = dict(action) if action else None
            return result

    def list_runs(self, tenant_id, actor_id, limit=50):
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(runs)
                .where(
                    runs.c.tenant_id == tenant_id,
                    runs.c.actor_id == actor_id,
                )
                .order_by(runs.c.created_at.desc())
                .limit(min(max(limit, 1), 100))
            ).mappings()
            return [dict(row) for row in rows]

    def get_action(self, tenant_id, actor_id, action_id):
        with self.engine.connect() as connection:
            return self._action(connection, tenant_id, actor_id, action_id)

    def _action(self, connection, tenant_id, actor_id, action_id):
        row = (
            connection.execute(
                select(actions).where(owned(actions, tenant_id, actor_id, action_id))
            )
            .mappings()
            .first()
        )
        if row is None:
            raise StateError("not_found", "Action not found", 404)
        return dict(row)

    def audit(self, tenant_id, actor_id, run_id):
        self.get_run(tenant_id, actor_id, run_id)
        with self.engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(audit_events)
                    .where(audit_events.c.run_id == run_id)
                    .order_by(audit_events.c.created_at, audit_events.c.id)
                ).mappings()
            ]

    def approve(self, tenant_id, actor_id, action_id, expected_version, expires_in_seconds=300):
        if not 1 <= expires_in_seconds <= 3600:
            raise StateError("invalid_expiry", "Approval lifetime must be 1-3600 seconds", 422)
        with self.engine.begin() as connection:
            action = self._action(connection, tenant_id, actor_id, action_id)
            changed = connection.execute(
                update(actions)
                .where(
                    owned(actions, tenant_id, actor_id, action_id),
                    actions.c.version == expected_version,
                    actions.c.status == "pending",
                )
                .values(status="approved")
            )
            if changed.rowcount != 1:
                raise StateError("stale_action", "Action is stale or no longer awaiting approval")
            approval = dict(
                id=str(uuid4()),
                action_id=action_id,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action_version=expected_version,
                payload_hash=action["payload_hash"],
                expires_at=self.clock() + expires_in_seconds,
                consumed=False,
                created_at=self.clock(),
            )
            connection.execute(insert(approvals).values(**approval))
            changed = connection.execute(
                update(runs)
                .where(
                    runs.c.id == action["run_id"],
                    runs.c.status == "awaiting_approval",
                )
                .values(status="ready", version=runs.c.version + 1, updated_at=self.clock())
            )
            if changed.rowcount != 1:
                raise StateError("invalid_state", "Run no longer accepts approval")
            self._event(connection, action["run_id"], "action.approved")
        return approval

    def revise_action(self, tenant_id, actor_id, action_id, expected_version, payload):
        if (
            set(payload) != {"destination", "text"}
            or payload["destination"] != "fake://outbox"
            or not isinstance(payload["text"], str)
            or not 1 <= len(payload["text"]) <= 20000
        ):
            raise StateError("invalid_payload", "Only bounded fake-outbox drafts are allowed", 422)
        with self.engine.begin() as connection:
            action = self._action(connection, tenant_id, actor_id, action_id)
            changed = connection.execute(
                update(actions)
                .where(
                    owned(actions, tenant_id, actor_id, action_id),
                    actions.c.version == expected_version,
                    actions.c.status.in_(["pending", "approved"]),
                )
                .values(
                    payload=payload,
                    payload_hash=digest(payload),
                    version=expected_version + 1,
                    status="pending",
                )
            )
            if changed.rowcount != 1:
                raise StateError("stale_action", "Action is stale or already executing")
            changed = connection.execute(
                update(runs)
                .where(
                    runs.c.id == action["run_id"],
                    runs.c.status.in_(["ready", "awaiting_approval"]),
                    or_(runs.c.lease_until.is_(None), runs.c.lease_until <= self.clock()),
                )
                .values(
                    status="awaiting_approval",
                    draft=payload,
                    version=runs.c.version + 1,
                    updated_at=self.clock(),
                )
            )
            if changed.rowcount != 1:
                raise StateError("busy", "A worker already owns this action")
            self._event(connection, action["run_id"], "action.revised")
        return self.get_action(tenant_id, actor_id, action_id)

    def reject(self, tenant_id, actor_id, action_id, expected_version):
        with self.engine.begin() as connection:
            action = self._action(connection, tenant_id, actor_id, action_id)
            changed = connection.execute(
                update(actions)
                .where(
                    owned(actions, tenant_id, actor_id, action_id),
                    actions.c.version == expected_version,
                    actions.c.status.in_(["pending", "approved"]),
                )
                .values(status="rejected", version=actions.c.version + 1)
            )
            if changed.rowcount != 1:
                raise StateError("stale_action", "Action is stale or already executing")
            changed = connection.execute(
                update(runs)
                .where(
                    runs.c.id == action["run_id"],
                    runs.c.status.in_(["awaiting_approval", "ready"]),
                    or_(runs.c.lease_until.is_(None), runs.c.lease_until <= self.clock()),
                )
                .values(status="rejected", version=runs.c.version + 1, updated_at=self.clock())
            )
            if changed.rowcount != 1:
                raise StateError("busy", "A worker already owns this action")
            self._event(connection, action["run_id"], "action.rejected")
        return self.get_run(tenant_id, actor_id, action["run_id"])

    def cancel(self, tenant_id, actor_id, run_id, expected_version):
        with self.engine.begin() as connection:
            changed = connection.execute(
                update(runs)
                .where(
                    owned(runs, tenant_id, actor_id, run_id),
                    runs.c.version == expected_version,
                    runs.c.status.in_(["queued", "researched", "awaiting_approval", "ready"]),
                    or_(runs.c.lease_until.is_(None), runs.c.lease_until <= self.clock()),
                )
                .values(status="cancelled", version=runs.c.version + 1, updated_at=self.clock())
            )
            if changed.rowcount != 1:
                raise StateError("stale_run", "Run is stale, busy, or cannot be cancelled")
            connection.execute(
                update(actions).where(actions.c.run_id == run_id).values(status="cancelled")
            )
            self._event(connection, run_id, "run.cancelled")
        return self.get_run(tenant_id, actor_id, run_id)

    def claim(self, worker_id, lease_seconds=30, tenant_id=None, actor_id=None, run_id=None):
        eligible = [
            runs.c.status.in_(["queued", "researched", "ready", "dispatching", "reconcile"]),
            or_(runs.c.lease_until.is_(None), runs.c.lease_until <= self.clock()),
        ]
        for column, value in (
            (runs.c.tenant_id, tenant_id),
            (runs.c.actor_id, actor_id),
            (runs.c.id, run_id),
        ):
            if value is not None:
                eligible.append(column == value)
        with self.engine.begin() as connection:
            statement = select(runs).where(*eligible).order_by(runs.c.created_at).limit(1)
            if self.engine.dialect.name == "postgresql":
                statement = statement.with_for_update(skip_locked=True)
            row = connection.execute(statement).mappings().first()
            if row is None:
                return None
            changed = connection.execute(
                update(runs)
                .where(
                    runs.c.id == row["id"],
                    runs.c.version == row["version"],
                    *eligible,
                )
                .values(
                    lease_owner=worker_id,
                    lease_until=self.clock() + lease_seconds,
                    version=runs.c.version + 1,
                    updated_at=self.clock(),
                )
            )
            if changed.rowcount != 1:
                return None
            return dict(row) | {
                "lease_owner": worker_id,
                "lease_until": self.clock() + lease_seconds,
                "version": row["version"] + 1,
            }

    def _fence(self, run):
        return and_(
            runs.c.id == run["id"],
            runs.c.version == run["version"],
            runs.c.lease_owner == run["lease_owner"],
            runs.c.lease_until > self.clock(),
        )

    def checkpoint(self, run, status, *, brief=None, draft=None, error_code=None):
        values = dict(
            status=status,
            version=runs.c.version + 1,
            lease_owner=None,
            lease_until=None,
            updated_at=self.clock(),
            error_code=error_code,
        )
        if brief is not None:
            values["brief"] = brief
        if draft is not None:
            values["draft"] = draft
        with self.engine.begin() as connection:
            changed = connection.execute(update(runs).where(self._fence(run)).values(**values))
            if changed.rowcount != 1:
                raise StateError("lease_lost", "Worker lease expired or was replaced")
            if draft is not None:
                connection.execute(
                    insert(actions).values(
                        id=str(uuid4()),
                        run_id=run["id"],
                        tenant_id=run["tenant_id"],
                        actor_id=run["actor_id"],
                        payload=draft,
                        payload_hash=digest(draft),
                        version=1,
                        status="pending",
                        created_at=self.clock(),
                    )
                )
            self._event(connection, run["id"], f"run.{status}")
        emit("workflow.checkpoint", run_id=run["id"], outcome=status, version=run["version"] + 1)
        return self.get_run(run["tenant_id"], run["actor_id"], run["id"])

    def begin_dispatch(self, run):
        with self.engine.begin() as connection:
            action = (
                connection.execute(select(actions).where(actions.c.run_id == run["id"]))
                .mappings()
                .one()
            )
            approval = (
                connection.execute(
                    select(approvals).where(
                        approvals.c.action_id == action["id"],
                        approvals.c.action_version == action["version"],
                        approvals.c.tenant_id == run["tenant_id"],
                        approvals.c.actor_id == run["actor_id"],
                    )
                )
                .mappings()
                .first()
            )
            if (
                not approval
                or approval["consumed"]
                or approval["expires_at"] <= self.clock()
                or approval["payload_hash"] != digest(action["payload"])
                or action["payload_hash"] != approval["payload_hash"]
                or action["status"] != "approved"
            ):
                raise StateError(
                    "invalid_approval", "Approval expired, consumed, or does not match action"
                )
            changed = connection.execute(
                update(runs)
                .where(self._fence(run), runs.c.status == "ready")
                .values(
                    status="dispatching",
                    version=runs.c.version + 1,
                    attempts=runs.c.attempts + 1,
                    updated_at=self.clock(),
                )
            )
            if changed.rowcount != 1:
                raise StateError("lease_lost", "Worker lease expired or was replaced")
            connection.execute(
                update(approvals).where(approvals.c.id == approval["id"]).values(consumed=True)
            )
            connection.execute(
                update(actions).where(actions.c.id == action["id"]).values(status="dispatching")
            )
            self._event(connection, run["id"], "action.dispatching")
        emit("action.dispatching", run_id=run["id"], action_id=action["id"])
        return dict(action), run | {
            "status": "dispatching",
            "version": run["version"] + 1,
            "attempts": run["attempts"] + 1,
        }

    def delivery_result(self, run, action, outcome, receipt=None, max_attempts=3):
        status = {
            "sent": "completed",
            "uncertain": "reconcile",
            "unknown": "manual_review",
            "denied": "failed",
            "retry": "reconcile",
        }[outcome]
        if outcome == "retry" and run["attempts"] >= max_attempts:
            status = "failed"
        with self.engine.begin() as connection:
            changed = connection.execute(
                update(runs)
                .where(self._fence(run))
                .values(
                    status=status,
                    version=runs.c.version + 1,
                    lease_owner=None,
                    lease_until=None,
                    error_code=None
                    if outcome == "sent"
                    else (
                        "retries_exhausted"
                        if status == "failed" and outcome == "retry"
                        else outcome
                    ),
                    updated_at=self.clock(),
                )
            )
            if changed.rowcount != 1:
                raise StateError("lease_lost", "Worker lease expired or was replaced")
            connection.execute(
                update(actions)
                .where(actions.c.id == action["id"])
                .values(status=status, receipt=receipt)
            )
            connection.execute(
                insert(attempts).values(
                    id=str(uuid4()),
                    action_id=action["id"],
                    outcome=outcome,
                    created_at=self.clock(),
                )
            )
            self._event(connection, run["id"], f"action.{outcome}")
        emit("action.result", run_id=run["id"], action_id=action["id"], outcome=outcome)
        return self.get_run(run["tenant_id"], run["actor_id"], run["id"])

    def retry_dispatch(self, run):
        with self.engine.begin() as connection:
            changed = connection.execute(
                update(runs)
                .where(self._fence(run))
                .values(
                    status="dispatching",
                    attempts=runs.c.attempts + 1,
                    version=runs.c.version + 1,
                )
            )
            if changed.rowcount != 1:
                raise StateError("lease_lost", "Worker lease expired or was replaced")
        return run | {
            "status": "dispatching",
            "attempts": run["attempts"] + 1,
            "version": run["version"] + 1,
        }
